# Mietspiegel Digitization

[![CI](https://github.com/ravidvr/mietspiegel-digitization/actions/workflows/ci.yml/badge.svg)](https://github.com/ravidvr/mietspiegel-digitization/actions/workflows/ci.yml)
[![Data Validation](https://github.com/ravidvr/mietspiegel-digitization/actions/workflows/validate-and-deploy.yml/badge.svg)](https://github.com/ravidvr/mietspiegel-digitization/actions/workflows/validate-and-deploy.yml)
[![GitHub Pages](https://img.shields.io/badge/demo-live-brightgreen)](https://ravidvr.github.io/mietspiegel-digitization/)

Digitizes German municipal rent indices (Mietspiegel) — bilingual DE/EN, 23 cities, 3 reconciled data sources. All values are **Nettokaltmiete (net cold rent)** in €/m²/month.

**Live dashboard:** https://ravidvr.github.io/mietspiegel-digitization/
**📐 Metric dictionary:** [docs/METRICS.md](docs/METRICS.md) — cold vs warm rent, data sources, derived metrics

> Looking for property sale prices? The **Berlin Property Market** dashboard is now a separate project: [ravidvr/berlin-property-market](https://github.com/ravidvr/berlin-property-market) — [Live dashboard](https://ravidvr.github.io/berlin-property-market/)

## What This Is

All calculations are relative to Berlin. Every z-score, average, and comparison uses Berlin-only data — not national averages.

- **12 Bezirke** with estimated average rents (derived from 400,505 address-level points)
- **467 Immoscout24 market-rent grid cells** (RWI-GEO-REDX PUF v16, Berlin-only)
- **1,155 Zensus 2022 census rent cells** (100m resolution, aggregated to 1km, Berlin-only)
- **Berlin Mietspiegel 2024** (full rent table: 3 Wohnlagen x 8 Baujahre x 4 sizes)
- **6 historical editions** (2013-2023, all three Wohnlagen tracked)

## Dashboard Features

- Interactive heatmap with Berlin-local z-score normalization (zoom-sensitive radius/blur)
- 12 Bezirke labels with estimated average rents
- Click anywhere for multi-layer rent data (Immoscout vs Census vs Official Mietspiegel)
- District comparison table (12 Bezirke ranked, sortable, with Mietspiegel table)
- Historical trends (Wohnlage comparison chart, growth ranking, edition history)
- DE/EN language toggle, dark mode, CSV export
- Mobile-friendly with bottom-sheet tooltips
- Address search via Nominatim (restricted to Berlin bounding box)

## Quick Start

```bash
git clone https://github.com/ravidvr/mietspiegel-digitization.git
cd mietspiegel-digitization

# Quickstart: one command to set up everything
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
make all

# Serve the dashboard locally:
python3 -m http.server 8000 --directory docs
# Open http://localhost:8000
```

### External Data Dependencies

The build pipeline references external datasets that are **not included in git** (too large).

| Dataset | Source | How to get |
|---------|--------|------------|
| RWI-GEO-REDX PUF v16 | RWI Essen | https://doi.org/10.7807/IMMO:REDX:PUF:V16 |
| Zensus 2022 (Nettokaltmiete) | Destatis | https://www.zensus2022.de |
| Berlin WFS (Wohnlage) | Berlin Senate | https://gdi.berlin.de/services/wfs/wohnlagenadr2026 |

Place downloaded files under `data/external/`.

## Project Structure

```
mietspiegel-digitization/
├── docs/                          ← GitHub Pages deployment root
│   ├── index.html                 ← Main Berlin dashboard (single-file, no framework)
│   ├── cross-city-comparison.html ← 12 Bezirke comparison + Mietspiegel table
│   ├── historical_trends.html     ← Berlin rent history by Wohnlage (Chart.js)
│   ├── berlin.html                ← Standalone Berlin map (Immoscout vs Zensus)
│   ├── about.html                 ← Project documentation
│   └── data/processed/            ← All dashboard data (served statically)
├── scripts/                       ← Build pipeline
├── validate/                      ← Data quality framework
├── data/                          ← Source data (not tracked in git)
└── .github/workflows/pages.yml    ← Auto-deploy to GitHub Pages
```

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (no framework, no build step, no npm)
- **Map:** Leaflet.js 1.9.4 + Leaflet.heat 0.2.0
- **Charts:** Chart.js 4.4.7 (historical trends)
- **Data:** Static JSON files served by GitHub Pages
- **Build:** Python 3 (pdfplumber, shapely, pyproj, scipy)
- **Deployment:** GitHub Pages via GitHub Actions

## Data Sources

| Source | Coverage | License |
|--------|----------|---------|
| Berlin Mietspiegel 2024 | Full rent table, 3 Wohnlagen | Public official document |
| RWI-GEO-REDX PUF v16 | 467 Berlin grid cells | Public Use File (DOI: 10.7807/IMMO:REDX:PUF:V16) |
| Zensus 2022 | 1,155 Berlin cells (100m→1km) | dl-de/by-2.0 |
| Berlin WFS | 400,505 address points | dl-de/zero-2.0 |
| OSM tiles | Map base | ODbL |

## License

Dashboard code: **CC BY-SA 4.0**
Data: See individual source licenses above.

## Why This Project

This project demonstrates the same analytical patterns used in supply chain and marketplace analytics:

- **Multi-source reconciliation** — Three independent data sources (market, census, official) that disagree. Finding and explaining the gaps is the same skill as reconciling supplier-reported costs with internal ERP data.
- **Monotonicity and plausibility checks** — 14 automated tests that catch impossible values before they reach a dashboard. Same pattern as KPI validation gates in production analytics pipelines.
- **Index construction** — Building a rent index from raw grid cells is structurally identical to building price indices, demand forecasting inputs, or supplier performance scores.
- **Experimentation mindset** — The A/B simulator models counterfactual policy scenarios with MDE calculations. Same framework used at Zalando and Delivery Hero for product experiments.

Built by [Ravi Dronamraju](https://ravidvr.github.io) — Senior Data Analyst, Berlin.
