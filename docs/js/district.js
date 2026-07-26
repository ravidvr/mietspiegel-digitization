// Mietspiegel Berlin — district card, Mietspiegel table, comparison (ES module)
import * as S from './state.js';
import { t } from './i18n.js';

// ─── Point-in-polygon ─────────────────────────────────────────
export function pointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];
    const intersect = ((yi > point[1]) !== (yj > point[1]))
      && (point[0] < (xj - xi) * (point[1] - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

export function findDistrict(lat, lng) {
  if (!S.districtGeo || !S.districtGeo.features) return null;
  for (const f of S.districtGeo.features) {
    if (f.geometry.type === 'Polygon') {
      if (pointInPolygon([lng, lat], f.geometry.coordinates[0])) return f.properties;
    } else if (f.geometry.type === 'MultiPolygon') {
      for (const poly of f.geometry.coordinates) {
        if (pointInPolygon([lng, lat], poly[0])) return f.properties;
      }
    }
  }
  return null;
}

// ─── District card ────────────────────────────────────────────
export function showDistrictCard(p) {
  S.cardDistrict = p;
  renderDistrictCard();
}

export function renderDistrictCard() {
  const p = S.cardDistrict;
  if (!p) return;
  const panel = document.getElementById('map-tooltip');
  panel.style.display = 'block';
  const col = p.avg_rent<10?'#48bb78':p.avg_rent<11.5?'#ecc94b':p.avg_rent<12.5?'#ed8936':'#f56565';
  panel.innerHTML = `<button class="close" onclick="document.getElementById('map-tooltip').style.display='none'">×</button>` + `<div class="dc">
    <h3>${p.district}</h3>
    <div class="loc">Berlin · ${p.total_addresses.toLocaleString()} ${t('addresses')}</div>
    <div style="margin-top:8px">
      <div>🟢 Einfach: <b>${p.einfach_pct}%</b></div>
      <div>🟡 Mittel: <b>${p.mittel_pct}%</b></div>
      <div>🔴 Gut: <b>${p.gut_pct}%</b></div>
    </div>
    <div style="margin-top:8px;padding:6px;background:var(--surface2);border-radius:4px;text-align:center">
      <div style="font-size:22px;font-weight:700;color:${col}">ø €${p.avg_rent}/m²</div>
      <div class="sub">${t('est_avg_cold')}</div>
    </div>
    ${S.berlinMietspiegel ? renderMietspiegelTable(p) : ''}
  </div>`;
}

function renderMietspiegelTable(p) {
  const d = S.berlinMietspiegel;
  const l = d.tables.find(t => t.lage === 'mittel') || d.tables[0];
  if (!l) return '';
  const szK = s => s==='bis 40 m²'?'bis_40':s==='40-60 m²'?'40_60':s==='60-90 m²'?'60_90':'ueber_90';
  const hd = (d.baujahr_groups || l.rows.map(r => r.baujahr)).map(b => `<th>${b}</th>`).join('');
  const bd = (d.size_categories || ['40-60 m²']).map(s => {
    const k = szK(s);
    return `<tr><td>${s}</td>${l.rows.map(r => `<td>${r[k]!=null?'€'+r[k].toFixed(2):'—'}</td>`).join('')}</tr>`;
  }).join('');
  const title = t('ms_title').replace('{year}', d.year);
  return `<div style="margin-top:10px">
    <div style="font-size:11px;font-weight:600;margin-bottom:4px">📋 ${title}</div>
    <table><thead><tr><th>Größe</th>${hd}</tr></thead><tbody>${bd}</tbody></table>
    <div class="sub">${t('net_cold')} · <a href="${d.source_url||'#'}" style="color:var(--accent)" target="_blank">${t('src')}</a></div>
  </div>`;
}

// ─── Comparison sidebar ───────────────────────────────────────
export function renderComparison() {
  const panel = document.getElementById('p-compare');
  if (!S.cmpData || !S.cmpData.districts) { panel.innerHTML = '<div class="es">Loading comparison data...</div>'; return; }
  panel.innerHTML = S.cmpData.districts.map(d => {
    const g = d.gap_pct;
    const gc = g > 5 ? 'var(--red)' : g > -5 ? 'var(--yellow)' : 'var(--green)';
    const barW = Math.min(100, Math.abs(g) * 3);
    const barC = g > 0 ? 'var(--red)' : 'var(--green)';
    return `<div class="cr">
      <span class="cn" onclick="document.querySelector('#map')._zoomToDistrict('${d.district}')">${d.district}</span>
      <span class="cv">€${d.avg_rent}</span>
      <span class="bar"><span class="fill" style="width:${barW}%;background:${barC}"></span></span>
      <span class="cg" style="color:${gc}">${g>0?'+':''}${g}%</span>
    </div>`;
  }).join('');
}

// ─── Zoom to district ─────────────────────────────────────────
export function zoomToDistrict(name) {
  if (!S.districtGeo) return;
  const feat = S.districtGeo.features.find(f => f.properties.district === name);
  if (!feat) return;
  const layer = Object.values(S.berlinLayer._layers).find(l => l.feature === feat);
  if (layer) {
    S.map.fitBounds(layer.getBounds(), {padding:[30,30], maxZoom:14});
    showDistrictCard(feat.properties);
  }
}

// Wire global onclick handler for zoom in comparison sidebar
document.querySelector('#map')._zoomToDistrict = zoomToDistrict;
