"""Write the windstorm app's synthetic data, from known true parameters (standard library only).

    python3 projects/windstorm/data/generate.py

A stretch of coast 200 km wide and 150 km deep, in metres on a local projection, cut into
300 territories (a jittered grid; the bottom row follows the coastline). 100,000 homeowners
policies are placed in them with very uneven density (lognormal, denser near the coast),
and each one's windstorm claims are drawn from a Poisson model:

    log(claims per policy-year) = intercept + construction + roof age + deductible + terrain
                                  + territory effect + log(wind load)

where the wind load is (v(d) / v_coast)^2 with v(d) = v_background + (v_coast - v_background)
* exp(-d / decay), d the distance inland. The territory effects are what the GLM cannot see
and credibility has to find. Writes, next to this script: policies.csv.gz,
territories.geojson, coast.geojson and truth.json (every true parameter). Living in data/,
it is not part of the app: no node reads it, so the page never embeds it.
"""
import bisect
import csv
import gzip
import io
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent   # this folder: the app's data/
R = random.Random(2026)
NX, NY, WIDTH, DEPTH, ROW0 = 20, 15, 200_000, 150_000, 20_000
POLICIES = 100_000
WIND = {"coast_speed": 60.0, "background_speed": 25.0, "decay_km": 40.0}
COEF = {"intercept": math.log(0.06), "masonry": -0.35, "concrete": -0.8, "roof_age_per_decade": 0.25,
        "log_deductible_per_1000": -0.3, "urban": -0.25, "open": 0.15}
TERRITORY_SD = 0.25


def coast_y(x):
    return 7000 + 3000 * math.sin(x / 30_000) + 1500 * math.sin(x / 11_000 + 1)


COAST = [(x, coast_y(x)) for x in range(-30_000, WIDTH + 30_001, 500)]
COAST_X = [p[0] for p in COAST]


def inland(x, y):
    """Distance to the coastline in metres (segments within 40 km of x are enough)."""
    lo, hi = bisect.bisect_left(COAST_X, x - 40_000), bisect.bisect_right(COAST_X, x + 40_000)
    best = math.inf
    for (ax, ay), (bx, by) in zip(COAST[max(lo - 1, 0):hi], COAST[max(lo, 1):hi + 1]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def wind_offset(d):
    v = WIND["background_speed"] + (WIND["coast_speed"] - WIND["background_speed"]) * math.exp(-d / 1000 / WIND["decay_km"])
    return 2 * math.log(v / WIND["coast_speed"])


def poisson(lam):
    k, p, limit = 0, 1.0, math.exp(-lam)
    while True:
        p *= R.random()
        if p <= limit:
            return k
        k += 1


# Grid vertices (shared, so the territories tile); row 0's bottom edge is the coastline.
rows = [ROW0 + j * (DEPTH - ROW0) / (NY - 1) for j in range(NY)]
V = [[(i * WIDTH / NX + (R.uniform(-2500, 2500) if 0 < i < NX else 0), y + (R.uniform(-2000, 2000) if j < NY - 1 else 0))
      for j, y in enumerate(rows)] for i in range(NX + 1)]


def bottom(i, j, u):
    if j == 0:
        x = (i + u) * WIDTH / NX
        return x, coast_y(x)
    (ax, ay), (bx, by) = V[i][j - 1], V[i + 1][j - 1]
    return ax + u * (bx - ax), ay + u * (by - ay)


def top(i, j, u):
    (ax, ay), (bx, by) = V[i][j], V[i + 1][j]
    return ax + u * (bx - ax), ay + u * (by - ay)


cells = [(i, j) for j in range(NY) for i in range(NX)]
territories, centres, density = [], {}, []
for n, (i, j) in enumerate(cells):
    tid = f"T{n + 1:03d}"
    edge = [bottom(i, j, k / 8) for k in range(9)]
    ring = [*edge, top(i, j, 1), top(i, j, 0), edge[0]]
    cx, cy = bottom(i, j, 0.5)[0], (bottom(i, j, 0.5)[1] + top(i, j, 0.5)[1]) / 2
    d = inland(cx, cy) / 1000
    city = min(math.hypot(cx - ux, cy - uy) for ux, uy in [(45_000, 25_000), (140_000, 40_000)]) / 1000
    terrain = "urban" if city < 18 else "open" if d > 60 and R.random() < 0.6 else "suburban"
    effect = R.gauss(0, TERRITORY_SD)
    territories.append({"type": "Feature", "properties": {"territory": tid, "terrain": terrain},
                        "geometry": {"type": "Polygon", "coordinates": [[[round(x, 1), round(y, 1)] for x, y in ring]]}})
    centres[tid] = (terrain, effect)
    density.append(math.exp(R.gauss(0, 1.1)) * (1 + 3 * math.exp(-d / 20)) * (2 if terrain == "urban" else 1))

rows_out, claims = [], 0
for k, n in enumerate(R.choices(range(len(cells)), weights=density, k=POLICIES)):
    (i, j), tid = cells[n], f"T{n + 1:03d}"
    u, v = R.random(), R.random()
    (bx, by), (tx, ty) = bottom(i, j, u), top(i, j, u)
    x, y = bx + v * (tx - bx), by + v * (ty - by)
    terrain, effect = centres[tid]
    construction = R.choices(["frame", "masonry", "concrete"], [55, 35, 10])[0]
    roof_age = R.randint(0, 30)
    deductible = R.choices([500, 1000, 2500, 5000], [20, 40, 30, 10])[0]
    exposure = 1.0 if R.random() < 0.7 else round(R.uniform(0.1, 1.0), 3)
    log_rate = (COEF["intercept"] + COEF.get(construction, 0) + COEF["roof_age_per_decade"] * roof_age / 10
                + COEF["log_deductible_per_1000"] * math.log(deductible / 1000) + COEF.get(terrain, 0) + effect
                + wind_offset(inland(x, y)))
    c = poisson(exposure * math.exp(log_rate))
    claims += c
    rows_out.append([f"P{k + 1:06d}", round(x, 1), round(y, 1), exposure, construction, roof_age, deductible, c])

OUT.mkdir(parents=True, exist_ok=True)
text = io.StringIO()
w = csv.writer(text, lineterminator="\n")
w.writerow(["policy_id", "x", "y", "exposure", "construction", "roof_age", "deductible", "claims"])
w.writerows(rows_out)
(OUT / "policies.csv.gz").write_bytes(gzip.compress(text.getvalue().encode(), mtime=0))
(OUT / "territories.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": territories}) + "\n")
(OUT / "coast.geojson").write_text(json.dumps({"type": "Feature", "properties": {"name": "coastline"},
                                               "geometry": {"type": "LineString", "coordinates": [[x, round(y, 1)] for x, y in COAST]}}) + "\n")
(OUT / "truth.json").write_text(json.dumps({"coefficients": COEF, "wind": WIND, "territory_sd": TERRITORY_SD,
                                            "territory_effect": {t: round(e, 6) for t, (_, e) in centres.items()}}, indent=1) + "\n")
print(f"{POLICIES} policies, {claims} claims, {len(territories)} territories -> {OUT}")
