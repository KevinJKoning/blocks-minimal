"""Difference in differences: the treated stores against the untreated, with each store's and each week's level.

A fixed-effects regression of log sales on a store effect, a week effect and the promotion:

    log sales = store + week + β · promo

The week effects are shared by both groups, so the season is taken out whatever the promotion
does; β is the promotion's effect on log sales, and the uplift is exp(β) − 1. Its 95% interval
clusters the standard error by store. The model assumes the treated and untreated stores share one
season: where they do not, the difference is the season, and it lands in the uplift.

The weekly picture is the model's prediction for the treated stores with the promotion taken out.
"""
import numpy as np

from blocks import ui
from panel import answer, estimate_view, fixed_effects, rows, week_means

METRICS = {"uplift": {"label": "uplift in weekly sales", "percent": True, "answer": True},
           "low": {"label": "95% interval, low", "percent": True}, "high": {"label": "95% interval, high", "percent": True},
           "stores": "treated stores"}


def estimate(clean):
    r = rows(clean["table"])
    y, use = np.log(r["sales"]), r["use"]
    fe = fixed_effects(r, y, use)
    without = week_means(r, r["treated"] & use, fe["fitted"] - fe["promo_part"])
    return answer(fe["beta"], fe["se"], len(np.unique(r["store"][r["treated"]])), r, y, use, without)


def view(out):
    return estimate_view(out, "Store and week effects in both groups, so the season is shared; it misses only if "
                              "the treated stores swing differently with the season.")
