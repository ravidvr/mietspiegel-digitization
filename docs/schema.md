# Unified Mietspiegel Data Schema

> **Version:** 1.0.0  
> **Purpose:** Standardize extracted German Mietspiegel (rent index) data from diverse city formats into a single queryable structure.

---

## Overview

German cities publish their official Mietspiegel as PDF tables with varying layouts. This schema normalises across those differences while preserving every city's original data. The core structure is a **3-dimensional matrix**:

| Dimension | Meaning | Typical cardinality |
|-----------|---------|-------------------|
| **Wohnlage** (location quality) | einfach / mittel / gut | 2–3 categories |
| **Bauperiode** (construction period) | e.g. "bis 1918", "1919–1949" | 6–12 periods |
| **Wohnfläche** (size group) | e.g. "< 35 m²", "35–40 m²" | 8–16 brackets |

Every cell in this matrix stores 3 values: **untere Spanne**, **obere Spanne**, and **Mittelwert** — each in €/m² net cold rent.

---

## Document Structure (top-level)

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/ravidvr/mietspiegel-digitization/main/docs/schema.json",
  "meta": {
    // Metadata about this dataset (see § Metadata)
  },
  "city": {
    // City identification (see § City)
  },
  "matrix": {
    // The data matrix (see § Matrix)
  },
  "source": {
    // Source document info (see § Source)
  }
}
```

---

## § Metadata

```jsonc
{
  "meta": {
    "schema_version": "1.0.0",
    "extracted_at": "2026-07-06T15:00:00Z",
    "extracted_by": "camelot-py",
    "extraction_notes": "Manually validated against PDF values, 98% accuracy",
    "quality": {
      "status": "validated",        // "raw" | "validated" | "flagged"
      "confidence": 0.98,            // 0.0 – 1.0
      "issues": [
        {
          "type": "missing_value",
          "location": "mittel/1950-1964/35-40",
          "detail": "Cell obscured by page fold"
        }
      ]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | ✓ | Semver of this schema |
| `extracted_at` | string (ISO-8601) | ✓ | When the PDF was parsed |
| `extracted_by` | string | | Tool used (e.g. `camelot-py`, `manual`) |
| `extraction_notes` | string | | Free-text notes about extraction quirks |
| `quality.status` | enum | ✓ | `raw` = just extracted, `validated` = checked against PDF, `flagged` = has known issues |
| `quality.confidence` | number | ✓ | Subjective accuracy score (0–1) |
| `quality.issues[]` | array | | List of known extraction problems |

---

## § City

```jsonc
{
  "city": {
    "name": "Berlin",
    "slug": "berlin",
    "state": "Berlin",
    "region": "Berlin-Brandenburg",       // optional metropolitan region
    "population": 3745000,                 // optional, for sorting
    "coordinates": {
      "lat": 52.5200,
      "lng": 13.4050
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | City name in German (e.g. "München") |
| `slug` | string | ✓ | URL-safe id (lowercase, no diacritics: "muenchen") |
| `state` | string | ✓ | Bundesland |
| `region` | string | | Optional metropolitan region grouping |
| `population` | integer | | Population for ranking/sorting on dashboard |
| `coordinates` | {lat, lng} | ✓ | City center for map markers |

---

## § Source

```jsonc
{
  "source": {
    "title": "Mietspiegel 2024 Berlin",
    "type": "qualifiziert",                // "qualifiziert" | "einfach" | "ortsueblich"
    "year": 2024,
    "effective_from": "2024-04-01",
    "effective_until": "2026-03-31",
    "publisher": "Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen",
    "url": "https://www.berlin.de/sen/wohnen/service/mietspiegel/",
    "pdf_url": "https://.../mietspiegel-2024.pdf",
    "local_pdf": "data/raw/berlin-2024.pdf",
    "pages": [12, 13, 14, 15],            // which PDF pages contain the tables
    "retrieved_at": "2026-06-01T10:00:00Z"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | ✓ | `qualifiziert` (scientific method, legally binding), `einfach` (simpler survey), or `ortsueblich` (local custom) |
| `year` | integer | ✓ | Publication year |
| `effective_from` | string (date) | ✓ | When the Mietspiegel takes legal effect |
| `effective_until` | string (date) | | When it expires (typically 2 years after `effective_from`) |
| `publisher` | string | ✓ | Issuing authority |
| `url` | string | ✓ | Landing page on the city's website |
| `pdf_url` | string | | Direct link to the PDF (may be unstable) |
| `local_pdf` | string | | Relative path to stored PDF copy |

---

## § Matrix — The core data

This is the heart of the schema. The `matrix` holds all 3-dimensional tables.

### Structure

```jsonc
{
  "matrix": {
    "lage_categories": [
      {
        "id": "einfach",
        "label": "einfache Wohnlage",
        "aliases": ["einfach", "einfache Wohnlage"],
        "description": "Einfache Lage"
      },
      {
        "id": "mittel",
        "label": "mittlere Wohnlage",
        "aliases": ["mittel", "mittlere Wohnlage", "normale Wohnlage"]
      },
      {
        "id": "gut",
        "label": "gute Wohnlage",
        "aliases": ["gut", "gute Wohnlage", "günstige Wohnlage"]
      }
    ],
    "bauperiods": [
      { "id": "bis_1918", "label": "bis 1918", "range": { "min": null, "max": 1918 } },
      { "id": "1919_1949", "label": "1919–1949", "range": { "min": 1919, "max": 1949 } },
      { "id": "1950_1964", "label": "1950–1964", "range": { "min": 1950, "max": 1964 } }
      // ...
    ],
    "size_groups": [
      { "id": "bis_35", "label": "unter 35 m²", "range": { "min": 0, "max": 34.99 } },
      { "id": "35_40", "label": "35–40 m²", "range": { "min": 35, "max": 40 } }
      // ...
    ],
    "values": [
      // One object per matrix cell
    ]
  }
}
```

### values array

Each entry in `values` is a single cell in the Wohnlage × Bauperiode × Größe matrix:

```jsonc
{
  "values": [
    {
      "lage_id": "einfach",
      "bauperiod_id": "bis_1918",
      "size_id": "bis_35",
      "value": {
        "untere_spanne": 4.52,
        "obere_spanne": 7.85,
        "mittelwert": 6.10
      }
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lage_id` | string | ✓ | Must match a category `id` in `lage_categories` |
| `bauperiod_id` | string | ✓ | Must match a `bauperiods[*].id` |
| `size_id` | string | ✓ | Must match a `size_groups[*].id` |
| `value.untere_spanne` | number (nullable) | ✓ | Lower bound of the rent range (€/m² net cold) |
| `value.obere_spanne` | number (nullable) | ✓ | Upper bound of the rent range (€/m² net cold) |
| `value.mittelwert` | number (nullable) | ✓ | Arithmetic mean (€/m² net cold) |

> **Null semantics:** If a city does not report a value (some cells are empty in the original PDF), store `null`. Do NOT use sentinel values like `-1` or `0`.

---

## § City-specific customisations

Some cities deviate from the standard 3-tier Wohnlage model:

- **2-tier cities** (e.g. some smaller cities): use only `einfach` and `mittel` (or their equivalents) — omit the missing category.
- **Cities with custom labels** (e.g. "Lage I / Lage II"): put the city's original labels in `aliases` and map them to the standard `id` (e.g. `"Lage I" → untere_siedlungslage`). Document the mapping in `extra.normalization_notes`.
- **Non-uniform size brackets:** each city declares its own `size_groups` — the schema does not enforce a universal set.

When a city's categories don't map cleanly to the 3-tier standard, add to `aliases` and set `extra.normalized_from`:

```jsonc
{
  "id": "einfach",
  "label": "einfache Wohnlage",
  "aliases": ["einfach", "einfache Wohnlage", "Lage I", "untere Siedlungslage"],
  "extra": {
    "normalized_from": "Lage I",
    "normalization_note": "Hamburg uses 'Lage I' for its lowest category; mapped to einfach"
  }
}
```

---

## § Full Example — Berlin 2024 (abbreviated)

```json
{
  "$schema": "https://raw.githubusercontent.com/ravidvr/mietspiegel-digitization/main/docs/schema.json",
  "meta": {
    "schema_version": "1.0.0",
    "extracted_at": "2026-06-15T14:30:00Z",
    "extracted_by": "camelot-py",
    "extraction_notes": null,
    "quality": {
      "status": "validated",
      "confidence": 0.99,
      "issues": []
    }
  },
  "city": {
    "name": "Berlin",
    "slug": "berlin",
    "state": "Berlin",
    "region": "Berlin-Brandenburg",
    "population": 3745000,
    "coordinates": { "lat": 52.5200, "lng": 13.4050 }
  },
  "source": {
    "title": "Mietspiegel 2024 Berlin",
    "type": "qualifiziert",
    "year": 2024,
    "effective_from": "2024-04-01",
    "effective_until": "2026-03-31",
    "publisher": "Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen",
    "url": "https://www.berlin.de/sen/wohnen/service/mietspiegel/",
    "pdf_url": "https://.../mietspiegel-2024.pdf",
    "local_pdf": "data/raw/berlin-2024.pdf",
    "pages": [12, 13, 14, 15],
    "retrieved_at": "2026-06-01T10:00:00Z"
  },
  "matrix": {
    "lage_categories": [
      { "id": "einfach", "label": "einfache Wohnlage", "aliases": ["einfach"] },
      { "id": "mittel",  "label": "mittlere Wohnlage", "aliases": ["mittel"] },
      { "id": "gut",     "label": "gute Wohnlage",    "aliases": ["gut"] }
    ],
    "bauperiods": [
      { "id": "bis_1918",   "label": "bis 1918",      "range": { "min": null, "max": 1918 } },
      { "id": "1919_1949",  "label": "1919–1949",     "range": { "min": 1919, "max": 1949 } },
      { "id": "1950_1964",  "label": "1950–1964",     "range": { "min": 1950, "max": 1964 } },
      { "id": "1965_1972",  "label": "1965–1972",     "range": { "min": 1965, "max": 1972 } },
      { "id": "1973_1990",  "label": "1973–1990",     "range": { "min": 1973, "max": 1990 } },
      { "id": "1991_2002",  "label": "1991–2002",     "range": { "min": 1991, "max": 2002 } },
      { "id": "2003_2013",  "label": "2003–2013",     "range": { "min": 2003, "max": 2013 } },
      { "id": "2014_2022",  "label": "2014–2022",     "range": { "min": 2014, "max": 2022 } },
      { "id": "ab_2023",    "label": "ab 2023",       "range": { "min": 2023, "max": null } }
    ],
    "size_groups": [
      { "id": "bis_35",      "label": "unter 35 m²",   "range": { "min": 0, "max": 34.99 } },
      { "id": "35_40",       "label": "35–40 m²",      "range": { "min": 35, "max": 39.99 } },
      { "id": "40_45",       "label": "40–45 m²",      "range": { "min": 40, "max": 44.99 } },
      { "id": "45_50",       "label": "45–50 m²",      "range": { "min": 45, "max": 49.99 } },
      { "id": "50_55",       "label": "50–55 m²",      "range": { "min": 50, "max": 54.99 } },
      { "id": "55_60",       "label": "55–60 m²",      "range": { "min": 55, "max": 59.99 } },
      { "id": "60_65",       "label": "60–65 m²",      "range": { "min": 60, "max": 64.99 } },
      { "id": "65_70",       "label": "65–70 m²",      "range": { "min": 65, "max": 69.99 } },
      { "id": "70_75",       "label": "70–75 m²",      "range": { "min": 70, "max": 74.99 } },
      { "id": "75_80",       "label": "75–80 m²",      "range": { "min": 75, "max": 79.99 } },
      { "id": "80_85",       "label": "80–85 m²",      "range": { "min": 80, "max": 84.99 } },
      { "id": "85_90",       "label": "85–90 m²",      "range": { "min": 85, "max": 89.99 } },
      { "id": "90_95",       "label": "90–95 m²",      "range": { "min": 90, "max": 94.99 } },
      { "id": "95_100",      "label": "95–100 m²",     "range": { "min": 95, "max": 99.99 } },
      { "id": "ab_100",      "label": "ab 100 m²",     "range": { "min": 100, "max": null } },
      { "id": "ab_150",      "label": "ab 150 m²",     "range": { "min": 150, "max": null } }
    ],
    "values": [
      { "lage_id": "einfach", "bauperiod_id": "bis_1918", "size_id": "bis_35",
        "value": { "untere_spanne": 4.52, "obere_spanne": 7.85, "mittelwert": 6.10 } },
      { "lage_id": "einfach", "bauperiod_id": "bis_1918", "size_id": "35_40",
        "value": { "untere_spanne": 4.72, "obere_spanne": 8.33, "mittelwert": 6.47 } },
      { "lage_id": "mittel", "bauperiod_id": "bis_1918", "size_id": "bis_35",
        "value": { "untere_spanne": 6.05, "obere_spanne": 10.50, "mittelwert": 8.25 } }
      // ... ~300–500 more cells
    ]
  }
}
```

---

## § Normalization rules for cross-city comparison

When comparing cities side-by-side, unify the dimensions:

### Wohnlage mapping

| Standard id | Equivalent city labels |
|-------------|----------------------|
| `einfach` | einfache Wohnlage, untere Siedlungslage, sehr einfach, einfache bis mittlere, Lage I |
| `mittel` | mittlere Wohnlage, normale Wohnlage, durchschnittlich, Lage II |
| `gut` | gute Wohnlage, gehobene Wohnlage, beste Wohnlage, günstige Wohnlage, Lage III |

### Bauperiod merging

For cross-city comparison, Bauperiods should be aligned to a **common set** (use inclusive buckets of ~20 years, each city's native resolution is preserved in its raw data):

| Standard bucket | Includes |
|----------------|----------|
| `bis_1918` | bis 1918 |
| `1919_1949` | 1919–1949, 1919–1945 |
| `1950_1964` | 1950–1964, 1945–1964 |
| `1965_1972` | 1965–1972, 1965–1975 |
| `1973_1990` | 1973–1990, 1976–1990, 1975–1990 |
| `1991_2002` | 1991–2002, 1990–2002 |
| `2003_2013` | 2003–2013 |
| `2014_heute` | 2014–heute, ab 2014 |

### Size group merging

For cross-city comparison, standardize to a common set of size groups (each city's native resolution is preserved in its raw data). The default set in the full example above serves as the canonical set. Cities with coarser grouping (e.g. "< 40, 40–60, 60–90, > 90") should target the closest matching standard bins during comparison.

---

## § JSON Schema (validation)

The companion JSON Schema file at `docs/schema.json` enforces these rules:

- `city.name`, `city.slug`, `city.state` are required
- `source.type` must be one of `qualifiziert`, `einfach`, or `ortsueblich`
- `matrix.values[*].lage_id` must reference a valid `lage_categories[*].id`
- `matrix.values[*].bauperiod_id` must reference a valid `bauperiods[*].id`
- `matrix.values[*].size_id` must reference a valid `size_groups[*].id`
- Each `value` sub-object must have `untere_spanne`, `obere_spanne`, `mittelwert` (nullable numbers)
- `quality.status` must be one of `raw`, `validated`, or `flagged`
- No duplicate (lage_id, bauperiod_id, size_id) tuples in `values`

---

## § File naming convention

Each city's data lives in `data/processed/`:

```
data/processed/berlin.json        # Berlin latest
data/processed/muenchen.json      # Munich latest
data/processed/hamburg.json       # Hamburg latest
```

Historical editions use a year suffix:

```
data/processed/berlin-2024.json
data/processed/berlin-2022.json
```
