// Functional DOM test for the Berlin Rent Check — the flagship feature.
// Loads docs/berlin.html in jsdom, stubs Leaflet + fetch (real berlin.json),
// fills the Rent Check form and asserts the verdict renders with the
// correct official-table numbers (Mietspiegel range + 110%-of-upper cap).
//
// Run: node scripts/verify-rent-check-dom.js   (from repo root, needs jsdom)
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'docs/berlin.html'), 'utf8');
const berlinData = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'docs/data/processed/berlin.json'), 'utf8'));

// strip external CDN scripts (Leaflet etc.) — we stub them instead
const stripped = html.replace(/<script src="https?[^"]*"><\/script>/g, '');

const dom = new JSDOM(stripped, {
  url: 'https://ravidvr.github.io/mietspiegel-digitization/berlin.html',
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  beforeParse(window) {
    // fetch stub: serve the real data files
    const immo = JSON.parse(require('fs').readFileSync(
      '/Users/ruhvee/mietspiegel-digitization/docs/data/processed/berlin_immoscout.json', 'utf8'));
    const zensus = JSON.parse(require('fs').readFileSync(
      '/Users/ruhvee/mietspiegel-digitization/docs/data/processed/berlin_zensus.json', 'utf8'));
    window.fetch = async (url) => {
      const u = String(url);
      if (u.includes('berlin_districts')) return { json: async () => JSON.parse(require('fs').readFileSync('/Users/ruhvee/mietspiegel-digitization/docs/data/processed/berlin_districts_comparison.json', 'utf8')) };
      if (u.includes('berlin.json')) return { json: async () => berlinData };
      if (u.includes('berlin_immoscout')) return { json: async () => immo };
      if (u.includes('berlin_zensus')) return { json: async () => zensus };
      if (u.includes('geojson')) return { json: async () => ({ features: [] }) };
      return { json: async () => ({}) };
    };
    // Leaflet stub — enough API for init()
    window.L = {
      map: () => ({
        setView: () => ({}), invalidateSize: () => ({}),
        addLayer: () => ({}), on: () => ({}), remove: () => ({}),
        fitBounds: () => ({}), closePopup: () => ({}), getZoom: () => 13,
        scrollWheelZoom: { enable: () => ({}), disable: () => ({}) },
      }),
      control: { zoom: () => ({ addTo: () => ({}) }) },
      tileLayer: () => ({ addTo: () => ({}) }),
      marker: () => ({ addTo: () => ({}), bindPopup: () => ({}) }),
      circleMarker: () => ({ addTo: () => ({}), bindPopup: () => ({}) }),
      geoJSON: () => ({ addTo: () => ({}), bindPopup: () => ({}) }),
      popup: () => ({ setLatLng: () => ({}), setContent: () => ({}) }),
      heatLayer: () => ({ addTo: () => ({}), setLatLngs: () => ({}) }),
    };
    window.localStorage.clear();
  },
});

const w = dom.window;
const d = w.document;

function fail(msg) {
  console.error('FAIL:', msg);
  process.exit(1);
}

// wait for init to settle (async loaders)
setTimeout(() => {
  try {
    // 1. Baujahr select must be populated from the real table
    const sel = d.getElementById('rc-baujahr');
    const cohorts = [...sel.options].map(o => o.value);
    if (cohorts.length < 12) fail(`baujahr select only ${cohorts.length} options: ${cohorts}`);
    if (!cohorts.includes('1973-1985 West') || !cohorts.includes('2016-2022'))
      fail('official West/Ost cohorts missing from select');

    // 2. Fill the form: Charlottenburg-Wilmersdorf, einfach, bis 1918, 45 m², 500 €
    d.getElementById('rc-district').value = 'Charlottenburg-Wilmersdorf';
    d.getElementById('rc-lage').value = 'einfach';
    d.getElementById('rc-baujahr').value = 'bis 1918';
    d.getElementById('rc-size').value = '45';
    d.getElementById('rc-rent').value = '500';
    w.updateRentCheck();

    const result = d.getElementById('rcResult');
    const htmlOut = result ? result.innerHTML : '';
    // official band einfach/bis1918/45-55: untere 6.10, obere 11.19 (PDF-verified)
    // 45 m²: range €275-€504; cap = 11.19*45*1.1 = €554
    // asking €500 -> at or below cap
    if (!htmlOut.includes('At or below the cap')) {
      fail('below-cap verdict missing — got: ' + htmlOut.replace(/<[^>]+>/g, ' ').slice(0, 250));
    }
    if (!htmlOut.includes('€554/month')) fail('cap value wrong — expected €554/month');
    if (!htmlOut.includes('€275 – €504/month')) fail('official range wrong — expected €275 – €504/month');

    // above-cap case: asking €600
    d.getElementById('rc-rent').value = '600';
    w.updateRentCheck();
    const html2 = d.getElementById('rcResult').innerHTML;
    if (!html2.includes('Above the Mietpreisbremse cap')) {
      fail('above-cap verdict missing — got: ' + html2.replace(/<[^>]+>/g, ' ').slice(0, 250));
    }
    if (!html2.includes('€46/month')) fail('overpay amount wrong — expected €46/month');

    console.log('Rent Check functional test PASSED');
    console.log('  baujahr options:', cohorts.length, '(official cohorts incl. West/Ost)');
    console.log('  below-cap case: €500 vs cap €554 -> "At or below the cap"');
    console.log('  above-cap case: €600 vs cap €554 -> "Above the Mietpreisbremse cap" +€46/month');
    process.exit(0);
  } catch (e) {
    fail('exception: ' + e.stack);
  }
}, 3000);
