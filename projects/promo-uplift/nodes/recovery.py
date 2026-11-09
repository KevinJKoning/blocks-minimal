"""How close the estimate gets to the truth: possible only because the data is synthetic.

`data/generate.py` made the sales with a known uplift (`data/truth.json`). Here the estimate's
uplift is set against it: the error, and whether the truth falls inside the 95% interval.
"""
import json

from blocks import ui

METRICS = {"truth": {"label": "true uplift", "percent": True},
           "error": {"label": "estimate minus the truth", "goal": "min", "percent": True},
           "covered": "truth inside the 95% interval (1 = yes)"}


def recovery(estimate, truth):
    with open(truth) as f:
        true = float(json.load(f)["uplift"])
    return {"truth": true, "error": estimate["uplift"] - true,
            "covered": float(estimate["low"] <= true <= estimate["high"])}


def view(out):
    verdict = "inside" if out["covered"] else "outside"
    return [
        ui.metrics(),
        ui.markdown(f"The estimate is **{out['error']:+.1%}** from the true uplift of {out['truth']:.0%}, and the truth "
                    f"is {verdict} its 95% interval."),
    ]
