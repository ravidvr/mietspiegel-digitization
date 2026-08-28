#!/usr/bin/env python3
"""Extract the Augsburg Mietspiegel 2025 Tabelle 1 from the official PDF.

Source: data/raw/augsburg.pdf (Mietspiegel 2025, Wohnen in Augsburg).

Tabelle 1 (page 4): Basis-Nettomiete (€/m²) by Wohnfläche (16 bands,
20-<25 ... 140-<=150 m²) x Baujahr (12 cohorts). Tabelle 2: Zu-/Abschläge
in Punktwerten (Lageklasse 1-7: +11/+7/+4/0/-4/-7/-11; plus Ausstattungs-
merkmale). Tabelle 3: ortsübliche Vergleichsmiete = A + A x B/100.

The committed JSON's old table (48 cells with lage categories) did not match
this document; replaced with the official 192-cell structure.

Usage: python3 scripts/extract_augsburg.py
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

COHORTS = ["bis 1918", "1919-1948", "1949-1960", "1961-1969", "1970-1979",
           "1980-1989", "1990-1995", "1996-2001", "2002-2007", "2008-2013",
           "2014-2019", "2020-2025"]

SIZE_BANDS = [
    ("20-<25", 20, 25), ("25-<30", 25, 30), ("30-<35", 30, 35),
    ("35-<40", 35, 40), ("40-<45", 40, 45), ("45-<50", 45, 50),
    ("50-<60", 50, 60), ("60-<70", 60, 70), ("70-<80", 70, 80),
    ("80-<90", 80, 90), ("90-<100", 90, 100), ("100-<110", 100, 110),
    ("110-<120", 110, 120), ("120-<130", 120, 130), ("130-<140", 130, 140),
    ("140-<=150", 140, 151),
]

LAGE_KLASSEN = [{"klasse": 1, "punktwert": 11}, {"klasse": 2, "punktwert": 7},
                {"klasse": 3, "punktwert": 4}, {"klasse": 4, "punktwert": 0},
                {"klasse": 5, "punktwert": -4}, {"klasse": 6, "punktwert": -7},
                {"klasse": 7, "punktwert": -11}]


def parse_de(s):
    return float(s.replace(",", "."))


def main():
    import fitz
    doc = fitz.open(REPO / "data/raw/augsburg.pdf")
    text = doc[3].get_text().replace("\n", " ")
    doc.close()

    # rows: size band label followed by 12 values
    rows = []
    pos = 0
    for label, lo, hi in SIZE_BANDS:
        m = re.search(re.escape(label), text[pos:])
        if not m:
            raise SystemExit(f"size band {label} not found")
        start = pos + m.end()
        seg = text[start:start + 260]
        vals = []
        for tok in re.findall(r"[\d,]+", seg):
            vals.append(parse_de(tok))
            if len(vals) == 12:
                break
        if len(vals) != 12:
            raise SystemExit(f"band {label}: expected 12 values, got {len(vals)}")
        rows.append({"size_range": label, "size_min_m2": lo, "size_max_m2": hi,
                     "values": [{"mittelwert": round(v, 2)} for v in vals]})
        pos = start

    official_rows = rows

    # legacy 4-band rollup (mean of Mittelwerte per legacy bucket, per cohort)
    buckets = {"bis_40": (0, 40), "40_60": (40, 60), "60_90": (60, 90),
               "ueber_90": (90, None)}
    legacy_rows = []
    for ci, cohort in enumerate(COHORTS):
        row = {"baujahr": cohort}
        for key, (lo, hi) in buckets.items():
            vals = [r["values"][ci]["mittelwert"] for r in official_rows
                    if (r["size_min_m2"] >= lo) and (hi is None or r["size_min_m2"] < hi)]
            row[key] = round(sum(vals) / len(vals), 2) if vals else None
        legacy_rows.append(row)

    out = {
        "city": "Augsburg",
        "city_slug": "augsburg",
        "slug": "augsburg",
        "state": "Bayern",
        "lat": 48.3705,
        "lng": 10.8978,
        "population": 300000,
        "year": 2025,
        "type": "qualifiziert",
        "source": ("Mietspiegel 2025, Wohnen in Augsburg. Tabelle 1: "
                   "Basis-Nettomiete (mittlere Wohnlage, mittlerer Standard) "
                   "nach Wohnfläche x Baujahr. Wohnlage/Standard via Tabelle 2 "
                   "Punktwerte (Lageklasse 1-7: +11/+7/+4/0/-4/-7/-11), "
                   "Berechnung: A + A x B/100 (Tabelle 3)."),
        "source_url": "https://www.augsburg.de/mietspiegel",
        "source_file": "data/raw/augsburg.pdf",
        "schema_note": ("official_rows preserves Tabelle 1 verbatim (16 size "
                        "bands x 12 cohorts). tables is a derived 4-band rollup "
                        "(mean per legacy bucket, mittlere Lage basis)."),
        "lage_klassen": LAGE_KLASSEN,
        "official_rows": official_rows,
        "tables": [{"lage": "mittel", "rows": legacy_rows}],
        "verification_status": "verified",
        "verification_note": ("Extracted from augsburg.pdf page 4 with "
                              "scripts/extract_augsburg.py; all 192 Mittelwerte "
                              "re-checked against the PDF text layer."),
    }

    # self-check: every value string appears in the PDF text
    hay = text
    ok, total = 0, 0
    for r in official_rows:
        for v in r["values"]:
            total += 1
            s = f"{v['mittelwert']:.2f}".replace(".", ",")
            s_trim = s.rstrip("0").rstrip(",")
            if (re.search(rf"(?<!\d){re.escape(s)}(?!\d)", hay)
                    or re.search(rf"(?<!\d){re.escape(s_trim)}(?!\d)", hay)):
                ok += 1
    print(f"self-check: {ok}/{total} Mittelwerte found in PDF text")
    assert ok == total, "self-check failed"

    out_path = REPO / "docs/data/processed/augsburg.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    (REPO / "data/processed/augsburg.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
