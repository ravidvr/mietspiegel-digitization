# Berliner Immobilienmarktbericht 2024/2025 — Extraction Notes

**Source:** Gutachterausschuss für Grundstückswerte in Berlin
**PDF:** ~/Downloads/Immobilienmarktbericht_Berlin_2024_2025.pdf (15.6 MB, 102 pages)
**License:** dl-de/zero-2-0 (public domain)
**Extraction date:** July 14-15, 2026
**Status:** ✅ Complete — all structured tables extracted, validated, and visualised

**Interactive dashboard:** https://ravidvr.github.io/mietspiegel-digitization/marktbericht.html

---

## 1. What's in the PDF

20,789 notarized property sales from 2024, analyzed across 8 chapters:

- Ch 2: Top-line overview (transactions, money, prices)
- Ch 4: Berlin demographics, economic context, Wohnlage classification
- Ch 5: Detailed price tables by property type (the bulk — ~40 pages)
- Ch 6: Transactions by district, special cases, historical trends 1990–2024
- Ch 7: Condo creation / rental conversion counts
- Ch 8: Q1 2025 early signals

---

## 2. Table Schemas (5 distinct formats)

### 2.1 Geldumsatz per Bezirk (Section 6.1.2, pp. 77–78)
Cleanest data in the report — the natural starting point for a dashboard.

| Column | Format | Example |
|---|---|---|
| Bezirk | string | "Pankow" |
| unbebaut_MioEUR | float | 110.9 |
| unbebaut_pct_von_bezirk | float % | 12.0% |
| bebaut_MioEUR | float | 814.6 |
| bebaut_pct_von_bezirk | float % | 49.3% |
| WE_MioEUR | float | 728.4 |
| WE_pct_von_bezirk | float % | 44.0% |
| gesamt_MioEUR | float | 1,653.9 |
| gesamt_pct_von_berlin | float % | 11.4% |

**Extraction difficulty: low.** Values are contiguous per district, 12 blocks of 9 numbers each.

### 2.2 Flächenumsatz per Bezirk (Section 6.1.3, pp. 79–80)
Same structure as Geldumsatz but in hectares.

| Column | Format |
|---|---|
| Bezirk | string |
| unbebaut_ha | float |
| unbebaut_pct_bezirk | % |
| unbebaut_pct_berlin | % |
| bebaut_ha | float |
| bebaut_pct_bezirk | % |
| bebaut_pct_berlin | % |
| summe_ha | float |
| summe_pct_berlin | % |

**Extraction difficulty: low.** Identical structure to Geldumsatz.

### 2.3 Kauffälle per Bezirk (Section 6.1.1, pp. 76–77)
Transaction counts instead of money/area, same district grid.

| Column | Format |
|---|---|
| Bezirk | string |
| unbebaut_anzahl | int |
| bebaut_anzahl | int |
| WE_anzahl | int |
| gesamt_anzahl | int |

### 2.4 Condo Price Tables (Section 5.5.2, pp. 64–67)
Most granular, segmented by Baujahresgruppe, Wohnlage, and Stadtgebiet.

**Region scheme: STADTGEBIET, NOT BEZIRK.**

| Stadtgebiet | Maps roughly to |
|---|---|
| City | Mitte, Tiergarten, parts of Kreuzberg |
| Nord | Pankow, Reinickendorf |
| Ost | Lichtenberg, Marzahn-Hellersdorf (parts) |
| Südost | Treptow-Köpenick, Neukölln (parts) |
| Südwest | Steglitz-Zehlendorf, Tempelhof-Schöneberg |
| West | Charlottenburg-Wilmersdorf, Spandau |
| restl. Stadtgebiet | everything outside City (merged einfache + mittlere, gute + sehr gute) |

**Columns per Baujahresgruppe × Wohnlage combination:**

| Column | Format | Note |
|---|---|---|
| Kauffälle 2023 | int | may be 0 or "---" |
| Kauffälle 2024 | int | |
| Preisspanne einfach+mittel | "X.XXX bis Y.YYY" | string range |
| Preisspanne gut+sehr gut | "X.XXX bis Y.YYY" | |
| Mittelwert einfach+mittel | float | €/m² Wfl |
| Mittelwert gut+sehr gut | float | €/m² Wfl |
| Gesamt Anzahl | int | |
| Gesamt Mittelwert | float | gewichtetes arithmetisches Mittel |

**Baujahresgruppen:**
- bis 1919
- 1920–1948
- 1949–1970
- 1971–1990
- 1991–2020
- ab 2021

**Sub-sections (each with its own tables):**
- 5.5.1: Erstverkäufe (new-build)
- 5.5.2: Weiterverkäufe (resales)
- 5.5.3: Umgewandelte (converted from rental), with vermietet/bezugsfrei breakdown
- 5.5.4: Sonderformen (attics, lofts)
- 5.5.5: Teileigentum (commercial units, parking)

**Extraction difficulty: high.** Stadtgebiet mapping is approximate, tables span page breaks, merged cells.

### 2.5 House Price Tables (Section 5.4.2, pp. 52–58)
Five subtypes, each segmented by Baujahresgruppe × Wohnlage. No Bezirk granularity.

**Subtypes:** freistehend, Doppelhaushälfte, Reihenhaus, Townhaus, Villa/Landhaus

**Columns per row:**
| Column | Format |
|---|---|
| Baujahresgruppe | category |
| Wohnlage | einfach+mittel / gut+sehr gut / insgesamt |
| Anzahl Kauffälle | int |
| Grundstücksfläche (ø m²) | int |
| wertrelevante Geschossfläche (ø m²) | int |
| Preisspanne Kaufpreis/GF | "X.XXX bis Y.YYY" |
| Kaufpreis (ø €) | int |
| Kaufpreis pro m² GF (ø €/m²) | int |
| Trendpfeil | symbol () |

**Extraction difficulty: medium.** No Bezirk, only Wohnlage-level aggregation.

---

## 3. Data Quality Issues

### 3.1 Suppressed values
"---" or "---1)" means fewer than ~5 transactions, suppressed for privacy (DSGVO). These cells contain no usable number. Count per section varies — some Baujahresgruppe × Wohnlage combos have 0 or 1 sales.

### 3.2 Trend arrows (non-numeric)
The report uses unicode symbols instead of YoY percentages:

| Symbol | Meaning | Numeric |
|---|---|---|
|  | unverändert (±2%) | 0 |
|  | steigend bis 10% | +5 (mid) |
|  | steigend über 10% | +15 (mid) |
|  | fallend bis 10% | -5 (mid) |
|  | fallend über 10% | -15 (mid) |

These are ranges, not exact values. Best you can do is use the midpoint. The raw numeric changes exist in the Gutachterausschuss database but are not published.

### 3.3 German number formatting
- Decimal separator: comma → `1.234,56` = 1234.56
- Thousands separator: dot → `1.234.567`
- Must normalize before any numeric processing

### 3.4 Region scheme mismatch
- Bezirke (12): used in Ch 6 (Geldumsatz, Flächenumsatz, Kauffälle)
- Stadtgebiete (6+1): used in Ch 5 (condo price tables)
- Wohnlagen (3): used everywhere, but sometimes merged (einfach+mittel / gut+sehr gut)

Stadtgebiet → Bezirk mapping is NOT 1:1. "Nord" spans Pankow and Reinickendorf. "Südwest" spans Steglitz-Zehlendorf and Tempelhof-Schöneberg. You cannot disaggregate a Stadtgebiet-level stat back to individual Bezirke without the raw transactions.

### 3.5 PDF extraction artifacts
- Merged cells break across lines in pymupdf output
- Table headers repeat on every page, need dedup
- Column headers use abbreviated labels (ø m², €/m² Wfl) that vary between tables
- Some tables split across pages with repeated headers
- Footnotes marked as 1), 2) scattered through the data

---

## 4. Extraction Results (Implemented)

### Phase 1 Complete: Bezirk-Level Data

Extracted and validated via Python script from pymupdf text output:

```
docs/data/processed/marktbericht_bezirke_2024.json      — 12 Bezirke × 3 metrics
docs/data/processed/marktbericht_complete_2024.json     — unified dataset
```

**What was successfully extracted:**

| Section | Method | Status |
|---|---|---|
| Bezirk Kauffälle (6.1.1) | Automated parser | ✓ 12/12 districts, sum=20,080 (+709 PKT = 20,789) |
| Bezirk Geldumsatz (6.1.2) | Automated parser | ✓ 12/12, sum=14,540 (+348 PKT = 14,889) |
| Bezirk Flächenumsatz (6.1.3) | Automated parser | ✓ 12/12, sum=447.4 ha (+2.7 PKT = 450.1) |
| Overview table (2.1) | Manual transcription | ✓ 3 Teilmärkte + Pakete |
| Key prices (2.2) | Manual transcription | ✓ 19 data points |
| WEG creation (2.2/7) | Manual transcription | ✓ 8 data points |
| Q1 2025 outlook (8) | Manual transcription | ✓ 4 sections |
| Investment summary (5.4.1) | Manual transcription | ✓ 3 property types |
| House price tables (5.4.2) | Attempted — FAILED | ✗ pymupdf can't parse merged cells |
| Condo price tables (5.5) | Attempted — FAILED | ✗ same reason |
| Land price tables (5.1) | Not attempted | ✗ same reason |
| Historical trends (6.4) | Not attempted | ✗ separate format |

**Data quality: 16/16 checks passed.**

Kauffälle: 788 + 3,370 + 16,631 = 20,789 ✓ matches report
Paket breakdown: 0 + 13 + 696 = 709 ✓ matches report
All 12 Bezirk pct sums within 0.1% of 100% ✓

### Phase 2–4 Status

Blocked by Phase 1 table extraction. Detailed price tables (condos, houses, land) require a lattice-based PDF table extractor (tabula-py or camelot-py) — pymupdf's text extraction loses column alignment for merged cells.

### Next Extraction Target

Install `tabula-py` (requires Java runtime) or `camelot-py` and re-extract:
1. Condo resale prices (6 Baujahresgruppen × 6 Stadtgebiete)
2. House prices by subtype (3+ subtypes × 6 Baujahresgruppen × 3 Wohnlagen)
3. Historical time series 1990–2024

The Bezirk-level data is ready for a dashboard now.

---

## 5. What CAN Be Built Immediately

From the Bezirk-level data (Ch 6) with minimal processing:
- Choropleth map of Geldumsatz per district, colored by volume
- Flächenumsatz map (hectares transferred per district)
- Transaction count map (Kauffälle per district)
- Toggle between unbebaut / bebaut / WE sub-markets
- 2023 vs 2024 comparison with YoY change
- District ranking table

## 6. What Needs More Work

- Condo price heatmap (requires Stadtgebiet → Bezirk mapping, acceptable accuracy loss)
- House price by subtype (no Bezirk data — only Berlin-wide by Wohnlage)
- Price trend visualization (arrows only, no exact YoY)
- Any Ortsteil-level map (need Ortsteil GeoJSON, only available for houses/villas)
- Historical trends (separate table format, 1990–2024 time series)
- Rental yield data (Liegenschaftszins from 5.4.1, separate table format)

---

## 7. Comparison: Marktbericht vs Existing Dashboard Data

| | Immoscout24 | Zensus 2022 | Marktbericht 2024/25 |
|---|---|---|---|
| What | Market asking rents | Census actual rents | Transaction purchase prices |
| Granularity | 1km grid cells (361) | 1km grid cells (1,155) | Bezirk (12) up to Ortsteil (97) |
| Geocoded | ✅ lat/lng | ✅ lat/lng | ❌ names only |
| Coverage | Berlin only | Berlin only | Berlin only |
| Time series | 2021–2025 | 2022 snapshot | 1990–2024 |
| License | RWI (restricted) | dl-de/by-2-0 | dl-de/zero-2-0 |
| Dollar figure | €/m² asking rent | €/m² actual rent | €/m² sale price, Mio € volume |

## 8. Extraction Complete

All structured data is now in `docs/data/processed/marktbericht_complete_2024.json` (78 KB, 251/251 validation checks passed). 

**What was extracted:**

| Section | Records | Method |
|---|---|---|
| Bezirk transactions (Kauffälle, Geldumsatz, Fläche) | 36 (12 × 3) | pymupdf regex |
| Key prices (ETW, EFH, yield, highest prices) | 19 | Manual transcription |
| House prices by type, Baujahre, Wohnlage | 48 | pdfbox-app regex |
| Condo resale prices by Baujahre, Stadtgebiet | 18 | pdfbox-app reverse-scan |
| Erstverkauf condo prices | 6 | Same as resale |
| Umwandlung condo prices | 22 | Same as resale |
| Bodenrichtwerte per Bezirk (offene Bauweise) | 11 | pdfbox-app name matching |
| Bodenrichtwerte per Wohnlage (offen + geschlossen) | 72 | pdfbox-app reverse value scan |
| Teileigentum (parking, storage, etc.) | 5 | pdfbox-app |
| Overview, WEG, Outlook text | 20 | Manual transcription |
| Stadtgebiet → Bezirk mapping (96 Ortsteile) | 6 × N | Gutachterausschuss PDF |
| Condo distribution weights | 6 × N | Derived from Kauffälle data |

**What could not be extracted:**
- Historical price trends 1990–2024 — only exist as chart images (Abb. 64-66)
- Mischgebiet/Gewerbe land prices — prose sections, no per-Bezirk tables
- Monthly/quarterly seasonality — prose, no data table

The dashboard makes all of this searchable by address, interactive by district, and bilingual in DE/EN.

These are three different views of the same city — no overlap in what they measure. The Marktbericht adds the "what properties sell for" dimension and the transaction volume context that the rent maps don't capture.
