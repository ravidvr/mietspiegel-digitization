// Mietspiegel Berlin — Insights tab (ES module)
import * as S from './state.js';

export async function loadInsights() {
  const panel = document.getElementById('insights-panel');
  panel.innerHTML = '<div class="es">⏳ Loading insights...</div>';

  try {
    const [rankings, spread, premium, berlinTable] = await Promise.all([
      fetch(S.DATA + 'insights_city_rankings.json').then(r => r.json()),
      fetch(S.DATA + 'insights_gut_spread.json').then(r => r.json()),
      fetch(S.DATA + 'insights_district_premium.json').then(r => r.json()),
      fetch(S.DATA + 'insights_berlin_table.json').then(r => r.json()),
    ]);

    panel.innerHTML = renderCityRankings(rankings) + renderGutSpread(spread) +
      renderDistrictPremium(premium) + renderBerlinTable(berlinTable);
  } catch(e) {
    panel.innerHTML = '<div class="es">⚠ Insights data not available. Run: python3 analytics/export_insights.py</div>';
  }
}

function renderCityRankings(data) {
  const cities = (data.data || []).slice(0, 12);
  const labels = cities.map(c => c.city);
  const values = cities.map(c => c.avg_rent);

  return `<div class="insight-card">
    <h3>📊 City Rent Rankings <span style="font-weight:400;font-size:11px;color:var(--text-dim)">— mittlere Wohnlage, 40–60 m²</span></h3>
    <div class="chart-wrap"><canvas id="chart-rankings"></canvas></div>
    <script-data id="data-rankings" data-labels='${JSON.stringify(labels)}' data-values='${JSON.stringify(values)}'></script-data>
  </div>`;
}

function renderGutSpread(data) {
  const cities = (data.data || []).slice(0, 10);
  const labels = cities.map(c => c.city);
  const gutVals = cities.map(c => c.gut_rent);
  const einfVals = cities.map(c => c.einfach_rent);

  return `<div class="insight-card">
    <h3>📈 Gut vs Einfach Rent Spread <span style="font-weight:400;font-size:11px;color:var(--text-dim)">— rent inequality by city</span></h3>
    <div class="chart-wrap"><canvas id="chart-spread"></canvas></div>
    <script-data id="data-spread" data-labels='${JSON.stringify(labels)}' data-gut='${JSON.stringify(gutVals)}' data-einfach='${JSON.stringify(einfVals)}'></script-data>
  </div>`;
}

function renderDistrictPremium(data) {
  const districts = (data.data || []);
  const labels = districts.map(d => d.district);
  const market = districts.map(d => d.market_rent);
  const official = districts.map(d => d.official_rent);

  return `<div class="insight-card">
    <h3>🏙️ Berlin Market Premium <span style="font-weight:400;font-size:11px;color:var(--text-dim)">— Immoscout asking rent vs Mietspiegel reference</span></h3>
    <p style="font-size:11px;color:var(--text-dim);margin-bottom:8px">Market asking rents are consistently higher than the official Mietspiegel reference. This gap represents the "market heat" — what landlords actually demand vs the legal benchmark.</p>
    <div class="chart-wrap"><canvas id="chart-premium"></canvas></div>
    <script-data id="data-premium" data-labels='${JSON.stringify(labels)}' data-market='${JSON.stringify(market)}' data-official='${JSON.stringify(official)}'></script-data>
  </div>`;
}

function renderBerlinTable(data) {
  if (!data || !data.rows) return '';
  const rows = data.rows;
  const sizeKeys = ['40_60', '60_90', 'ueber_90', 'bis_40'];
  const sizeLabels = {'40_60': '40–60 m²', '60_90': '60–90 m²', 'ueber_90': '>90 m²', 'bis_40': '≤40 m²'};

  return `<div class="insight-card">
    <h3>📋 Berlin Mietspiegel ${data.year} <span style="font-weight:400;font-size:11px;color:var(--text-dim)">— mittlere Wohnlage, €/m²</span></h3>
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px">
      <thead><tr><th style="text-align:left;padding:4px 8px;border-bottom:2px solid var(--border)">Baujahr</th>
        ${sizeKeys.map(s => `<th style="padding:4px 8px;border-bottom:2px solid var(--border)">${sizeLabels[s]||s}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r => `<tr>
        <td style="padding:3px 8px;font-weight:600;border-bottom:1px solid var(--border)">${r.baujahr}</td>
        ${sizeKeys.map(s => `<td style="text-align:center;padding:3px 8px;border-bottom:1px solid var(--border)">${r[s] != null ? '€' + Number(r[s]).toFixed(2) : '—'}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>
    <p style="font-size:10px;color:var(--text-dim);margin-top:6px">Net cold rent (Nettokaltmiete). Source: Berliner Mietspiegel ${data.year}.</p>
  </div>`;
}

// ─── Chart rendering (called after DOM is ready) ──────────────
export function renderInsightCharts() {
  const chartDefaults = {
    type: 'bar',
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8b8fa3', font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: '#8b8fa3', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,.05)' } },
        y: { ticks: { color: '#8b8fa3', font: { size: 10 }, callback: v => '€' + v }, grid: { color: 'rgba(255,255,255,.05)' } }
      }
    }
  };

  // City rankings
  const rEl = document.getElementById('data-rankings');
  if (rEl) {
    new Chart(document.getElementById('chart-rankings'), {
      ...chartDefaults,
      data: {
        labels: JSON.parse(rEl.dataset.labels),
        datasets: [{
          label: 'Avg rent (€/m²)', data: JSON.parse(rEl.dataset.values),
          backgroundColor: '#5b8def', borderRadius: 4
        }]
      }
    });
  }

  // Gut spread
  const sEl = document.getElementById('data-spread');
  if (sEl) {
    new Chart(document.getElementById('chart-spread'), {
      ...chartDefaults,
      data: {
        labels: JSON.parse(sEl.dataset.labels),
        datasets: [
          { label: 'Gut', data: JSON.parse(sEl.dataset.gut), backgroundColor: '#f56565', borderRadius: 4 },
          { label: 'Einfach', data: JSON.parse(sEl.dataset.einfach), backgroundColor: '#48bb78', borderRadius: 4 }
        ]
      }
    });
  }

  // District premium
  const pEl = document.getElementById('data-premium');
  if (pEl) {
    new Chart(document.getElementById('chart-premium'), {
      ...chartDefaults,
      data: {
        labels: JSON.parse(pEl.dataset.labels),
        datasets: [
          { label: 'Immoscout market', data: JSON.parse(pEl.dataset.market), backgroundColor: '#ed8936', borderRadius: 4 },
          { label: 'Mietspiegel official', data: JSON.parse(pEl.dataset.official), backgroundColor: '#5b8def', borderRadius: 4 }
        ]
      }
    });
  }
}
