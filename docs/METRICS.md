# Metric Dictionary — Mietspiegel Digitization

**All rent values in this project are Nettokaltmiete (net cold rent) in €/m²/month — unless explicitly stated otherwise.**

---

## What is Nettokaltmiete?

In Germany, rent is reported two ways:

| Term | German | Meaning |
|------|--------|---------|
| **Net cold rent** | Nettokaltmiete / Kaltmiete | Base rent per m². Excludes heating, water, garbage, and other Betriebskosten (operating costs). This is the legally regulated figure in Mietspiegel tables. |
| **Gross warm rent** | Warmmiete / Bruttowarmmiete | Total monthly payment. Includes cold rent + Betriebskosten + heating. NOT used in this project. |

**Example:** A 60 m² apartment in Berlin-Mitte (mittel Lage, 2011-2024 Baujahr) rents for €10.07/m² Nettokaltmiete = €604.20/month base rent. With ~€3.00/m² for Betriebskosten and heating, the Warmmiete would be ~€13.07/m² = ~€784/month total.

All Mietspiegel values are **reference rents for new leases** (Neuvertragsmiete), not existing contracts (Bestandsmiete). New leases are typically 20-40% higher than rents paid by long-term tenants.

---

## Data Sources & Metrics

### 1. Official Mietspiegel (23 cities)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `bis_40` | float | €/m² | Net cold rent for apartments ≤ 40 m² |
| `40_60` | float | €/m² | Net cold rent for apartments 40–60 m² |
| `60_90` | float | €/m² | Net cold rent for apartments 60–90 m² |
| `ueber_90` | float | €/m² | Net cold rent for apartments > 90 m² |

**Dimensions:**
- **Wohnlage** (location quality): `einfach` (simple), `mittel` (medium), `gut` (good). Some cities use 2 or 4 tiers.
- **Baujahr** (construction year): `bis 1918` through `2014+`. 6–8 groups per city depending on local Mietspiegel structure.
- **Size class**: 4 standard buckets as above.

**Source:** Official PDF Mietspiegel tables published by each city. Legally binding reference rents (qualifizierter Mietspiegel where available).

**Value range across 23 cities:** €4.43/m² (Halle, einfach, pre-1918, large) to €30.00/m² (München, gut, 2014+, small).

---

### 2. Immoscout24 Market Rents (Berlin only)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `rent_per_sqm` | float | €/m² | **Net cold asking rent** from Immoscout24 listings, aggregated at 1 km² grid cells |
| Grid cell ID | string | — | RWI-GEO-REDX PUF v16 grid cell identifier |
| `year` | int | — | Year of listing data |

**Coverage:** 467 grid cells across Berlin. 9,407 observations (2008–2025).

**Source:** RWI-GEO-REDX PUF v16 (DOI: 10.7807/IMMO:REDX:PUF:V16). Research dataset from RWI Essen.

**Note:** These are **market asking rents** (Angebotsmiete), typically higher than Mietspiegel reference rents. The market premium (Immoscout ÷ Mietspiegel) varies by neighborhood.

---

### 3. Zensus 2022 Census Rents (Berlin only)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `nettokaltmiete` | float | €/m² | **Net cold rent** reported by tenants in the 2022 German census, aggregated to 1 km² grid cells |

**Coverage:** 1,155 cells across Berlin at 100 m resolution, aggregated to 1 km for privacy.

**Source:** Zensus 2022, Destatis. License: dl-de/by-2.0.

**Note:** These are **existing contract rents** (Bestandsmiete) from a census snapshot, typically lower than both Mietspiegel reference rents and Immoscout market rents. This reflects the gap between what long-term tenants actually pay vs. what new tenants would pay.

---

### 4. Berlin Bezirke (District Aggregates)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `estimated_rent` | float | €/m² | Estimated average **net cold rent** per Bezirk, derived from 400,505 address-level WFS points with Wohnlage classification |
| `einfach_pct` | float | % | Percentage of addresses in einfache Wohnlage |
| `mittel_pct` | float | % | Percentage of addresses in mittlere Wohnlage |
| `gut_pct` | float | % | Percentage of addresses in gute Wohnlage |

**Source:** Berlin Senate WFS (Wohnlagenadr2026). License: dl-de/zero-2.0.

**Coverage:** 12 Bezirke: Mitte, Friedrichshain-Kreuzberg, Pankow, Charlottenburg-Wilmersdorf, Spandau, Steglitz-Zehlendorf, Tempelhof-Schöneberg, Neukölln, Treptow-Köpenick, Marzahn-Hellersdorf, Lichtenberg, Reinickendorf.

---

### 5. Bodenrichtwerte (Land Values, Berlin only)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `bodenrichtwert` | float | €/m² | Official land value per m² of land area (not living space) |

**Source:** Berlin Gutachterausschuss, BORIS Berlin.

**Coverage:** Zonal values for Berlin. Updated every 2 years.

---

### 6. Historical Mietspiegel Editions (Berlin only)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `by_lage_same_cohort` | float | €/m² | Per edition and Wohnlage: average of the official Mittelwerte for buildings from 1991–2002, the one age group in every edition (the like-for-like series) |
| `by_lage` | float | €/m² | The same average for each edition's newest age group (2003–2015 in 2017, 2003–2017 from 2019), so it mixes two definitions |

Both averages leave out cells the official table marks as based on too few rents.

**Editions tracked:** 2017, 2019, 2021, 2023 (`berlin_historical.json`). 2013 and 2015 aren't in the official archive. 2021 and 2023 weren't new surveys: they raised every value of the previous table by a flat 1.1% and 5.4%. The current table (2024) is in `berlin.json`.

**Source:** Official Mietspiegeltabelle PDFs from the Berlin Senate archive (`data/raw/`).

---

### 7. Baugenehmigungen & Baufertigstellungen (Berlin only)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `genehmigt` | int | count | Building permits issued (new residential units) |
| `fertiggestellt` | int | count | Completed residential units |
| `wohnungsbestand` | int | count | Total housing stock |

---

## Key Calculations & Derived Metrics

| Metric | Formula | Unit | Description |
|--------|---------|------|-------------|
| **Gut/Einfach spread** | avg(gut) ÷ avg(einfach) | ratio | Rent inequality within a city. Dresden 1.05 (fairest), Essen 2.24 (most unequal). |
| **Market premium** | Immoscout ÷ Mietspiegel | ratio | How much above the official reference rent are market asking rents? |
| **Size discount** | bis_40 ÷ ueber_90 | ratio | How much more per m² do small apartments cost vs. large ones? |
| **New-build premium** | post-2010 ÷ pre-1918 | ratio | How much more does a new building cost vs. a prewar one? |
| **Z-score** | (value − Berlin_mean) ÷ Berlin_std | σ | Berlin-local normalization. Positive = above Berlin average. |

---

## What This Project Does NOT Measure

- **Warmmiete / Bruttowarmmiete** (total rent with utilities). Mietspiegel tables only regulate the net cold component.
- **Existing contract rents** (except Zensus 2022 snapshot). The Mietspiegel is a reference for new leases.
- **Furnished / short-term rents.** Mietspiegel applies to unfurnished long-term rentals.
- **Staffelmiete / Indexmiete** (graduated or indexed rent contracts). Only the base reference rent is captured.
- **Actual transaction prices for purchases.** This project covers rents, not sale prices. See the separate [Berlin Property Market](https://github.com/ravidvr/berlin-property-market) project for purchase data.

---

*Last updated: 2026-07-26*
