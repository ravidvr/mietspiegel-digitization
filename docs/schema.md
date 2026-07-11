# Data Schema

## File format
Each city's Mietspiegel data is stored as a JSON file in `docs/data/processed/<city_slug>.json`.

## Schema

```json
{
  "city": "Berlin",
  "city_slug": "berlin",
  "slug": "berlin",
  "state": "Berlin",
  "lat": 52.52,
  "lng": 13.405,
  "population": 3700000,
  "year": 2024,
  "type": "qualifiziert",
  "source_url": "https://...",
  "source_pdf": "mietspiegeltabelle2024.pdf",
  "lage_categories": ["einfach", "mittel", "gut"],
  "baujahr_groups": ["bis 1918", "1919-1949", "1950-1964", ...],
  "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
  "tables": [
    {
      "lage": "mittel",
      "rows": [
        {
          "baujahr": "bis 1918",
          "bis_40": 10.50,
          "40_60": 11.80,
          "60_90": 12.00,
          "ueber_90": 12.50
        }
      ]
    }
  ]
}
```

## Field reference

| Field | Type | Description |
|-------|------|-------------|
| `city` | string | City name in German (e.g., "München") |
| `slug` | string | URL-safe identifier (e.g., "muenchen") |
| `state` | string | German federal state (Bundesland) |
| `lat`, `lng` | float | City center coordinates (WGS84) |
| `population` | int | City population |
| `year` | int | Mietspiegel edition year |
| `type` | string | Mietspiegel type (e.g., "qualifiziert") |
| `source_url` | string | URL to original PDF |
| `lage_categories` | array | Wohnlage tiers used by this city |
| `baujahr_groups` | array | Construction year periods |
| `size_categories` | array | Apartment size ranges |
| `tables` | array | One table object per Wohnlage |

## Size keys

Each table row uses flat numeric keys (single value, not range objects):

| Key | Meaning |
|-----|---------|
| `bis_40` | Up to 40 m² |
| `40_60` | 40–60 m² |
| `60_90` | 60–90 m² |
| `ueber_90` | Over 90 m² |

Values are net cold rent in €/m²/month (float). Missing values are `null`.

## Normalization rules
- Wohnlage: map to "einfach", "mittel", "gut" (3-tier standard)
- Baujahr: preserve original period labels as-is
- Sizes: normalize to 4 standard keys (`bis_40`, `40_60`, `60_90`, `ueber_90`)
- Missing values: `null` (never 0)
- All rent values are positive floats in €/m²/month
