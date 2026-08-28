#!/usr/bin/env python3
"""Audit: are the committed city-table values traceable to the raw PDFs?

For every city JSON with rent tables, extract the text of the matching raw
PDF(s) and check whether each numeric table value appears anywhere in the
document (German comma-decimal format). High hit rate = value traceable.
Near-zero = the committed table cannot be reproduced from the source
document (same failure mode Berlin had).

Also checks whether the city's baujahr_groups appear in the PDF.

Usage: python3 scripts/audit_city_sources.py
"""
import json
import re
from pathlib import Path

import pdfplumber

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "docs/data/processed"
RAW = REPO / "data/raw"

# slug -> candidate PDF name fragments (order of preference)
PDF_MAP = {
    "aachen": None,  # formula-based; PDF not in repo? check
    "augsburg": ["augsburg"],
    "bonn": ["bonn"],
    "braunschweig": None,
    "bremen": None,
    "chemnitz": None,
    "dresden": ["dresden"],
    "duesseldorf": ["duesseldorf"],
    "essen": None,
    "frankfurt": ["frankfurt"],
    "freiburg": None,
    "halle": None,
    "hamburg": ["hamburg-mietenspiegel-tabelle", "hamburg-mietspiegel-table",
                "hamburg-mietspiegel-broschuere"],
    "hannover": ["hannover"],
    "kiel": ["kiel"],
    "koeln": None,
    "leipzig": None,
    "luebeck": ["luebeck"],
    "mainz": ["mainz"],
    "muenchen": None,
    "nuernberg": None,
    "rostock": None,
    "stuttgart": None,
}

SKIP_KEYS = {"baujahr", "lage", "city", "city_slug", "slug", "state",
             "population", "year", "type", "lat", "lng", "notes", "source",
             "source_url"}


def pdf_texts(slug):
    import fitz  # PyMuPDF — much faster than pdfplumber
    frags = PDF_MAP.get(slug) or [slug]
    found = []
    for p in RAW.iterdir():
        if not p.suffix.lower() == ".pdf":
            continue
        for f in frags:
            if f.lower() in p.name.lower():
                found.append(p)
                break
    texts = []
    for p in sorted(set(found)):
        try:
            doc = fitz.open(p)
            texts.append("\n".join(pg.get_text() for pg in doc))
            doc.close()
        except Exception:
            texts.append("")
    return texts


def main():
    rows_out = []
    for f in sorted(PROC.glob("*.json")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(j, dict) or ("tables" not in j and "official_rows" not in j):
            continue
        slug = j.get("slug") or j.get("city_slug") or f.stem
        if slug == "berlin":
            continue
        tables = j.get("tables", [])
        values = []
        cohorts = set()
        for t in tables:
            for r in t.get("rows", []):
                for k, v in r.items():
                    if k in SKIP_KEYS or k == "baujahr":
                        continue
                    if isinstance(v, (int, float)):
                        values.append(v)
                if isinstance(r.get("baujahr"), str):
                    cohorts.add(r["baujahr"])
        if not values:
            rows_out.append((slug, 0, 0, "no tables", sorted(cohorts)))
            continue
        texts = pdf_texts(slug)
        if not texts:
            rows_out.append((slug, len(values), None, "NO PDF in data/raw/", sorted(cohorts)))
            continue
        hay = "\n".join(texts)
        hits = 0
        misses = []
        for v in values:
            s = f"{v:.2f}".replace(".", ",").rstrip("0").rstrip(",")
            if re.search(rf"(?<!\d){re.escape(s)}(?!\d)", hay):
                hits += 1
            else:
                misses.append(v)
        cohort_hits = sum(1 for c in cohorts if re.search(re.escape(c), hay))
        rows_out.append((slug, len(values), round(hits / len(values) * 100),
                         f"cohorts {cohort_hits}/{len(cohorts)}", sorted(cohorts)))

    print(f"{'city':16s} {'cells':>6s} {'hit%':>6s}  cohorts  {'status'}")
    for slug, n, hit, ch, _ in rows_out:
        status = ("OK" if hit is not None and hit >= 80 else
                  "LOW" if hit is not None else "NO-PDF")
        print(f"{slug:16s} {n:6d} {str(hit)+'%' if hit is not None else '  —':>6s}  {ch:14s} {status}")


if __name__ == "__main__":
    main()
