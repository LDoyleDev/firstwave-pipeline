"""Recover hotel website URLs the enrichment pipeline dropped.

`enrich_leads_haiku.py` read each lead's `website` but never persisted it, so
email sourcing has nothing to scrape. This module re-matches existing leads to
the raw scrape JSON files by hotel name + address, and upserts the recovered
website into the `companies` table so the data is durable from now on.

The normalisation helpers are pure (no DB) and unit-testable anywhere; only
`upsert_company_for_lead` and `run_osm_refresh` touch Supabase / the OS, and
they import lazily so this module loads cleanly in a stub environment.
"""

import glob
import json
import logging
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from backend.integrations.website_fetch import site_domain

logger = logging.getLogger(__name__)

# Where raw scrape output may sit — globbed under the repo root and $HOME.
_SCRAPE_GLOBS = ("data/phase2/*.json", "data/phase2_batch_*.json", "data/*phase2*.json")

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalise_name(name: str | None) -> str:
    """Lowercase, de-accent, drop punctuation, collapse whitespace."""
    if not name:
        return ""
    s = _strip_accents(str(name)).lower()
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def normalise_addr(addr: str | None) -> str:
    """Normalise an address for matching — same rules as a name."""
    return normalise_name(addr)


def lead_address(location: str | None) -> str:
    """The address part of a lead `location` — the scrape stores location as
    '{address}, {country}', so drop the final comma-field."""
    if not location:
        return ""
    return location.rsplit(",", 1)[0].strip() if "," in location else location.strip()


def extract_city(text: str | None, drop_last: bool = False) -> str:
    """Best-effort city from a comma-delimited address/location string.

    drop_last=True (a lead `location`, which ends with the country) → take the
    second-to-last field. Otherwise (a scrape `address`) → take the last field.
    """
    if not text:
        return ""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return ""
    if drop_last and len(parts) >= 2:
        return normalise_name(parts[-2])
    return normalise_name(parts[-1])


def lead_keys(lead: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    """(exact_key, fuzzy_key) for a lead. exact = (name, address);
    fuzzy = (name, city). Uses enrichment_data.raw_name — the original scraped
    hotel name (first/last_name are hotel-name fragments, unusable)."""
    enr = lead.get("enrichment_data") or {}
    raw_name = enr.get("raw_name") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}"
    loc = lead.get("location") or ""
    name = normalise_name(raw_name)
    return (
        (name, normalise_addr(lead_address(loc))),
        (name, extract_city(loc, drop_last=True)),
    )


def scrape_keys(rec: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    """(exact_key, fuzzy_key) for a raw scrape record."""
    name = normalise_name(rec.get("name"))
    addr = rec.get("address") or ""
    return (
        (name, normalise_addr(addr)),
        (name, extract_city(addr, drop_last=False)),
    )


def load_scrape_records(repo_root: str | Path = ".") -> list[dict]:
    """Load every raw scrape JSON found under the repo root and $HOME.

    Each file is either {"leads": [...]} or a bare list. Records are returned
    as-is (expected keys: name, address, country, website, email, osm_type,
    osm_id). Returns [] if no files exist — the caller then falls back to OSM.
    """
    roots = [Path(repo_root), Path.home()]
    seen_files: set[str] = set()
    records: list[dict] = []
    for root in roots:
        for pattern in _SCRAPE_GLOBS:
            for path in glob.glob(str(root / pattern)):
                if path in seen_files:
                    continue
                seen_files.add(path)
                try:
                    data = json.loads(Path(path).read_text())
                except Exception as e:
                    logger.warning("could not read scrape file %s (%s)", path, e)
                    continue
                rows = data.get("leads") if isinstance(data, dict) else data
                if isinstance(rows, list):
                    records.extend(r for r in rows if isinstance(r, dict) and r.get("name"))
    logger.info("loaded %d scrape records from %d files", len(records), len(seen_files))
    return records


def build_indexes(records: list[dict]) -> tuple[dict, dict]:
    """Build (exact_index, fuzzy_index) from scrape records. First record wins
    on a key collision."""
    exact: dict[tuple[str, str], dict] = {}
    fuzzy: dict[tuple[str, str], dict] = {}
    for rec in records:
        ek, fk = scrape_keys(rec)
        if ek[0] and ek[1]:
            exact.setdefault(ek, rec)
        if fk[0] and fk[1]:
            fuzzy.setdefault(fk, rec)
    return exact, fuzzy


def match_lead(lead: dict, exact_idx: dict, fuzzy_idx: dict) -> tuple[dict | None, str]:
    """Match a lead to a scrape record. Returns (record_or_None, method) where
    method is 'exact' | 'fuzzy_name_city' | 'none'. The fuzzy path is
    deliberately conservative — exact normalised name AND exact city — because a
    wrong website poisons every downstream tier."""
    ek, fk = lead_keys(lead)
    if ek[0] and ek[1] and ek in exact_idx:
        return exact_idx[ek], "exact"
    if fk[0] and fk[1] and fk in fuzzy_idx:
        return fuzzy_idx[fk], "fuzzy_name_city"
    return None, "none"


def osm_permalink(rec: dict) -> str | None:
    """openstreetmap.org permalink for a scrape record that carries OSM identity."""
    osm_type, osm_id = rec.get("osm_type"), rec.get("osm_id")
    if osm_type and osm_id:
        return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
    return None


def run_osm_refresh(iso_codes: list[str], out_path: str, repo_root: str | Path = ".") -> str | None:
    """Run scripts/scrape_osm.py for the given ISO countries. Returns the output
    path on success, else None. Used as the Tier-1 fallback when scrape JSONs
    are absent or a lead did not match."""
    codes = sorted({c.strip().upper() for c in iso_codes if c and c.strip()})
    if not codes:
        return None
    cmd = [sys.executable, "scripts/scrape_osm.py",
           "--countries", ",".join(codes), "--output", out_path]
    logger.info("OSM refresh: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=str(repo_root), check=True, timeout=3600)
    except Exception as e:
        logger.warning("OSM refresh failed (%s)", e)
        return None
    return out_path if os.path.exists(os.path.join(str(repo_root), out_path)) else None


def upsert_company_for_lead(lead_id: str, name: str, website: str) -> str | None:
    """Upsert a `companies` row for a recovered website and link the lead to it.

    Dedups on lower(domain). Returns the company_id, or None on failure. Imports
    Supabase lazily so the pure helpers above stay importable in a stub env.
    """
    from backend.integrations.supabase_client import supabase  # noqa: PLC0415

    domain = site_domain(website)
    try:
        company_id: str | None = None
        if domain:
            existing = (
                supabase.table("companies").select("id")
                .eq("domain", domain).limit(1).execute()
            )
            if existing.data:
                company_id = existing.data[0]["id"]
        if company_id is None:
            inserted = supabase.table("companies").insert({
                "name": name or domain or "Unknown",
                "website": website,
                "domain": domain,
            }).execute()
            company_id = inserted.data[0]["id"]
        supabase.table("leads").update({"company_id": company_id}).eq("id", lead_id).execute()
        return company_id
    except Exception:
        logger.exception("companies upsert failed for lead %s", lead_id)
        return None
