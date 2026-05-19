# Next Lead Sources Overview

**Current state**: 695 verified candidates from Phase 2 (Wikipedia + directories)
**Gap to target**: 305 leads (to reach 1000)
**Date**: 2026-05-18

---

## What Worked & What Didn't

### Worked ✅
| Source | Yield | Notes |
|--------|-------|-------|
| Wikipedia "Category:Hotels_in_X" | 700+ | Reliable, structured, free, no auth |
| Haiku JSON extraction | 95%+ valid | Ollama gpt-oss:20b → reliable |
| Multi-shell parallel | 10 shells | No conflicts, clean dedup |

### Didn't work ❌
| Source | Issue |
|--------|-------|
| Relais & Châteaux directory | JS-heavy, blocks scrapers |
| Small Luxury Hotels | Same — needs headless browser |
| Michelin Guide hotels | Anti-bot detection |
| Chamber of Commerce sites | 403 Forbidden on most |
| OpenCorporates API | Requires API key |
| Wikipedia "List_of_hotels_in_X" | Page format doesn't exist |

---

## Option Catalogue — Ranked by ROI

### Tier 1: Highest yield, lowest effort

#### A) Expand country approval list — **+56 leads instantly**
**Cost**: 0 effort | **Yield**: Already scraped, filtered out
**Action**: Edit `scripts/screening_filter.py` `APPROVED_COUNTRIES` to include Turkey (20), Serbia (8), Croatia (6), Bulgaria (4), Cyprus (2), Romania (1), Slovenia (1). These are Mediterranean/European hospitality markets worth targeting.

#### B) More Wikipedia regions — **+200-300 leads, 30-45 min**
**Cost**: ~$0.50 Haiku | **Yield**: 200-300
**Coverage**: Asia (Tokyo, Singapore, Hong Kong, Bangkok, Bali, Seoul, Kyoto, Shanghai), Oceania (Sydney, Melbourne, Auckland), LATAM (Mexico City, Buenos Aires, Rio, Cancun)
**How**: Add shell_11_asia.json, shell_12_oceania_latam.json with `Category:Hotels_in_<city>`. Run via existing `scrape_haiku_coordinator.sh`.

#### C) More Wikipedia US states — **+150-200 leads**
**Cost**: ~$0.30 | **Yield**: 150-200
**Coverage**: We hit major metros + 6 states. Untapped: Hawaii (resorts), Colorado (ski), Arizona (resorts), Tennessee (Nashville), Washington (Seattle), Oregon (Portland), Georgia (Atlanta), North Carolina, Virginia.

### Tier 2: Medium effort, free

#### D) OpenStreetMap "tourism=hotel" — **1000+ globally**
**Cost**: 0 (free Overpass API) | **Yield**: Massive
**Effort**: 1-2 hours to write extractor
**Data**: name, lat/lon, address, phone, website, often star rating
**How**: Query Overpass API: `[out:json];node[tourism=hotel](bbox);out;` for each city bounding box
**Quality**: Real operational hotels (community-verified), great phone/website coverage

#### E) Bulk registry downloads — **2000-3000+**
| Source | Format | Size | Yield |
|--------|--------|------|-------|
| Companies House UK | CSV | 2GB | ~2000 |
| Bundesanzeiger (DE) | CSV | 500MB | ~1500 |
| BORME (ES) | XML | 200MB | ~500 |
| SIRENE (FR) | CSV | 5GB | ~3000 |

**Effort**: 2-3 hours to download + parse + filter by SIC/NACE codes (hotels = 5510)
**No auth needed**, just bulk download from gov sites

### Tier 3: Free with registration

#### F) Free API keys — **2500+ leads combined**
| API | Registration | Yield |
|-----|--------------|-------|
| OpenCorporates | Sign up (free) | 1500 |
| Companies House API | Free key | 500 |
| SIRENE API | Free key | 400 |
| Google Places API | $200/mo free credit | 1000+ |

**Effort**: 5-30 min per service (registration). Code is ready (`scrape_*.py` scrapers already have fallback to OpenCorporates).

### Tier 4: Manual + paid

#### G) LinkedIn reverse lookup — **150-250 decision-makers**
**Tool**: PhantomBuster ($30/mo) or Apollo.io ($49/mo)
**Output**: General Managers + Owners at hotels in target cities
**Quality**: High — already includes decision-maker name + LinkedIn

#### H) Trade publications — **100-200 leads**
- Hotel Management Magazine subscriber list
- Hospitality Net member directory
- IHIF / WTM / ITB Berlin exhibitor lists (paid PDFs)

---

## Recommended Next Sprint (to hit 1000+)

| Step | Source | Time | Yield | Cumulative |
|------|--------|------|-------|------------|
| 1 | Expand approved countries | 5 min | +56 | 751 |
| 2 | Wikipedia: Asia + Oceania + LATAM | 45 min | +250 | **1001 ✓** |
| 3 | OpenStreetMap (bonus) | 1-2 hrs | +500-1000 | 1500-2000 |
| 4 | Bulk Companies House CSV (bonus) | 1 hr | +500-2000 | 2000-4000 |

**Target hit**: Steps 1 + 2 alone get us past 1000 verified candidates.
**Stretch target (2000+)**: Add OSM or Companies House bulk.

---

## Sources To Skip (low ROI)

- **Booking.com / Expedia scraping** — Heavy anti-bot, partner API is paid
- **TripAdvisor** — Same, plus most listings overlap Wikipedia/OSM
- **Chamber of Commerce sites** — Mostly 403/JS-heavy as we discovered
- **Tourism board sites** — Inconsistent structure, low yield per scrape attempt

---

## What Goes Where

After enrichment + group consolidation, the funnel is:

```
695 verified candidates
    ↓ Phase 3 Haiku enrich (~3 hrs after-hours)
~570 verified_hotel (82% pass rate)
~110 manual_review (16%)
~15 discarded (2%)
    ↓ Group consolidation (chain dedup)
~350-400 unique sales teams (Marriott/Hilton/etc collapse into 1 primary each)
    ↓ Outreach approval gate
~350-400 outreach_approved = TRUE
```

So even at 695 raw candidates, after grouping we end up with **~350-400 actual outreach targets**.
To reach **1000 outreach targets**, we need ~1800-2000 raw candidates before grouping.
