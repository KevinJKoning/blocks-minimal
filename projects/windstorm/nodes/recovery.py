"""How close the app gets to the truth: possible only because the data is synthetic.

`data/generate.py` drew the claims from known coefficients and a known effect
for every territory (`data/truth.json`). Here the GLM's coefficients are set against the
true ones, and three estimates of each territory's effect are scored against the truth:
its own experience alone, the GLM alone (no territory effect), and credibility. Each is
scaled to average 1 over the expected claims, so only the pattern between territories is
compared.

With the wind settings at the values the data was made with, the policy-level coefficients
(construction, roof age, deductible) land inside their intervals; move the wind settings and
watch them drift to absorb the error. The terrain coefficients can miss, and that is a real
lesson rather than a bug: terrain belongs to a whole territory, so it is confounded with the
territory effects the GLM leaves out, and the GLM's intervals, which treat every policy as
independent, are too narrow for it. A model with territory as a random effect would widen
them; credibility, which comes after, is where this app accounts for territories.
"""
import json

import numpy as np

from blocks import ui

METRICS = {"coefficients.inside": "coefficients inside their 95% interval",
           "territories.error_own": {"label": "territory error: own experience", "goal": "min"},
           "territories.error_glm": {"label": "territory error: GLM alone", "goal": "min"},
           "territories.error_credibility": {"label": "territory error: credibility", "goal": "min"}}


def coefficients(fitted, true):
    """Each fitted coefficient beside the one the data was made with, and how many of the true
    ones lie inside their 95% interval."""
    rows = [{**c, "true": true[c["term"]]} for c in fitted]
    return {"rows": rows, "inside": sum(r["low"] <= r["true"] <= r["high"] for r in rows)}


def territories(table, log_effect):
    """Three estimates of each territory's effect against the true one: its own experience, the
    GLM alone (1 everywhere) and credibility.

    Only territories with expected claims are scored. Each estimate, and the truth, is scaled to
    average 1 over the expected claims; an estimate's error is its root-mean-square distance
    from the truth."""
    m = table["expected"].to_numpy()
    seen = m > 0
    norm = lambda v: v[seen] / np.average(v[seen], weights=m[seen])
    true = norm(np.exp([log_effect[x] for x in table["territory"].to_pylist()]))
    own, credibility = norm(table["ratio"].to_numpy()), norm(table["theta"].to_numpy())
    error = lambda v: float(np.sqrt(np.mean((v - true) ** 2)))
    return {"error_own": error(own), "error_glm": error(norm(np.ones_like(m))), "error_credibility": error(credibility),
            "true": true, "own": own, "credibility": credibility}


def recovery(glm, credibility, truth):
    with open(truth) as f:
        truth = json.load(f)
    return {"coefficients": coefficients(glm["coefficients"], truth["coefficients"]),
            "territories": territories(credibility["table"], truth["territory_effect"])}


def view(out):
    s, rows = out["territories"], out["coefficients"]["rows"]
    terms = rows[1:]   # the intercept left out
    order = np.argsort(s["true"])
    return [
        ui.metrics(),
        ui.markdown(f"Root-mean-square error of each territory's effect: **{s['error_credibility']:.3f}** with credibility, "
                    f"against {s['error_own']:.3f} from its own experience alone and {s['error_glm']:.3f} from the GLM "
                    "alone. Credibility beats both: it trusts big territories and lets small ones lean on the model."),
        ui.bars([r["term"] for r in terms], {"estimate": [r["estimate"] for r in terms], "truth": [r["true"] for r in terms]},
                kind="dot", intervals={"estimate": ([r["low"] for r in terms], [r["high"] for r in terms])},
                reference=0, title="Coefficients against the truth, with 95% intervals (the intercept left out)",
                label="coefficient (log scale)"),
        ui.table([{"term": r["term"], "true": r["true"], "estimate": r["estimate"], "95% low": r["low"],
                   "95% high": r["high"], "inside": "yes" if r["low"] <= r["true"] <= r["high"] else "no"}
                  for r in rows], title="Coefficients against the truth"),
        ui.chart(s["true"][order], {"own experience": s["own"][order], "credibility": s["credibility"][order], "truth": s["true"][order]},
                 kind={"own experience": "scatter", "credibility": "scatter", "truth": "line"},
                 title="Territory effects against the truth", x_label="true effect"),
    ]
