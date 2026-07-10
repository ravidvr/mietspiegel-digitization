# National Mietspiegel Choropleth — Milestone Plan

**Goal:** Every German city, town, and village colored by Mietspiegel rent data on an interactive choropleth map.

**Reality check:** ~11,000+ municipalities in Germany. Official Mietspiegel exists for ~200 cities (>50k pop). For the other 10,800+, there is no official rent index. This plan phases from what's immediately buildable to what requires new data sources.

---

## Milestone 1: National Municipality Base Map (1 week)

**What:** Germany-wide choropleth background with our 23 cities highlighted.

- Download Germany municipality boundaries (GeoJSON) from BKG or OpenStreetMap
- Create a base map showing ALL ~11,000 Gemeinde boundaries in light gray
- Color-fill only the 23 cities where we have Mietspiegel data
- Gray-out everything else with a "no data" pattern
- Click an uncolored area → tooltip "No Mietspiegel data yet"

**Deliverable:** A Germany-wide map that shows our 23 cities in context, demonstrating the gap vs the ambition.

**Effort:** 1-2 days (boundary download + merging with our data + dashboard update)

---

## Milestone 2: Scale to ~200 Cities (3-4 weeks)

**What:** Extract all remaining ~180 cities with Mietspiegel.

**Bottleneck:** Each city's PDF is different. Format variation is extreme. Some PDFs are scanned images, not text.

**Approach (in order of priority):**
- **Batch 1 (week 1):** Next 20 largest cities (>250k pop) — most have clean PDFs
- **Batch 2 (week 2):** Next 40 cities (100-250k pop) — mixed PDF quality
- **Batch 3 (week 3):** Remaining ~120 cities (50-100k pop) — most are simple PDFs or web tables
- **Per-city pipeline:** Search PDF → download → extract (camelot-py) → validate → convert to schema

**Deliverable:** National choropleth with ~200 colored cities, covering ~70% of Germany's population.

**Effort:** ~3-4 weeks of focused extraction (30-60 min per city average)

---

## Milestone 3: District-Level via RWI-GEO-RED (ongoing, in parallel)

**What:** Apply for and integrate actual district-level market rent data.

**The data:** RWI-GEO-RED (Immoscout24 asking rents, curated by RWI-Leibniz institute). Covers ALL of Germany at district (Kreis) level. Free for non-commercial use.

**Process:**
1. Apply at fdz.rwi-essen.de (data use agreement) — ~1 week
2. Receive the dataset (CSV with ~400 districts × monthly observations)
3. Join to district boundary GeoJSON
4. Add as an alternative layer: "Market asking rents (Immoscout24)"
5. This is NOT official Mietspiegel, but it's district-level and covers every corner of Germany

**Deliverable:** Two layers on the map:
- 🔵 Official Mietspiegel (city-level, where available)
- 🟠 Market asking rents (district-level, nationwide)

**Effort:** 1 week application + 1 week integration

---

## Milestone 4: Community Contribution Pipeline (2 weeks)

**What:** Let others contribute data for their cities.

**Approach:**
- GitHub issue template: "Add a city's Mietspiegel"
- Contributor submits the PDF URL or table values
- Automated validation checks format
- PR merged → city appears on map
- Recognition in footer ("Data contributed by ...")

**Deliverable:** Self-sustaining growth beyond the ~200 official cities. Enthusiasts can contribute their local Mietspiegel.

**Effort:** 1-2 weeks (templates, validation script, automation)

---

## Milestone 5: Small Towns — Alternative Data Sources (4+ weeks)

**What:** Estimate rent data for the ~10,800 towns without Mietspiegel.

**No official Mietspiegel exists for these.** Options:

| Option | Method | Quality | Effort |
|--------|--------|---------|--------|
| **5a** | Statistical imputation (rent = f(population, state, proximity to big city, building stock)) | Medium | 2 weeks |
| **5b** | Scrape Immowelt/Immoscout24 asking rents per town (fragile, anti-bot) | Medium | 2-4 weeks |
| **5c** | Use GdW aggregate data (€6.63/m² avg) + regional adjustments | Low | 1 week |
| **5d** | Partner with a proptech for data access | High | Varies |

**Recommended:** 5a + 5c — build a simple regression model that estimates rent based on:
- Population (bigger = higher rent)
- State (Bavaria vs Saxony vs ...)
- Distance to next Großstadt
- East/West binary

This won't be accurate per town but gives a plausible color gradient for the 10,800 gaps.

**Deliverable:** National choropleth with every Gemeinde colored — 23 cities = actual Mietspiegel, ~200 cities = extracted PDFs, ~10,800 towns = model estimate.

---

## Timeline Summary

```
Week 1     ─ Milestone 1: National base map with 23 cities
Week 2-5   ─ Milestone 2: Scale to ~200 cities (parallel with M3)
Week 3-4   ─ Milestone 3: RWI-GEO-RED application + integration
Week 6-7   ─ Milestone 4: Community contribution pipeline
Week 8-11  ─ Milestone 5: Estimate model for remaining 10,800 towns
```

## What this enables (LinkedIn story)

| Milestone | Headline |
|-----------|----------|
| M1 | "I mapped 23 German cities' official rent data onto every municipality boundary — here's the gap" |
| M2 | "200 cities, 70% of Germany's population — every official Mietspiegel on one map" |
| M3 | "Nationwide district-level rent map — powered by Immoscout24 data (with attribution)" |
| M5 | "Every village, every town — estimated rent data for all 11,000+ German municipalities" |
