# Format Variation Catalog

> **Purpose:** Document how each city's Mietspiegel format differs from the standard reference model (Berlin 2024: 3 Wohnlage categories, 8 Baujahr periods, 4 size ranges, single Mittelwert values).
> 
> This catalog feeds the normalization layer (task 2.6) and should be updated as new cities are extracted.

---

## Standard Reference (Berlin 2024)

| Dimension | Structure | Notes |
|-----------|----------|-------|
| **Wohnlage** | 3-tier: einfach, mittel, gut | |
| **Bauperiods** | 8 periods (bis 1918 → 2011-2024) | |
| **Size groups** | 4 brackets (bis 40, 40-60, 60-90, über 90 m²) | |
| **Values per cell** | Single Mittelwert (€/m² net cold) | No untere/obere Spanne |
| **Type** | qualifiziert | |

---

## Cities with Complete Table Data

### Matches Standard (3 lages × 8 Baujahr × 4 sizes)

| City | State | Year | Lages | Baujahr | Sizes | Notes |
|------|-------|------|-------|---------|-------|-------|
| Berlin | Berlin | 2024 | 3 | 8 | 4 | Reference standard |
| Düsseldorf | Nordrhein-Westfalen | 2024 | 3 | 8 | 4 | |
| Frankfurt am Main | Hessen | 2024 | 3 | 8 | 4 | |
| Hannover | Niedersachsen | 2024 | 3 | 8 | 4 | |
| Leipzig | Sachsen | 2024 | 3 | 8 | 4 | |
| Essen | Nordrhein-Westfalen | 2024 | 3 | 8 | 4 | Only 8 total rows (sparse?) |
| Hamburg | Hamburg | 2024 | 3 | 8 | 4 | |
| München | Bayern | 2025 | 3 | 8 | 4 | |
| Stuttgart | Baden-Württemberg | 2024 | 3 | 8 | 4 | |

### Deviations from Standard

| City | State | Year | Lages | Baujahr | Sizes | Rows | Deviations |
|------|-------|------|-------|---------|-------|------|------------|
| **Aachen** | Nordrhein-Westfalen | 2024 | 3 | **1** | 4 | 16 | Only 1 aggregated Baujahr period. All 16 rows under a single period — need to verify if this is a simplified extraction or Aachen's actual format. |
| **Braunschweig** | Niedersachsen | 2025 | 3 | **1** | 4 | 40 | Only 1 aggregated Baujahr period. 40 rows suggests detailed size/spec data collapsed to one period. |
| **Bremen** | Bremen | 2024 | 3 | **8** | 4 | 8 | Only 8 total rows (1 per Baujahr). Likely missing size dimension. |
| **Dresden** | Sachsen | 2025 | 3 | **5** | 4 | 15 | 5 Baujahr periods (vs 8). Older buildings grouped differently. |
| **Freiburg im Breisgau** | Baden-Württemberg | 2024 | 3 | **8** | 4 | 9 | Only 9 rows (mostly empty table?). |
| **Halle (Saale)** | Sachsen-Anhalt | 2026 | 3 | **1** | 4 | 17 | Only 1 aggregated Baujahr period. |
| **Köln** | Nordrhein-Westfalen | 2024 | 3 | 8 | 4 | 15 | Slightly sparse (should be 24 rows for 3 lages × 8 periods). |
| **Nürnberg** | Bayern | 2024 | 3 | **8** | 4 | 9 | Only 9 rows — sparse extraction. |

---

## Placeholder Cities (no table data yet)

These 11 cities have metadata (location, state) but no extracted rent tables:

| City | State | Priority |
|------|-------|----------|
| Augsburg | Bayern | High (300k pop) |
| Bielefeld | Nordrhein-Westfalen | High |
| Bonn | Nordrhein-Westfalen | High |
| Chemnitz | Sachsen | Medium |
| Duisburg | Nordrhein-Westfalen | High |
| Kiel | Schleswig-Holstein | High |
| Lübeck | Schleswig-Holstein | Medium |
| Mainz | Rheinland-Pfalz | High |
| Mannheim | Baden-Württemberg | High |
| Moenchengladbach | Nordrhein-Westfalen | Medium |
| Rostock | Mecklenburg-Vorpommern | Medium |

---

## Cross-Cutting Observations

1. **All cities use single Mittelwert** — No city has untere/obere Spanne in the extracted data. This is either a simplification choice in the extraction pipeline or these cities publish only the mean value.

2. **Sizes are normalized to 4 tiers** — Every city uses bis 40, 40-60, 60-90, über 90 m² regardless of their native size brackets. This is good for comparison but loses granularity.

3. **Baujahr periods vary widely** — 5 to 8 periods depending on city. Aachen/Braunschweig/Halle show only 1 period, which is likely an extraction error (need re-extraction).

4. **Köln and Nürnberg have sparse tables** — They show fewer rows than expected for 3 lages × 8 periods × 4 sizes. May need re-extraction.

---

## Recommended Normalization Rules

1. **Lage:** Map all to 3-tier (einfach/mittel/gut). If city has only 2, map to (mittel/gut) or (einfach/mittel).
2. **Baujahr:** Preserve original periods in the data. For comparison, map to 8 standard periods via lookup table.
3. **Sizes:** Keep current 4-tier system. Add native size ranges as metadata when available.
4. **Values:** Since all cities use single Mittelwert, comparison is straightforward. If untere/obere Spanne is added later, store as separate fields.
