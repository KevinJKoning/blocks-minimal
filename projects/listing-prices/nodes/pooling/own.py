"""Each neighbourhood keeps its own estimate, however few listings it has.

The option to beat. A neighbourhood with five listings is then reported at what those five say,
with no help from the city, and one surviving error is taken in full.
"""
from blocks import ui

METRICS = {"mean_weight": "mean weight on the neighbourhood's own estimate"}


def pooling(estimate):
    table = [{**r, "weight": 1.0, "final": r["estimate"]} for r in estimate["table"]]
    return {"table": table, "mean_weight": 1.0}


def view(out):
    t = out["table"]
    return [
        ui.download("pooled_estimates.csv", t, title="every neighbourhood's final estimate"),
        ui.metrics(),
        ui.chart([r["listings"] for r in t], {"final estimate": [r["final"] for r in t]}, kind="scatter",
                 x_label="listings in the neighbourhood", y_label="price per m²", title="Each neighbourhood's final estimate, "
                                                                                       "against how many listings it has"),
    ]
