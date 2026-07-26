// Mietspiegel Berlin — i18n translations + language toggle (ES module)
import { clickCell, cardDistrict } from './state.js';

export const I18N = {
  en: {
    dash:'Mietspiegel', subtitle:'Berlin rent index — block by block',
    dark:'Dark', about:'About',
    all_rents:'All Rents', all_districts:'All Districts',
    loading:'Loading data...', no_data:'Data pending.',
    no_match:'No matching districts',
    welcome_desc:'Berlin rent data — block by block. Market rents (Immoscout24, €12.07/m²), official census rents (2022, €7.97/m²), and the official Mietspiegel. Click anywhere on the map for local rent details.',
    welcome_tip:'Heatmap shows market rents (Immoscout24). District labels show estimated average rent. Click anywhere for details.',
    got_it:'Got it! →', source_data:'Source Data',
    census_rent_lbl:'Official census rent (2022)',
    market_rent_lbl:'Market rent for new listings (Immoscout24)',
    above:'above', below:'below',
    what_people_pay:'What people actually pay',
    official_census:'Official census (2022)',
    more:'more', less:'less',
    listings_cost:'New listings cost',
    than_tenants:'than what current tenants pay',
    off_mietspiegel:'Official Mietspiegel',
    legal_ref:'Legal reference rent:',
    above_off_idx:'above official index',
    below_off_idx:'below official index',
    market_listings_are:'Market listings are',
    est_avg_cold:'Estimated average net cold rent',
    addresses:'addresses',
    ms_title:'Berlin Mietspiegel {year} — Mittlere Wohnlage',
    net_cold:'Net cold rent (€/m²/month)',
    src:'Source', btwn:'between',
  },
  de: {
    dash:'Mietspiegel', subtitle:'Berliner Mietdaten — Block für Block',
    dark:'Dunkel', about:'Über',
    all_rents:'Alle Mieten', all_districts:'Alle Bezirke',
    loading:'Lade Daten...', no_data:'Daten ausstehend.',
    no_match:'Keine passenden Bezirke',
    welcome_desc:'Berliner Mietdaten — Block für Block. Marktmieten (Immoscout24, €12.07/m²), offizielle Zensus-Mieten (2022, €7.97/m²) und der offizielle Mietspiegel. Klicke auf die Karte für lokale Mietdetails.',
    welcome_tip:'Heatmap zeigt Marktmieten (Immoscout24). Bezirks-Labels zeigen geschätzte Durchschnittsmiete. Klicke für Details.',
    got_it:'Verstanden! →', source_data:'Datenquellen',
    census_rent_lbl:'Offizielle Zensus-Miete (2022)',
    market_rent_lbl:'Marktmiete für Neuvermietungen (Immoscout24)',
    above:'über', below:'unter',
    what_people_pay:'Was Mieter tatsächlich zahlen',
    official_census:'Offizieller Zensus (2022)',
    more:'mehr', less:'weniger',
    listings_cost:'Neuvermietungen kosten',
    than_tenants:'als Bestandsmieter zahlen',
    off_mietspiegel:'Offizieller Mietspiegel',
    legal_ref:'Gesetzliche Vergleichsmiete:',
    above_off_idx:'über dem offiziellen Mietspiegel',
    below_off_idx:'unter dem offiziellen Mietspiegel',
    market_listings_are:'Marktangebote liegen',
    est_avg_cold:'Geschätzte durchschnittliche Nettokaltmiete',
    addresses:'Adressen',
    ms_title:'Berliner Mietspiegel {year} — Mittlere Wohnlage',
    net_cold:'Nettokaltmiete (€/m²/Monat)',
    src:'Quelle', btwn:'zwischen',
  }
};

export let lang = localStorage.getItem('lang') || 'en';

export function t(key) { return I18N[lang][key] || key; }

export function applyLang() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (el.tagName === 'OPTION') el.textContent = t(key);
    else el.innerHTML = t(key);
  });
  document.getElementById('lang-btn').textContent = lang === 'en' ? 'DE' : 'EN';
}

export async function toggleLang() {
  lang = lang === 'en' ? 'de' : 'en';
  localStorage.setItem('lang', lang);
  applyLang();
  const tt = document.getElementById('map-tooltip');
  if (tt && tt.style.display === 'block') {
    if (clickCell) {
      const { renderClickTooltip } = await import('./map.js');
      renderClickTooltip();
    } else if (cardDistrict) {
      const { renderDistrictCard } = await import('./district.js');
      renderDistrictCard();
    }
  }
}
