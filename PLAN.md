# Mietspiegel Digitization — Implementation Plan

> **Goal:** Build a digitized, standardized, searchable database of official German city Mietspiegel (rent indexes) — extracted from PDFs into structured data, with an interactive map dashboard on GitHub Pages.

**Approach:** Start with top 10 cities (proof of concept), scale to top 50, then open to community contributions. Extract PDF tables with camelot-py, normalize across different city formats, host on GitHub Pages with Leaflet map.

**Stack:** Python (camelot-py, pdfplumber, pandas) → JSON/CSV data files → Leaflet.js map → GitHub Pages

**Repository:** `github.com/ravidvr/mietspiegel-digitization` (private)

---

## Phase 0: Foundation & Infrastructure

### 0.1 — Initialize repo and project structure
**Files:** Create root structure
- `/data/raw/` — original PDFs (gitignored)
- `/data/processed/` — extracted JSON/CSV
- `/sources/` — scraper scripts
- `/docs/` — methodology
- `/index.html` — dashboard placeholder

### 0.2 — Set up PDF extraction toolchain
- Install camelot-py, pdfplumber, pandas, ghostscript, tabula-py
- Test extraction on Berlin Mietspiegel 2024 PDF
- Validate output accuracy

### 0.3 — Define unified data schema
```json
{
  "city": "Berlin",
  "state": "Berlin",
  "year": 2024,
  "type": "qualifiziert",
  "lage_categories": ["einfach", "mittel", "gut"],
  "tables": [
    {
      "lage": "mittel",
      "rows": [
        {"baujahr": "bis 1918", "size_under_35": 12.50, "size_35_40": 12.10, ...}
      ]
    }
  ],
  "source_url": "https://...",
  "source_pdf": "mietspiegeltabelle2024.pdf"
}
```

---

## Phase 1: Top 10 Cities (MVP)

### 1.1 — Berlin Mietspiegel extraction
- Download Berlin 2024 (or 2026) Mietspiegel PDF
- Extract table with camelot-py
- Map to unified schema
- Manual validation against PDF values
- Save as `/data/processed/berlin.json`

### 1.2 — Munich Mietspiegel extraction
- Download Munich 2025 Mietspiegel PDF from stadt.muenchen.de
- Munich has an online calculator as well — use PDF as primary source
- Extract and validate
- Save as `/data/processed/munich.json`

### 1.3 — Hamburg Mietspiegel extraction
- Find current Hamburg Mietspiegel PDF (site restructured recently)
- Extract and validate
- Save as `/data/processed/hamburg.json`

### 1.4 — Cologne Mietspiegel extraction
- Find and download Cologne Mietspiegel
- Extract and validate

### 1.5 — Frankfurt Mietspiegel extraction
- Find and download Frankfurt Mietspiegel
- Extract and validate

### 1.6 — Stuttgart Mietspiegel extraction
### 1.7 — Düsseldorf Mietspiegel extraction
### 1.8 — Leipzig Mietspiegel extraction
### 1.9 — Dresden Mietspiegel extraction
### 1.10 — Hannover Mietspiegel extraction

### 1.11 — Build MVP dashboard
- Leaflet.js map with city markers
- Click marker → show Mietspiegel table for that city
- Basic city comparison view
- Deploy to GitHub Pages

---

## Phase 2: Scale to Top 50 Cities

### 2.1 — Build city discovery pipeline
- Scrape list of German cities >50k inhabitants from Destatis
- Cross-reference with known Mietspiegel cities
- Find PDF URLs programmatically where possible

### 2.2 — Extract cities 11-30
- Batch extraction of medium-large cities
- Handle format variations per city
- Manual validation per city

### 2.3 — Extract cities 31-50
- Batch extraction
- Build format variation catalog

### 2.4 — Build normalization layer
- Map each city's Wohnlage categories to a standard 3-tier system
- Handle cities with 2-tier or custom systems
- Document normalization rules

### 2.5 — Add cross-city comparison features
- Side-by-side table comparison
- Sort by rent level
- Filter by Baujahr period
- Highlight extremes (cheapest/most expensive)

### 2.6 — Add search & filter to dashboard
- Search by city name
- Filter by state (Bundesland)
- Filter by rent range

---

## Phase 3: Data Quality & Automation

### 3.1 — Build validation framework
- Automated sanity checks (rents increase with newer buildings, better lage)
- Cross-reference against GdW aggregate data (~€6.63/m² avg)
- Flag outliers for manual review

### 3.2 — Build update monitoring
- Track each city's Mietspiegel publication cycle (every 2 years)
- Alert when a city publishes a new edition
- Version history for each city

### 3.3 — Add historical data
- Track previous Mietspiegel editions for major cities
- Show rent development over time
- Highlight cities with fastest/slowest rent growth

### 3.4 — Open source / community contribution pipeline
- CONTRIBUTING.md with format guide
- Issue templates for new city submissions
- PR validation workflow

---

## Phase 4: Monetization (Post-MVP)

### 4.1 — API layer
- Simple REST API for programmatic access
- Rate-limited free tier
- API key management for paid tier

### 4.2 — Premium features
- Bulk CSV export of all cities
- Historical trends
- Email alerts on Mietspiegel changes

### 4.3 — Pro features
- White-label embed for real estate websites
- Tenant-side analysis tools ("is my rent fair?")
- PDF report generation

---

## Appendix: City Priority List

**Tier 1 (MVP — Top 10):**
1. Berlin (3.7M)
2. Hamburg (1.9M)
3. Munich (1.5M) — has online calculator too
4. Cologne (1.1M)
5. Frankfurt (760K)
6. Stuttgart (630K)
7. Düsseldorf (620K)
8. Leipzig (600K)
9. Dresden (560K)
10. Hannover (540K)

**Tier 2 (Phase 2 — Top 50):**
Nuremberg, Bremen, Duisburg, Bochum, Wuppertal, Bielefeld, Bonn, Münster, Mannheim, Karlsruhe, Augsburg, Wiesbaden, Mönchengladbach, Gelsenkirchen, Aachen, Braunschweig, Kiel, Chemnitz, Halle, Magdeburg, Freiburg, Krefeld, Mainz, Lübeck, Erfurt, Oberhausen, Rostock, Kassel, Hagen, Potsdam, Saarbrücken, Hamm, Ludwigshafen, Oldenburg, Osnabrück, Leverkusen, Heidelberg, Darmstadt, Solingen, Regensburg
