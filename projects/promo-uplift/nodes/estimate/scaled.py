"""Scaled comparison: the treated stores' weekly sales follow the untreated stores', scaled, before the promotion.

Before the promotion, the treated stores' average log sales in each week are regressed on the
untreated stores' average log sales in the same week:

    treated_w = a + b · untreated_w        (weeks before the promotion only)

If the two groups share a season, b is 1; if the treated stores swing more with it, b is above 1,
and the line carries that swing into the promotion weeks. Each promotion week's counterfactual is
a + b · untreated_w; the uplift is the average of the gaps between the treated stores and that line.
The interval is the prediction error of that average, from the pre-promotion fit.
"""
import numpy as np

from blocks import ui
from panel import WEEKS, answer, estimate_view, rows, week_means

METRICS = {"uplift": {"label": "uplift in weekly sales", "percent": True, "answer": True},
           "low": {"label": "95% interval, low", "percent": True}, "high": {"label": "95% interval, high", "percent": True},
           "stores": "treated stores", "slope": "pre-promotion slope on the untreated stores"}


def estimate(clean):
    r = rows(clean["table"])
    y, use = np.log(r["sales"]), r["use"]
    tr = week_means(r, r["treated"] & use, y)
    un = week_means(r, ~r["treated"] & use, y)
    promo_week = np.array([r["promo"][r["week"] == w].sum() > 0 for w in range(1, WEEKS + 1)])
    pre = ~promo_week
    X = np.column_stack([np.ones(pre.sum()), un[pre]])
    (a, b), *_ = np.linalg.lstsq(X, tr[pre], rcond=None)
    resid = tr[pre] - X @ np.array([a, b])
    s2 = resid @ resid / (pre.sum() - 2)
    line = a + b * un
    gap = tr[promo_week] - line[promo_week]
    p = np.array([1.0, un[promo_week].mean()])
    se = float(np.sqrt(s2 * (p @ np.linalg.inv(X.T @ X) @ p + 1 / promo_week.sum())))
    out = answer(gap.mean(), se, len(np.unique(r["store"][r["treated"]])), r, y, use, line)
    return {**out, "slope": float(b)}


def view(out):
    return estimate_view(out, f"The treated stores' pre-promotion sales move {out['slope']:.2f} times as much as the "
                              "untreated stores' with the season, and that is carried into the promotion weeks.")
