# Berlin Mietspiegel & Immobilienmarkt

Two dashboards, one map. Rent data and actual sale prices for every Berlin district.

## Live Dashboards

| Dashboard | What it shows | URL |
|---|---|---|
| **Rent Map** | Market rents vs census rents, block by block | [ravidvr.github.io/mietspiegel-digitization/](https://ravidvr.github.io/mietspiegel-digitization/) |
| **Property Market** | Actual sale prices — not estimates, not asking prices | [ravidvr.github.io/mietspiegel-digitization/marktbericht.html](https://ravidvr.github.io/mietspiegel-digitization/marktbericht.html) |

---

## Property Market — 5 Key Insights

The Marktbericht dashboard visualises 20,789 notarised property sales from 2024. Here's what the data actually says:

**1. Three districts move 36% of all money**
Charlottenburg-Wilmersdorf, Pankow, and Mitte together account for €5.2 billion. Mitte has the highest average transaction at €860,000.

**2. Land values vary by a factor of 10 across Berlin**
From €300/m² in outer Treptow-Köpenick to €2,800/m² in central Mitte. Even within a single district, the spread can be 6×. The dashboard shows the range — not just a misleading average.

**3. Most of Berlin is a condo market**
In Friedrichshain-Kreuzberg, 96% of all property sales are apartments. Mitte: 94%. Only outer districts like Spandau and Steglitz-Zehlendorf have meaningful numbers of houses.

**4. More transactions, lower prices — the market is clearing**
Sales volume is up 18% year-on-year. But condo prices fell 1%, house prices fell 7%, and land values dropped in 9 out of 12 districts. Sellers are accepting lower prices, and buyers are returning.

**5. Rental buildings are negative-carry investments**
Investors pay 23.5× annual rent — that's a 4.3% gross yield. With financing at 3.5-4%, there's no cash-flow surplus. Buyers are betting on future rent growth, not current returns.

---

## Dashboard Features

- **10 switchable metrics** — transaction volume, sales count, land area, condo prices, land values
- **Colour-coded district map** — green (low) to red (high) for every metric
- **Address and postal code search** — type any Berlin address and the map zooms to that district
- **Click any district** for a full breakdown with price ranges (einfache to gute Lage)
- **Range bars** show the spread between cheap and expensive — not just the average
- **Berlin-wide benchmark cards** — average prices for condos, houses, new-builds, and yields
- **DE/EN language toggle** — all text, metrics, and tooltips translate
- **Help overlay** — auto-shows on first visit, re-openable any time

---

## What This Is (Rent Map)

All calculations are relative to Berlin. Every z-score, average, and comparison uses Berlin-only data — not national averages.

- **12 Bezirke** with estimated average rents (derived from 400,505 address-level points)
- **467 Immoscout24 market-rent grid cells** (RWI-GEO-REDX PUF v16, Berlin-only)
- **1,155 Zensus 2022 census rent cells** (100m resolution, aggregated to 1km, Berlin-only)
- **Berlin Mietspiegel 2024** (full rent table: 3 Wohnlagen x 8 Baujahre x 4 sizes)
- **6 historical editions** (2013-2023, all three Wohnlagen tracked)
- Address search via Nominatim (restricted to Berlin bounding box)
- DE/EN language toggle, dark mode, CSV export
- Mobile-friendly with bottom-sheet tooltips

---

## Quick Start

```bash
git clone https://github.com/ravidvr/mietspiegel-digitization.git
cd mietspiegel-digitization

# Serve locally:
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

---

## Project Structure

```
mietspiegel-digitization/
├── docs/                          ← GitHub Pages deployment root
│   ├── index.html                 ← Main Berlin dashboard (single-file, no framework)
│   ├── marktbericht.html          ← Property market dashboard
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

---

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (no framework, no build step, no npm)
- **Map:** Leaflet.js 1.9.4 + Leaflet.heat 0.2.0
- **Charts:** Chart.js 4.4.7 (historical trends)
- **Data:** Static JSON files served by GitHub Pages
- **Build:** Python 3 (pdfplumber, shapely, pyproj, scipy)
- **Deployment:** GitHub Pages via GitHub Actions

---

## Data Sources

| Source | Coverage | License |
|--------|----------|---------|
| Berlin Mietspiegel 2024 | Full rent table, 3 Wohnlagen | Public official document |
| RWI-GEO-REDX PUF v16 | 467 Berlin grid cells | Public Use File (DOI: 10.7807/IMMO:REDX:PUF:V16) |
| Zensus 2022 | 1,155 Berlin cells (100m→1km) | dl-de/by-2.0 |
| Berlin WFS | 400,505 address points | dl-de/zero-2.0 |
| Immobilienmarktbericht 2024/2025 | 20,789 sale contracts | dl-de/zero-2.0 |
| OSM tiles | Map base | ODbL |

---

## License

Dashboard code: **CC BY-SA 4.0**
Data: See individual source licenses above.
