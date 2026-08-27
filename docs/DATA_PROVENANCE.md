# Data Provenance — mietspiegel-digitization

## berlin_districts_index.json

**Status:** Manually curated reference dimension
**Last reviewed:** 2026-07-26
**Review cadence:** Each Mietspiegel cycle (typically every 2 years)

### What it contains

12 Berlin Bezirke with:
- `district` — Bezirk name
- `avg_rent` — Estimated average net cold rent (€/m²), derived from Immoscout24 market asking rents (RWI-GEO-REDX PUF v16) averaged per district
- `einfach_pct`, `mittel_pct`, `gut_pct` — Wohnlage distribution (%) from Berlin Senate WFS address points (400,505 addresses)
- `total_addresses` — Address count per district from WFS
- `lat`, `lng` — District centroid coordinates

### Why manual

This dataset combines two sources that are updated on different schedules:
1. Immoscout24 market rents (RWI-GEO-REDX) — annual PUF releases
2. Berlin Senate WFS Wohnlage classification — periodic WFS updates

An automated join requires both sources to be simultaneously available and correctly aligned. Currently this is done manually to ensure:
- District boundaries are respected (grid cells near borders are correctly assigned)
- Wohnlage classification percentages are validated against the official Mietspiegel tables
- Outlier grid cells are identified and reviewed before inclusion

### Generation methodology (for future automation)

```python
# Pseudocode for scripts/build_districts_index.py (pending)
# 1. Load berlin_immoscout.json (467 grid cells with rent/lat/lng)
# 2. Load berlin-districts-choropleth.geojson (district boundaries)
# 3. For each grid cell, find containing district via point-in-polygon
# 4. Compute district-level avg_rent = mean of all cell rents in that district
# 5. Load Berlin WFS Wohnlage data and compute einfach/mittel/gut % per district
# 6. Write berlin_districts_index.json
```

### Verification

Cross-check against `berlin_districts_comparison.json`:
- Both files should have identical `avg_rent` and `gap_pct` values
- Berlin average Immoscout rent should be €10.79/m²
- District ranking should be: Charlottenburg-Wilmersdorf > Steglitz-Zehlendorf > ... > Neukölln

---

## Other Data Files

| File | Source | Update cadence | Auto-generated? |
|---|---|---|---|
| `berlin_immoscout.json` | RWI-GEO-REDX PUF v16 | Annual (when new PUF released) | Yes — `scripts/build_berlin_data.py` |
| `berlin_zensus.json` | Zensus 2022 (Destatis) | Static (census every 10 years) | Yes — `scripts/build_berlin_data.py` |
| `berlin_districts_comparison.json` | Derived from districts_index | Same as districts_index | Partially (manual input) |
| `berlin-districts-choropleth.geojson` | Berlin Senate WFS | Per WFS update | Yes — WFS download |
| `berlin_raw_2024.json` | Official Mietspiegel PDF 2024 | Per Mietspiegel cycle (2 years) | Yes — `sources/extract_mietspiegel.py`, gated by `scripts/verify_berlin_extraction.py` (PDF-diff, 0 diffs required) |
| `berlin.json` | Derived from `berlin_raw_2024.json` | Same | Yes — `scripts/build_city_tables.py` |
| `berlin_historical_editions.json` | Official edition PDFs 2017/2019/2021/2023 | Per edition | Yes — `scripts/extract_wide_editions.py` + `scripts/build_historical.py` |
| `data/historical_mietspiegel.json` | Derived from editions file | Same | Yes — `scripts/build_historical.py` |
| Other city JSONs | Official Mietspiegel PDFs | Per Mietspiegel cycle (2 years) | Yes — PDF extraction pipeline |

*Last updated: 2026-08-27*

### Verified-extraction architecture (Berlin 2024, since 2026-08)

The Berlin 2024 table is no longer a hand-normalized grid. The pipeline is:

1. `sources/extract_mietspiegel.py` extracts 163 rows verbatim from
   `data/raw/berlin-mietspiegeltabelle-2024.pdf` (official cohorts incl.
   West/Ost, per-cohort size bands, untere/obere Spanne).
2. `scripts/verify_berlin_extraction.py` re-extracts and diffs every row
   against the committed raw JSON — CI-gated, 0 diffs required.
3. `scripts/build_city_tables.py` derives `berlin.json`: `official_rows`
   (verbatim, for the Rent Check and legal comparisons) plus a clearly
   labeled 4-band legacy rollup for old consumers.
4. Historical editions 2017-2023 are extracted by
   `scripts/extract_wide_editions.py` (coordinate-based; 359/359 Mittelwerte
   verified present in the PDF text layer) and reduced by
   `scripts/build_historical.py` into two documented series:
   `by_lage` (newest cohort) and `by_lage_same_cohort` (1991-2002,
   apples-to-apples). 2013/2015 are not in the official archive.

The previous uniform 96-cell grid and interpolated 2013-2023 series were
removed — their values could not be reproduced from the official documents.
