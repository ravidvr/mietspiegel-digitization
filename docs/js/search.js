// Mietspiegel Berlin — address search + autocomplete (ES module)
import * as S from './state.js';

function escapeHtml(s) {
  const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
}

export function hideSuggestions() {
  document.getElementById('suggestions').classList.remove('open');
  S.suggestResults = [];
  S.suggestIdx = -1;
}

export async function fetchSuggestions(q) {
  if (!q || q.length < 2) { hideSuggestions(); return; }
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(q + ', Berlin, Germany')}&countrycodes=de&accept-language=de`;
    const r = await fetch(url, { headers: { 'User-Agent': 'BerlinMietspiegel/1.0' } });
    S.suggestResults = await r.json();
    S.suggestIdx = -1;
    renderSuggestions();
  } catch(e) { hideSuggestions(); }
}

export function debouncedSuggest() {
  clearTimeout(S.suggestTimer);
  S.suggestTimer = setTimeout(() => fetchSuggestions(document.getElementById('f-search').value.trim()), 250);
}

function renderSuggestions() {
  const el = document.getElementById('suggestions');
  if (!S.suggestResults.length) { el.classList.remove('open'); return; }
  el.innerHTML = S.suggestResults.map((r, i) => {
    const name = r.display_name.split(',')[0];
    const detail = r.display_name.split(',').slice(1, 3).join(',').trim();
    const cls = i === S.suggestIdx ? ' active' : '';
    return `<div class="s-item${cls}" data-idx="${i}" onmousedown="document._selectSuggestion(${i})">
      <span class="s-icon">📍</span>
      <span class="s-text"><span class="s-name">${escapeHtml(name)}</span><br><span class="s-detail">${escapeHtml(detail)}</span></span>
    </div>`;
  }).join('');
  el.classList.add('open');
}

export function handleSearchKey(e) {
  if (e.key === 'Escape') { hideSuggestions(); return true; }
  if (e.key === 'ArrowDown') { e.preventDefault(); S.suggestIdx = Math.min(S.suggestIdx + 1, S.suggestResults.length - 1); renderSuggestions(); return false; }
  if (e.key === 'ArrowUp') { e.preventDefault(); S.suggestIdx = Math.max(S.suggestIdx - 1, -1); renderSuggestions(); return false; }
  if (e.key === 'Enter') { e.preventDefault(); selectSuggestion(S.suggestIdx); return false; }
  return true;
}

export function selectSuggestion(idx) {
  hideSuggestions();
  const q = document.getElementById('f-search').value.trim();
  if (idx >= 0 && S.suggestResults[idx]) {
    flyToResult(S.suggestResults[idx]);
  } else if (q.length >= 2) {
    fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q + ', Berlin, Germany')}&countrycodes=de&accept-language=de`)
      .then(r => r.json())
      .then(results => { if (results.length) flyToResult(results[0]); else document.getElementById('f-search').placeholder = '❌ Not found — try again'; })
      .catch(() => {});
  }
}

export function flyToResult(result) {
  const lat = parseFloat(result.lat), lng = parseFloat(result.lon);
  const input = document.getElementById('f-search');
  S.map.flyTo([lat, lng], 15, { duration: 1.2 });
  const marker = L.circleMarker([lat, lng], { radius: 6, color: '#5b8def', fillColor: '#5b8def', fillOpacity: 0.6, weight: 2 }).addTo(S.map);
  const name = result.display_name.split(',')[0];
  const safeName = document.createElement('div'); safeName.textContent = name;
  marker.bindPopup('<b>' + safeName.innerHTML + '</b>', { closeButton: false }).openPopup();
  setTimeout(() => S.map.removeLayer(marker), 8000);
  S.map.fire('click', { latlng: { lat, lng }, originalEvent: { target: null } });
  input.value = name;
  input.placeholder = '📍 ' + name;
  setTimeout(() => { input.placeholder = '🔍 Search by address, building name, or PLZ...'; }, 4000);
}

// Wire global onclick for suggestion items
document._selectSuggestion = selectSuggestion;
