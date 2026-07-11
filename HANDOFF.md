# Mietspiegel Digitization — Session Handoff

> **Switch to GLM 5.2:** Start new session with `hermes -p glm`
> **Load this file:** `read_file("mietspiegel-digitization/HANDOFF.md")`
> **Load these skills:** `skill_view("kanban-orchestrator")`, `skill_view("writing-plans")`

---

## 1. Project Identity

**Dashboard:** German Mietspiegel (official rent index) data — digitized from city PDFs, mapped, searchable, comparable.
**Live:** https://ravidvr.github.io/mietspiegel-digitization/
**Repo:** https://github.com/ravidvr/mietspiegel-digitization (private)
**Repo root:** `/Users/ruhvee/mietspiegel-digitization/`

---

## 2. Current State (what exists)

| Metric | Value |
|--------|-------|
| Cities with complete rent tables | **23** |
| Cities with metadata only (no table) | **5** (Bielefeld, Chemnitz, Duisburg, Mannheim, Mönchengladbach – PDFs never found) |
| Berlin district data | ✅ 12 Bezirke with choropleth polygons + estimated rent |
| Berlin Immoscout heatmap | ✅ 467 grid cells, ø €10.79/m² (Berlin-only z-scores) |
| Berlin Zensus heatmap | ✅ 1,155 cells, ø €7.97/m² (Berlin-only z-scores) |
| Dashboard features | City map, detail table, comparison, Berlin district auto-drill-down, DE/EN, dark mode, CSV export, welcome modal, footer |

### 23 Cities with data
Aachen, Augsburg, Berlin, Bonn, Braunschweig, Bremen, Dresden, Düsseldorf, Essen, Frankfurt am Main, Freiburg im Breisgau, Halle (Saale), Hamburg, Hannover, Kiel, Köln, Leipzig, Lübeck, Mainz, München, Nürnberg, Rostock, Stuttgart

---

## 3. Architecture

```
docs/
├── index.html                     ← MAIN DASHBOARD (single-file app, Leaflet.js)
├── about.html                     ← Methodology page
├── data/processed/
│   ├── cities_index.json          ← Index of all cities (lat/lng/population)
│   ├── <city>.json                ← Per-city Mietspiegel data
│   ├── berlin-districts-choropleth.geojson   ← Berlin 12 Bezirke polygons + rent
│   └── berlin-districts-geo.json            ← Berlin district centroids (legacy)
├── format-variation-catalog.md    ← How each city's PDF format differs
├── schema.md / schema.json        ← Data schema docs
├── extraction-pipeline.md         ← Extraction methodology
└── national-choropleth-plan.md    ← 5-milestone plan for nation-wide coverage

data/processed/                    ← Mirror of docs/data/processed/
data/raw/                          ← Original PDFs (gitignored)

scripts/
├── compile_data.py                ← Data compilation
├── export-csv.py                  ← CSV export utility
├── extract_*.py                   ← Per-city extraction scripts
└── alert-monitor.py               ← Change monitoring

validate/
├── sanity_checks.py               ← Automated data validation
├── gdw_crossref.py               ← Cross-ref with GdW aggregates
└── run_validations.py             ← Validation runner
```

---

## 4. Dashboard Tech Stack

**Single HTML file** — no build step, no framework, no npm. Just vanilla HTML+CSS+JS.

| Component | What |
|-----------|------|
| Map | Leaflet.js 1.9.4 from unpkg CDN |
| City data | Local JSON files fetched via `fetch()` |
| i18n | `const I18N = { en: {...}, de: {...} }` — manually toggled |
| Dark mode | CSS custom properties + `[data-theme="dark"]` |
| Deployment | GitHub Actions workflow → GitHub Pages from `docs/` |

**Critical gotchas (from past bugs):**
- `const L = { en, de }` will OVERWRITE Leaflet's global `L` namespace — i18n object MUST be named `I18N` or similar
- `{.6}` is invalid JS — must be `{duration: .6}` in Leaflet options
- GitHub Pages serves from `docs/` — data files MUST be under `docs/data/processed/`
- Deploy workflow sometimes gets stuck in queue — cancel queued runs and retry

---

## 5. Key Functions in the Dashboard (index.html)

Located inside the `<script>` block (~lines 220-556):

| Function | Line | Purpose |
|----------|------|---------|
| `init()` | 310 | Loads index, caches city data, adds markers, populates filters |
| `addMarkers(filter)` | 362 | Adds/refreshes city circle markers on map |
| `showCity(slug)` | 492 | Shows city detail — Berlin auto-enters district view |
| `enterDistrictView()` | 395 | Hides city markers, shows Berlin choropleth |
| `exitDistrictView()` | 404 | Hides choropleth, restores city markers |
| `showDistricts()` | 412 | Loads choropleth GeoJSON, renders L.geoJSON |
| `showDistrict(p)` | 455 | Shows district detail panel with einfach/mittel/gut |
| `rDet(slug,d,meta,lage)` | 503 | Renders city detail table |
| `updCmp()` | 518 | Updates comparison table |
| `toggleLang()` | 270 | Switches between EN/DE |
| `toggleDark()` | 275 | Dark mode toggle |
| `applyLang()` | 263 | Applies current language to all `[data-i18n]` elements |

---

## 6. Data Schema (per city JSON)

```json
{
  "city": "Berlin",
  "city_slug": "berlin",
  "state": "Berlin",
  "lat": 52.52,
  "lng": 13.405,
  "population": 3700000,
  "year": 2024,
  "type": "qualifiziert",
  "lage_categories": ["einfach", "mittel", "gut"],
  "baujahr_groups": ["bis 1918", "1919-1949", "1950-1964", ...],
  "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
  "source_url": "https://...",
  "tables": [
    {
      "lage": "einfach",
      "rows": [
        {"baujahr": "bis 1918", "bis_40": 8.03, "40_60": 7.68, "60_90": 7.35, "ueber_90": 7.02},
        ...
      ]
    }
  ]
}
```

**Size key mapping:** `bis_40`, `40_60`, `60_90`, `ueber_90`
**Values:** €/m² net cold rent (Mittelwert — some cities have untere/obere Spanne too)

---

## 7. Berlin District Layer

**Data source:** Berlin Senate WFS — `https://gdi.berlin.de/services/wfs/wohnlagenadr2026`
**License:** Datenlizenz Deutschland – Zero (free, no restrictions)
**Coverage:** 400,505 address-level points with Wohnlage (einfach/mittel/gut) + Bezirk + Stadtteil

**Pipeline:**
1. Query WFS → download all 400K points (batch of 20K)
2. Aggregate by Bezirk → count einfach/mittel/gut per district
3. Cross-reference with Berlin Mietspiegel table → estimate weighted avg rent per district
4. Merge with district boundary polygons from `m-hoerz/berlin-shapes` GitHub repo

**Boundary GeoJSON:** Merged into `berlin-districts-choropleth.geojson` (12 Polygon features with rent data in properties)
**District names** must match `spatial_alias` field in the boundary file.

---

## 8. National Choropleth Plan (next steps)

See `docs/national-choropleth-plan.md` for full detail.

### M1 — National Base Map (1-2 days)
- Download Germany municipality boundaries (BKG or OSM)
- Light gray base with our 23 cities colored
- This is the natural next task

### Data sources for boundaries:
| Source | URL | Format | License |
|--------|-----|--------|---------|
| BKG (federal) | https://gdz.bkg.bund.de | GeoJSON/Shapefile | dl-de/zero-2.0 |
| OpenStreetMap | Overpass API | GeoJSON | ODbL |
| GitHub (isellsoap) | https://github.com/isellsoap/deutschlandGeoJSON | GeoJSON | MIT |

### M3 — RWI-GEO-RED (most impactful)
Apply at fdz.rwi-essen.de for free academic access to Immoscout24 panel data. Covers ALL 400 German districts at sub-city level.

---

## 9. Residual Issues

| Issue | Status |
|-------|--------|
| 5 cities with no PDF found | ✅ Bielefeld, Chemnitz, Duisburg, Mannheim, Mönchengladbach — manual search needed |
| Hamburg Wohnlagenverzeichnis | ⏳ PDF exists (5.6MB, selectable text) — could be parsed for Hamburg district layer |
| Other cities' district data | ❌ No open data exists beyond Berlin |
| GitHub Actions deploy often queued | ⚠️ Cancel stuck runs, retry with empty commit |
| Kanban board | Exists at `~/.hermes/kanban/boards/mietspiegel-digitization/` — 29 tasks mostly done |

---

## 10. Commands to Rebuild Data (if needed)

```bash
# Extract a city PDF
python3 -c "
import pdfplumber, json
with pdfplumber.open('data/raw/<city>.pdf') as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        text = page.extract_text()
        # parse...
"

# Query Berlin WFS
curl -s 'https://gdi.berlin.de/services/wfs/wohnlagenadr2026?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=wohnlagenadr2026:wohnlagenadr2026&COUNT=3&OUTPUTFORMAT=json'

# Deploy
git commit --allow-empty -m "chore: trigger deploy" && git push
```

---

## 11. Style Guide for Dashboard Changes

- Keep it a **single HTML file** (no build step, no npm)
- All CSS in inline `<style>`, all JS in inline `<script>`
- Minimized class names (`.h-btn`, `.fbar`, `.sc`, `.ci`, `.ls`)
- Dark mode via CSS custom properties on `[data-theme="dark"]`
- i18n via `[data-i18n]` attributes + `I18N` object (NOT `const L`)
- DE/EN toggle calls `toggleLang()` which updates `document.querySelectorAll('[data-i18n]')`
- For performance: data loaded once, cached in JS object, markers recreated on filter change
- District polygons rendered via `L.geoJSON()` with style function, NOT circle markers

---

*Session started: July 9, 2026 · Previous model: deepseek-v4-flash*
*Switch to: `hermes -p glm` then `read_file("mietspiegel-digitization/HANDOFF.md")`*
