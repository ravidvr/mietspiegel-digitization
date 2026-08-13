# Analytics Engineering — Mietspiegel Digitization

This directory contains the SQL analytics layer, LookML model, and experiment framework for the Mietspiegel dataset — 23 German cities with official rent index tables.

## BigQuery Star Schema

`berlin_bigquery_schema.sql` — Berlin-specific schema. One fact table (`rent_cells`) with dimension tables for city, Lage, Baujahr, and size class.

`bigquery_schema.sql` — Full 23-city schema. Traditional star schema optimized for OLAP:
- **`fact_rent_cells`**: Central fact table — one row per Mietspiegel cell (city × Lage × Baujahr × size)
- **`dim_cities`**: City metadata (name, state, population)
- **`dim_lage`**: Wohnlage categories (einfach, mittel, gut)
- **`dim_baujahr`**: Building age bands with year ranges
- **`dim_size_class`**: Apartment size categories

## Analytics Queries (`queries.sql`)

10 production-quality SQL queries answering core business questions about the German rental market. All use parameterized patterns compatible with BigQuery and Looker.

| Query | Business Question |
| :--- | :--- |
| `q1_city_ranking` | Which city has the highest official rent for a gut-Lage mid-size apartment? |
| `q2_rent_per_sqm_by_district` | Which Berlin Bezirke offer the most/least space per euro? |
| `q3_supply_by_size_band` | What is the market distribution of available unit sizes? |
| `q4_price_vs_age_correlation` | How does building age impact rental price? |
| `q5_expensive_districts` | Which districts are ultra-premium (top 10%)? |
| `q6_wohnlage_premium` | What is the rent premium for gut vs einfach Lage? |
| `q7_year_over_year_growth` | How have Mietspiegel values changed across editions? |
| `q8_city_size_matrix` | Average rent segmented by city and size class? |
| `q9_district_density` | Which areas have the densest concentration of rental units? |
| `q10_market_vs_official_gap` | Where is the gap between Immoscout market rent and official Mietspiegel widest? |

## Looker Model (`looker_mietspiegel.model.lkml`)

984-line LookML model with explores for:
- `rent_cells` — Core rent table
- `cities` — City metadata
- `immoscout` — Berlin Immoscout24 market rent grid
- `historical_trends` — Berlin YoY Mietspiegel editions (2013–2023)
- `berlin_districts` — Berlin 12 Bezirke Wohnlage distribution

## Usage

```bash
bq query --use_legacy_sql=false < queries.sql
```
