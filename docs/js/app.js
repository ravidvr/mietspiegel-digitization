/* Mietspiegel Digitization — Main Application */
(function() {
  'use strict';

  const DATA_PATH = 'data/processed/';
  const CITIES = ['berlin','hamburg','munich','cologne','frankfurt','stuttgart','duesseldorf','leipzig','dresden','hannover'];
  let cityData = {};
  let trendChart = null;

  // ---- Utility ----
  const formatEur = v => v.toFixed(2).replace('.', ',');

  // ---- Data loading ----
  async function loadAllCities() {
    const container = document.getElementById('app');
    container.innerHTML = '<div class="loading">Daten werden geladen</div>';
    const results = await Promise.allSettled(
      CITIES.map(slug =>
        fetch(DATA_PATH + slug + '.json').then(r => r.json())
      )
    );
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') cityData[CITIES[i]] = r.value;
    });
    const loaded = Object.keys(cityData).length;
    if (loaded === 0) {
      container.innerHTML = '<div class="status-message status-error">❌ Failed to load city data. Files may not exist at ' + DATA_PATH + '</div>';
      return;
    }
    return cityData;
  }

  // ---- Tabs ----
  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      });
    });
  }

  // ---- Map ----
  let map = null;
  function initMap() {
    const el = document.getElementById('map');
    if (!el) return;
    map = L.map('map', { zoomControl: true }).setView([51.15, 10.45], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '© <a href="https://openstreetmap.org/copyright">OSM</a>'
    }).addTo(map);
  }

  function addCityMarkers(data) {
    if (!map) return;
    Object.values(data).forEach(c => {
      const rent = c.current_edition.tables.mittel.find(r => r.baujahr === '2011-2024' || r.baujahr.includes('2011'));
      const avg = rent ? rent.size_60_90 : 0;
      const color = avg > 14 ? '#ef4444' : avg > 10 ? '#f59e0b' : '#22c55e';
      const marker = L.circleMarker([c.lat, c.lng], {
        radius: 10 + Math.sqrt(c.population) / 200,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
      }).addTo(map);
      marker.bindPopup(`
        <b>${c.city}</b><br>
        <span style="color:#666">${c.state}</span><br>
        Ø Mietspiegel (Mittel, 60-90m²): <b>${formatEur(avg)} €/m²</b><br>
        <a href="#" onclick="window.showCityDetail('${c.city_slug}'); return false;">Details anzeigen →</a>
      `);
    });
  }

  // ---- City list cards ----
  function renderCityList(data) {
    const el = document.getElementById('city-list');
    if (!el) return;
    el.innerHTML = '<h2 class="section-title">Städte (Top 10)</h2><div class="city-grid">' +
      Object.values(data).sort((a,b)=>b.population-a.population).map(c => {
        const rent = c.current_edition.tables.mittel.find(r => r.baujahr.includes('2011'));
        const avg = rent ? rent.size_60_90 : 0;
        return `<div class="city-card" onclick="window.showCityDetail('${c.city_slug}')">
          <h3>${c.city}</h3>
          <div class="state">${c.state}</div>
          <div class="rent-info">Mietspiegel (Mittel, 60-90m²): <strong>${formatEur(avg)} €/m²</strong></div>
          <div class="pop">👤 ${(c.population/1000).toFixed(0)}k Einwohner · ${c.current_edition.year} Edition</div>
        </div>`;
      }).join('') + '</div>';
  }

  // ---- City detail ----
  window.showCityDetail = function(slug) {
    const c = cityData[slug];
    if (!c) return;
    const el = document.getElementById('city-detail');
    const tables = c.current_edition.tables;
    const lageNames = {einfach:'Einfach', mittel:'Mittel', gut:'Gut'};
    const sizeNames = {size_under_40:'< 40m²', size_40_60:'40-60m²', size_60_90:'60-90m²', size_over_90:'> 90m²'};

    let tableHtml = '';
    ['einfach','mittel','gut'].forEach(lage => {
      if (!tables[lage]) return;
      tableHtml += `<h4 style="margin:1rem 0 0.5rem"><span class="lage-label lage-${lage}">${lageNames[lage]}</span></h4>
        <table class="data-table"><thead><tr><th>Baujahr</th>
        ${Object.keys(tables[lage][0]).filter(k=>k!=='baujahr').map(k=>`<th>${sizeNames[k]||k}</th>`).join('')}
        </tr></thead><tbody>
        ${tables[lage].map(row => `<tr>
          <td class="baujahr-label">${row.baujahr}</td>
          ${Object.entries(row).filter(([k])=>k!=='baujahr').map(([,v])=>`<td>${formatEur(v)} €/m²</td>`).join('')}
        </tr>`).join('')}
        </tbody></table>`;
    });

    const hist = c.history || [];
    const histHtml = hist.length ? `<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border)">
      <h4>Historische Entwicklung</h4>
      <table class="data-table"><thead><tr><th>Jahr</th><th>Gültig ab</th><th>Mittel (60-90m²)</th><th>Mittel (1919-1949)</th></tr></thead><tbody>
      ${hist.map(h => `<tr><td>${h.year}</td><td>${h.valid_from||'—'}</td><td>${formatEur(h.base_rent_mittel_60_90)} €/m²</td><td>${formatEur(h.base_rent_mittel_1919_1949)} €/m²</td></tr>`).join('')}
      </tbody></table></div>` : '';

    el.innerHTML = `<div class="city-detail">
      <div class="city-detail-header">
        <div>
          <h2>${c.city}</h2>
          <div class="meta">${c.state} · ${c.current_edition.year} Edition · <span class="lage-label lage-${c.lage_categories[1]}">${c.type}</span></div>
          <div class="meta" style="margin-top:0.2rem">Gültig: ${c.current_edition.valid_from} – ${c.current_edition.valid_until}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:1.8rem;font-weight:700;color:var(--primary)">${hist.length ? formatEur(hist[hist.length-1].base_rent_mittel_60_90) : '—'} €/m²</div>
          <div class="meta">Ø Mittel (60-90m²)</div>
        </div>
      </div>
      ${tableHtml}
      ${histHtml}
      <div style="margin-top:1rem;font-size:0.8rem;color:var(--text-muted)">
        Quelle: <a href="${c.current_edition.source_url}" target="_blank" style="color:var(--primary)">${c.current_edition.source_url}</a>
      </div>
    </div>`;
    el.scrollIntoView({behavior:'smooth', block:'start'});
  };

  // ================================================================
  // 1. PREMIUM: Bulk CSV Export
  // ================================================================
  function initExport(data) {
    const btn = document.getElementById('export-btn');
    const filterState = document.getElementById('export-state');
    const filterLage = document.getElementById('export-lage');
    const preview = document.getElementById('csv-preview');
    if (!btn) return;

    // Populate state filter
    if (filterState) {
      const states = [...new Set(Object.values(data).map(c => c.state))].sort();
      states.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        filterState.appendChild(opt);
      });
    }

    function generateCSV() {
      const lage = filterLage ? filterLage.value : 'mittel';
      const state = filterState ? filterState.value : 'all';
      const cities = Object.values(data).filter(c => state === 'all' || c.state === state);

      // Header row
      const sizeKeys = ['size_under_40','size_40_60','size_60_90','size_over_90'];
      let csv = 'City,State,Population,Lage,Baujahr,<40 m²,40-60 m²,60-90 m²,>90 m²,Year\n';

      cities.forEach(c => {
        const tables = c.current_edition.tables;
        const lageData = tables[lage];
        if (!lageData) return;
        lageData.forEach(row => {
          csv += `"${c.city}","${c.state}",${c.population},${lage},"${row.baujahr}"`;
          sizeKeys.forEach(k => { csv += `,${row[k] || ''}`; });
          csv += `,${c.current_edition.year}\n`;
        });
      });

      // Append historical data if available
      csv += '\n# Historical Trends\n# City,State,Year,Rent Type,Value\n';
      cities.forEach(c => {
        (c.history || []).forEach(h => {
          csv += `"${c.city}","${c.state}",${h.year},Mittel_60_90,${h.base_rent_mittel_60_90}\n`;
          csv += `"${c.city}","${c.state}",${h.year},Mittel_1919_1949,${h.base_rent_mittel_1919_1949}\n`;
        });
      });

      return csv;
    }

    btn.addEventListener('click', () => {
      const csv = generateCSV();
      const blob = new Blob(['\ufeff' + csv], {type: 'text/csv;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mietspiegel-digitization.csv';
      a.click();
      URL.revokeObjectURL(url);
      if (preview) {
        const lines = csv.split('\n');
        preview.textContent = lines.slice(0, 6).join('\n') + '\n... (' + (lines.length-1) + ' Zeilen insgesamt)';
      }
    });
  }

  // ================================================================
  // 2. PREMIUM: Historical Trends (Chart.js)
  // ================================================================
  function initTrends(data) {
    if (typeof Chart === 'undefined') {
      document.getElementById('trends-panel').innerHTML = '<div class="status-message status-error">Chart.js nicht geladen. Bitte Internetverbindung prüfen.</div>';
      return;
    }
    const citySelect = document.getElementById('trend-city');
    const chartCanvas = document.getElementById('trend-chart');
    const trendType = document.getElementById('trend-type');
    if (!citySelect || !chartCanvas) return;

    // Populate city select
    Object.values(data).sort((a,b)=>a.city.localeCompare(b.city)).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.city_slug; opt.textContent = c.city;
      citySelect.appendChild(opt);
    });

    function renderChart() {
      const slug = citySelect.value;
      const type = trendType ? trendType.value : 'mittel_60_90';
      const c = data[slug];
      if (!c || !c.history || c.history.length < 2) {
        return;
      }
      const hist = c.history.sort((a,b) => a.year - b.year);
      const labels = hist.map(h => h.year);
      let values;
      let label;
      if (type === 'mittel_60_90') {
        values = hist.map(h => h.base_rent_mittel_60_90);
        label = 'Mittelwert 60-90m² (€/m²)';
      } else {
        values = hist.map(h => h.base_rent_mittel_1919_1949);
        label = 'Mittelwert Baujahr 1919-1949 (€/m²)';
      }

      if (trendChart) trendChart.destroy();
      const ctx = chartCanvas.getContext('2d');
      trendChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: c.city + ' — ' + label,
            data: values,
            borderColor: '#1a73e8',
            backgroundColor: '#1a73e840',
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#1a73e8',
            pointRadius: 5,
            pointHoverRadius: 7
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#e1e4ed' } },
            tooltip: {
              callbacks: {
                label: ctx => ctx.parsed.y.toFixed(2) + ' €/m²'
              }
            }
          },
          scales: {
            x: { ticks: { color: '#8b8fa3' }, grid: { color: '#2a2d3a' } },
            y: {
              ticks: { color: '#8b8fa3', callback: v => v + ' €' },
              grid: { color: '#2a2d3a' }
            }
          }
        }
      });
    }

    citySelect.addEventListener('change', renderChart);
    if (trendType) trendType.addEventListener('change', renderChart);
    window._renderTrends = renderChart;

    // City ranking
    renderCityRanking(data);
  }

  function renderCityRanking(data) {
    const el = document.getElementById('city-ranking');
    if (!el) return;
    const entries = Object.values(data).map(c => {
      const rent = c.current_edition.tables.mittel.find(r => r.baujahr.includes('2011'));
      return { name: c.city, slug: c.city_slug, state: c.state, avg: rent ? rent.size_60_90 : 0 };
    }).sort((a,b) => b.avg - a.avg);

    const max = entries[0]?.avg || 1;
    el.innerHTML = entries.map((c, i) => {
      const pct = (c.avg / max * 100).toFixed(0);
      const color = c.avg > 14 ? '#ef4444' : c.avg > 10 ? '#f59e0b' : '#22c55e';
      return `<div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid var(--border)">
        <div style="width:2rem;font-weight:700;color:var(--text-muted);text-align:center">${i+1}.</div>
        <div style="flex:1">
          <div style="font-weight:600">${c.name}</div>
          <div style="font-size:0.75rem;color:var(--text-muted)">${c.state}</div>
        </div>
        <div style="width:60%;background:var(--bg);border-radius:4px;height:1.5rem;position:relative;overflow:hidden">
          <div style="position:absolute;left:0;top:0;height:100%;width:${pct}%;background:${color};border-radius:4px;opacity:0.7;transition:width 0.5s"></div>
        </div>
        <div style="width:6rem;text-align:right;font-weight:700;color:${color}">${c.avg.toFixed(2).replace('.',',')} €/m²</div>
      </div>`;
    }).join('');
  }

  // ================================================================
  // 3. PREMIUM: Email Alerts
  // ================================================================
  function initAlerts(data) {
    const form = document.getElementById('alert-form');
    const emailInput = document.getElementById('alert-email');
    const citySelect = document.getElementById('alert-city');
    const statusEl = document.getElementById('alert-status');
    const subsBody = document.getElementById('subscriptions-body');
    if (!form) return;

    // Populate city select
    Object.values(data).sort((a,b)=>a.city.localeCompare(b.city)).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.city_slug; opt.textContent = c.city;
      citySelect.appendChild(opt);
    });

    // Load stored subscriptions
    function loadSubs() {
      try {
        return JSON.parse(localStorage.getItem('mietspiegel_alerts') || '[]');
      } catch { return []; }
    }

    function saveSubs(subs) {
      localStorage.setItem('mietspiegel_alerts', JSON.stringify(subs));
    }

    function renderSubs() {
      if (!subsBody) return;
      const subs = loadSubs();
      if (subs.length === 0) {
        subsBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:2rem">Noch keine Abonnements</td></tr>';
        return;
      }
      subsBody.innerHTML = subs.map((s, i) => {
        const cityName = data[s.city] ? data[s.city].city : s.city;
        const maxRentText = s.max_rent ? `${s.max_rent.toFixed(2)} €/m²` : '—';
        const changePct = s.change_pct ? `${s.change_pct}%` : '—';
        return `<tr>
          <td>${escapeHtml(s.email)}</td>
          <td>${cityName}</td>
          <td>${maxRentText}</td>
          <td>${changePct}</td>
          <td><button class="btn btn-sm btn-danger" onclick="window._removeAlert(${i})">× Entfernen</button></td>
        </tr>`;
      }).join('');
    }

    window._removeAlert = function(idx) {
      const subs = loadSubs();
      subs.splice(idx, 1);
      saveSubs(subs);
      renderSubs();
      if (statusEl) {
        statusEl.className = 'status-message status-info';
        statusEl.textContent = 'Abonnement entfernt.';
      }
    };

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = emailInput.value.trim();
      const city = citySelect.value;
      const maxRent = parseFloat(document.getElementById('alert-max-rent').value) || 0;
      const changePct = parseFloat(document.getElementById('alert-change').value) || 0;
      if (!email || !email.includes('@')) {
        if (statusEl) { statusEl.className = 'status-message status-error'; statusEl.textContent = 'Bitte eine gültige E-Mail-Adresse eingeben.'; }
        return;
      }
      const subs = loadSubs();
      subs.push({ email, city, max_rent: maxRent, change_pct: changePct, created_at: new Date().toISOString() });
      saveSubs(subs);
      renderSubs();
      emailInput.value = '';
      if (statusEl) {
        statusEl.className = 'status-message status-success';
        statusEl.textContent = `✅ Abonnement für ${data[city]?.city || city} wurde gespeichert!`;
      }

      // Demo: show what would happen on a Mietspiegel change
      const c = data[city];
      if (c && c.history && c.history.length >= 2) {
        const last = c.history[c.history.length - 1];
        const prev = c.history[c.history.length - 2];
        const pctChange = ((last.base_rent_mittel_60_90 - prev.base_rent_mittel_60_90) / prev.base_rent_mittel_60_90 * 100).toFixed(1);
        setTimeout(() => {
          if (statusEl) {
            statusEl.className = 'status-message status-info';
            statusEl.innerHTML = `ℹ️ <strong>Simulation:</strong> Bei der letzten Änderung (${last.year}) stieg der Mietspiegel in ${c.city} um <strong>${pctChange}%</strong>. Bei Überschreitung deiner ${changePct > 0 ? `${changePct}%-Schwelle` : 'konfigurierten'} Schwelle würdest du benachrichtigt werden.`;
          }
        }, 1500);
      }
    });

    renderSubs();
    window._renderAlerts = renderSubs;
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  // ---- Init ----
  async function init() {
    initTabs();
    initMap();

    const data = await loadAllCities();
    if (!data || Object.keys(data).length === 0) return;

    renderCityList(data);
    addCityMarkers(data);

    // Show first city as default detail
    const firstCity = Object.keys(data)[0];
    window.showCityDetail(firstCity);

    // Premium features
    initExport(data);
    initTrends(data);
    initAlerts(data);

    // If there's historical data, auto-render the trend chart on tab switch
    document.querySelector('[data-tab="trends-panel"]')?.addEventListener('click', () => {
      setTimeout(() => {
        if (window._renderTrends) window._renderTrends();
        if (window._renderAlerts) window._renderAlerts();
      }, 100);
    });
    document.querySelector('[data-tab="alerts-panel"]')?.addEventListener('click', () => {
      setTimeout(() => {
        if (window._renderAlerts) window._renderAlerts();
      }, 100);
    });

    // Fit map bounds
    if (map && Object.keys(data).length > 1) {
      const group = L.featureGroup(Object.values(data).map(c =>
        L.circleMarker([c.lat, c.lng])
      ));
      map.fitBounds(group.getBounds().pad(0.1));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
