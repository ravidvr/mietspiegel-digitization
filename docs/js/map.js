// Mietspiegel Berlin — map: heatmap, overlay, labels, click handler (ES module)
import * as S from './state.js';
import { t, lang } from './i18n.js';
import { findDistrict, showDistrictCard } from './district.js';

// ─── Heatmap helpers ──────────────────────────────────────────
export function zScore(v, mean, std) { return std > 0 ? (v - mean) / std : 0; }

function getHeatParams(z) {
  if (z <= 9)  return { radius: 20, blur: 12, minOpacity: 0.15 };
  if (z <= 11) return { radius: 14, blur: 8,  minOpacity: 0.20 };
  if (z <= 13) return { radius: 10, blur: 6,  minOpacity: 0.25 };
  if (z <= 15) return { radius: 8,  blur: 4,  minOpacity: 0.30 };
  return { radius: 12, blur: 3, minOpacity: 0.35 };
}

export function buildHeatmap() {
  if (S.heatLayer) { S.map.removeLayer(S.heatLayer); S.heatLayer = null; }
  const cells = S.zensusMode ? S.zensusCells : S.immoGrids;
  const mean = S.zensusMode ? S.zensusMean : S.immoMean;
  const std  = S.zensusMode ? S.zensusStd  : S.immoStd;
  if (!cells.length) return;

  const heatData = S.zensusMode
    ? cells.map(c => [c[0], c[1], Math.max(0, Math.min(1, (zScore(c[2], mean, std) + 3) / 6))])
    : cells.map(g => [g.lat, g.lng, Math.max(0, Math.min(1, (zScore(g.rent, mean, std) + 3) / 6))]);

  const p = getHeatParams(S.map.getZoom());
  S.heatLayer = L.heatLayer(heatData, {
    radius: p.radius, blur: p.blur, max: 1.0, minOpacity: p.minOpacity,
    gradient: { 0.0:'#00a550', 0.2:'#7fc440', 0.4:'#e0d040', 0.6:'#f09030', 0.8:'#e04030', 1.0:'#b01020' }
  }).addTo(S.map);
  S.map._currentCells = S.zensusMode
    ? cells.map(c => ({ lat:c[0], lng:c[1], rent:c[2] }))
    : cells;

  S.map.on('zoomend', () => {
    if (!S.heatLayer) return;
    const zp = getHeatParams(S.map.getZoom());
    S.heatLayer.setOptions({ radius: zp.radius, blur: zp.blur, minOpacity: zp.minOpacity });
  });
}

// ─── District overlay ─────────────────────────────────────────
export function loadDistrictOverlay() {
  if (!S.districtGeo) return;
  S.berlinLayer = L.geoJSON(S.districtGeo, {
    style: f => {
      const a = f.properties.avg_rent || 12;
      return { fillColor: a<10?'#48bb78':a<11?'#86c97a':a<11.5?'#ecc94b':a<12?'#ed8936':'#f56565', fillOpacity: 0.15, weight: 1.5, color: '#8b8fa3', dashArray: '4 2' };
    },
    onEachFeature: (f, layer) => {
      layer.bindTooltip(`${f.properties.district}<br>ø €${f.properties.avg_rent}/m²`, { sticky: true });
      layer.on('click', () => showDistrictCard(f.properties));
    }
  }).addTo(S.map);
}

// ─── District labels ──────────────────────────────────────────
export function buildDistrictLabels() {
  S.districts.forEach(d => {
    const icon = L.divIcon({
      className: 'district-label',
      html: `<div class="dl-bg"><span class="dl-n">${d.district}</span><br><span class="dl-r">€${d.avg_rent}/m²</span></div>`,
      iconSize: [0, 0], iconAnchor: [40, 10]
    });
    const m = L.marker([d.lat, d.lng], { icon, interactive: true, zIndexOffset: 100 }).addTo(S.map);
    m.on('click', () => showDistrictCard(d));
    m._district = d.district;
    S.districtLabels.push(m);
  });
}

export function filterDistrictLabels() {
  const dr = document.getElementById('f-district').value;
  const rt = document.getElementById('f-rent').value;
  const sr = document.getElementById('f-search').value.toLowerCase();
  S.districtLabels.forEach(m => {
    const d = S.districts.find(x => x.district === m._district);
    if (!d) { if (m._icon) m._icon.style.display = 'none'; return; }
    if (dr && d.district !== dr) { if (m._icon) m._icon.style.display = 'none'; return; }
    if (sr && !d.district.toLowerCase().includes(sr)) { if (m._icon) m._icon.style.display = 'none'; return; }
    const a = d.avg_rent;
    if (rt==='lt10'&&a>=10||rt==='10-14'&&(a<10||a>=14)||rt==='gt14'&&a<14) { if (m._icon) m._icon.style.display = 'none'; return; }
    if (m._icon) m._icon.style.display = '';
  });
}

export function applyFilters() { filterDistrictLabels(); }

// ─── Zensus toggle ────────────────────────────────────────────
export async function toggleZensus() {
  const btn = document.getElementById('zensus-btn');
  S.zensusMode = !S.zensusMode;
  if (!S.zensusCells.length && S.zensusMode) { btn.textContent = '⏳ No data'; S.zensusMode = false; return; }
  buildHeatmap();
  const leg = document.getElementById('legend-title');
  if (S.zensusMode) {
    leg.textContent = 'Zensus 2022 (Official Census)';
    btn.style.background = 'var(--accent)'; btn.style.color = '#fff'; btn.textContent = '📋 Census ✓';
  } else {
    leg.textContent = 'Heatmap (Immoscout24)';
    btn.style.background = ''; btn.style.color = ''; btn.textContent = '📋 Zensus 2022';
  }
}

// ─── Sidebar toggle ───────────────────────────────────────────
export function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  sb.classList.toggle('hidden');
  document.getElementById('sidebar-toggle').textContent = sb.classList.contains('hidden') ? '📊' : '✕';
}

// ─── Click handler ────────────────────────────────────────────
export function setupClickHandler() {
  S.map.on('click', e => {
    if (e.originalEvent && e.originalEvent.target && e.originalEvent.target.closest('.district-label')) return;
    const { lat, lng } = e.latlng;
    const cells = S.map._currentCells;
    if (!cells) return;

    let best = null, bestD = Infinity;
    for (const p of cells) {
      const d = (p.lat-lat)**2 + (p.lng-lng)**2;
      if (d < bestD) { bestD = d; best = p; }
    }
    S.clickThreshold = 0.001 * Math.pow(2, 14 - S.map.getZoom());
    if (!best || bestD > S.clickThreshold) return;

    S.clickCell = best; S.clickLat = lat; S.clickLng = lng;
    S.clickDistrict = findDistrict(lat, lng);
    renderClickTooltip();
  });
}

export function renderClickTooltip() {
  if (!S.clickCell) return;
  const best = S.clickCell, lat = S.clickLat, lng = S.clickLng;
  const mean = S.zensusMode ? S.zensusMean : S.immoMean;
  const std  = S.zensusMode ? S.zensusStd  : S.immoStd;
  const loc = best.plz ? `PLZ ${best.plz} · ${best.location || 'Berlin'}` : 'Berlin';
  const district3 = S.clickDistrict;

  let html = `<button class="close" onclick="document.getElementById('map-tooltip').style.display='none'">×</button><div class="dc">
    <h3>📍 ${loc}</h3>
    <div class="val">€${best.rent.toFixed ? best.rent.toFixed(1) : best.rent}/m²</div>
    <div class="sub" style="margin-top:2px">${S.zensusMode ? t('census_rent_lbl') : t('market_rent_lbl')}</div>`;

  if (district3 && !S.zensusMode) {
    const dDiff = best.rent - district3.avg_rent;
    const dPct = Math.round(Math.abs(dDiff) / district3.avg_rent * 100);
    const dAbove = dDiff > 0;
    const dc = dAbove ? 'var(--red)' : 'var(--green)';
    html += '<div style="margin-top:6px;padding:6px 8px;background:var(--surface2);border-radius:4px;font-size:11px">' +
      '<span style="color:var(--text-dim)">📍 ' + district3.district + ' \xF8:</span>' +
      '<span style="font-weight:700;margin:0 4px">\u20AC' + district3.avg_rent + '/m\u00B2</span>' +
      '<span style="color:' + dc + ';font-weight:600">\u2014 ' + dPct + '% ' + t(dAbove ? 'above' : 'below') + ' Kiez</span>' +
      '</div>';
  }

  if (!S.zensusMode && S.zensusCells.length) {
    let zBest = null, zBestD = Infinity;
    for (const zc of S.zensusCells) {
      const d = (zc[0]-lat)**2 + (zc[1]-lng)**2;
      if (d < zBestD) { zBestD = d; zBest = zc; }
    }
    if (zBest && zBestD < S.clickThreshold) {
      const zsRent = zBest[2];
      const premium = ((best.rent - zsRent) / zsRent * 100);
      const pct = premium > 0 ? `${premium.toFixed(0)}% ${t('more')}` : `${Math.abs(premium).toFixed(0)}% ${t('less')}`;
      const pc = premium > 20 ? 'var(--red)' : premium > 5 ? 'var(--orange)' : premium > -5 ? 'var(--yellow)' : 'var(--green)';
      html += `<div style="margin-top:8px;padding:8px;background:var(--surface2);border-radius:4px">
        <div style="font-size:11px;font-weight:600;margin-bottom:4px">📊 ${t('what_people_pay')}</div>
        <div style="display:flex;justify-content:space-between;align-items:baseline">
          <span style="font-size:10px;color:var(--text-dim)">${t('official_census')}</span>
          <span style="font-weight:700;font-size:15px">€${zsRent.toFixed(1)}/m²</span>
        </div>
        <div style="margin-top:3px;font-size:10px;color:${pc};font-weight:600">
          ${t('listings_cost')} <b>${pct}</b> ${t('than_tenants')}
        </div></div>`;
    }
  }

  if (!S.zensusMode && S.berlinMietspiegel) {
    const l = S.berlinMietspiegel.tables.find(t => t.lage === 'mittel') || S.berlinMietspiegel.tables[0];
    if (l) {
      const vals = l.rows.map(r => r['40_60'] || r.bis_40 || 0).filter(x => x > 0);
      const msAvg = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : null;
      if (msAvg) {
        const gap = ((best.rent - msAvg) / msAvg * 100);
        const gc = gap > 5 ? 'var(--red)' : gap > -5 ? 'var(--yellow)' : 'var(--green)';
        const gapDir = gap > 0 ? 'above_off_idx' : 'below_off_idx';
        const gapText = `${Math.abs(gap).toFixed(0)}% ${t(gapDir)}`;
        html += `<div style="margin-top:6px;padding:8px;background:var(--surface2);border-radius:4px">
          <div style="font-size:11px;font-weight:600;margin-bottom:4px">📋 ${t('off_mietspiegel')} (${S.berlinMietspiegel.year})</div>
          <div style="display:flex;justify-content:space-between;margin-top:3px">
            <span>${t('legal_ref')}</span><span style="font-weight:700">€${msAvg.toFixed(2)}/m²</span>
          </div>
          <div style="margin-top:2px;font-size:10px;color:${gc};font-weight:600">
            ${t('market_listings_are')} <b>${gapText}</b>
          </div></div>`;
      }
    }
  }
  html += '</div>';
  document.getElementById('map-tooltip').style.display = 'block';
  document.getElementById('map-tooltip').innerHTML = html;
}
