"""Each estimate is blended with the city's median, by how many listings it has.

A neighbourhood with n listings keeps weight w = n / (n + prior_listings) on its own estimate and
takes 1 - w on the city's median: a neighbourhood with many listings is left as it is, and one
with few is pulled toward what every neighbourhood shares. The setting is the number of listings
that would count as much as the city's median itself.
"""
from typing import Annotated

from blocks import Range, ui

METRICS = {"mean_weight": "mean weight on the neighbourhood's own estimate"}


def pooling(estimate, *, prior_listings: Annotated[float, Range(0, 50, 0.5)] = 10.0):
    table = []
    for r in estimate["table"]:
        w = r["listings"] / (r["listings"] + prior_listings)
        table.append({**r, "weight": w, "final": w * r["estimate"] + (1 - w) * estimate["city"]})
    return {"table": table, "mean_weight": sum(r["weight"] for r in table) / len(table)}


def view(out):
    t = out["table"]
    return [
        ui.download("pooled_estimates.csv", t, title="every neighbourhood's final estimate, its own and its weight"),
        ui.metrics(),
        ui.chart([r["listings"] for r in t], {"own estimate": [r["estimate"] for r in t], "final estimate": [r["final"] for r in t]},
                 kind="scatter", x_label="listings in the neighbourhood", y_label="price per m²",
                 title="Each neighbourhood's own estimate and its final one, against how many listings it has"),
    ]
