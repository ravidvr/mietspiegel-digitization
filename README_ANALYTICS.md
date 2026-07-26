# German Rent Index Analytics — A Multi-City Mietspiegel Database

> **SQL · BigQuery · Python · ETL · Statistical Analysis · Data Quality · Geospatial**

---

| 🏙️ 23 Cities | 🏗️ 7–9 Baujahr Groups | 📊 ~2,000 Rent Cells | 📡 5 Data Sources |
|:---:|:---:|:---:|:---:|

**Live dashboard:** [ravidvr.github.io/mietspiegel-digitization](https://ravidvr.github.io/mietspiegel-digitization/)

---

## What This Is

A structured, machine-readable database of official German Mietspiegel (rent index) tables — extracted from municipal PDFs into a unified JSON schema, cross-referenced against census data and market rents, and served as both an interactive dashboard and an analytics-ready data product. Every rent value is traceable to its source PDF, validated for internal consistency, and benchmarked against aggregate national statistics from the GdW (German housing industry association).

This is not just a map. It's a **data product** for rent analysis: query it, join it, model it, and use it to answer real questions about Germany's housing market.

---

## Analytics Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Warehouse** | BigQuery | Central analytics store, cross-city queries |
| **Query** | SQL | Ad-hoc analysis, aggregation, tenant fairness checks |
| **ETL** | Python (pdfplumber, pandas) | PDF extraction, normalization, validation |
| **BI** | Looker / Tableau Public | Dashboards, stakeholder reporting |
| **Statistical Testing** | Python (scipy, statsmodels) | A/B tests, rent forecasting, inequality metrics |
| **Data Quality** | pytest + custom validators | Monotonicity, schema, GdW cross-ref |
| **Geospatial** | Leaflet.js + GeoJSON | Interactive heatmaps, district boundaries |
| **Deployment** | GitHub Pages | Static hosting, zero-cost CDN |

---

## Key Analytical Capabilities

**What questions can this data answer?**

### City Comparison
Which city has the highest rent for a 60 m² apartment built after 2014? How does München's *einfach* tier compare to Hamburg's *mittel* tier? Rank all 23 cities by rent level, filter by Baujahr and Wohnlage.

```sql
-- Median rent for 40–60 m² apartments built 2014+, by city
SELECT city, AVG(rent_40_60) AS avg_rent
FROM mietspiegel.rent_cells
WHERE baujahr_group LIKE '%2014%'
GROUP BY city ORDER BY avg_rent DESC;
```

### Rent Forecasting
Track historical Mietspiegel editions (Berlin: 2013–2024, 6 editions) to model rent growth trajectories. Which cities are accelerating fastest?

### Inequality Metrics
Compute rent-to-income ratios by city. Compare the spread between *einfach* and *gut* Wohnlage tiers — which cities have the widest housing inequality gap? Cross-reference with GdW state-level averages to identify outliers.

### "Is My Rent Fair?"
Given a specific apartment (city, Baujahr, size, Wohnlage), look up the official Mietspiegel value. Compare against market rents (Immoscout24) and census rents (Zensus 2022). Determine if a tenant is overpaying — and by how much.

### Market vs. Official Gap
In Berlin, Immoscout24 market rents in newer buildings are ~25–40% above the official Mietspiegel. How does this gap vary across cities? Which cities have the largest disconnect between market and regulated rents?

### Data Quality Monitoring
Every data point is validated against:
- **Internal consistency:** newer buildings > older, better Lage > worse, smaller units > larger (€/m²)
- **External benchmarks:** cross-referenced against GdW national (€6.63/m²) and state-level aggregates
- **Schema compliance:** all 23 cities conform to a unified JSON schema

---

## Data Model

```
┌──────────────────────────────────────────────────────────────┐
│                        City                                  │
│  city (PK) · state · lat · lng · population · year · type   │
└────────────┬─────────────────────────────────────────────────┘
             │ 1:N
             ▼
┌──────────────────────────────────────────────────────────────┐
│                     Rent Table                               │
│  city (FK) · lage (einfach|mittel|gut)                      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                   Rent Row                               ││
│  │  baujahr · bis_40 · 40_60 · 60_90 · ueber_90            ││
│  │  (all values: €/m² net cold rent, NULL if missing)      ││
│  └──────────────────────────────────────────────────────────┘│
│  3–4 Wohnlage tables per city                                │
│  6–9 Baujahr rows per table                                  │
│  ~85–96 rent cells per city                                  │
└──────────────────────────────────────────────────────────────┘

External Reference Data:
┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐
│   GdW Aggregate      │  │   Immoscout24        │  │   Zensus 2022      │
│   national: €6.63    │  │   (RWI-GEO-REDX)     │  │   100m→1km grid    │
│   13 state averages  │  │   467 Berlin cells   │  │   1,155 Berlin cells│
└──────────────────────┘  └─────────────────────┘  └────────────────────┘
```

**Entity count:** 23 cities → ~69 Wohnlage tables → ~500 Baujahr rows → ~2,000 rent values

---

## Quick Start: Load into BigQuery

### 1. Clone and prepare

```bash
git clone https://github.com/ravidvr/mietspiegel-digitization.git
cd mietspiegel-digitization
```

### 2. Pivot to flat table

The city JSONs store data in nested `tables → rows` format. Pivot to a flat analytics table:

```python
import json, csv, glob

rows = []
for path in sorted(glob.glob("docs/data/processed/*.json")):
    with open(path) as f:
        data = json.load(f)
    if "tables" not in data:
        continue
    for table in data["tables"]:
        for row in table["rows"]:
            rows.append({
                "city": data["city"],
                "state": data.get("state", ""),
                "year": data["year"],
                "lage": table["lage"],
                "baujahr": row["baujahr"],
                "rent_bis_40": row.get("bis_40"),
                "rent_40_60": row.get("40_60"),
                "rent_60_90": row.get("60_90"),
                "rent_ueber_90": row.get("ueber_90"),
            })

with open("mietspiegel_flat.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
```

### 3. Upload to BigQuery

```bash
bq load --autodetect --source_format=CSV \
  mietspiegel.rent_cells mietspiegel_flat.csv
```

### 4. Run your first query

```sql
-- Top 5 most expensive cities for a 60 m² apartment (mittel Lage, newest Baujahr)
SELECT city, state, MAX(rent_60_90) AS rent_per_sqm
FROM mietspiegel.rent_cells
WHERE lage = 'mittel'
  AND baujahr LIKE '%2014%' OR baujahr LIKE '%202%'
GROUP BY city, state
ORDER BY rent_per_sqm DESC
LIMIT 5;
```

---

## Links

| Resource | URL |
|----------|-----|
| **Live Dashboard** | [ravidvr.github.io/mietspiegel-digitization](https://ravidvr.github.io/mietspiegel-digitization/) |
| **BigQuery Schema** | `analytics/schema.sql` |
| **SQL Query Library** | `analytics/queries/` |
| **Looker Model** | `analytics/lookml/mietspiegel.model.lkml` |
| **Experiments** | `experiments/` (A/B tests, statistical analyses) |
| **Data Quality Reports** | `validate/` (CI-gated, runs weekly) |
| **Validation Methodology** | [`docs/validation_methodology.md`](docs/validation_methodology.md) |

---

## Dashboard

The interactive dashboard layers three independent data sources on a single map:

- **Immoscout24 market rents** — 467 Berlin grid cells (RWI-GEO-REDX PUF v16)
- **Zensus 2022 census rents** — 1,155 Berlin cells at 100m resolution, aggregated to 1km
- **Berlin Mietspiegel 2024** — full official rent table (3 Wohnlagen × 8 Baujahre × 4 sizes), plus 6 historical editions (2013–2024)

### Features

- Interactive heatmap with Berlin-local z-score normalization (zoom-sensitive radius/blur)
- 12 Bezirke labels with estimated average rents
- Click anywhere for multi-layer rent data (Immoscout vs Census vs Official Mietspiegel)
- Cross-city comparison table (23 cities ranked, sortable, Wohnlage-filterable)
- Historical trends (Wohnlage comparison chart, growth ranking, edition history)
- DE/EN language toggle, dark mode, CSV export
- Mobile-friendly with bottom-sheet tooltips
- Address search via Nominatim (restricted to Berlin bounding box)

### Quick Start (local)

```bash
git clone https://github.com/ravidvr/mietspiegel-digitization.git
cd mietspiegel-digitization
python3 -m http.server 8000 --directory docs
# Open http://localhost:8000
```

---

## Data Sources

| Source | Coverage | License |
|--------|----------|---------|
| Municipal Mietspiegel PDFs | 23 cities, officially published rent tables | Public official documents |
| RWI-GEO-REDX PUF v16 | 467 Berlin grid cells (market rents) | Public Use File (DOI: 10.7807/IMMO:REDX:PUF:V16) |
| Zensus 2022 | 1,155 Berlin cells (100m→1km census rents) | dl-de/by-2.0 |
| GdW Aggregate | National (€6.63/m²) + 13 state-level averages | GdW Jahresstatistik |
| Berlin WFS (Wohnlage) | 400,505 address-level points | dl-de/zero-2.0 |

---

## Project Structure

```
mietspiegel-digitization/
├── docs/                          ← GitHub Pages deployment root
│   ├── index.html                 ← Main dashboard (vanilla HTML/CSS/JS)
│   ├── cross-city-comparison.html ← 23-city comparison + Mietspiegel table
│   ├── historical_trends.html     ← Rent history by Wohnlage (Chart.js)
│   └── data/processed/            ← All city JSONs served statically
├── analytics/                     ← BigQuery schema, SQL queries, LookML
├── experiments/                   ← A/B testing, statistical tests
├── scripts/                       ← Python ETL pipeline
├── validate/                      ← Data quality framework (sanity checks, GdW cross-ref)
├── tests/                         ← pytest validation suite
├── data/                          ← Source data, raw PDFs (gitignored)
└── .github/workflows/             ← CI/CD (validation gate → deploy)
```

---

## License

Dashboard code: **CC BY-SA 4.0**
Data: See individual source licenses above.

---

*Built by [Ravi Dronamraju](https://github.com/ravidvr) — Senior Data Analyst, Berlin. Previously: Delivery Hero (supply chain analytics), OLX (experimentation), Zalando (product analytics).*
