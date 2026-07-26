// Mietspiegel Berlin — main entry point (ES module)
import * as S from './state.js';
import { lang, applyLang } from './i18n.js';
import { buildHeatmap, loadDistrictOverlay, buildDistrictLabels, setupClickHandler } from './map.js';
import { renderComparison } from './district.js';
import { dismissWelcome } from './welcome.js';

// ─── Init ─────────────────────────────────────────────────────
async function init() {
  document.getElementById('p-compare').innerHTML = '<div class="es">⏳ Loading data...</div>';

  const BERLIN_BOUNDS = [[52.32, 13.05], [52.70, 13.78]];
  S.map = L.map('map', {
    center: [52.52, 13.405], zoom: 11, scrollWheelZoom: true,
    minZoom: 10, maxZoom: 18,
    maxBounds: BERLIN_BOUNDS, maxBoundsViscosity: 1.0
  });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OSM', maxZoom: 18 }).addTo(S.map);

  // Load data
  try { const r = await fetch(S.DATA + 'berlin_districts_index.json'); S.districts = await r.json(); } catch(e) { console.error('District index failed:', e); }
  try { const r = await fetch(S.DATA + 'berlin-districts-choropleth.geojson'); S.districtGeo = await r.json(); } catch(e) { console.error('District geojson failed:', e); }
  try {
    const r = await fetch(S.DATA + 'berlin_immoscout.json?v=2');
    const d = await r.json();
    S.immoMean = d.mean; S.immoStd = d.std; S.immoGrids = d.grids;
    document.getElementById('district-count').textContent = d.clean + ' cells · 12 Bezirke';
    if (d.generated_at) {
      const dt = new Date(d.generated_at);
      document.getElementById('data-freshness').textContent =
        '📅 Data: ' + dt.toLocaleDateString(lang === 'de' ? 'de-DE' : 'en-US',
          { year: 'numeric', month: 'short', day: 'numeric' });
    }
  } catch(e) { console.error('Immoscout failed:', e); }
  try { const r = await fetch(S.DATA + 'berlin_zensus.json?v=2'); const d = await r.json(); S.zensusMean = d.mean; S.zensusStd = d.std; S.zensusCells = d.cells_slim; } catch(e) { console.error('Zensus failed:', e); }
  try { const r = await fetch(S.DATA + 'berlin.json?v=1'); S.berlinMietspiegel = await r.json(); } catch(e) { console.error('Mietspiegel failed:', e); }
  try { const r = await fetch(S.DATA + 'berlin_districts_comparison.json?v=1'); S.cmpData = await r.json(); } catch(e) { console.error('Comparison failed:', e); }

  // District filter dropdown
  const sel = document.getElementById('f-district');
  sel.innerHTML = '<option value="" data-i18n="all_districts">All Districts</option>';
  S.districts.sort((a,b) => a.district.localeCompare(b.district)).forEach(d => {
    const o = document.createElement('option'); o.value = d.district; o.textContent = d.district; sel.appendChild(o);
  });

  // Build UI
  loadDistrictOverlay();
  buildDistrictLabels();
  buildHeatmap();
  setupClickHandler();
  renderComparison();
  applyLang();

  if (localStorage.getItem('mietspiegel-welcome') === '1') document.getElementById('welcome').style.display = 'none';

  // Expose globals for onclick handlers in HTML
  window.toggleLang = (await import('./i18n.js')).toggleLang;
  window.toggleDark = function() { document.body.classList.toggle('dark'); };
  window.toggleZensus = (await import('./map.js')).toggleZensus;
  window.toggleSidebar = (await import('./map.js')).toggleSidebar;
  window.applyFilters = (await import('./map.js')).applyFilters;
  window.dismissWelcome = dismissWelcome;
  window.showWelcome = (await import('./welcome.js')).showWelcome;
  window.debouncedSuggest = (await import('./search.js')).debouncedSuggest;
  window.handleSearchKey = (await import('./search.js')).handleSearchKey;
}

// ─── Boot ─────────────────────────────────────────────────────
init().catch(e => console.error('Init failed:', e));
