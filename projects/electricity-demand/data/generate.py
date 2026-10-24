"""Write the electricity-demand app's synthetic data (standard library only).

    python3 projects/electricity-demand/data/generate.py

Ten years of monthly electricity demand for a mid-sized utility, January 2015 to December
2024, in GWh:

    demand = 900 + 2.5 * months since Jan 2015                     (load growth)
             + 120 * cos(2π (month - 1) / 12) + 70 * cos(4π (month - 7) / 12)
                                                                     (winter heating, summer cooling)
             + noise, normal with sd 25

The two cosines give a winter peak and a smaller summer peak, so a year has two humps.
Writes demand.csv (month as YYYY-MM, demand_gwh) next to this script. Living in data/,
it is not part of the app: no node reads it, so the page never embeds it.
"""
import csv
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
R = random.Random(2026)

with open(OUT / "demand.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["month", "demand_gwh"])
    for t in range(120):
        year, month = 2015 + t // 12, t % 12 + 1
        y = (900 + 2.5 * t + 120 * math.cos(2 * math.pi * (month - 1) / 12)
             + 70 * math.cos(4 * math.pi * (month - 7) / 12) + R.gauss(0, 25))
        w.writerow([f"{year}-{month:02d}", f"{y:.1f}"])
