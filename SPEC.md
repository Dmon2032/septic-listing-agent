# Septic Listing Agent — Spec

## Purpose
Every Monday morning, scan assigned ZIP codes for **newly listed** real estate where the property is on a **septic / on-site wastewater system**, enrich the matches with agent and (where available) homeowner contact info, and email a summary with a CSV attachment.

This is a personal/business automation, not a public service. Data comes from a **paid, authorized data provider** — no scraping of MLS portals or listing sites.

---

## Schedule
- Runs once per week: **Mondays at 06:00 America/Los_Angeles**.
- Implemented as a **GitHub Actions** cron workflow so it runs in the cloud (no need to leave a laptop on).
- The workflow can also be triggered manually from the Actions tab (`workflow_dispatch`).

---

## Configuration files (committed to repo)

### `config/zip_codes.yml`
```yaml
zip_codes:
  - "92024"
  - "92067"
  - "92091"
```

### `config/recipients.yml`
```yaml
recipients:
  - "danny@building5media.com"
```

### `config/keywords.yml` (so terms can evolve without code changes)
```yaml
structured_sewer_values:   # match against the structured Sewer/Sewage field
  - "septic"
  - "septic tank"
  - "private"
  - "owts"
  - "on-site"
  - "cesspool"

description_keywords:      # whole-word, case-insensitive, in description text
  - "septic"
  - "septic system"
  - "owts"
  - "on-site wastewater"

negation_patterns:         # if any appear NEAR a keyword, exclude the listing
  - "no septic"
  - "not on septic"
  - "removed septic"
  - "converted to sewer"
  - "sewer connected"
  - "public sewer"
```

---

## Secrets (env vars — never committed)

Set these in **GitHub → Settings → Secrets and variables → Actions**:

| Name | Purpose |
|------|---------|
| `LISTINGS_API_KEY` | Paid data provider API key |
| `OWNER_API_KEY` | Owner-record enrichment API key (optional) |
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | e.g. `587` |
| `SMTP_USER` | sending email address |
| `SMTP_PASSWORD` | app password (Gmail) or SMTP token |
| `EMAIL_FROM` | display sender address |

Locally, the same values live in a `.env` file (gitignored). Provide a `.env.example` with empty placeholders.

---

## Data source — pluggable provider layer

The paid data service hasn't been chosen yet. Build the agent **provider-agnostic** so we can swap one in later (likely candidates: ATTOM Data, Bridge Interactive, MLS Grid, BatchData, Estated).

### `src/providers/base.py`
```python
class ListingProvider(Protocol):
    def fetch_listings(
        self, zip_codes: list[str], since: datetime
    ) -> list[Listing]: ...
```

### `src/providers/mock.py`
Returns 8–10 canned sample listings — a mix of: septic-in-structured-field, septic-in-description, OWTS-in-description, negation case (e.g. "previously on septic, now sewer connected"), and non-septic. Used for local dev and CI.

The real provider implementations (`providers/attom.py` etc.) will be added in a later session once a service is signed up for. Until then, everything runs end-to-end against the mock.

### `Listing` model (`src/models.py`)
Use Pydantic. RESO-aligned field names where possible (real estate data standards).

```python
class Listing(BaseModel):
    listing_id: str            # stable provider-assigned ID — dedup key
    mls_number: str | None
    list_date: date
    list_price: int | None
    address_line: str
    city: str
    state: str
    zip_code: str
    beds: float | None
    baths: float | None
    sqft: int | None
    sewer: list[str] = []      # structured Sewer field, RESO-style
    public_remarks: str = ""   # the description / blurb
    listing_url: str | None
    agent_name: str | None
    agent_phone: str | None
    agent_email: str | None
    homeowner_name: str | None = None   # filled by enrichment
```

---

## Septic detection — `src/filters/septic.py`

A listing matches if **either** condition is true:

1. **Structured match**: any value in `listing.sewer` contains (case-insensitive) any item from `structured_sewer_values`.
2. **Description match**: `listing.public_remarks` contains a **word-boundary, case-insensitive** match for any item in `description_keywords`.

**Negation guard** — if a match was found via the description, check a ±50-character window around the matched keyword for any `negation_patterns`. If found, exclude the listing.

The filter function returns a tuple: `(matched: bool, reason: str, snippet: str | None)` where `snippet` is ±60 chars around the description match (or `None` if matched only via structured field). Snippets go into the CSV and email body so the user can sanity-check at a glance.

Log every decision at DEBUG: listing_id, matched, reason.

---

## Enrichment — `src/enrichment/owner.py`

Homeowner names are rarely in MLS data — they come from property/assessor records. If `OWNER_API_KEY` is set, look up each matched listing's owner of record by APN or address.

- Failures here are **non-fatal**: log a warning, set `homeowner_name = None`, continue.
- Cache results in `state/owner_cache.json` keyed by address hash, with a 30-day TTL — same address won't be hit twice.

---

## State — so we don't re-email the same listings

`state/seen_listings.json`:
```json
{
  "last_run_utc": "2026-05-18T13:00:00Z",
  "listing_ids": ["A12345", "A12346", "..."]
}
```

On each run:
1. Load state.
2. Fetch listings (since = `last_run_utc` minus 1 day for safety overlap).
3. Drop any whose `listing_id` is already in `listing_ids`.
4. Run the septic filter on the remainder.
5. Enrich + report on matches.
6. Add **all fetched listing IDs** (not just matches) to `listing_ids` so we don't re-check them next week.
7. Update `last_run_utc` and write back.

The GitHub Actions workflow commits `state/seen_listings.json` and any updated cache files back to the repo at the end of a successful run. Requires `permissions: contents: write` in the workflow.

Cap `listing_ids` at the most recent 50,000 entries to prevent unbounded growth.

---

## Output

### Email
- **Subject**: `Septic listings — week of {MMM D, YYYY} — {N} new`
- **Body** (multipart, HTML + plain text fallback):
  - Short intro line: how many ZIPs scanned, how many listings fetched, how many matched.
  - HTML table of the first 10 matches: address, price, beds/baths/sqft, agent name, agent phone, the snippet.
  - "Full list attached as CSV."
  - Footer with run timestamp and a link to the GitHub Actions run.
- **Attachment**: `septic_listings_{YYYY-MM-DD}.csv` with **every** match and all output columns.
- If `N == 0`: send the email anyway, with body "No new septic listings this week." The user needs to know the agent ran.

### CSV columns (in this order)
```
listing_id, list_date, address_line, city, state, zip_code,
list_price, beds, baths, sqft, sewer_field, match_reason,
description_snippet, listing_url,
agent_name, agent_phone, agent_email,
homeowner_name
```

---

## Error handling

- **Provider call fails**: retry 3× with exponential backoff (1s, 4s, 16s). If still failing, email recipients an error report including the last 50 log lines and exit non-zero so the Actions run is marked failed.
- **Email send fails**: write the report + CSV to `out/` (which the workflow uploads as a build artifact) and exit non-zero.
- **Enrichment fails**: warn and continue, never fail the whole run.
- Every run writes a structured log to `logs/{YYYY-MM-DD}.log`, committed back with state.

---

## Tech stack

- **Python 3.11+**
- Dependencies (`requirements.txt`): `httpx`, `pydantic`, `pyyaml`, `python-dotenv`, `tenacity`, `pytest`
- Standard-library `smtplib` + `email.message.EmailMessage` for sending — no extra email lib
- No frameworks beyond that — keep it boring and obvious

---

## Project layout

```
.
├── .github/
│   └── workflows/
│       └── monday-run.yml
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI entrypoint
│   ├── config.py               # loads yml + env
│   ├── models.py               # Listing pydantic model
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── mock.py
│   ├── filters/
│   │   ├── __init__.py
│   │   └── septic.py
│   ├── enrichment/
│   │   ├── __init__.py
│   │   └── owner.py
│   ├── state_store.py
│   ├── report.py               # builds CSV + HTML body
│   └── email_sender.py
├── config/
│   ├── zip_codes.yml
│   ├── recipients.yml
│   └── keywords.yml
├── state/
│   └── seen_listings.json
├── tests/
│   ├── test_septic_filter.py
│   └── test_state_store.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## CLI / local dev

```bash
# end-to-end against the mock provider, no email sent
python -m src.main --provider mock --dry-run

# send to a single override recipient for testing
python -m src.main --provider mock --to me@example.com

# real run (when a provider is wired up)
python -m src.main --provider attom
```

---

## Tests (must exist before "done")

`tests/test_septic_filter.py` — at minimum:

**Positive cases:**
1. Sewer field = `["Septic Tank"]` → match.
2. Description contains "Property is on septic system." → match.
3. Description contains "OWTS permit on file." → match.
4. Mixed case: "On-Site Wastewater system installed 2019." → match.
5. Both structured + description match → match (no double-count).

**Negative cases:**
1. Sewer field = `["Public Sewer"]`, no description keywords → no match.
2. Description: "No septic — public sewer connected." → no match (negation).
3. Description: "Septic was removed; now on city sewer." → no match (negation).
4. Description mentions septic in unrelated context, e.g. "septic-style fermentation" → acceptable false positive, document but don't try to filter (real estate context makes this extremely rare).
5. Empty/missing fields → no match, no crash.

---

## README must cover

1. What this does (one paragraph).
2. Quick start: clone, `pip install -r requirements.txt`, copy `.env.example` → `.env`, run with mock.
3. How to configure ZIP codes, recipients, keywords.
4. How to set GitHub Actions secrets.
5. How the schedule works and how to change it.
6. How to swap in a real data provider (point to `providers/base.py`).
7. Troubleshooting: how to view logs from a failed run.

---

## Build order (please follow this order and **pause for review after each step**)

1. Scaffold the full directory structure with empty/stub files.
2. `models.py` + `config.py` (load yml + env).
3. `providers/base.py` + `providers/mock.py` with sample data.
4. `filters/septic.py` + `tests/test_septic_filter.py` — get tests green.
5. `state_store.py` + tests.
6. `report.py` (CSV + HTML).
7. `email_sender.py`.
8. `main.py` wiring it all together — verify `--dry-run` works end-to-end.
9. `.github/workflows/monday-run.yml`.
10. `README.md`.

After each step: stop, show me a summary of what you built and any decisions you made, and wait for my OK before moving on.
