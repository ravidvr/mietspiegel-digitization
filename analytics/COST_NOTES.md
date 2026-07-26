# BigQuery Cost Notes — mietspiegel-digitization

## Partitioning & Clustering Strategy

The fact table `fact_rent_observation` contains ~5,000 rows across 23 cities × 3 Wohnlage categories × 8 Baujahr groups × 4 size classes. At this scale, partitioning is about demonstrating competency, not cost savings.

### Recommended DDL

```sql
CREATE OR REPLACE TABLE `mietspiegel.fact_rent_observation`
PARTITION BY DATE_TRUNC(extract_date, MONTH)
CLUSTER BY city_slug, lage
AS SELECT ...;
```

### Why partition by extract_date

- Each Mietspiegel publication cycle adds a new batch of rows
- Queries filtering by "latest vintage only" scan only the most recent partition
- Partition pruning reduces bytes scanned by ~80% for common dashboard queries

### Why cluster by city_slug, lage

- Most analytical queries filter or group by city and Wohnlage
- Clustering eliminates full-table scans for per-city comparisons
- Combined with partitioning, typical query cost drops from ~50MB scanned to ~5MB

### Estimated cost comparison

| Query type | Without optimization | With partition + cluster | Savings |
|---|---|---|---|
| Latest Berlin rents | 50 MB | 5 MB | 90% |
| Cross-city ranking | 200 MB | 50 MB | 75% |
| Time-series by city | 500 MB | 100 MB | 80% |
| Full scan (rare) | 200 MB | 200 MB | 0% |

*Note: Actual costs depend on data volume. These are illustrative estimates based on ~5K rows × 23 cities pattern.*

---

## On-Demand vs. Flat-Rate Pricing

For a portfolio project with 5K rows:
- **On-demand:** ~$5/TB scanned. A full scan costs < $0.001. Monthly query cost with optimization: negligible.
- **Flat-rate:** Not warranted at this scale.

The real value is demonstrating that you *thought about* partitioning — a senior analyst at Delivery Hero or Zalando manages tables with billions of rows where this design pattern saves thousands per month.
