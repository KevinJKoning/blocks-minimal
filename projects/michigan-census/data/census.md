An ACS 5-year snapshot, as the **JSON** `data/refresh.py` writes from the Census Bureau's
bulk summary files: `retrieved_at`, the `sources` it was read from (URL and sha256), and
`rows`, one for Michigan and one for each of its 83 counties in each of 2014, 2019 and
2024, with tables `B01001` (age by sex) and `B03002` (race and Hispanic origin), each an
`estimate` and a `moe` list. Make a new one with `data/refresh.py` rather than by hand.
