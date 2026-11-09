"""How close the app gets to the truth: possible only because the data is synthetic.

`data/generate.py` drew the claims from known coefficients and a known effect
for every territory (`data/truth.json`). Here the GLM's coefficients are set against the
true ones, and three estimates of each territory's effect are scored against the truth:
its own experience alone, the GLM alone (no territory effect), and credibility. Each is
scaled to average 1 over the expected claims, so only the pattern between territories is
compared.

What the app is for is the rates, so they are scored too: each territory's base rate against
the rate the truth gives its reference home (the true coefficients, wind and territory
effect), as a typical relative error, weighing territories by their policy-years. That one
number is the app's answer to "how good are these rates?", and the one its forks are judged by.

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

METRICS = {"rate_error": {"label": "typical rate error against the truth", "goal": "min", "percent": True, "answer": True},
           "within_interval": "coefficients inside their 95% interval",
           "error_own": {"label": "territory error: own experience", "goal": "min"},
           "error_glm": {"label": "territory error: GLM alone", "goal": "min"},
           "error_credibility": {"label": "territory error: as credibility blends it", "goal": "min"}}


def true_rates(join, truth):
    """Claims per 1,000 reference homes a year in each territory, as the data was made."""
    t, b, w = join["territories"], truth["coefficients"], truth["wind"]
    speed = w["background_speed"] + (w["coast_speed"] - w["background_speed"]) * np.exp(-t["distance_km"].to_numpy() / w["decay_km"])
    return 1000 * np.exp(b["intercept"] + b["roof_age_per_decade"] + np.array([b.get(x, 0) for x in t["terrain"].to_pylist()])
                         + 2 * np.log(speed / w["coast_speed"]) + np.array([truth["territory_effect"][x] for x in t["territory"].to_pylist()]))


def recovery(join, glm, credibility, rates, truth):
    with open(truth) as f:
        truth = json.load(f)
    off = np.log(rates["table"]["rate"].to_numpy() / true_rates(join, truth))
    rate_error = float(np.sqrt(np.average(off ** 2, weights=join["territories"]["policy_years"].to_numpy())))
    rows = [{**c, "true": truth["coefficients"][c["term"]]} for c in glm["coefficients"]]
    t = credibility["table"]
    m = t["expected"].to_numpy()
    seen = m > 0
    effect = np.exp([truth["territory_effect"][x] for x in t["territory"].to_pylist()])
    norm = lambda v: v[seen] / np.average(v[seen], weights=m[seen])
    true = norm(effect)
    error = lambda v: float(np.sqrt(np.mean((norm(v) - true) ** 2)))
    return {"rate_error": rate_error, "rate_off": off, "coefficients": rows, "within_interval": sum(r["low"] <= r["true"] <= r["high"] for r in rows),
            "error_own": error(t["ratio"].to_numpy()), "error_glm": error(np.ones_like(m)),
            "error_credibility": error(t["theta"].to_numpy()),
            "scatter": {"true": true, "own": norm(t["ratio"].to_numpy()), "credibility": norm(t["theta"].to_numpy())}}


def view(out):
    s, terms = out["scatter"], out["coefficients"][1:]   # the intercept left out
    order = np.argsort(s["true"])
    return [
        ui.metrics(),
        ui.markdown(f"A territory's base rate is typically **{out['rate_error']:.0%}** off the true one."),
        ui.histogram(100 * (np.exp(out["rate_off"]) - 1), title="Each territory's base rate against the true one",
                     x_label="% above or below the truth", mark=0),
        ui.markdown(f"Root-mean-square error of each territory's effect: **{out['error_credibility']:.3f}** as `credibility` "
                    f"blends it, against {out['error_own']:.3f} from its own experience alone and {out['error_glm']:.3f} from "
                    "the GLM alone."
                    + (" The blend beats both: it trusts big territories and lets small ones lean on the model."
                       if out["error_credibility"] < min(out["error_own"], out["error_glm"]) - 1e-9 else "")),
        ui.bars([r["term"] for r in terms], {"estimate": [r["estimate"] for r in terms], "truth": [r["true"] for r in terms]},
                kind="dot", intervals={"estimate": ([r["low"] for r in terms], [r["high"] for r in terms])},
                reference=0, title="Coefficients against the truth, with 95% intervals (the intercept left out)",
                label="coefficient (log scale)"),
        ui.table([{"term": r["term"], "true": r["true"], "estimate": r["estimate"], "95% low": r["low"],
                   "95% high": r["high"], "inside": "yes" if r["low"] <= r["true"] <= r["high"] else "no"}
                  for r in out["coefficients"]], title="Coefficients against the truth"),
        ui.chart(s["true"][order], {"own experience": s["own"][order], "credibility": s["credibility"][order], "truth": s["true"][order]},
                 kind={"own experience": "scatter", "credibility": "scatter", "truth": "line"},
                 title="Territory effects against the truth", x_label="true effect"),
    ]
