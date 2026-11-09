"""Before and after, in the treated stores alone: no untreated stores to compare with.

Each treated store's promotion weeks against its own other weeks, on the log scale, averaged over
the treated stores, with a 95% interval from how much the stores differ. The untreated stores are
ignored, so the season is not: the promotion weeks are the year's peak, and this counts the season
as promotion.

It is the option to beat: what the treated stores' numbers say with no comparison at all.
"""
import numpy as np

from blocks import ui
from panel import WEEKS, answer, estimate_view, rows

METRICS = {"uplift": {"label": "uplift in weekly sales", "percent": True, "answer": True},
           "low": {"label": "95% interval, low", "percent": True}, "high": {"label": "95% interval, high", "percent": True},
           "stores": "treated stores"}


def estimate(clean):
    r = rows(clean["table"])
    y, use = np.log(r["sales"]), r["use"]
    gains = []
    for s in np.unique(r["store"][r["treated"]]):
        m = use & (r["store"] == s)
        gains.append(y[m & (r["promo"] == 1)].mean() - y[m & (r["promo"] == 0)].mean())
    g = np.array(gains)
    before = y[r["treated"] & use & (r["promo"] == 0)].mean()
    return answer(g.mean(), g.std(ddof=1) / np.sqrt(len(g)), len(g), r, y, use, np.full(WEEKS, before))


def view(out):
    return estimate_view(out, "Before and after in the treated stores alone: the season is counted as promotion.")
