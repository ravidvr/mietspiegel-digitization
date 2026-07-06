# Mietspiegel Update Monitoring

## Overview

The monitoring system tracks each city's official Mietspiegel website for new editions. German cities publish Mietspiegel every 2 years (qualifizierte Mietspiegel). This system automatically checks for new editions and maintains version history.

## Components

### 1. City Registry (`data/monitoring/cities.json`)
Contains metadata for 50 German cities:
- `page_url` — Official Mietspiegel page URL
- `known_editions` — Years already captured in the dataset
- `url_status` — `reachable` / `broken_404` / `broken_403` / `untested`
- `publication_frequency_years` — Typically 2

### 2. Monitor Script (`scripts/monitor.py`)
Python script that checks each city's page for new editions.

**Usage:**
```
python3 scripts/monitor.py                          # Check all 50 cities
python3 scripts/monitor.py --city berlin            # Single city
python3 scripts/monitor.py --city berlin --city munich  # Multiple cities
python3 scripts/monitor.py --status                 # Print last status
python3 scripts/monitor.py --export-json            # Machine-readable JSON
```

**What it detects:**
- PDF links containing edition years in filenames
- Page text mentioning "Mietspiegel 2025", "Mietspiegel 2025/2026"
- Year hints in context
- Falls back through multiple URL patterns if the primary URL fails

### 3. Version History (`data/versions/<city>.json`)
Per-city JSON files tracking:
- `versions` — Array of `{year, detected_at, source}` records
- `first_seen` — When the city was first monitored
- `last_check` — Last time the monitor ran

### 4. Status Dashboard (`data/monitoring/status.json`)
Aggregate status after each run:
- `last_run` — Timestamp
- `new_editions` — Editions detected for the first time
- `errors` — Cities that couldn't be reached
- `city_summary` — Per-city reachability and editions

## Alerting

The system alerts via:

1. **Cron job output** — The scheduled cron run prints a summary; if new editions are found, they're highlighted
2. **JSON status** — `--export-json` emits machine-readable data for downstream processing
3. **Terminal** — `--status` shows a quick dashboard of all cities

## City URL Status (Top 10)

| City | Status | Found Editions | Notes |
|------|--------|---------------|-------|
| Berlin | ✓ reachable | 2024 | Online calculator, no PDFs |
| Hamburg | ✗ broken | — | Site restructured, URL unknown |
| München | ✓ reachable | 2023, 2025* | PDFs found |
| Köln | ✗ broken | — | Site restructured |
| Frankfurt | ✗ broken | — | Cloudflare blocking |
| Stuttgart | ✓ reachable | 2023, 2025 | PDF: mietspiegel_2025_2026.pdf |
| Düsseldorf | ✗ broken | — | Site restructured |
| Leipzig | ✗ broken | — | Site restructured |
| Dresden | ✗ broken | — | Site restructured |
| Hannover | ✗ broken | — | Site restructured |

\* Detected from PDF filename (Durchschnittsmieten-Info PDF).

## Adding a New City

1. Open `data/monitoring/cities.json`
2. Add an entry with: `slug`, `name`, `state`, `page_url`
3. Optionally set `known_editions` and `publication_frequency_years`
4. Run `python3 scripts/monitor.py --city <slug>` to test
5. The monitor will auto-create version history on first check

## Future Improvements

- [ ] Email/Telegram alert when new edition detected
- [ ] Automatic URL discovery using search engines
- [ ] Historical edition archive (link to past PDFs)
- [ ] Integration with the main dashboard
- [ ] GitHub Actions workflow for weekly checks
