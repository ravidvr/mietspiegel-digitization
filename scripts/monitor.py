#!/usr/bin/env python3
"""
Mietspiegel Update Monitor
==========================
Checks official city websites for new Mietspiegel editions.
Compares found editions against known versions, logs changes,
and maintains per-city version history.

Usage:
  python3 scripts/monitor.py                          # run full check
  python3 scripts/monitor.py --city berlin            # single city
  python3 scripts/monitor.py --status                 # print status only
  python3 scripts/monitor.py --export-json            # export status as JSON

Output:
  - data/versions/<city>.json        — per-city version history
  - data/monitoring/status.json      — aggregate status (last check, new editions)
  - stdout                           — human-readable report
"""

import json
import os
import re
import sys
from datetime import UTC, datetime
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Run: pip install requests")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CITIES_PATH = os.path.join(REPO_ROOT, "data", "monitoring", "cities.json")
VERSIONS_DIR = os.path.join(REPO_ROOT, "data", "versions")
STATUS_PATH = os.path.join(REPO_ROOT, "data", "monitoring", "status.json")
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ── HTTP config ────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "MietspiegelDigitization/1.0 (update-monitor; +https://github.com/ravidvr/mietspiegel-digitization)",
    "Accept": "text/html,application/pdf,*/*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
})
CHECK_TIMEOUT = 30  # seconds per city


def load_cities():
    """Load the city registry."""
    with open(CITIES_PATH, encoding="utf-8") as f:
        return json.load(f)["cities"]


def save_cities(cities):
    """Persist updated known_editions back to the registry."""
    payload = {"_meta": {}, "cities": cities}
    with open(CITIES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_version_history(slug):
    """Load per-city version history JSON, or return empty."""
    path = os.path.join(VERSIONS_DIR, f"{slug}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"city": slug, "versions": [], "first_seen": None, "last_check": None}


def save_version_history(slug, history):
    """Persist per-city version history."""
    path = os.path.join(VERSIONS_DIR, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
        f.write("\n")


def extract_year(text):
    """Extract the most likely edition year from text/filename."""
    # Look for 4-digit years (e.g. "Mietspiegel 2024")
    years = set()
    for m in re.finditer(r'\b(19[89]\d|20[0-2]\d|2030)\b', text):
        years.add(int(m.group()))
    return years


def extract_pdf_links(html, base_url):
    """Extract PDF links from HTML, returning relative→absolute URLs."""
    pdfs = []
    # href="...pdf"
    for m in re.finditer(r'href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE):
        url = urljoin(base_url, m.group(1))
        pdfs.append(url)
    return pdfs


def extract_edition_info(url, text):
    """Try to determine the edition year from a PDF URL or surrounding text."""
    # Pattern: mietspiegel2024.pdf, Mietspiegel_2024.pdf, 2024_mietspiegel.pdf
    year_match = re.search(r'(?:mietspiegel|msp)[_-]?(\d{4})', url, re.IGNORECASE)
    if year_match:
        return int(year_match.group(1))
    year_match = re.search(r'(\d{4})[_-]?(?:mietspiegel|msp)', url, re.IGNORECASE)
    if year_match:
        return int(year_match.group(1))
    return None


def check_city_page(city):
    """
    Fetch a city's Mietspiegel page and return detected edition information.
    Returns dict with: editions_found, pdf_urls, page_reachable, error, year_hints
    """
    result = {
        "slug": city["slug"],
        "name": city["name"],
        "url": city["page_url"],
        "page_reachable": False,
        "status_code": None,
        "editions_found": [],
        "pdf_urls": [],
        "year_hints": set(),
        "error": None,
    }

    try:
        resp = SESSION.get(city["page_url"], timeout=CHECK_TIMEOUT, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["page_reachable"] = 200 <= resp.status_code < 400

        if not result["page_reachable"]:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        html = resp.text

        # 1. Extract year hints from page content
        result["year_hints"] = extract_year(html)

        # 2. Find PDF links
        pdfs = extract_pdf_links(html, resp.url)
        result["pdf_urls"] = pdfs

        # 3. Try to determine edition years from PDF URLs
        for pdf_url in pdfs:
            edition_year = extract_edition_info(pdf_url, html)
            if edition_year:
                result["editions_found"].append({
                    "year": edition_year,
                    "url": pdf_url,
                    "source": "pdf_url"
                })

        # 4. Extract edition years from heading/text patterns
        # Patterns like "Mietspiegel 2024/2026", "Mietspiegel 2024"
        for year in result["year_hints"]:
            # Check if any text around the year suggests it's the edition year
            patterns = [
                rf'Mietspiegel\s+{year}',
                rf'Mietspiegel\s+{year}/{year+2}',
                rf'{year}\s*er\s+Mietspiegel',
            ]
            for pat in patterns:
                if re.search(pat, html, re.IGNORECASE):
                    # Only add if we don't already have it from PDF
                    if not any(e["year"] == year for e in result["editions_found"]):
                        result["editions_found"].append({
                            "year": year,
                            "source": "page_text",
                            "context": pat,
                        })
                    break

        # Deduplicate
        seen_years = set()
        unique = []
        for e in result["editions_found"]:
            if e["year"] not in seen_years:
                seen_years.add(e["year"])
                unique.append(e)
        result["editions_found"] = unique

    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "connection_error"
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)[:200]
    except Exception as e:
        result["error"] = f"unexpected: {e}"

    return result


def is_new(edition_year, known_editions, history):
    """Check if an edition year is genuinely new (not in known_editions or history)."""
    if edition_year in known_editions:
        return False
    for v in history.get("versions", []):
        if v.get("year") == edition_year:
            return False
    return True


def run_check(cities=None):
    """Run the full monitoring check across all (or specified) cities."""
    all_cities = load_cities()

    if cities:
        slugs = [c.lower() for c in cities]
        to_check = [c for c in all_cities if c["slug"].lower() in slugs]
        if not to_check:
            print(f"ERROR: No cities found matching: {cities}")
            sys.exit(1)
    else:
        to_check = all_cities

    results = []
    new_editions = []
    errors = []

    print(f"Mietspiegel Update Monitor — {datetime.now(UTC).isoformat()}")
    print(f"Cities to check: {len(to_check)}")
    print("=" * 60)

    for city in to_check:
        slug = city["slug"]
        name = city["name"]
        known = city.get("known_editions", [])
        history = load_version_history(slug)

        print(f"\n  [{slug}] {name}")
        print(f"  └─ URL:           {city['page_url']}")
        print(f"  └─ Known editions: {known or '(none)'}")

        check_result = check_city_page(city)

        if not check_result["page_reachable"]:
            print(f"  └─ ⚠  UNREACHABLE: {check_result['error']}")
            errors.append({"slug": slug, "name": name, "error": check_result["error"]})
            results.append(check_result)
            continue

        print(f"  └─ HTTP:          {check_result['status_code']}")
        print(f"  └─ Year hints:    {sorted(check_result['year_hints']) or '(none)'}")
        print(f"  └─ PDF links:     {len(check_result['pdf_urls'])}")
        for pdf in check_result["pdf_urls"][:3]:
            print(f"      └─ {pdf}")
        if len(check_result["pdf_urls"]) > 3:
            print(f"      └─ ... and {len(check_result['pdf_urls'])-3} more")

        editions = check_result["editions_found"]
        if editions:
            years_found = sorted(set(e["year"] for e in editions))
            print(f"  └─ Editions found: {years_found}")

            # Check for new editions
            new_years = []
            for e in editions:
                if is_new(e["year"], known, history):
                    new_years.append(e["year"])
                    new_editions.append({
                        "city_slug": slug,
                        "city_name": name,
                        "year": e["year"],
                        "source": e.get("source", "detected"),
                        "url": e.get("url", city["page_url"]),
                        "detected_at": datetime.now(UTC).isoformat(),
                    })
                    print(f"  └─ 🆕 NEW EDITION: {e['year']}")

                    # Add to version history
                    history.setdefault("versions", []).append({
                        "year": e["year"],
                        "detected_at": datetime.now(UTC).isoformat(),
                        "source": e.get("url", city["page_url"]),
                        "type": "detected_from_web",
                    })

            if not new_years:
                print("  └─ ✓ All editions already known")
        else:
            print("  └─ No editions detected on page")

        # Update timestamps
        history["city"] = slug
        history["city_name"] = name
        history["last_check"] = datetime.now(UTC).isoformat()
        if history.get("first_seen") is None:
            history["first_seen"] = history["last_check"]
        save_version_history(slug, history)

        results.append(check_result)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Checked:  {len(to_check)} cities")
    print(f"  Reachable: {sum(1 for r in results if r['page_reachable'])}")
    print(f"  Errors:   {len(errors)}")
    if new_editions:
        print(f"\n  🆕 NEW EDITIONS FOUND: {len(new_editions)}")
        for ne in new_editions:
            print(f"    └─ {ne['city_name']} — edition {ne['year']}")
    else:
        print("\n  ✓ No new editions found (all up to date)")

    if errors:
        print("\n  ⚠  ERRORS:")
        for e in errors:
            print(f"    └─ {e['name']}: {e['error']}")

    # ── Save aggregate status ────────────────────────────────────────────
    status = {
        "last_run": datetime.now(UTC).isoformat(),
        "cities_checked": len(to_check),
        "errors": errors,
        "new_editions": new_editions,
        "city_summary": [],
    }
    for r in results:
        status["city_summary"].append({
            "slug": r["slug"],
            "name": r["name"],
            "reachable": r["page_reachable"],
            "status_code": r["status_code"],
            "editions_found": [e["year"] for e in r.get("editions_found", [])],
            "error": r.get("error"),
        })
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("\n  ✓ Status saved to: data/monitoring/status.json")

    return status


def print_status():
    """Print the current monitoring status without re-checking cities."""
    if not os.path.exists(STATUS_PATH):
        print("No status available yet. Run the monitor first.")
        return

    with open(STATUS_PATH, encoding="utf-8") as f:
        status = json.load(f)

    print("Mietspiegel Monitoring Status")
    print(f"Last run: {status.get('last_run', 'never')}")
    print("=" * 60)

    for cs in status.get("city_summary", []):
        icon = "✓" if cs["reachable"] else "⚠"
        editions = ", ".join(str(y) for y in cs.get("editions_found", [])) or "?"
        error = f" — {cs['error']}" if cs.get("error") else ""
        print(f"  {icon} {cs['name']:20s} | {editions:15s} | {cs['status_code']}{error}")

    new_eds = status.get("new_editions", [])
    if new_eds:
        print(f"\n🆕 NEW EDITIONS: {len(new_eds)}")
        for ne in new_eds:
            print(f"  └─ {ne['city_name']} — edition {ne['year']}")
    else:
        print("\n✓ No pending new editions.")


def export_json():
    """Export full status as JSON to stdout (for cron/scripting)."""
    if not os.path.exists(STATUS_PATH):
        print(json.dumps({"error": "no_status_yet", "run": "python3 scripts/monitor.py first"}))
        return
    with open(STATUS_PATH) as f:
        print(f.read().strip())


# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mietspiegel Update Monitor")
    parser.add_argument("--city", "-c", action="append", help="Check only specific city slug(s)")
    parser.add_argument("--status", "-s", action="store_true", help="Print status dashboard")
    parser.add_argument("--export-json", "-j", action="store_true", help="Export status as JSON")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.export_json:
        export_json()
    else:
        run_check(cities=args.city)
