#!/bin/bash
set -euo pipefail

# Mietspiegel Dashboard — Full build pipeline
# Usage: ./scripts/build.sh [--skip-grid] [--skip-zensus]

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

SKIP_GRID=false
SKIP_ZENSUS=false
for arg in "$@"; do
  case $arg in
    --skip-grid)  SKIP_GRID=true ;;
    --skip-zensus) SKIP_ZENSUS=true ;;
  esac
done

echo "════════════════════════════════════════════════"
echo "  MIETSPIEGEL DASHBOARD BUILD"
echo "════════════════════════════════════════════════"
echo "Repo: $REPO_ROOT"
echo ""

# ─── 1. Normalize city data ─────────────────────────
echo "▶ Step 1/4: Normalizing city Mietspiegel data..."
python3 scripts/compile_data.py
echo ""

# ─── 2. Copy processed data to docs/ ────────────────
echo "▶ Step 2/4: Syncing processed data → docs/data/processed/..."
mkdir -p docs/data/processed
rsync -a --delete data/processed/ docs/data/processed/ 2>/dev/null || \
  cp -r data/processed/* docs/data/processed/
echo "  Synced $(ls docs/data/processed/*.json 2>/dev/null | wc -l | tr -d ' ') files"
echo ""

# ─── 3. Build national choropleth (optional) ────────
if [ "$SKIP_GRID" = false ] && [ -f data/processed/redx_grid_rent.json ]; then
  echo "▶ Step 3/4: Building national rent grid GeoJSON..."
  python3 scripts/build_national_choropleth.py || echo "  ⚠ Skipped (missing dependencies or data)"
else
  echo "▶ Step 3/4: Skipping grid (flag or missing data)"
fi
echo ""

# ─── 4. Process Zensus 2022 (optional) ──────────────
if [ "$SKIP_ZENSUS" = false ] && [ -f data/external/Zensus2022_Durchschn_Nettokaltmiete_100m-Gitter.csv ]; then
  echo "▶ Step 4/4: Processing Zensus 2022 census rent data..."
  python3 scripts/process_zensus2022.py || echo "  ⚠ Skipped (missing dependencies or data)"
else
  echo "▶ Step 4/4: Skipping Zensus (flag or missing data)"
fi
echo ""

# ─── Summary ────────────────────────────────────────
echo "════════════════════════════════════════════════"
echo "  BUILD COMPLETE"
echo "════════════════════════════════════════════════"
echo "Dashboard:  docs/index.html"
echo "Data files: $(find docs/data/processed -name '*.json' | wc -l | tr -d ' ') JSON files"
SIZE=$(du -sh docs/data/ 2>/dev/null | cut -f1)
echo "Data size:  $SIZE"
echo ""
echo "To deploy:  git push origin main"
echo "Live URL:   https://ravidvr.github.io/mietspiegel-digitization/"
