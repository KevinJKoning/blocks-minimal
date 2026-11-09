"""What the estimate options share: each store's ratio, the lift and its interval, and the picture.

A store's ratio is its average weekly sales after the promotion over its average before. The
options differ only in which ratios they compare, and how.
"""
import numpy as np

from blocks import ui

Z = 1.96   # a 95% interval, by the normal approximation


def ratios(panel):
    """The promoted stores' ratios and the other stores' ratios, as arrays."""
    table = panel["store_table"]
    promoted = np.array([s["ratio"] for s in table if s["promoted"]])
    other = np.array([s["ratio"] for s in table if not s["promoted"]])
    return promoted, other


def result(lift, se, promoted, other):
    return {"lift": float(lift), "low": float(lift - Z * se), "high": float(lift + Z * se),
            "promoted_stores": len(promoted), "other_stores": len(other),
            "promoted_ratio": promoted.tolist(), "other_ratio": other.tolist()}


def picture(out, groups):
    """The answer with its interval, and each group's ratios (groups: {name: ratios})."""
    return [
        ui.metrics(),
        ui.bars(["lift"], {"lift": [out["lift"]]}, kind="dot", intervals={"lift": ([out["low"]], [out["high"]])},
                reference=0, percent=True, title="Lift in weekly sales, with a 95% interval", label="lift"),
        ui.histogram(groups, title="Each store's after-over-before ratio", x_label="ratio (after / before)", mark=1),
    ]
