"""A Poisson GLM of windstorm claim frequency, with the wind load as an offset.

    claims ~ Poisson(exposure · load · exp(Xβ))

with a log link, and log(exposure) + log(load) as the offset. The rating factors are
construction (frame is the base), roof age per decade, the deductible (as log(deductible /
1,000)) and terrain (suburban is the base). Territory is deliberately not in the model: with
300 territories, many of them nearly empty, it would be estimated from noise. Blending each
territory's own experience with this model is `credibility`'s job.

A Pearson dispersion above 1 says the claims vary more than the rating factors and the
wind explain: here, by territory.
"""
import numpy as np
import statsmodels.api as sm

from blocks import ui
from rating import TERMS, design

METRICS = {"deviance": {"label": "deviance", "goal": "min"},
           "dispersion": {"label": "Pearson dispersion", "goal": "min"}, "aic": {"label": "AIC", "goal": "min"}}


def glm(join, wind):
    t = join["table"]
    col = lambda name: t[name].to_numpy(zero_copy_only=False)
    X = design(col("construction"), col("roof_age"), col("deductible"), col("terrain"))
    fit = sm.GLM(col("claims"), X, family=sm.families.Poisson(), offset=np.log(col("exposure")) + wind["offset"]).fit()
    low, high = fit.conf_int().T
    return {"coefficients": [{"term": term, "estimate": float(b), "se": float(se), "low": float(lo), "high": float(hi)}
                             for term, b, se, lo, hi in zip(TERMS, fit.params, fit.bse, low, high)],
            "expected": fit.mu, "deviance": float(fit.deviance), "dispersion": float(fit.pearson_chi2 / fit.df_resid),
            "aic": float(fit.aic)}


def view(out):
    rows = [{"term": c["term"], "estimate": c["estimate"], "95% low": c["low"], "95% high": c["high"],
             "relativity": float(np.exp(c["estimate"]))} for c in out["coefficients"]]
    return [
        ui.download("coefficients.csv", out["coefficients"], title="the fitted coefficients with standard errors and 95% intervals"),
        ui.metrics(),
        ui.table(rows, title="Coefficients (relativity = exp(estimate), against the base levels)"),
        ui.markdown(f"Pearson dispersion {out['dispersion']:.2f}: the claims vary "
                    + ("more than the rating factors and wind explain, the territory effect credibility will look for."
                       if out["dispersion"] > 1.05 else "about as a Poisson model expects.")),
    ]
