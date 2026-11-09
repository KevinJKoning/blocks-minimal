"""Cap the flagged store-weeks: each keeps its row, but its residual is pulled back to the flag's edge.

The screen (panel.screen) flags a store-week whose log sales sit more than four robust standard
deviations from what its store, its week and the promotion predict. A flagged week is still a week
that happened, so it stays; only its excess over the edge is taken off, so one spike cannot pull a
store's average. The residual the rows keep is what the model predicts plus the edge, not the
row's own.
"""
import numpy as np

from blocks import ui
from panel import clean_view, finish, rows, screen, FLAG

METRICS = {"flagged": "store-weeks flagged", "changed": "store-weeks capped", "largest": "largest flagged residual (log)"}


def clean(prepare):
    t = prepare["table"]
    r = rows(t)
    s = screen(r)
    e, edge = s["resid"], FLAG * s["scale"]
    sales = np.exp(s["y"] - e + np.clip(e, -edge, edge))
    return finish(t, r, s, use=np.ones(len(r["sales"]), bool), sales=sales, changed=int(s["flag"].sum()))


def view(out):
    return clean_view(out, f"Capped the {out['changed']} flagged store-weeks at the edge of the flag; every "
                           f"store-week is still used.")
