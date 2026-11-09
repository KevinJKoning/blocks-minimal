"""Write the listing-prices app's synthetic listings, from known true prices (standard library only).

    python3 projects/listing-prices/data/generate.py

Thirty neighbourhoods, each with a true price per square metre (truth.json), and a year of
their listings (listings.csv): an agency's export, messy the way real ones are.

- Some neighbourhoods have only a handful of listings (five of them, 4 to 8), some a few
  dozen (ten of them), and the rest a couple of hundred.
- Each listing's price per square metre is its neighbourhood's true value times lognormal
  noise (sd 0.18 in the log).
- 3% of listings have a price off by a factor of 10 and 3% an area off by a factor of 10
  (a misplaced decimal point, either way).
- 5% are missing the area.
- 3% are reposts: the same listing again, under a new listing_id.

Writes, next to this script: listings.csv and truth.json. The app never reads truth.json
except to score its answer; with real listings there is no truth to replace it with.
"""
import csv
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(2026)
NEIGHBOURHOODS = [f"N{i:02d}" for i in range(1, 31)]
SPARSE = NEIGHBOURHOODS[::6]      # five neighbourhoods with a handful of listings
MEDIUM = NEIGHBOURHOODS[2::3]     # ten with a few dozen
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]
NOISE, ERROR, MISSING, REPOST = 0.18, 0.03, 0.05, 0.03

# The true price per m² of each neighbourhood: typically 3,200, spread about a factor of 3 either way.
truth = {n: round(math.exp(R.gauss(math.log(3200), 0.3)), 1) for n in NEIGHBOURHOODS}

rows, errors = [], 0
for n in NEIGHBOURHOODS:
    count = R.randint(4, 8) if n in SPARSE else R.randint(20, 45) if n in MEDIUM else R.randint(120, 260)
    for _ in range(count):
        per_m2 = truth[n] * math.exp(R.gauss(0, NOISE))
        area = min(250.0, max(25.0, R.lognormvariate(math.log(78), 0.3)))
        row = {"neighbourhood": n, "listed": R.choice(MONTHS), "price": round(per_m2 * area, -3), "area_m2": round(area, 1)}
        if R.random() < ERROR:
            row["price"] = round(row["price"] * R.choice((10, 0.1)))
            errors += 1
        if R.random() < ERROR:
            row["area_m2"] = round(row["area_m2"] * R.choice((10, 0.1)), 1)
            errors += 1
        if R.random() < MISSING:
            row["area_m2"] = ""
        rows.append(row)

copies = [dict(r) for r in rows if R.random() < REPOST]
rows += copies
R.shuffle(rows)
for k, r in enumerate(rows):
    r["listing_id"] = f"L{k + 1:05d}"

OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "listings.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["listing_id", "neighbourhood", "listed", "price", "area_m2"])
    w.writerows([[r["listing_id"], r["neighbourhood"], r["listed"], int(r["price"]), r["area_m2"]] for r in rows])
(OUT / "truth.json").write_text(json.dumps({"price_per_m2": truth, "listing_noise_sd": NOISE, "error_share": ERROR,
                                            "missing_area_share": MISSING, "repost_share": REPOST, "seed": 2026},
                                           indent=1) + "\n")
print(f"{len(rows)} listings ({len(copies)} reposts, {errors} factor-10 errors, "
      f"{sum(r['area_m2'] == '' for r in rows)} without an area) -> {OUT}")
