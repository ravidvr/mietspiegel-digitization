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
| City JSONs (`berlin.json`, `hamburg.json`, …) | Official Mietspiegel PDFs | Per Mietspiegel cycle (2 years) | Yes — PDF extraction pipeline |

*Last updated: 2026-07-26*
