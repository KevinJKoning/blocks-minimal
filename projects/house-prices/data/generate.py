"""Write the house-prices app's synthetic listings and their true prices (standard library only).

    python3 projects/house-prices/data/generate.py

Thirty neighbourhoods, each with a true price per square metre, drawn around a city-wide level.
Listings are spread over them unevenly: some neighbourhoods have three to six, others a hundred
or more. The listings are a year of portal scrapes, made messy the way real ones are:

- some listings are repeated (a scrape picks up the same advert twice), each with a new id;
- some have no floor area;
- some have a data-entry error of a factor of 10: the price has an extra zero, or the area
  is ten times too big or too small.

Writes, next to this script: listings.csv (one row per listing, repeats included) and
truth.json (the true price per square metre of each neighbourhood). Living in data/, it is
not part of the app's graph: no node reads it, so the page never embeds it.
"""
import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(2026)
CITY_LEVEL = 5500.0          # the city-wide price per square metre, around which neighbourhoods differ
LISTING_SD = 0.2             # how far one listing's price per m² strays from its neighbourhood's, in log terms
NEIGHBOURHOODS = [
    "Alder Park", "Ashford", "Birchmoor", "Brackwater", "Cedar Hill", "Clayton Cross", "Corbin Vale",
    "Dunmere", "Eastgate", "Elm Row", "Fairlea", "Foxhollow", "Greystone", "Harrow End", "Hollins",
    "Ivy Bank", "Kestrel Bay", "Larkfield", "Maple Green", "Millbrook", "Northam", "Oakridge",
    "Pennock", "Quarry Side", "Rowan Gate", "Sandle", "Stonebridge", "Thornley", "Upper Wexford", "Westcombe",
]
DUPLICATE_SHARE, NO_AREA_SHARE = 0.03, 0.05
PRICE_ZERO_SHARE, AREA_TEN_UP_SHARE, AREA_TEN_DOWN_SHARE = 0.04, 0.03, 0.015

truth = {name: int(round(CITY_LEVEL * math.exp(R.gauss(0, 0.35)), -1)) for name in NEIGHBOURHOODS}

# How many listings each neighbourhood has: eight thin ones (three to six), twelve middling, ten large.
sizes = [R.randint(3, 6) for _ in range(8)] + [R.randint(15, 40) for _ in range(12)] + [R.randint(50, 150) for _ in range(10)]
R.shuffle(sizes)

rows = []
for name, n in zip(NEIGHBOURHOODS, sizes):
    for _ in range(n):
        area = round(min(250.0, max(25.0, R.lognormvariate(math.log(78), 0.35))), 1)
        price = round(truth[name] * area * math.exp(R.gauss(0, LISTING_SD)))
        u = R.random()
        if u < PRICE_ZERO_SHARE:
            price *= 10
        elif u < PRICE_ZERO_SHARE + AREA_TEN_UP_SHARE:
            area = round(area * 10, 1)
        elif u < PRICE_ZERO_SHARE + AREA_TEN_UP_SHARE + AREA_TEN_DOWN_SHARE:
            area = round(area / 10, 1)
        rows.append({"neighbourhood": name, "price": price, "area_m2": area,
                     "rooms": max(1, round(area / 28 + R.gauss(0, 0.6))),
                     "listed_on": (date(2026, 1, 1) + timedelta(days=R.randrange(365))).isoformat()})

R.shuffle(rows)
for r in R.sample(rows, round(DUPLICATE_SHARE * len(rows))):
    rows.insert(R.randrange(len(rows) + 1), dict(r))
for r in rows:
    if R.random() < NO_AREA_SHARE:
        r["area_m2"] = ""

OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "listings.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["listing_id", "neighbourhood", "price", "area_m2", "rooms", "listed_on"])
    for i, r in enumerate(rows, 1):
        w.writerow([f"L{i:05d}", r["neighbourhood"], r["price"], r["area_m2"], r["rooms"], r["listed_on"]])
(OUT / "truth.json").write_text(json.dumps({"unit": "price per square metre, in the listings' currency",
                                            "price_per_m2": truth}, indent=1) + "\n")
print(f"{len(rows)} listings in {len(NEIGHBOURHOODS)} neighbourhoods -> {OUT}")
