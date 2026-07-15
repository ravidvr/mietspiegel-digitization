# Berlin Property Market — Marktbericht Dashboard

> The Property Market dashboard is now a separate project: **[ravidvr/berlin-property-market](https://github.com/ravidvr/berlin-property-market)**
>
> **Live:** https://ravidvr.github.io/berlin-property-market/

This directory contains the data extraction pipeline for the Berlin Immobilienmarktbericht 2024/2025. All structured tables have been extracted and validated (251/251 checks passed).

## Data Files

| File | Contents |
|------|----------|
| `docs/data/processed/marktbericht_complete_2024.json` | Full 2024 dataset — sales, prices, BRW, condos |
| `docs/data/processed/marktbericht_combined.json` | Combined dataset — Marktbericht + Baufertig + Genehmigungen + Bestand + BORIS |
| `docs/data/processed/marktbericht_timeseries.json` | 10-year ETW price time series (2015-2024) |
| `docs/data/processed/brw_2025_zones.json` | 1,619 BORIS BRW zones (full geometry) |
| `docs/data/processed/brw_2025_slim.json` | BRW zones (no geometry, for dashboards) |
| `docs/data/processed/baufertigstellungen_2024.json` | New apartment completions per Bezirk |
| `docs/data/processed/baugenehmigungen_2024.json` | Building permits per Bezirk |
| `docs/data/processed/wohnungsbestand_2024.json` | Housing stock per Bezirk |
| `docs/data/processed/stadtgebiet_bezirk_mapping.json` | 96 Ortsteile → 12 Bezirke → 6 Stadtgebiete |

## Sources

- Gutachterausschuss für Grundstückswerte in Berlin (dl-de/zero-2-0)
- Amt für Statistik Berlin-Brandenburg (dl-de/by-2-0)
- BORIS Berlin / Geoportal Berlin (dl-de/zero-2-0)

## Documentation

- `marktbericht-extraction.md` — Full extraction methodology
- `marktbericht.md` — Data dictionary (this file)

---

See the **[berlin-property-market README](https://github.com/ravidvr/berlin-property-market)** for all 17 key insights from the dataset.
