"""Naive before and after: the promoted stores' change, taken as the lift.

The promoted stores' average ratio, less one, is the lift. Nothing else is compared, so
whatever moved every store in the promotion's weeks (the season, the holidays) is counted as
the promotion's effect.

The option to beat: it says what the other option buys.
"""
import numpy as np

from lift import picture, ratios, result

METRICS = {"lift": {"label": "lift in weekly sales", "percent": True, "answer": True}}


def estimate(panel):
    promoted, other = ratios(panel)
    lift = promoted.mean() - 1
    se = promoted.std(ddof=1) / np.sqrt(len(promoted))
    return result(lift, se, promoted, other[:0])


def view(out):
    return picture(out, {"promoted stores": out["promoted_ratio"]})
