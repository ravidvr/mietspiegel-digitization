# Mietspiegel Digitization

Official German city rent index data (Mietspiegel) — extracted from PDFs, standardized, and visualized on an interactive map.

## Data

| City | State | Year | Type |
|------|-------|------|------|
| Berlin | Berlin | 2024 | Qualifiziert |
| Hamburg | Hamburg | 2025 | Qualifiziert |
| Munich | Bayern | 2025 | Qualifiziert |
| Cologne | Nordrhein-Westfalen | 2024 | Qualifiziert |
| Frankfurt | Hessen | 2024 | Qualifiziert |
| Stuttgart | Baden-Württemberg | 2024 | Qualifiziert |
| Düsseldorf | Nordrhein-Westfalen | 2024 | Qualifiziert |
| Leipzig | Sachsen | 2024 | Qualifiziert |
| Dresden | Sachsen | 2024 | Qualifiziert |
| Hannover | Niedersachsen | 2024 | Qualifiziert |

### Data Format

Each city is stored as a JSON file in `data/processed/{city_slug}.json` with:
- City metadata (name, state, coordinates, population)
- Mietspiegel tables organized by:
  - **Wohnlage** (location quality): einfach, mittel, gut
  - **Baujahr** (construction year period): 8 groups
  - **Wohnungsgröße** (apartment size): 4 categories
- All values are **Nettokaltmiete** (net cold rent) in €/m²/month

## Dashboard

Interactive Leaflet.js map at [ravidvr.github.io/mietspiegel-digitization](https://ravidvr.github.io/mietspiegel-digitization)

Features:
- City markers color-coded by rent level
- Click for full Mietspiegel table
- Cross-city comparison with filters
- Searchable city list

## License

Data sourced from official city publications. Code is MIT.
