"""Drop the flagged store-weeks: the estimates use only the store-weeks the screen did not flag.

The screen (panel.screen) flags a store-week whose log sales sit more than four robust standard
deviations from what its store, its week and the promotion predict. If the flags are stock-outs or
data errors, they say nothing about the promotion, and dropping them is the clean answer. If they
are real sales, dropping them throws away a week that happened, and biases the estimate if the
flags are more common in one group.
"""
import numpy as np

from blocks import ui
from panel import clean_view, finish, rows, screen

METRICS = {"flagged": "store-weeks flagged", "changed": "store-weeks dropped", "largest": "largest flagged residual (log)"}


def clean(prepare):
    t = prepare["table"]
    r = rows(t)
    s = screen(r)
    return finish(t, r, s, use=~s["flag"], sales=r["sales"], changed=int(s["flag"].sum()))


def view(out):
    return clean_view(out, f"Dropped the {out['changed']} flagged store-weeks; the estimates use the other "
                           f"{len(out['resid']) - out['changed']:,}.")
