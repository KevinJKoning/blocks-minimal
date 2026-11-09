"""Keep every store-week as recorded: the flagged ones stay in the estimates, as they are.

The screen (panel.screen) flags a store-week whose log sales sit more than four robust standard
deviations from what its store, its week and the promotion predict. A bulk order or a local event
is real sales, so keeping it is where most analysts start. It is also the option to beat if the
flags are data errors: then the estimates should not carry them.
"""
import numpy as np

from blocks import ui
from panel import clean_view, finish, rows, screen

METRICS = {"flagged": "store-weeks flagged", "largest": "largest flagged residual (log)"}


def clean(prepare):
    t = prepare["table"]
    r = rows(t)
    s = screen(r)
    return finish(t, r, s, use=np.ones(len(r["sales"]), bool), sales=r["sales"], changed=0)


def view(out):
    return clean_view(out, f"Kept all {len(out['resid']):,} store-weeks, the {out['flagged']} flagged ones among them.")
