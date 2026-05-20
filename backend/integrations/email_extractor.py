"""Email extraction, junk filtering, scoring, and opt-out-disclaimer detection.

Pure functions — no DB, no network, no LLM — so this module imports and
unit-tests anywhere. The Tier-3 website scrape feeds raw HTML in; this module
decides which address (if any) is the hotel's publishable business contact, and
flags pages that carry a "no unsolicited email" statement.
"""

import re

# Address pattern: local@label(.label)+. Junk is filtered separately by is_junk.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
_MAILTO_RE = re.compile(r"mailto:([^\"'?\s>]+)", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"\s+")

# Role / shared-mailbox local-parts — a published business contact, not a
# person. Parallel to provenance._GENERIC_LOCALPARTS; kept local so this module
# stays import-pure. The orchestrator passes address_type to set_lead_email.
GENERIC_LOCALPARTS = {
    "info", "contact", "contacts", "reservations", "reservation", "reservierung",
    "hotel", "booking", "bookings", "stay", "mail", "email", "office", "reception",
    "frontdesk", "front.desk", "frontoffice", "hello", "hallo", "enquiries",
    "enquiry", "inquiries", "sales", "admin", "welcome", "rooms", "book", "gm",
    "manager", "management", "concierge", "guest", "guestservices", "kontakt",
    "empfang", "rezeption",
}

# Local-parts that are never a usable contact.
_JUNK_LOCALPARTS = {
    "noreply", "no-reply", "no.reply", "donotreply", "do-not-reply", "do.not.reply",
    "mailer-daemon", "mailerdaemon", "postmaster", "abuse", "bounce", "bounces",
}

# Domains that are not a real business mailbox — placeholders, SaaS infra,
# analytics, schema/standards hosts.
_JUNK_DOMAINS = {
    "example.com", "example.org", "example.net", "domain.com", "yourdomain.com",
    "yoursite.com", "yourhotel.com", "email.com", "test.com", "sentry.io",
    "sentry.wixpress.com", "sentry-next.wixpress.com", "wix.com", "wixpress.com",
    "squarespace.com", "godaddy.com", "schema.org", "w3.org", "googleapis.com",
    "gstatic.com", "cloudflare.com", "jquery.com", "fontawesome.com",
    "placeholder.com",
}

_IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|svg|ico|bmp|tiff?)$", re.IGNORECASE)

# Free webmail providers — acceptable only as a last resort.
FREE_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "yahoo.fr",
    "hotmail.com", "hotmail.co.uk", "hotmail.fr", "outlook.com", "live.com",
    "aol.com", "icloud.com", "me.com", "gmx.de", "gmx.net", "gmx.com", "web.de",
    "t-online.de", "orange.fr", "free.fr", "wanadoo.fr", "libero.it", "mail.ru",
    "protonmail.com", "proton.me",
}

# Opt-out disclaimer phrases — kept TIGHT (high precision). The Haiku confirm
# step is the recall backstop for paraphrased wording.
_OPTOUT_PHRASES = (
    "no unsolicited", "unsolicited commercial", "unsolicited email",
    "unsolicited e-mail", "unsolicited messages", "not accept unsolicited",
    "do not wish to receive", "no marketing email", "no marketing emails",
    "do not add us to", "not be added to any mailing", "no sales solicitation",
    "do not contact us for marketing", "do not send us marketing",
    "no cold email", "no cold emails",
)


def _norm_domain(domain: str | None) -> str:
    """Lowercase and strip a leading www. — for comparing an email domain to a site."""
    d = (domain or "").strip().lower()
    return d[4:] if d.startswith("www.") else d


def html_to_text(html: str) -> str:
    """Strip scripts/styles/tags and collapse whitespace — for the disclaimer
    scan, context snippets, and the Haiku-confirm input."""
    no_scripts = _SCRIPT_STYLE_RE.sub(" ", html or "")
    text = _TAG_RE.sub(" ", no_scripts)
    return _WS_RE.sub(" ", text).strip()


def page_title(html: str) -> str | None:
    """The page <title>, cleaned, or None."""
    m = _TITLE_RE.search(html or "")
    if not m:
        return None
    return _WS_RE.sub(" ", _TAG_RE.sub("", m.group(1))).strip() or None


def is_junk(email: str) -> bool:
    """True if the address can never be a usable published business contact."""
    e = (email or "").strip().lower()
    if "@" not in e:
        return True
    local, _, domain = e.partition("@")
    if not local or not domain or "." not in domain:
        return True
    if _IMAGE_EXT_RE.search(e):
        return True
    if local in _JUNK_LOCALPARTS:
        return True
    if _norm_domain(domain) in _JUNK_DOMAINS:
        return True
    # Long all-hex local-part — a tracking / Sentry-key style string, not a mailbox.
    if len(local) >= 24 and re.fullmatch(r"[0-9a-f]+", local):
        return True
    return False


def extract_emails(html: str, page_url: str = "") -> list[str]:
    """Every plausible address on a page — mailto: hrefs + body/JSON-LD regex.
    Lowercased, deduped, junk removed. mailto: hits come first (highest intent)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in _MAILTO_RE.findall(html or "") + EMAIL_RE.findall(html or ""):
        e = raw.strip().lower().rstrip(".")
        if e in seen or is_junk(e):
            continue
        seen.add(e)
        ordered.append(e)
    return ordered


def classify_address_type(email: str) -> str:
    """generic_role vs named_individual, from the local-part."""
    local = email.split("@")[0].strip().lower()
    return "generic_role" if local in GENERIC_LOCALPARTS else "named_individual"


def score_email(email: str, hotel_domain: str | None) -> int:
    """Rank a candidate — higher = more likely the hotel's own published contact."""
    if is_junk(email):
        return -1000
    local, _, domain = email.lower().partition("@")
    ed = _norm_domain(domain)
    hd = _norm_domain(hotel_domain) if hotel_domain else None
    score = 0
    if hd and ed == hd:
        score += 100
    elif ed in FREE_PROVIDERS:
        score += 10
    elif hd:
        # Third-party domain when the hotel's own domain is known — almost
        # certainly a web agency / booking platform, not the hotel. Penalise
        # hard so the generic-role bonus below cannot rescue it.
        score -= 200
    if local in GENERIC_LOCALPARTS:
        score += 40
    return score


def best_email(candidates: list[str], hotel_domain: str | None) -> tuple[str, str] | None:
    """Pick the strongest candidate. Returns (email, address_type), or None if
    nothing scores as a plausible business contact."""
    best: tuple[int, str] | None = None
    for e in candidates:
        s = score_email(e, hotel_domain)
        if best is None or s > best[0]:
            best = (s, e)
    if best is None or best[0] < 0:
        return None
    return best[1], classify_address_type(best[1])


def find_optout_disclaimer(text: str) -> str | None:
    """Return the first opt-out phrase found in the page text, else None.
    Deterministic high-precision screen; the Haiku confirm is the recall backstop."""
    low = (text or "").lower()
    for phrase in _OPTOUT_PHRASES:
        if phrase in low:
            return phrase
    return None


def context_snippet(text: str, email: str, width: int = 200) -> str:
    """The text surrounding the address on the page — evidence of where and how
    it was published. Empty if the address appears only in markup, not in text."""
    low = text.lower()
    idx = low.find(email.lower())
    if idx == -1:
        return ""
    start = max(0, idx - width)
    end = min(len(text), idx + len(email) + width)
    return _WS_RE.sub(" ", text[start:end]).strip()
