Monthly electricity demand, as a **folder of CSV exports**, one per year, read in name
order (`2015.csv`, `2016.csv`, ...). Choose every file at once; together they must hold
one row per month, in order, with no gaps.

| column | means |
|---|---|
| `month` | the month, as `YYYY-MM` |
| `demand_gwh` | that month's demand in GWh |
