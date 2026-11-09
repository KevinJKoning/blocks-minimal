"""Write the promo-lift app's synthetic data, from known true parameters (standard library only).

    python3 projects/promo-lift/data/generate.py

40 stores, 52 weeks of sales in dollars. Stores differ in size (lognormal). 20 of them,
chosen at random, ran a promotion in the last 8 weeks (weeks 45 to 52). Each store's weekly
sales are drawn from

    log(sales) = log(size) + season + holiday x sensitivity + trend x week + week shock
                 + store noise + log(1 + uplift, if promoted)

- season: a yearly sine, the same in every store;
- holiday: a rise over weeks 48 to 52, the same in every store, but treated stores respond
  1.15 times as much (so the promotion's weeks are not quite like the others);
- trend: treated stores grow 0.03% a week faster, so they do not follow the control stores
  exactly (the parallel-trends assumption is off by a little);
- week shock: the same for every store in a week;
- uplift: each treated store has its own, drawn around 8%;
- outliers: about 0.4% of store-weeks are off by a factor of 1.5 to 2.2, or 0.45 to 0.67.

Writes, next to this script: sales.csv.gz (one row per store-week) and truth.json (every true
parameter, the uplift the app is scored against included). Living in data/, it is not part of
the app: no node reads it except through the dataset, and the score reads truth.json.
"""
import csv
import gzip
import io
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent   # this folder: the app's data/
R = random.Random(2026)
STORES, WEEKS, TREATED, PROMO_FROM = 40, 52, 20, 45
UPLIFT_MEAN, UPLIFT_SD = 0.08, 0.02
SEASON_AMP = 0.05
HOLIDAY = {48: 0.05, 49: 0.12, 50: 0.15, 51: 0.18, 52: 0.22}
HOLIDAY_SENS = {False: 1.0, True: 1.15}   # treated stores respond more to the holidays
TREND = {False: 0.0, True: 0.0003}        # treated stores grow a little faster, per week
SHOCK_SD, NOISE_SD, OUTLIER_RATE = 0.02, 0.04, 0.004

treated = set(R.sample(range(STORES), TREATED))
size = {s: 40_000 * math.exp(R.gauss(0, 0.5)) * (1.2 if s in treated else 1.0) for s in range(STORES)}
uplift = {s: R.gauss(UPLIFT_MEAN, UPLIFT_SD) for s in sorted(treated)}
shock = [R.gauss(0, SHOCK_SD) for _ in range(WEEKS)]

rows, outliers = [], 0
for s in range(STORES):
    t = s in treated
    for w in range(1, WEEKS + 1):
        log_mu = (math.log(size[s]) + SEASON_AMP * math.sin(2 * math.pi * (w - 1) / 52)
                  + HOLIDAY.get(w, 0.0) * HOLIDAY_SENS[t] + TREND[t] * (w - 1)
                  + shock[w - 1] + R.gauss(0, NOISE_SD))
        if R.random() < OUTLIER_RATE:
            outliers += 1
            log_mu += R.choice([-1, 1]) * R.uniform(0.4, 0.8)
        if t and w >= PROMO_FROM:
            log_mu += math.log(1 + uplift[s])
        rows.append([f"S{s + 1:02d}", w, int(t), round(math.exp(log_mu), 2)])

OUT.mkdir(parents=True, exist_ok=True)
text = io.StringIO()
out = csv.writer(text, lineterminator="\n")
out.writerow(["store", "week", "treated", "sales"])
out.writerows(rows)
(OUT / "sales.csv.gz").write_bytes(gzip.compress(text.getvalue().encode(), mtime=0))

# The true uplift is the mean over the treated stores, as drawn: what an unbiased estimate targets.
truth = {
    "uplift": round(sum(uplift.values()) / len(uplift), 6),
    "uplift_nominal": UPLIFT_MEAN,
    "store_uplift": {f"S{s + 1:02d}": round(u, 6) for s, u in sorted(uplift.items())},
    "promo_from_week": PROMO_FROM,
    "holiday_sensitivity_treated": HOLIDAY_SENS[True],
    "trend_per_week_treated": TREND[True],
    "outlier_store_weeks": outliers,
    "seed": 2026,
}
(OUT / "truth.json").write_text(json.dumps(truth, indent=1) + "\n")
print(f"{STORES} stores, {len(treated)} treated, {len(rows)} store-weeks, {outliers} outliers, "
      f"true uplift {truth['uplift']:.4f} -> {OUT}")
