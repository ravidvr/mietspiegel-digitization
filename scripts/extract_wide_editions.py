#!/usr/bin/env python3
"""Deterministic extractor for the wide-table Mietspiegel editions (2017-2023).

Layout: one page, 8 Bezugsfertigkeit columns x 12 rows (3 Wohnlagen x 4 size
bands). Each cell = Mittelwert line + 3/4-Spanne line ("lo - hi").
Columns are ~300pt apart on an A4 page; median x positions cluster around
~795..2930pt. Size labels sit at x<350, footnote margin text at x>3500.

Method:
1. Data band: y in [0.45*H, 0.88*H], x in [350, 3500].
2. Group numeric tokens by y (tol 3pt), merge groups <8pt apart.
3. Classify y-groups as MEDIAN (no dash between its numbers) or SPANNE.
4. Sort median groups by y -> 12 rows cycling einfach/mittel/gut x
   <40/40-60/60-90/90+; nearest lage-label word verifies the cycle.
5. Cluster median-token x globally (tol 60pt) into 8 column centers.
6. Per row: median = token within +-70pt of center; spanne lo/hi = min/max
   numeric tokens within +-110pt of center. Footnotes (*, **) stripped.
"""
import argparse
import json
import re
from pathlib import Path

import pdfplumber

SIZE_CYCLE = ["<40", "40-60", "60-90", "90+"]
LAGE_CYCLE = ["einfach", "mittel", "gut"]

COHORTS = {
    2017: ["bis 1918", "1919-1949", "1950-1964", "1965-1972",
           "1973-1990 West", "1973-1990 Ost", "1991-2002", "2003-2015"],
    2019: ["bis 1918", "1919-1949", "1950-1964", "1965-1972",
           "1973-1990 West", "1973-1990 Ost", "1991-2002", "2003-2017"],
    2021: ["bis 1918", "1919-1949", "1950-1964", "1965-1972",
           "1973-1990 West", "1973-1990 Ost", "1991-2002", "2003-2017"],
    2023: ["bis 1918", "1919-1949", "1950-1964", "1965-1972",
           "1973-1990 West", "1973-1990 Ost", "1991-2002", "2003-2017"],
}


def parse_de_num(token: str):
    t = token.replace(",", ".").replace("€", "").strip()
    t = re.sub(r"[*a-zA-Z\s]+$", "", t)
    try:
        return float(t)
    except ValueError:
        return None


def extract_wide(pdf_path, year):
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[0]
    H = page.height
    words = page.extract_words()

    y_lo, y_hi = 0.30 * H, 0.99 * H
    data = []
    dashes = []
    stars = []  # standalone '*' footnote markers (2019 renders them detached)
    for w in words:
        x0, top, txt = w["x0"], w["top"], w["text"].strip()
        if not (y_lo <= top <= y_hi and 350 <= x0 <= 3050):
            continue
        if txt == "*" or txt == "**":
            stars.append((top, x0))
            continue
        if txt in ("-", "–", "—"):
            dashes.append((top, x0))
            continue
        flagged = txt.endswith("*")
        val = parse_de_num(txt)
        if val is not None:
            data.append((top, x0, val, flagged))

    # attach detached stars: a star FOLLOWS the flagged value — flag the
    # rightmost same-line token left of the star within 250pt (matches the
    # attached-star pattern of the 2017/2021 PDFs)
    def attach_stars(tokens, stars):
        out = [(t, x, v, f) for t, x, v, f in tokens]
        for st_y, st_x in stars:
            same_line = [i for i, (t, x, v, f) in enumerate(out)
                         if abs(t - st_y) < 6 and 0 < st_x - x < 250]
            if same_line:
                idx = max(same_line, key=lambda i: out[i][1])
                t, x, v, f = out[idx]
                out[idx] = (t, x, v, True)
        return out

    data = attach_stars(data, stars)

    # group numeric tokens by y (tol 3), merge groups <8pt apart
    groups = {}
    for top, x0, val, flag in data:
        groups.setdefault(round(top / 3), []).append((x0, val, flag))
    merged = []
    for gkey in sorted(groups):
        y = gkey * 3
        toks = groups[gkey]
        if merged and y - merged[-1][0] < 8:
            merged[-1][1].extend(toks)
            merged[-1][0] = (merged[-1][0] + y) / 2
        else:
            merged.append([y, toks])

    medians, spannes = [], []
    for y, toks in merged:
        xs = sorted(x for x, _, _ in toks)
        has_dash = any(
            abs(dy - y) < 5 and xs[0] - 20 < dx < xs[-1] + 20
            for dy, dx in dashes
        )
        (spannes if has_dash else medians).append((y, toks))

    # noise filter: real lines have >=4 tokens (stray footnote numbers = 1)
    medians = [(y, t) for y, t in medians if len(t) >= 4]
    spannes = [(y, t) for y, t in spannes if len(t) >= 6]

    medians.sort(key=lambda t: t[0])
    spannes.sort(key=lambda t: t[0])

    # 8 column centers from all median x positions (tol 60pt)
    all_x = sorted({round(x0, 1) for _, toks in medians for x0, _, _ in toks})
    centers = []
    for v in all_x:
        if centers and v - centers[-1] <= 60:
            centers[-1] = (centers[-1] + v) / 2
        else:
            centers.append(v)

    lage_words = [(w["top"], w["text"].strip()) for w in page.extract_words()
                  if w["text"].strip() in LAGE_CYCLE and y_lo <= w["top"] <= y_hi]

    rows_out = []
    for ri, (my, mtoks) in enumerate(medians):
        lage = LAGE_CYCLE[ri % 3]
        size = SIZE_CYCLE[ri // 3]
        nearest = min(lage_words, key=lambda p: abs(p[0] - my), default=(0, "?"))
        cand = [s for s in spannes if s[0] > my + 30]
        sline = min(cand, key=lambda s: s[0]) if cand else None

        values = []
        for ci in range(8):
            cx = centers[ci] if ci < len(centers) else None
            median = None
            flagged = False
            if cx is not None:
                mt = [(v, f) for x, v, f in mtoks if abs(x - cx) < 70]
                if mt:
                    median = round(mt[0][0], 2)
                    flagged = any(f for _, f in mt)
            lo = hi = None
            if sline and cx is not None:
                nums = sorted(v for x, v, _ in sline[1] if abs(x - cx) < 110)
                if len(nums) >= 2:
                    lo, hi = round(nums[0], 2), round(nums[-1], 2)
            if median is None and lo is None and hi is None:
                values.append(None)
            else:
                values.append({"mittelwert": median, "untere": lo, "obere": hi,
                               "low_sample": flagged})
        rows_out.append({"lage": lage, "size": size, "lage_check": nearest[1],
                         "values": values})

    pdf.close()
    return {"year": year, "cohorts": COHORTS[year], "rows": rows_out,
            "n_medians": len(medians), "n_spannes": len(spannes),
            "n_columns": len(centers)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = extract_wide(args.pdf, args.year)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{out['n_medians']} median lines, {out['n_spannes']} spanne lines, "
          f"{out['n_columns']} columns, {len(out['rows'])} rows -> {args.output}")


if __name__ == "__main__":
    main()
