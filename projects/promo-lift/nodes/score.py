"""How close the estimate comes to the truth the data was made with: possible only because the data is synthetic.

`data/truth.json` holds the uplift the generator drew, the mean over the promoted stores of
their own uplifts. The error is the estimate less that, in points of sales. `covered` says
whether the estimate's 95% interval holds the truth.
"""
import json

from blocks import ui

METRICS = {"abs_error": {"label": "size of the error against the truth", "goal": "min", "percent": True}}


def score(estimate, truth):
    with open(truth) as f:
        true = json.load(f)["uplift"]
    return {"truth": true, "estimate": estimate["lift"], "low": estimate["low"], "high": estimate["high"],
            "error": estimate["lift"] - true, "abs_error": abs(estimate["lift"] - true),
            "covered": "yes" if estimate["low"] <= true <= estimate["high"] else "no"}


def view(out):
    holds = "holds" if out["covered"] == "yes" else "misses"
    return [
        ui.metrics(),
        ui.markdown(f"The estimate is **{out['estimate']:.1%}**, against a true **{out['truth']:.1%}**: its "
                    f"95% interval {holds} the truth."),
        ui.bars(["estimate", "true uplift"], {"lift": [out["estimate"], out["truth"]]}, kind="dot",
                intervals={"lift": ([out["low"], out["truth"]], [out["high"], out["truth"]])}, percent=True,
                title="Estimate against the truth, with its 95% interval", label="lift"),
    ]
