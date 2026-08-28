#!/usr/bin/env python3
"""Stamp verification_status on every city JSON (audit outcome, 2026-08-27).

Statuses:
- verified: table reproduces the official source document (Berlin — PDF-diff
  gated; Mainz — values trace to mainz-2025.pdf).
- partial: some values trace but cohorts/structure don't (kept distinct).
- unverified: a raw PDF exists in data/raw/ but the committed table's values
  and/or cohorts do not reproduce from it.
- no_source_document: no PDF in the repo for this city — table cannot be
  traced at all.
- empty_stub: metadata-only file, no table.

Every derived file keeps working; this is additive metadata that makes the
state of verification explicit instead of implied by the "23 cities" claim.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "docs/data/processed"

PDF_BY_SLUG = {
    "augsburg": "augsburg.pdf", "bonn": "bonn.pdf", "dresden": "dresden-2025.pdf",
    "duesseldorf": "duesseldorf-mietspiegel-2024.pdf",
    "frankfurt": "frankfurt_mietspiegel_2026.pdf",
    "hamburg": "hamburg-mietenspiegel-tabelle-2025.pdf",
    "hannover": "hannover-mietspiegel-2025.pdf", "kiel": "kiel.pdf",
    "luebeck": "luebeck-2025.pdf", "mainz": "mainz-2025.pdf",
    "rostock": "rostock-2026.pdf",
    "stuttgart": "stuttgart-mietspiegel-2025-2026.pdf",
}

STATUS = {
    "berlin": ("verified", "Extracted 163/163 rows from the official 2024 PDF; PDF-diff gated (scripts/verify_berlin_extraction.py)."),
    "hamburg": ("verified", "Extracted from the official 2025 table PDF (scripts/extract_hamburg.py); 88/88 cells match the PDF text layer."),
    "dresden": ("verified", "Formula-based Mietspiegel: scripts/extract_dresden.py embeds the PDF's Tabelle 1 base rents and Tabelle 2/3 factors and reproduces the PDF's worked example (1,00x1,03x1,039x1,009x1,028x0,999x0,989 = 1,097). Committed table values regenerate from the script."),
    "augsburg": ("verified", "Tabelle 1 extracted from augsburg.pdf (16 size bands x 12 cohorts, 192 Mittelwerte all match the PDF text); Lageklassen 1-7 factors embedded."),
    "luebeck": ("verified", "Mietspiegeltabelle extracted from luebeck-2025.pdf p8 (10 cohorts x 4 bands, 40/40 cells match the PDF text); Lage adjustments +0,44/-0,47 €/m² embedded."),
    "mainz": ("partial", "Values trace to mainz-2025.pdf (~90%) but the committed Baujahr groups do not match the PDF's cohorts."),
}

AUDIT = "scripts/audit_city_sources.py"


def main():
    touched = 0
    for f in sorted(PROC.glob("*.json")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(j, dict) or ("tables" not in j and "official_rows" not in j):
            continue
        slug = j.get("slug") or j.get("city_slug") or f.stem
        nrows = sum(len(t["rows"]) for t in j.get("tables", []))
        orows = j.get("official_rows", [])
        if orows and isinstance(orows[0], dict) and "rows" in orows[0]:
            nrows += sum(len(t["rows"]) for t in orows)
        else:
            nrows += len(orows)
        if nrows == 0:
            status, note = "empty_stub", "Metadata-only file; no rent table published."
        elif slug in STATUS:
            status, note = STATUS[slug]
        elif slug in PDF_BY_SLUG:
            status = "unverified"
            note = (f"Raw PDF {PDF_BY_SLUG[slug]} exists in data/raw/ but the "
                    f"committed table does not reproduce from it ({AUDIT}). "
                    f"Pending re-extraction.")
        else:
            status = "no_source_document"
            note = ("No source PDF in the repository; the committed table "
                    "cannot be traced to a document. Pending re-extraction.")
        j["verification_status"] = status
        j["verification_note"] = note
        f.write_text(json.dumps(j, ensure_ascii=False, indent=2))
        touched += 1
    print(f"stamped {touched} city files")


if __name__ == "__main__":
    main()
