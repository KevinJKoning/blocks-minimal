"""How close the estimates get to the truth: possible only because the listings are synthetic.

`data/generate.py` drew each neighbourhood's listings around a known true price per square
metre (`data/truth.json`). Each neighbourhood's final estimate is set against its truth as a
relative error. The answer is the median of those errors across the 30 neighbourhoods: the
typical error of a neighbourhood's price per square metre, the one number the app exists to give.
"""
import json
import math
import statistics

from blocks import ui

METRICS = {"median_error": {"label": "typical error against the truth (median of the neighbourhoods)", "goal": "min",
                            "percent": True, "answer": True},
           "worst_error": {"label": "worst neighbourhood's error", "goal": "min", "percent": True},
           "within_10": {"label": "neighbourhoods within 10% of the truth", "goal": "max", "percent": True},
           "unrated": "neighbourhoods with no estimate"}


def score(pooling, truth):
    with open(truth) as f:
        true = json.load(f)["price_per_m2"]
    got = {r["neighbourhood"]: r for r in pooling["table"]}
    rows = []
    for n, t in true.items():
        r = got.get(n)
        final = r["final"] if r else None
        rows.append({"neighbourhood": n, "listings": r["listings"] if r else 0, "true": t,
                     "estimate": None if final is None else round(final),
                     "error": None if final is None else final / t - 1})
    errors = [abs(r["error"]) for r in rows if r["error"] is not None]
    return {"table": rows, "median_error": statistics.median(errors) if errors else math.nan,
            "worst_error": max(errors) if errors else math.nan,
            "within_10": sum(e <= 0.1 for e in errors) / len(rows), "unrated": len(rows) - len(errors)}


def view(out):
    rows = out["table"]
    rated = [r for r in rows if r["estimate"] is not None]
    return [
        ui.download("neighbourhoods_against_truth.csv", rows, title="every neighbourhood's estimate, its true value and its error"),
        ui.metrics(),
        ui.markdown(f"A neighbourhood's estimate is typically **{out['median_error']:.0%}** off its true price per square metre. "
                    f"The worst is **{out['worst_error']:.0%}** off, and **{out['within_10']:.0%}** of the neighbourhoods are "
                    "within 10%."),
        ui.bars([r["neighbourhood"] for r in rated], {"true": [r["true"] for r in rated],
                                                       "estimate": [r["estimate"] for r in rated]},
                kind="dot", label="price per m²", title="Each neighbourhood's estimate against its true price per square metre"),
        ui.table(rows, title="Neighbourhoods against the truth", percent=["error"], limit=200),
    ]
