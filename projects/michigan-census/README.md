# Michigan population and demographics

Compare population, age, and race/ethnicity across Michigan and its 83 counties using
**2010–2014, 2015–2019, and 2020–2024 ACS five-year estimates**. Choose the periods in
**periods** and a geography in **geography**, then explore charts, county maps and downloads.

## Run

The bundled snapshot works offline. To refresh it, retrieve official Census bulk
files with native Python; analysis runs in Pyodide. No API key is needed.

```sh
.venv/bin/python projects/michigan-census/data/refresh.py             # optional refresh
.venv/bin/python projects/michigan-census/data/refresh_boundaries.py  # optional map refresh
.venv/bin/blocks serve                                                 # /michigan-census/
.venv/bin/blocks verify michigan-census
.venv/bin/blocks build michigan-census
```

Refresh downloads a few hundred MB and saves the Michigan subset in `data/census.json`,
including source URLs, checksums, retrieval time, estimates, and margins of error.
After refreshing, inspect verification differences before intentionally updating the baseline.

## Pipeline

`census → ingest → geography → population / demographics`, with `periods` feeding all
four comparisons and `boundaries → shapes → maps`.

**ingest** checks coverage, uniqueness and population totals. **periods** sets the two
periods compared; **geography** the place **population** and **demographics** describe.
**counties** compares all 83 counties, and **maps** shades them by population change,
demographic share and share change. Changing the geography re-runs only the two pages
that use it.

## Interpretation

These non-overlapping five-year estimates are not annual counts. Published 90%
margins of error are retained; unavailable values remain null. Shares, changes, and
rankings are descriptive, without significance claims.

Sources: [ACS summary files](https://www.census.gov/programs-surveys/acs/data/summary-file.html),
[comparison guidance](https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html),
and [race-question changes](https://www.census.gov/programs-surveys/acs/technical-documentation/user-notes/2021-03.html).
Exact file URLs and checksums are on the ingest page.
