# Historical PDF Provenance

Official Berlin Mietspiegeltabelle PDFs (mietspiegel.berlin.de archive).

| File | Edition | Stichtag | Status |
|---|---|---|---|
| mietspiegeltabelle2017.pdf | 2017 | 01.09.2016 | EXTRACTED & VERIFIED (extract_wide_editions.py) |
| mietspiegeltabelle2019.pdf | 2019 | 01.09.2018 | EXTRACTED & VERIFIED (extract_wide_editions.py) |
| mietspiegeltabelle2021.pdf | 2021 | 01.09.2020 | EXTRACTED & VERIFIED (extract_wide_editions.py) |
| mietspiegeltabelle2023.pdf | 2023 | 01.09.2022 | EXTRACTED & VERIFIED (extract_wide_editions.py) |
| berlin-mietspiegeltabelle-2024.pdf | 2024 | 01.09.2023 | extracted 163/163, PDF-diff verified (berlin_raw_2024.json) |

Sources:
- 2023/2024: https://mietspiegel.berlin.de/wp-content/uploads/2026/01/ (official archive)
- 2021: https://www.berlin.de/sen/wohnen/_assets/archiv/mietspiegeltabelle2021.pdf
- 2013/2015: NOT in the official archive (archive starts at 2017)

Extraction: scripts/extract_wide_editions.py — coordinate-based parser
(grouping numeric tokens by y into median/spanne lines, clustering x into
8 cohort columns, verifying each row against the lage label word). Every
extracted Mittelwert was confirmed present verbatim in the PDF text layer
(359/359 cells across the four editions). Cells the official table flags
as low-sample (* or **, < 30 Mietwerte) carry low_sample: true.

Derived series (scripts/build_historical.py):
- by_lage = mean of Mittelwerte in the NEWEST cohort across non-empty size
  bands, excluding low-sample cells.
- by_lage_same_cohort = same for the 1991-2002 cohort (present in all
  editions) — the apples-to-apples time series for growth comparisons.
