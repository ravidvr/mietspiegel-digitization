# Tokyo Rental Market Analytics

This directory contains the SQL analytics layer for the Tokyo apartment rental dataset. 

## Data Warehouse Schema

The underlying data is structured in a traditional BigQuery **Star Schema**, optimized for OLAP and reporting. The schema consists of one central fact table surrounded by four dimensional tables:

*   **`fact_rent_observation`**: The central fact table. Contains the quantitative metrics (monthly rent, management fees, area, etc.) and foreign keys linking to the dimensions.
*   **`dim_city`**: Geographic dimension at the municipal/city level (e.g., Shibuya, Shinjuku).
*   **`dim_district`**: Geographic dimension at the specific neighborhood/district level (e.g., Dogenzaka, Kamiyamacho).
*   **`dim_size_band`**: Categorical dimension standardizing property sizes into discrete buckets (e.g., "30-40 sqm", "40-50 sqm").
*   **`dim_build_year`**: Temporal dimension capturing the construction year/decade of the property.

## Analytics Queries (`queries.sql`)

The `queries.sql` file contains 10 pre-configured queries designed to answer core business questions about the Tokyo rental market. 

| Query Name | Business Question | Grain | Expected Output |
| :--- | :--- | :--- | :--- |
| `q1_avg_rent_by_city` | What is the average rental cost across different cities? | City | City name, average rent |
| `q2_rent_per_sqm_by_district` | Which neighborhoods offer the most/least space per yen? | District | District name, average rent per square meter |
| `q3_supply_by_size_band` | What is the market distribution of available unit sizes? | Size Band | Size category, unit count, percentage of total |
| `q4_price_vs_age_correlation` | How does the age of a building impact its rental price? | Build Decade | Decade, average rent, average unit size |
| `q5_expensive_districts` | Which districts are considered ultra-premium (top 10%)? | District | District name, average rent, total units |
| `q6_fee_impact_analysis` | Do high monthly management fees correlate with higher base rent? | Size Band | Size category, avg base rent, avg management fee |
| `q7_year_over_year_supply` | How has construction volume changed over recent years? | Build Year | Year, number of properties built |
| `q8_city_size_matrix` | What is the average rent segmented by both city and size? | City, Size Band | Matrix/Cross-tab of city by size band with avg rent |
| `q9_district_density` | Which areas have the densest concentration of rental units? | District | District name, total unit count, avg area |
| `q10_accessibility_premium` | What is the rent difference between properties based on proximity to transit?* | Distance Band | Distance category, average rent |

*\*Note: Replace generic distance/proximity metrics with your actual transit access columns if applicable.*

### Usage
To execute these queries, ensure your BigQuery credentials are configured and run:
```bash
bq query --use_legacy_sql=false < queries.sql
```