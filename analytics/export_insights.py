#!/usr/bin/env python3
"""Export analytical insights from local JSON data to docs/data/insights_*.json

Emulates the BigQuery SQL queries using the existing processed JSON files.
This keeps the analytics layer connected to the dashboard without requiring
a live BigQuery instance.

Usage: python3 analytics/export_insights.py

Outputs:
  docs/data/insights_city_rankings.json   — all 23 cities ranked by avg rent
  docs/data/insights_gut_spread.json      — gut/einfach rent ratio per city
  docs/data/insights_district_premium.json — Immoscout vs Mietspiegel gap per Bezirk
  docs/data/insights_berlin_table.json    — Berlin Mietspiegel table (mittel, 40-60m²)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'processed'
DOCS_DATA = ROOT / 'docs' / 'data' / 'processed'

SIZE_KEYS = ['bis_40', '40_60', '60_90', 'ueber_90']
SKIP = {'cities_index', 'cities_comparison', 'berlin-districts-geo', 'redx_grid_rent',
        'redx_district_rent', 'hamburg_streets', 'kiel_streets', 'saarbruecken_streets',
        'berlin_immoscout', 'berlin_zensus', 'berlin_districts_index',
        'berlin_districts_comparison', 'berlin-districts-choropleth', 'berlin_historical',
        'zensus2022_rent_1km', 'brw_2025_zones', 'brw_2025_slim', 'stadtgebiet_distribution_weights',
        'stadtgebiet_bezirk_mapping', 'marktbericht_bezirke_2024', 'marktbericht_dashboard_data',
        'marktbericht_complete_2024', 'marktbericht_combined', 'marktbericht_timeseries',
        'baufertigstellungen_2024', 'baugenehmigungen_2024', 'wohnungsbestand_2024'}


def load_cities():
    cities = {}
    for f in sorted(DATA.glob('*.json')):
        name = f.stem
        if name in SKIP:
            continue
        with open(f) as fh:
            d = json.load(fh)
        if 'tables' in d and d.get('city'):
            cities[name] = d
    return cities


def city_avg_rent(city_data, lage=None, size_key='40_60'):
    """Compute average rent for a city, optionally filtered by lage and size."""
    vals = []
    for t in city_data.get('tables', []):
        if lage and t.get('lage', '').lower() != lage.lower():
            continue
        for row in t.get('rows', []):
            if size_key in row and isinstance(row[size_key], (int, float)) and row[size_key] > 0:
                vals.append(float(row[size_key]))
    return round(sum(vals) / len(vals), 2) if vals else None


def build_city_rankings(cities):
    """Query: city rent rankings by avg rent (mittel, 40-60m²)"""
    rankings = []
    for slug, data in cities.items():
        avg = city_avg_rent(data, lage='mittel')
        if avg:
            rankings.append({
                'city': data['city'],
                'slug': slug,
                'state': data.get('state', ''),
                'avg_rent': avg,
                'population': data.get('population', 0),
                'year': data.get('year', ''),
            })
    rankings.sort(key=lambda x: x['avg_rent'], reverse=True)
    return rankings


def build_gut_spread(cities):
    """Query: gut/einfach spread ratio per city (rent inequality)"""
    spreads = []
    for slug, data in cities.items():
        gut = city_avg_rent(data, lage='gut')
        einf = city_avg_rent(data, lage='einfach')
        if gut and einf and einf > 0:
            spreads.append({
                'city': data['city'],
                'slug': slug,
                'gut_rent': gut,
                'einfach_rent': einf,
                'spread_ratio': round(gut / einf, 2),
                'spread_eur': round(gut - einf, 2),
            })
    spreads.sort(key=lambda x: x['spread_ratio'], reverse=True)
    return spreads


def build_district_premium():
    """Query: Immoscout market rent vs Mietspiegel official rent per Bezirk"""
    # Load districts comparison (has Immoscout avg_rent)
    comp_path = DOCS_DATA / 'berlin_districts_comparison.json'
    if not comp_path.exists():
        return []
    
    with open(comp_path) as f:
        comp = json.load(f)
    
    # Load Berlin Mietspiegel for the official reference rent
    berlin_path = DATA / 'berlin.json'
    mietspiegel_avg = None
    if berlin_path.exists():
        with open(berlin_path) as f:
            berlin = json.load(f)
        mietspiegel_avg = city_avg_rent(berlin, lage='mittel')
    
    premiums = []
    for d in comp.get('districts', []):
        premium_pct = None
        if mietspiegel_avg and d.get('avg_rent'):
            premium_pct = round((d['avg_rent'] - mietspiegel_avg) / mietspiegel_avg * 100, 1)
        
        premiums.append({
            'district': d['district'],
            'market_rent': d['avg_rent'],
            'official_rent': mietspiegel_avg,
            'premium_pct': premium_pct,
            'gap_pct': d.get('gap_pct'),
            'einfach_pct': d.get('einfach_pct'),
            'mittel_pct': d.get('mittel_pct'),
            'gut_pct': d.get('gut_pct'),
        })
    return premiums


def build_berlin_table():
    """Query: Berlin Mietspiegel table — mittlere Wohnlage, all Baujahr × size"""
    berlin_path = DATA / 'berlin.json'
    if not berlin_path.exists():
        return None
    
    with open(berlin_path) as f:
        berlin = json.load(f)
    
    table = None
    for t in berlin.get('tables', []):
        if t.get('lage', '').lower() == 'mittel':
            table = t
            break
    if not table and berlin.get('tables'):
        table = berlin['tables'][0]
    if not table:
        return None
    
    return {
        'city': berlin['city'],
        'year': berlin.get('year'),
        'lage': table.get('lage'),
        'baujahr_groups': berlin.get('baujahr_groups', []),
        'size_categories': berlin.get('size_categories', SIZE_KEYS),
        'rows': [{k: v for k, v in row.items() if k in SIZE_KEYS + ['baujahr']}
                  for row in table.get('rows', [])],
    }


def main():
    print('═══ Insights Exporter ═══\n')
    
    cities = load_cities()
    print(f'Loaded {len(cities)} cities')
    
    os.makedirs(DOCS_DATA, exist_ok=True)
    
    # 1. City rankings
    rankings = build_city_rankings(cities)
    with open(DOCS_DATA / 'insights_city_rankings.json', 'w') as f:
        json.dump({'insight': 'city_rankings',
                   'description': f'All cities ranked by average rent (mittel, 40-60m²)',
                   'cities': len(rankings),
                   'data': rankings}, f, indent=2)
    print(f'  ✓ City rankings: {len(rankings)} cities, top={rankings[0]["city"]} €{rankings[0]["avg_rent"]}')
    
    # 2. Gut spread
    spreads = build_gut_spread(cities)
    with open(DOCS_DATA / 'insights_gut_spread.json', 'w') as f:
        json.dump({'insight': 'gut_spread',
                   'description': 'Gut/einfach rent ratio per city (rent inequality)',
                   'cities': len(spreads),
                   'data': spreads}, f, indent=2)
    print(f'  ✓ Gut spread: {len(spreads)} cities')
    
    # 3. District premium
    premiums = build_district_premium()
    with open(DOCS_DATA / 'insights_district_premium.json', 'w') as f:
        json.dump({'insight': 'district_premium',
                   'description': 'Immoscout market rent vs Mietspiegel official rent per Berlin Bezirk',
                   'districts': len(premiums),
                   'data': premiums}, f, indent=2)
    print(f'  ✓ District premium: {len(premiums)} Bezirke')
    
    # 4. Berlin table
    berlin_table = build_berlin_table()
    if berlin_table:
        with open(DOCS_DATA / 'insights_berlin_table.json', 'w') as f:
            json.dump(berlin_table, f, indent=2)
        print(f'  ✓ Berlin table: {len(berlin_table["rows"])} Baujahr rows × {len(berlin_table.get("size_categories",[]))} sizes')
    
    print('\n✓ All insights exported to docs/data/processed/insights_*.json')


if __name__ == '__main__':
    main()
