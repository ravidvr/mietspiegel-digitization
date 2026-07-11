# Mietspiegel Digitization

Digitized, standardized, searchable database of official German city Mietspiegel (rent indexes) — extracted from PDFs into structured data with an interactive map dashboard.

**Live dashboard:** https://ravidvr.github.io/mietspiegel-digitization/

## What This Is

Germany has no unified national rent database. Each city publishes its Mietspiegel independently as a PDF — this project extracts, normalizes, and visualizes them all in one place.

- **28 cities** of official rent index data (23 with complete tables)
- **7,304 Immoscout24 market-rent grid cells** (RWI-GEO-REDX PUF v16)
- **113K Zensus 2022 census rent cells** (100m resolution, aggregated to 1km)
- **Berlin district overlay** (400,505 address-level classifications)

## Dashboard Features

- Interactive heatmap with z-score normalization (zoom-sensitive radius/blur)
- City labels with official Mietspiegel average rents
- Click anywhere for multi-layer rent data (Immoscout vs Census vs Official)
- Cross-city comparison table (filter by Wohnlage, size, Baujahr)
- Historical trends (Chart.js line chart, growth ranking, edition tracking)
- Berlin-only dashboard with district panel and dual-source toggle
- DE/EN language toggle, dark mode, CSV export
- Mobile-friendly with bottom-sheet tooltips

## Quick Start

```bash
git clone https://github.com/ravidvr/mietspiegel-digitization.git
cd mietspiegel-digitization

# Build the full dashboard (normalize data, build GeoJSON, process census)
./scripts/build.sh

# Or skip the heavy grid/census processing if data already exists:
./scripts/build.sh --skip-grid --skip-zensus

# Serve locally:
python3 -m http.server 8000 --directory docs
# Open http://localhost:8000
```

### External Data Dependencies

The build pipeline references external datasets that are **not included in git** (too large).
Download them separately:

| Dataset | Source | How to get |
|---------|--------|------------|
| RWI-GEO-REDX PUF v16 | RWI Essen | https://doi.org/10.7807/IMMO:REDX:PUF:V16 |
| Zensus 2022 (Nettokaltmiete) | Destatis | https://www.zensus2022.de |
| German boundaries (Kreise/States) | GADM | https://gadm.org |
| PLZ centroids | WZB | `data/external/plz_centroids.csv` |

Place downloaded files under `data/external/`.

## Project Structure

```
mietspiegel-digitization/
├── docs/                          ← GitHub Pages deployment root
│   ├── index.html                 ← Main dashboard (single-file, no framework)
│   ├── cross-city-comparison.html ← Side-by-side comparison view
│   ├── historical_trends.html     ← Rent development over time (Chart.js)
│   ├── berlin.html                ← Berlin-only standalone dashboard
│   ├── about.html                 ← Full project documentation
│   ├── berlin-about.html          ← Berlin dashboard docs
│   ├── schema.md                  ← Data schema reference
│   └── data/processed/            ← All dashboard data (served statically)
├── scripts/                       ← Build pipeline
│   ├── build.sh                   ← Full pipeline orchestrator
│   ├── compile_data.py            ← Normalize city data → dashboard JSON
│   ├── build_national_choropleth.py ← RWI grids → GeoJSON with spatial joins
│   ├── process_zensus2022.py      ← Zensus 100m → 1km aggregated JSON
│   └── ...
├── validate/                      ← Data quality framework
│   ├── sanity_checks.py           ← Monotonicity, completeness, positivity
│   ├── gdw_crossref.py            ← Cross-reference vs GdW benchmarks
│   └── run_validations.py         ← CLI runner
├── data/                          ← Source data (not tracked in git)
│   ├── raw/                       ← Original Mietspiegel PDFs
│   ├── external/                  ← RWI, Zensus, GADM downloads
│   ├── processed/                 ← Build staging area
│   └── versions/                  ← Historical edition snapshots
└── .github/workflows/pages.yml    ← Auto-deploy to GitHub Pages
```

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (no framework, no build step, no npm)
- **Map:** Leaflet.js 1.9.4 + Leaflet.heat 0.2.0
- **Charts:** Chart.js 4.4.7 (historical trends only)
- **Data:** Static JSON files served by GitHub Pages
- **Build:** Python 3 (pdfplumber, shapely, pyproj, scipy)
- **Deployment:** GitHub Pages via GitHub Actions

## Data Sources

| Source | Coverage | License |
|--------|----------|---------|
| City Mietspiegel PDFs | 28 cities, 2024-2026 | Public official documents |
| RWI-GEO-REDX PUF v16 | 7,304 grid cells nationwide | Public Use File (DOI: 10.7807/IMMO:REDX:PUF:V16) |
| Zensus 2022 | 113K cells at 100m resolution | Datenlizenz Deutschland – Namensnennung 2.0 |
| Berlin WFS | 400,505 addresses | Datenlizenz Deutschland – Zero |
| OSM tiles | Map base | ODbL |

See [docs/about.html](docs/about.html) for full documentation including methodology, limitations, and reproducibility instructions.

## Validation

```bash
# Run all sanity checks on extracted city data
python3 -m validate.run_validations

# Single city
python3 -m validate.run_validations --city berlin

# JSON output
python3 -m validate.run_validations --json
```

Checks: Baujahr monotonicity, Lage monotonicity, positive values, field completeness, GdW cross-reference.

## License

Dashboard code: **CC BY-SA 4.0**
Data: See individual source licenses above.

## Contributing

Found a bug or have data for a new city? Open an issue or PR on [GitHub](https://github.com/ravidvr/mietspiegel-digitization).
