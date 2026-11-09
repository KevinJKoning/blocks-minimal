"""Difference-in-differences: the promoted stores' change, over the other stores' change.

The promoted stores' average ratio, divided by the other stores' average ratio, less one, is
the lift. Whatever moved every store in those weeks (the season, the holidays, a shock)
is in both and cancels. It needs the other stores to be a fair picture of what the promoted
ones would have done without the promotion.
"""
import numpy as np

from lift import picture, ratios, result
from blocks import ui

METRICS = {"lift": {"label": "lift in weekly sales", "percent": True, "answer": True}}


def estimate(panel):
    promoted, other = ratios(panel)
    lift = promoted.mean() / other.mean() - 1
    se = np.sqrt(promoted.var(ddof=1) / len(promoted) + other.var(ddof=1) / len(other)) / other.mean()
    return result(lift, se, promoted, other)


def view(out):
    return picture(out, {"promoted stores": out["promoted_ratio"], "other stores": out["other_ratio"]})
