"""Read the monthly demand series from its yearly exports, in name order (2015.csv first):
one row per month, in order, with no gaps.

Months are given as `YYYY-MM`; for charts each is also placed on a decimal-year axis
(January 2015 is 2015.0, July 2015 is 2015.5).
"""
import csv

import numpy as np

from blocks import ui

METRICS = {"months": "months", "mean_gwh": "mean demand (GWh)", "peak_gwh": "peak month (GWh)"}


def history(demand):
    rows = []
    for path in demand:
        with open(path) as f:
            rows += csv.DictReader(f)
    month = [r["month"] for r in rows]
    gwh = np.array([float(r["demand_gwh"]) for r in rows])
    year = np.array([int(m[:4]) + (int(m[5:7]) - 1) / 12 for m in month])
    if np.any(np.abs(np.diff(year) - 1 / 12) > 1e-9):
        raise ValueError("the exports must hold one row per month, in order, with no gaps")
    return {"month": month, "year": year, "gwh": gwh,
            "months": len(gwh), "mean_gwh": float(gwh.mean()), "peak_gwh": float(gwh.max())}


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"{out['months']} months, {out['month'][0]} to {out['month'][-1]}."),
        ui.chart(out["year"], {"demand": out["gwh"]}, title="Monthly demand", x_label="year", y_label="GWh", x_text=True),
    ]
