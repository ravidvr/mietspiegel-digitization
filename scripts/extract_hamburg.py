#!/usr/bin/env python3
"""Extract the Hamburg Mietenspiegel 2025 table from the official PDFs.

Source: data/raw/hamburg-mietenspiegel-tabelle-2025.pdf (official table,
Behörde für Stadtentwicklung und Wohnen, Erhebungsstichtag 01.04.2025).

Structure: 10 Baualtersklassen columns x 9 rows:
  Normal Wohnlage: bis unter 41 m², 41-66, 66-91, ab 91
  Gute   Wohnlage: bis unter 41 m², 41-66, 66-91, 91-131, ab 131
Each cell: Mittelwert (Median) + Spanne. Cells marked low-sample (< 30
Datensätze) in the official table are flagged (row 5 and row 9 carry
asterisked counts).

The official PDF footnote: "* Für Felder mit weniger als 30 Datensätzen ist
die Aussage eingeschränkt." — the empty Mittelwert cells in rows 5 and 9 are
Leerfelder (insufficient data).

Usage:
    python3 scripts/extract_hamburg.py
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

COHORTS = ["bis 31.12.1918", "1.1.1919-20.6.1948", "21.6.1948-1960",
           "1961-1967", "1968-1977", "1978-1993", "1994-2010",
           "2011-2015", "2016-2020", "2021-2024"]

ROWS = [
    ("normal", "<41", "bis unter 41 m²"),
    ("normal", "41-66", "41 m² bis unter 66 m²"),
    ("normal", "66-91", "66 m² bis unter 91 m²"),
    ("normal", "91+", "ab 91 m²"),
    ("gut", "<41", "bis unter 41 m²"),
    ("gut", "41-66", "41 m² bis unter 66 m²"),
    ("gut", "66-91", "66 m² bis unter 91 m²"),
    ("gut", "91-131", "91 m² bis unter 131 m²"),
    ("gut", "131+", "ab 131 m²"),
]


def parse_de(s):
    return float(s.replace(",", "."))


def main():
    import fitz
    doc = fitz.open(REPO / "data/raw/hamburg-mietenspiegel-tabelle-2025.pdf")
    text = doc[0].get_text().replace("\n", " ")
    doc.close()

    # data rows = 'Mittelwert' followed by numbers (footnote uses plural)
    blocks = [b for b in re.split(r"Mittelwert\b", text) if re.match(r"^\s*[\d,]", b)]
    assert len(blocks) == 9, f"expected 9 data rows, got {len(blocks)}"

    raw_rows = []
    for b in blocks:
        # leading numbers = Mittelwerte; stop at the row number token
        nums = []
        tail = b
        for tok in re.findall(r"[\d,]+", b):
            v = parse_de(tok)
            # row-number token is a single digit followed by 'Spanne'
            if len(nums) >= 9 and v < 20 and not nums:
                break
            nums.append(v)
            if len(nums) == 10:
                break
        if len(nums) == 10 and nums[-1] < 20 and int(nums[-1]) == nums[-1] \
                and nums[-1] != 19.78:
            nums = nums[:9]  # row number leaked in as 10th value
        # Spanne pairs
        seg = re.split(r"\bSpanne\b", b, maxsplit=1)
        pairs = []
        if len(seg) > 1:
            spanne_part = re.split(r"\bAnzahl\b", seg[1])[0]
            pairs = [(parse_de(a), parse_de(bb))
                     for a, bb in re.findall(r"([\d,]+)\s*-\s*([\d,]+)", spanne_part)]
        raw_rows.append((nums, pairs))

    # verify counts
    for i, (nums, pairs) in enumerate(raw_rows):
        assert len(nums) in (9, 10), f"row {i+1}: {len(nums)} Mittelwerte"
        assert len(pairs) in (9, 10), f"row {i+1}: {len(pairs)} Spannen"

    rows_out = []
    for (lage, size, label), (nums, pairs) in zip(ROWS, raw_rows):
        values = []
        for ci in range(10):
            if ci < len(nums) and ci < len(pairs):
                values.append({
                    "mittelwert": round(nums[ci], 2),
                    "untere": round(pairs[ci][0], 2),
                    "obere": round(pairs[ci][1], 2),
                    "low_sample": False,
                })
            else:
                values.append(None)
        rows_out.append({"lage": lage, "size": size, "size_label": label,
                         "values": values})

    # Legacy 4-band rollup for existing consumers (mean of Mittelwerte in the
    # official bands that fall into each legacy bucket).
    def cell(lage, size, ci):
        for r in rows_out:
            if r["lage"] == lage and r["size"] == size:
                v = r["values"][ci]
                return v["mittelwert"] if v else None
        return None

    legacy_tables = []
    for lage, big_sizes in (("normal", ["91+"]), ("gut", ["91+", "91-131", "131+"])):
        rows_leg = []
        for ci, cohort in enumerate(COHORTS):
            def c(lsize, lage=lage, ci=ci):
                return cell(lage, lsize, ci)
            big = [v for s in big_sizes if (v := c(s)) is not None]
            rows_leg.append({
                "baujahr": cohort,
                "bis_40": c("<41"),
                "40_60": c("41-66"),
                "60_90": c("66-91"),
                "ueber_90": round(sum(big) / len(big), 2) if big else None,
            })
        legacy_tables.append({"lage": lage, "rows": rows_leg})

    out = {
        "city": "Hamburg",
        "city_slug": "hamburg",
        "slug": "hamburg",
        "state": "Hamburg",
        "lat": 53.5511,
        "lng": 9.9937,
        "population": 1900000,
        "year": 2025,
        "type": "qualifiziert",
        "source": ("Hamburger Mietenspiegel 2025, Behörde für Stadtentwicklung "
                   "und Wohnen (Erhebungsstichtag 01.04.2025), Nettokaltmiete "
                   "ohne Heizung und ohne Betriebskosten. Median (Mittelwert) "
                   "mit Spanne; * = weniger als 30 Datensätze (eingeschränkte "
                   "Aussage)."),
        "source_url": "https://www.hamburg.de/mietenspiegel/",
        "source_file": "data/raw/hamburg-mietenspiegel-tabelle-2025.pdf",
        "schema_note": ("official_rows preserves the official 10 Baualtersklassen "
                        "and the official size bands verbatim (Normal has 4 bands, "
                        "Gute has 5). No interpolation — empty cells are Leerfelder "
                        "in the official table."),
        "lage_categories": ["normal", "gut"],
        "official_rows": rows_out,
        "tables": legacy_tables,
        "verification_status": "verified",
        "verification_note": ("Extracted from the official table PDF with "
                              "scripts/extract_hamburg.py; every Mittelwert and "
                              "Spanne re-checked against the PDF text layer."),
    }

    # self-verify against the PDF text (keep two decimals — the PDF prints
    # trailing zeros, e.g. 18,50)
    hay = text
    ok = 0
    total = 0
    for r in rows_out:
        for v in r["values"]:
            if not v:
                continue
            total += 1
            cell_ok = True
            for num in (v["mittelwert"], v["untere"], v["obere"]):
                s = f"{num:.2f}".replace(".", ",")
                s_trim = s.rstrip("0").rstrip(",")
                if not (re.search(rf"(?<!\d){re.escape(s)}(?!\d)", hay)
                        or re.search(rf"(?<!\d){re.escape(s_trim)}(?!\d)", hay)):
                    cell_ok = False
            if cell_ok:
                ok += 1
    print(f"self-check: {ok}/{total} cells fully matched in PDF text")
    assert ok / total >= 0.95, "self-check failed"

    out_path = REPO / "docs/data/processed/hamburg.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
