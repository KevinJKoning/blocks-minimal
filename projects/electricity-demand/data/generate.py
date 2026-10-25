"""Write the electricity-demand app's synthetic data (standard library only).

    python3 projects/electricity-demand/data/generate.py

Ten years of monthly electricity demand for a mid-sized utility, January 2015 to December
2024, in GWh:

    demand = 900 + 2.5 * months since Jan 2015                     (load growth)
             + 120 * cos(2π (month - 1) / 12) + 70 * cos(4π (month - 7) / 12)
                                                                     (winter heating, summer cooling)
             + noise, normal with sd 25

The two cosines give a winter peak and a smaller summer peak, so a year has two humps.
Writes one export per year, demand/<year>.csv (month as YYYY-MM, demand_gwh), as a utility's
yearly files arrive. A script in data/ is not a dataset; the folder demand/ is one.
"""
import csv
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(2026)

(OUT / "demand").mkdir(exist_ok=True)
for year in range(2015, 2025):
    with open(OUT / "demand" / f"{year}.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["month", "demand_gwh"])
        for month in range(1, 13):
            t = (year - 2015) * 12 + month - 1
            y = (900 + 2.5 * t + 120 * math.cos(2 * math.pi * (month - 1) / 12)
                 + 70 * math.cos(4 * math.pi * (month - 7) / 12) + R.gauss(0, 25))
            w.writerow([f"{year}-{month:02d}", f"{y:.1f}"])
