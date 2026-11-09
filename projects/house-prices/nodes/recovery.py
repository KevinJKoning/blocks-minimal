"""How close the estimates get to the truth: possible only because the data is synthetic.

`data/generate.py` drew every neighbourhood's listings around a known true price per square
metre (`data/truth.json`). Each estimate is compared with its truth as a relative error (how
far above or below, as a share of the truth). The answer is the typical error: the median over
neighbourhoods of how far off each estimate is, either way.
"""
import json

import numpy as np
import pyarrow as pa

from blocks import ui

METRICS = {"typical_error": {"label": "typical error against the truth", "goal": "min", "percent": True, "answer": True},
           "within_10": {"label": "neighbourhoods within 10% of the truth", "goal": "max", "percent": True},
           "worst": {"label": "worst neighbourhood's error", "goal": "min", "percent": True},
           "missing": "neighbourhoods with no estimate"}


def recovery(estimate, truth):
    with open(truth) as f:
        true = json.load(f)["price_per_m2"]
    t = estimate["table"]
    names = t["neighbourhood"].to_pylist()
    est = t["estimate"].to_numpy()
    tru = np.array([true[n] for n in names], dtype=float)
    err = est / tru - 1
    table = pa.table({"neighbourhood": names, "listings": t["listings"], "true": tru, "estimate": est, "error": err})
    return {"typical_error": float(np.median(np.abs(err))), "within_10": float(np.mean(np.abs(err) <= 0.1)),
            "worst": float(np.max(np.abs(err))), "missing": len(true) - len(names), "table": table,
            "error": err, "true": tru, "estimate_values": est}


def view(out):
    t = out["table"]
    return [
        ui.metrics(),
        ui.markdown(f"A neighbourhood's estimate is typically **{out['typical_error']:.0%}** off its true price per square "
                    f"metre, and {out['within_10']:.0%} of the neighbourhoods are within 10%."),
        ui.histogram(100 * out["error"], title="Each neighbourhood's estimate against its truth",
                     x_label="% above or below the truth", mark=0),
        ui.chart(out["true"], {"estimate": out["estimate_values"]}, kind="scatter", x_scale="log", y_scale="log",
                 title="Estimates against the truth, on log axes", x_label="true price per m²", y_label="estimate"),
        ui.table(t.sort_by([("error", "descending")]), percent=["error"], title="Neighbourhoods against the truth",
                 limit=100),
    ]
