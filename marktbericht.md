# Marktbericht — Berliner Immobilienmarktbericht 2024/2025

**Source:** Gutachterausschuss für Grundstückswerte in Berlin
**Published:** August 2025 | **Report year:** 2024
**File:** ~/Downloads/Immobilienmarktbericht_Berlin_2024_2025.pdf
**License:** dl-de/zero-2-0 (public domain, no attribution required)
**Data basis:** 20,789 notarized sales contracts from the Kaufpreissammlung (§195 BauGB)

---

## What This Is

The Berlin Gutachterausschuss collects every property sale contract in the city. Notaries are legally required to send copies. They read them all, record what sold, where, for how much, size, age, location quality — then publish this annual report. It's actual transaction data, not asking prices or estimates.

2024 was the recovery year: transactions up 18%, money volume up 20%, but prices still declining across most segments. Q1 2025 suggests the price slide may be bottoming out.

---

## 1. Top-Line Numbers (2024 vs 2023)

| Metric | 2023 | 2024 | Change |
|---|---|---|---|
| Total transactions | 17,563 | 20,789 | +18% |
| Total money volume | 12.4 Mrd € | 14.9 Mrd € | +20% |
| Land area sold | 456 ha | 450 ha | -1% |
| Condo floor area sold | 881,000 m² | 1,053,000 m² | +19% |
| Package deals | 580 cases / 172 pkgs | 709 cases / 192 pkgs | +22% |

### By Market Segment

| Segment | Kauffälle | Change | Geldumsatz | Change | Fläche |
|---|---|---|---|---|---|
| Undeveloped land | 788 | +14% | 925 Mio € | +19% | 116 ha |
| Developed properties | 3,370 | +15% | 7,991 Mio € | +22% | 334 ha |
| Condos (WE/TE) | 16,631 | +19% | 5,973 Mio € | +18% | 1.05 Mio m² |
| **Total** | **20,789** | **+18%** | **14,889 Mio €** | **+20%** | — |

### Umsatz Shares (2024)
- Condos: 77% of transactions, 38% of money
- Developed properties: 16% of transactions, 53% of money
- Undeveloped land: 4% of transactions, 6% of money
- Package deals: 3% of transactions, 3% of money

---

## 2. Key Prices (2024)

| Property Type | Avg Price | Unit | YoY Change |
|---|---|---|---|
| Single/two-family houses | 3,800 | €/m² Gfkl | -7% |
| Pure rental apartment buildings | 1,915 | €/m² Gfkl | -6% |
| Mixed-use buildings | 1,855 | €/m² Gfkl | -10% |
| Condos (all resales) | 5,251 | €/m² Wfl | -1% |
| Condos (new-build) | 7,912 | €/m² Wfl | +1% |
| Parking space | 31,658 | € | +1% |

### Record Sales
- Highest condo: 8.3 Mio € (22,000 €/m²) — Charlottenburg
- Highest house: 12,120 €/m² Wfl — Grunewald
- Highest villa: 17.2 Mio € — Kladow
- Highest parking: ~100,000 € — Mitte

### Land Value Changes (Bodenrichtwerte, Jan 2025)
- Office/retail land: -10 to -30%
- Individual housing land: -5%
- MFH land: unchanged
- Simple commercial (IKEA-scale): unchanged

---

## 3. Price Development by Property Type (Chapter 5)

### 3.1 Bauland (Undeveloped Land)
Five sub-types with min/max/mean/median per district and Wohnlage:
- `bauland_offen` — individual housing, open construction
- `bauland_geschlossen` — MFH, closed construction
- `bauland_misch_kern` — mixed-use / core-area
- `bauland_gewerbe` — commercial land
- `sanierung_entwicklung` — redevelopment areas

Each record: Bezirk, Wohnlage, Kauffälle, min/mean/median/max €/m², Bodenrichtwert ratio.

### 3.2 Special Land Types
- `bauerwartungsland` — expected future building land
- `rohbauland` — raw building land
- `gemeinbedarfsflaechen` — public-purpose land
- `land_forstwirtschaft` — agriculture/forestry
- `sonstige_flaechen` — other non-building land

### 3.3 Investment Properties (Renditegrundstücke)
- **Mietwohnhäuser** (pure rental): Preis/m² Gfkl, Liegenschaftszins (cap rate), Jahresrohertrag, Baujahr, Wohnlage, Bezirk
- **Wohn- und Geschäftshäuser** (mixed-use): same + Gewerbeanteil
- **Büro- und Geschäftsimmobilien** (office/commercial): Preis/m² Nfl, Nutzfläche

### 3.4 Single/Two-Family Houses
Five subtypes, each with Preis/m² Wfl, Preis/m² Gfkl, Grundstücksfläche, Wohnfläche, Baujahr, Bezirk, Ortsteil:
- `freistehend` — detached
- `doppelhaushaelfte` — semi-detached
- `reihenhaus` — row house
- `townhaus` — townhouse
- `villa_landhaus` — villa / country house

### 3.5 Condominiums (Wohnungseigentum)
| Subtype | Description |
|---|---|
| `etw_neubau_mfh` | New-build condos in MFH |
| `etw_neubau_eigenheim` | New-build condo homes |
| `etw_resale_mfh` | Resale condos in MFH |
| `etw_resale_eigenheim` | Resale condo homes |
| `etw_umwandlung_mfh` | Converted from rental in MFH |
| `etw_umwandlung_eigenheim` | Converted rental homes |
| `dachgeschoss_ausbau` | Converted attic apartments |
| `lofts` | Loft apartments |
| `teileigentum` | Non-residential partial ownership |
| `stellplatz` | Parking spaces |

Each record: Bezirk, Ortsteil, Wohnlage, Kauffälle, Kaufpreis/€/m² Wfl, Wohnfläche, Baujahr, Zimmer, Geschoss.

---

## 4. Transactions by District (Chapter 6)

Per district (all 12 Bezirke):
- Kauffälle, Geldumsatz (Mio €), Flächenumsatz (ha)
- Broken down by: unbebaut, bebaut, WE/TE
- Historical time series from 1990

Special breakdowns:
- Monthly transaction counts (seasonality)
- Individual sales over 10 Mio €
- Foreclosures: 118 cases (-5%), by property type
- Leasehold transactions (Erbbaurecht)

---

## 5. Condo Creation (Chapter 7)

| Type | 2023 | 2024 | Change |
|---|---|---|---|
| New WEG units total | ~8,100 | 4,206 | -48% |
| New-build condos | ~3,650 | 2,654 | -27% |
| Rental conversions | ~4,450 | 1,552 | -65% |

Top conversion districts: Weißensee (253), Prenzlauer Berg (157)
Top new-build districts: Treptow (532), Reinickendorf (445), Köpenick (435)

---

## 6. Q1 2025 Early Signals (Chapter 8)

| Indicator | Change (Q1 2025 vs Q1 2024) |
|---|---|
| Transaction count | +28% |
| Money volume | +8% |
| Rental buildings price | +10% |
| Individual housing land | -5% |
| New single-family homes | +12% |
| New condos | +10% |

The report warns: Q1 price changes are "statistisches Rauschen" — driven by sample composition, not genuine appreciation. The market appears to be bottoming out, not yet rising. ECB rate cuts are happening but financing remains expensive. High building costs and CO₂ tax/sanierung requirements continue to suppress price growth. Verdict: Bodenbildung (price floor forming), no uptrend yet.

---

## 7. Segments and Dimensions

Every data point can be sliced by:
- **Bezirk** — 12 Berlin districts
- **Ortsteil** — 97 sub-districts (for houses and condos)
- **Wohnlage** — einfach / mittel / gut (3-tier location quality)
- **Baujahr** — construction year (for developed properties)
- **Zimmer** — room count (for condos)
- **Geschoss** — floor level (for condos)
- **Year** — 1990–2024 for historical trends

### Berlin Districts (12)
Mitte · Friedrichshain-Kreuzberg · Pankow · Charlottenburg-Wilmersdorf · Spandau · Steglitz-Zehlendorf · Tempelhof-Schöneberg · Neukölln · Treptow-Köpenick · Marzahn-Hellersdorf · Lichtenberg · Reinickendorf

### Core Unit Abbreviations
| Abbr | Meaning |
|---|---|
| Wfl | Wohnfläche (living space) |
| Gfkl | wertrelevante Geschossfläche (value-relevant floor area) |
| Nfl | Nutzfläche (usable floor area) |
| WE | Wohnungseigentum (condominium) |
| TE | Teileigentum (partial ownership) |
| WEG | Wohnungseigentumsgesetz |
| MFH | Mehrfamilienhaus (multi-family building) |
| EFH/ZFH | Ein-/Zweifamilienhaus (single/two-family house) |
