"""Each store's weekly sales before and after the promotion, side by side.

The promotion runs from `from_week` to the last week (the last 8 of 52, by default). A store's
ratio is its average weekly sales after over its average before, so every store counts the
same, whatever its size. The chart indexes each group's sales to its own weeks before, so
the two groups can be compared as they moved.
"""
import csv
import gzip
from statistics import mean
from typing import Annotated

from blocks import Range, ui

METRICS = {"stores": "stores", "store_weeks": "store-weeks", "promoted_stores": "stores promoted",
           "promo_weeks": "promotion weeks"}


def panel(sales, *, from_week: Annotated[int, Range(2, 52, 1)] = 45):
    weekly, promoted = {}, {}
    with gzip.open(sales, "rt") as f:
        for r in csv.DictReader(f):
            weekly.setdefault(r["store"], {})[int(r["week"])] = float(r["sales"])
            promoted[r["store"]] = int(r["treated"])
    weeks = sorted({w for v in weekly.values() for w in v})

    table = []
    for s in sorted(weekly):
        before = [weekly[s][w] for w in weeks if w < from_week]
        after = [weekly[s][w] for w in weeks if w >= from_week]
        table.append({"store": s, "promoted": promoted[s], "weekly_sales_before": mean(before),
                      "weekly_sales_after": mean(after), "ratio": mean(after) / mean(before)})

    def index(group):
        ids = [s for s in weekly if promoted[s] == group]
        avg = [mean(weekly[s][w] for s in ids) for w in weeks]
        base = mean(a for w, a in zip(weeks, avg) if w < from_week)
        return [100 * a / base for a in avg]

    return {"store_table": table, "weeks": weeks, "index_promoted": index(1), "index_other": index(0),
            "from_week": from_week, "stores": len(weekly), "store_weeks": sum(len(v) for v in weekly.values()),
            "promoted_stores": sum(promoted.values()), "promo_weeks": sum(1 for w in weeks if w >= from_week)}


def view(out):
    rows = out["store_table"]
    return [
        ui.metrics(),
        ui.download("store_ratios.csv", rows, title="each store's sales before and after the promotion"),
        ui.chart(out["weeks"], {"promoted stores": out["index_promoted"], "other stores": out["index_other"]},
                 title="Average weekly sales, each group indexed to its weeks before the promotion (100)",
                 x_label="week", y_label="index", x_lines={"promotion starts": out["from_week"]}),
        ui.table(rows, title="Each store's sales before and after the promotion"),
    ]
