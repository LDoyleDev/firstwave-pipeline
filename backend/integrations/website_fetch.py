"""Polite async multi-page website fetch for email sourcing.

Fetches a hotel's homepage + likely contact pages as RAW HTML — `mailto:` hrefs
must survive, so this deliberately does NOT reuse
`web_researcher.scrape_website_text` (which strips all tags). `robots.txt` is
fetched and honoured: only permitted paths are retrieved.
"""

import logging
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# A real browser UA — many hotel sites 403 an obvious bot. robots.txt is still
# honoured below, so this is polite, not evasive.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en;q=0.9",
}

# Contact-bearing paths, tried in priority order — homepage ("") always first.
_BASE_PATHS = ("", "/contact", "/contact-us", "/contacts", "/about", "/about-us")
# DACH sites publish contact details on an Impressum / Kontakt page.
_EU_PATHS = ("/impressum", "/imprint", "/kontakt")
_EU_ISO = {"DE", "AT", "CH", "LU", "LI"}

_ROBOTS_UA = "firstwave-pipeline"


def _normalise_base(website: str) -> str | None:
    """Coerce a stored website value into a fetchable scheme://host base URL."""
    w = (website or "").strip()
    if not w:
        return None
    if not w.startswith(("http://", "https://")):
        w = "https://" + w
    parsed = urlparse(w)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def site_domain(website: str) -> str | None:
    """The bare domain (no scheme, no www, no path) of a website value."""
    base = _normalise_base(website)
    if not base:
        return None
    host = urlparse(base).netloc.lower()
    return host[4:] if host.startswith("www.") else host


async def _load_robots(client: httpx.AsyncClient, base: str) -> urllib.robotparser.RobotFileParser:
    """Fetch + parse robots.txt. A missing/unreadable robots.txt = allow all."""
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = await client.get(urljoin(base, "/robots.txt"))
        if resp.status_code == 200 and resp.text:
            rp.parse(resp.text.splitlines())
        else:
            rp.allow_all = True
    except Exception:
        rp.allow_all = True
    return rp


async def fetch_site(
    client: httpx.AsyncClient,
    website: str,
    country_iso: str | None = None,
) -> dict:
    """Fetch a hotel site's contact-bearing pages as raw HTML.

    Returns {"base": str|None, "domain": str|None, "pages": {final_url: html}}.
    Only `robots.txt`-permitted paths are fetched, so every page in `pages` is
    robots-allowed. `pages` is empty on any failure — callers treat that as
    "no email found", never as an error.
    """
    base = _normalise_base(website)
    result: dict = {"base": base, "domain": None, "pages": {}}
    if not base:
        return result
    result["domain"] = site_domain(website)

    paths = list(_BASE_PATHS)
    if country_iso and country_iso.upper() in _EU_ISO:
        paths += list(_EU_PATHS)

    rp = await _load_robots(client, base)

    for path in paths:
        url = urljoin(base, path)
        if not rp.can_fetch(_ROBOTS_UA, url):
            logger.debug("robots.txt disallows %s — skipping", url)
            continue
        try:
            resp = await client.get(url)
        except Exception as e:
            logger.debug("fetch failed %s (%s)", url, e.__class__.__name__)
            continue
        ctype = resp.headers.get("content-type", "text/html")
        if resp.status_code == 200 and "html" in ctype.lower():
            result["pages"][str(resp.url)] = resp.text

    return result
