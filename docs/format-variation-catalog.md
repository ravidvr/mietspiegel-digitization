# Format Variation Catalog

> **Purpose:** Document how each city's Mietspiegel format differs from the standard model (3 Wohnlage categories × ~9 Bauperiods × ~16 size groups with untere/obere Spanne + Mittelwert). This catalog feeds the normalization layer (task 2.6).

---

## Standard Model (Berlin 2024 reference)

| Dimension | Structure |
|-----------|-----------|
| Wohnlage | 3-tier: einfach, mittel, gut |
| Bauperiods | 9 periods: bis 1918 → ab 2023 |
| Size groups | 14 brackets: <35 m² → ab 100 m² |
| Values per cell | untere Spanne, Mittelwert, obere Spanne (all €/m² net cold) |
| Type | qualifiziert |

---

## Cities 1-10 (Tier 1 — to be documented)

| # | City | Format | Differences from Standard |
|---|------|--------|--------------------------|
| 1 | Berlin | 3×9×14, 3-value | Baseline reference |
| 2 | Hamburg | TBD | |
| 3 | Munich | TBD | |
| 4 | Cologne | TBD | |
| 5 | Frankfurt | TBD | |
| 6 | Stuttgart | TBD | |
| 7 | Düsseldorf | TBD | |
| 8 | Leipzig | TBD | |
| 9 | Dresden | TBD | |
| 10 | Hannover | TBD | |

## Cities 11-20 (Tier 2a — to be documented)

| # | City | Format | Differences from Standard |
|---|------|--------|--------------------------|
| 11 | Nuremberg | TBD | |
| 12 | Bremen | TBD | |
| 13 | Duisburg | TBD | |
| 14 | Bochum | TBD | |
| 15 | Wuppertal | TBD | |
| 16 | Bielefeld | TBD | |
| 17 | Bonn | TBD | |
| 18 | Münster | TBD | |
| 19 | Mannheim | TBD | |
| 20 | Karlsruhe | TBD | |

## Cities 21-30 (Tier 2b — to be documented)

| # | City | Format | Differences from Standard |
|---|------|--------|--------------------------|
| 21 | Augsburg | TBD | |
| 22 | Wiesbaden | TBD | |
| 23 | Mönchengladbach | TBD | |
| 24 | Gelsenkirchen | TBD | |
| 25 | Aachen | TBD | |
| 26 | Braunschweig | TBD | |
| 27 | Kiel | TBD | |
| 28 | Chemnitz | TBD | |
| 29 | Halle | TBD | |
| 30 | Magdeburg | TBD | |

## Cities 31-40 (Tier 2c — this batch)

| # | City | Format | Differences from Standard |
|---|------|--------|--------------------------|
| 31 | Freiburg | TBD | |
| 32 | Krefeld | TBD | |
| 33 | Mainz | TBD | |
| 34 | Lübeck | TBD | |
| 35 | Erfurt | TBD | |
| 36 | Oberhausen | TBD | |
| 37 | Rostock | TBD | |
| 38 | Kassel | TBD | |
| 39 | Hagen | TBD | |
| 40 | Potsdam | TBD | |

## Cities 41-50 (Tier 2d — to be documented)

| # | City | Format | Differences from Standard |
|---|------|--------|--------------------------|
| 41 | Saarbrücken | TBD | |
| 42 | Hamm | TBD | |
| 43 | Ludwigshafen | TBD | |
| 44 | Oldenburg | TBD | |
| 45 | Osnabrück | TBD | |
| 46 | Leverkusen | TBD | |
| 47 | Heidelberg | TBD | |
| 48 | Darmstadt | TBD | |
| 49 | Solingen | TBD | |
| 50 | Regensburg | TBD | |

---

## Common Format Variations Observed

*(To be populated as extraction proceeds)*

### Wohnlage variations
- **2-tier system:** Some cities use only `einfach` and `gut` (no `mittel`)
- **Custom labels:** `Lage I / Lage II / Lage III`, `Siedlungslage / normale Lage / gute Lage`
- **4-tier system:** Rare but possible

### Bauperiod variations
- **Coarser grouping:** Some cities use only 4-6 periods instead of 9
- **Different cutoffs:** `bis 1960`, `1961-1977`, `1978-1991`, etc.

### Size group variations
- **Simplified:** Some cities use only 3 size groups (`bis 60`, `60-90`, `über 90`)
- **Single value:** Some cities publish a single €/m² number per Baujahr/Lage cell without size differentiation

### Value column variations
- **No range:** Some cities publish only `Mittelwert` without `untere/obere Spanne`
- **Tabellenmietspiegel:** A single specific value per cell instead of a range
- **Spanneneinordnung:** Some provide additional adjustment factors for specific features (bad, kitchen, etc.)
