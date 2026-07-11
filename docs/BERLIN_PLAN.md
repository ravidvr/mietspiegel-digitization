# Berlin-Only Dashboard — Planning Document

## Goal
A standalone Berlin rent dashboard with ALL calculations based on Berlin-local averages, no national data at all.

## Current State (berlin.html)
- Centers map on Berlin ✓
- Only loads Berlin city JSON ✓
- Shows 12 districts ✓
- Loads Berlin-only Immoscout data (467 cells, ø €10.79/m²) ✓
- Loads Berlin-only Zensus data (1,155 cells, ø €7.97/m²) ✓
- Heatmap uses Berlin-only z-scores ✓
- Legend says "Berlin average" ✓
- Tooltips show Berlin context ✓
- No national data loaded ✓
- No sidebar (full-screen map) ✓
- District list in floating panel ✓
- Clickable districts zoom on map ✓

## Tasks (all completed)

### T1: Filter Immoscout data to Berlin
- **What:** Filter `redx_grid_rent.json` grid cells to Berlin bounding box
- **Box:** lat 52.35–52.65, lng 13.05–13.75
- **Recalculate:** Berlin-only mean, std, z-scores
- **Save as:** `docs/data/processed/berlin_immoscout.json`
- **Est:** 15 min

### T2: Filter Zensus data to Berlin  
- **What:** Filter `zensus2022_rent_1km.json` cells to Berlin bounding box
- **Box:** same as above
- **Recalculate:** Berlin-only mean, std
- **Save as:** `docs/data/processed/berlin_zensus.json`
- **Est:** 5 min

### T3: Rebuild Berlin heatmap with local stats
- **What:** Heatmap uses Berlin-only mean/std for z-scores
- **Legend:** "Berlin average" instead of "National average"
- **Color scale:** Calibrated to Berlin's narrower rent range
- **Est:** 10 min

### T4: Update tooltips to Berlin context
- **What:** Replace "vs national avg (€9.93)" → "vs Berlin avg (€X)"
- **What:** Zensus row uses Berlin census avg, not national
- **What:** "Market premium" recalculated against Berlin census
- **Est:** 10 min

### T5: Remove all national code paths
- **What:** Delete city list loading (23 cities)
- **What:** Delete comparison data loading (cities_comparison.json)
- **What:** Delete renderComparison()
- **What:** Delete showCityCard() — or repurpose for Berlin only
- **What:** Delete toggleSidebar, showDetail, showCompare
- **What:** Remove city labels (markers) — not needed for single city
- **Est:** 15 min

### T6: Simplify UI
- **What:** Remove sidebar entirely
- **What:** Map gets full screen width
- **What:** Only tooltip overlay for detail
- **What:** District list in a small floating panel
- **Est:** 10 min

### T7: Add Berlin district selector
- **What:** Clickable list of 12 districts in floating panel
- **What:** Clicking a district highlights it on map
- **What:** Show district stats (einfach/mittel/gut %)
- **Est:** 20 min

## Implementation Order
T1 → T2 → T3 → T4 → T5 → T6 → T7

## Files to create/modify
- NEW: `docs/berlin.html` (rewrite from scratch, ~300 lines)
- NEW: `scripts/build_berlin_data.py` (filter + recalculate)
- NEW: `docs/data/processed/berlin_immoscout.json`
- NEW: `docs/data/processed/berlin_zensus.json`
