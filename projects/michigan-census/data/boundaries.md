Michigan's 83 county outlines, as the **JSON** `data/refresh_boundaries.py` writes:
`retrieved_at`, `sources`, `crs` (which must be `EPSG:5070`) and `features` in Esri JSON,
each with `attributes.GEOID` (the five-digit county FIPS) and `geometry.rings`.
