# Data Schema

## File format
Each city's Mietspiegel data is stored as a JSON file in `/data/processed/<city_slug>.json`.

## Schema

```json
{
  "city": "Berlin",
  "state": "Berlin",
  "year": 2024,
  "type": "qualifiziert",
  "source_url": "https://...",
  "source_pdf": "mietspiegeltabelle2024.pdf",
  "lage_categories": ["einfach", "mittel", "gut"],
  "notes": "Any caveats about this extraction",
  "tables": [
    {
      "lage": "mittel",
      "rows": [
        {
          "baujahr": "bis 1918",
          "size_under_35": {"untere": 10.50, "mittel": 12.00, "obere": 13.50},
          "size_35_40": {"untere": 10.20, "mittel": 11.80, "obere": 13.20}
        }
      ]
    }
  ]
}
```

## Normalization rules
- Wohnlage: map to "einfach", "mittel", "gut" (3-tier)
- Baujahr: preserve original period labels as-is
- Sizes: preserve original ranges as-is
- Missing values: null
