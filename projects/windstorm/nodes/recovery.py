"""How close the app gets to the truth: possible only because the data is synthetic.

`scripts/make_windstorm_data.py` drew the claims from known coefficients and a known effect
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

METRICS = {"within_interval": "coefficients inside their 95% interval",
           "error_own": {"label": "territory error: own experience", "goal": "min"},
           "error_glm": {"label": "territory error: GLM alone", "goal": "min"},
           "error_credibility": {"label": "territory error: credibility", "goal": "min"}}


def recovery(glm, credibility, truth):
    with open(truth) as f:
        truth = json.load(f)
    rows = [{**c, "true": truth["coefficients"][c["term"]]} for c in glm["coefficients"]]
    t = credibility["table"]
    m = t["expected"].to_numpy()
    seen = m > 0
    effect = np.exp([truth["territory_effect"][x] for x in t["territory"].to_pylist()])
    norm = lambda v: v[seen] / np.average(v[seen], weights=m[seen])
    true = norm(effect)
    error = lambda v: float(np.sqrt(np.mean((norm(v) - true) ** 2)))
    return {"coefficients": rows, "within_interval": sum(r["low"] <= r["true"] <= r["high"] for r in rows),
            "error_own": error(t["ratio"].to_numpy()), "error_glm": error(np.ones_like(m)),
            "error_credibility": error(t["theta"].to_numpy()),
            "scatter": {"true": true, "own": norm(t["ratio"].to_numpy()), "credibility": norm(t["theta"].to_numpy())}}


def view(out):
    s = out["scatter"]
    order = np.argsort(s["true"])
    return [
        ui.metrics(),
        ui.markdown(f"Root-mean-square error of each territory's effect: **{out['error_credibility']:.3f}** with credibility, "
                    f"against {out['error_own']:.3f} from its own experience alone and {out['error_glm']:.3f} from the GLM "
                    "alone. Credibility beats both: it trusts big territories and lets small ones lean on the model."),
        ui.table([{"term": r["term"], "true": r["true"], "estimate": round(r["estimate"], 4), "95% low": round(r["low"], 4),
                   "95% high": round(r["high"], 4), "inside": "yes" if r["low"] <= r["true"] <= r["high"] else "no"}
                  for r in out["coefficients"]], title="Coefficients against the truth"),
        ui.chart(s["true"][order], {"own experience": s["own"][order], "credibility": s["credibility"][order], "truth": s["true"][order]},
                 kind={"own experience": "scatter", "credibility": "scatter", "truth": "line"},
                 title="Territory effects against the truth", x_label="true effect"),
    ]
