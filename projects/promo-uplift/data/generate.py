"""Write the promo-uplift app's synthetic data, from a known true uplift (standard library only).

    python3 projects/promo-uplift/data/generate.py

Forty stores, fifty-two weeks of weekly sales. Twenty stores (the bigger ones, likelier) run a
promotion in the last eight weeks, weeks 45 to 52; the rest never do. Each store-week's sales:

    sales = size · base · exp(trend · week + season + noise) · (1 + uplift · promo) · outlier

    season = amplitude · cos(2π (week − 47) / 52)     a winter peak at week 47, which the
                                                      promotion weeks sit on
    amplitude = 0.10 for untreated stores, 0.13 for treated ones: the treated stores swing
                more with the season, so they differ a little beyond their size
    noise    normal, sd 0.05 on the log scale
    outlier  twelve store-weeks, three in treated promotion weeks, three in treated weeks
             before, six in untreated stores: spikes of 2.2 to 3.5 times, or drops to a
             fifth or a third, as a bulk order or a stock-out would make them

Writes, next to this script: sales.csv (store, size_m2, week, promo, sales) and truth.json
(the true uplift, and what the data was drawn from). A script in data/ is not a dataset;
sales.csv and truth.json are.
"""
import csv
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(7)
STORES, WEEKS, TREATED = 40, 52, 20
PROMO = range(45, 53)              # the last eight of the fifty-two weeks
UPLIFT = 0.10                      # sales in promotion weeks are 10% higher than they would be
SEASON = {"untreated": 0.10, "treated": 0.13}
TREND, NOISE, BASE = 0.001, 0.05, 2.2

names = [f"S{n:02d}" for n in range(1, STORES + 1)]
size = {s: round(R.lognormvariate(math.log(900), 0.35)) for s in names}
# Bigger stores are likelier to run the promotion.
treated = set(sorted(names, key=lambda s: math.log(size[s]) + R.gauss(0, 0.5), reverse=True)[:TREATED])

cells = [(s, w) for s in names for w in range(1, WEEKS + 1)]
promo_cells = [c for c in cells if c[0] in treated and c[1] in PROMO]
pre_cells = [c for c in cells if c[0] in treated and c[1] not in PROMO]
other_cells = [c for c in cells if c[0] not in treated]
outliers = {}
for c in R.sample(promo_cells, 3) + R.sample(pre_cells, 3) + R.sample(other_cells, 6):
    outliers[c] = round(R.uniform(2.2, 3.5), 2) if R.random() < 0.6 else round(R.uniform(0.15, 0.35), 2)

rows = []
for s in names:
    amp = SEASON["treated" if s in treated else "untreated"]
    for w in range(1, WEEKS + 1):
        promo = int(s in treated and w in PROMO)
        season = amp * math.cos(2 * math.pi * (w - 47) / 52)
        mean = size[s] * BASE * math.exp(TREND * w + season) * (1 + UPLIFT * promo)
        sales = mean * math.exp(R.gauss(0, NOISE)) * outliers.get((s, w), 1.0)
        rows.append([s, size[s], w, promo, round(sales, 2)])

with open(OUT / "sales.csv", "w", newline="") as f:
    out = csv.writer(f, lineterminator="\n")
    out.writerow(["store", "size_m2", "week", "promo", "sales"])
    out.writerows(rows)

truth = {
    "uplift": UPLIFT,
    "uplift_means": "weekly sales in a promotion week are this share higher than they would have been, "
                    "in a treated store (multiplicative)",
    "promo_weeks": [PROMO.start, PROMO.stop - 1],
    "treated_stores": sorted(treated),
    "season": SEASON,
    "season_shape": "cos(2π (week - 47) / 52)",
    "trend_per_week": TREND,
    "noise_sd_log": NOISE,
    "outliers": [[s, w, f] for (s, w), f in outliers.items()],
}
with open(OUT / "truth.json", "w") as f:
    json.dump(truth, f, indent=1)
    f.write("\n")
