# Historical Mietspiegel Tracking

Tracks previous Mietspiegel editions for Germany's largest cities, showing rent development over time and highlighting cities with the fastest/slowest growth.

## Data

**File:** `data/historical_mietspiegel.json`

Covers the 10 largest German cities (Berlin, Hamburg, Munich, Cologne, Frankfurt, Stuttgart, Düsseldorf, Leipzig, Dresden, Hannover) with Mietspiegel editions spanning 2013–2024.

Each entry includes:
- Edition year and type
- Base rent per sqm (net cold) for "mittlere Wohnlage" (middle residential location)
- Values by location category (einfach / mittel / gut)
- Source references

## Dashboard

**File:** `historical_trends.html`

Interactive visualization with:
1. **Line chart** — rent development over time for all cities. Toggle cities via legend. Switch between Wohnlage categories (einfach/mittel/gut).
2. **Growth ranking table** — cities ranked by total rent growth. Filter by period (total / last ~5 years / last ~3 years). Visual bars show relative growth.
3. **Edition history cards** — per-city detail with edition-by-edition values and growth arrows.
4. **Summary cards** — aggregate metrics: fastest/slowest growth, highest rent, total editions tracked.

## Key Findings (as of 2024)

| City | First | Latest | Total Growth | Annualized |
|------|-------|--------|-------------|------------|
| Berlin | €6.16 (2013) | €12.50 (2023) | +102.9% | +7.3%/yr |
| Munich | €10.50 (2013) | €17.80 (2023) | +69.5% | +5.4%/yr |
| Leipzig | €5.30 (2014) | €9.10 (2024) | +71.7% | +5.5%/yr |
| Hannover | €5.90 (2013) | €9.70 (2023) | +64.4% | +5.1%/yr |
| Frankfurt | €7.60 (2014) | €13.60 (2024) | +78.9% | +6.0%/yr |

## Sources

Official city Mietspiegel tables from each city's administration:
- Berlin: berlin.de/mietspiegel
- Hamburg: hamburg.de/mietspiegel  
- Munich: stadt.muenchen.de/infos/mietspiegel.html
- Cologne: stadt-koeln.de/mietspiegel
- Frankfurt: frankfurt.de/mietspiegel
- Stuttgart: stuttgart.de/mietspiegel
- Düsseldorf: duesseldorf.de/mietspiegel.html
- Leipzig: leipzig.de/mietspiegel
- Dresden: dresden.de/mietspiegel
- Hannover: hannover.de/mietspiegel

## Notes

- Only "qualifizierte Mietspiegel" editions (legally recognized) are tracked
- Values are for "mittlere Wohnlage", 60–80 sqm apartments, typical building-age cohort
- Some cities publish in even years (Frankfurt, Leipzig), others in odd (Berlin, Munich)
- Data will be refreshed as new editions are published
