#!/usr/bin/env python3
"""Verify that a raw extraction JSON matches the source PDF exactly.

Re-runs the extraction pipeline against the PDF and diffs every row/field
against the committed JSON. Catches: PDF edits, extraction-parameter drift,
accidental tampering, stale files.

Usage:
    python3 scripts/verify_berlin_extraction.py \
        data/raw/berlin-mietspiegeltabelle-2024.pdf \
        data/processed/berlin_raw_2024.json

Exit 0 = identical. Exit 1 = any mismatch.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sources"))
import extract_mietspiegel  # noqa: E402


def extract_rows(pdf_path: Path) -> list[dict]:
    rows = extract_mietspiegel.extract_with_pdfplumber_detailed(str(pdf_path))
    if isinstance(rows, dict):
        rows = rows.get("data") or []
    if isinstance(rows, dict):
        rows = [r for v in rows.values() if isinstance(v, list) for r in v]
    return rows


def norm(r: dict) -> tuple:
    return (
        str(r.get("row")),
        str(r.get("baujahr") or ""),
        str(r.get("size_range") or ""),
        str(r.get("_lage") or r.get("lage") or ""),
        round(float(r.get("untere_spanne") or 0), 2),
        round(float(r.get("mittelwert") or 0), 2),
        round(float(r.get("obere_spanne") or 0), 2),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("json_path")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    jp = Path(args.json_path)
    if not pdf.exists():
        print(f"FAIL: PDF not found: {pdf}")
        sys.exit(1)
    if not jp.exists():
        print(f"FAIL: JSON not found: {jp}")
        sys.exit(1)

    committed = json.loads(jp.read_text())
    committed_rows = committed.get("data") or committed.get("rows") or []
    live = extract_rows(pdf)

    print(f"PDF rows re-extracted: {len(live)} | committed: {len(committed_rows)}")
    if len(live) != len(committed_rows):
        print(f"FAIL: row count drift ({len(live)} != {len(committed_rows)})")
        sys.exit(1)

    errors = 0
    for a, b in zip(committed_rows, live):
        if norm(a) != norm(b):
            errors += 1
            if errors <= 10:
                print(f"  MISMATCH row {a.get('row')}: committed {norm(a)} != pdf {norm(b)}")
    if errors:
        print(f"FAIL: {errors} mismatched rows")
        sys.exit(1)
    print("PASS: extraction identical to source PDF — 0 diffs")
    sys.exit(0)


if __name__ == "__main__":
    main()
