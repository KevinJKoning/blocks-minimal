"""A Poisson GLM of windstorm claim frequency, with the wind load as an offset.

    claims ~ Poisson(exposure · load · exp(Xβ))

with a log link, and log(exposure) + log(load) as the offset. The rating factors are
construction (frame is the base), roof age per decade, the deductible (as log(deductible /
1,000)) and terrain (suburban is the base). Territory is deliberately not in the model: with
300 territories, many of them nearly empty, it would be estimated from noise. Blending each
territory's own experience with this model is `credibility`'s job.

A Pearson dispersion above 1 says the claims vary more than the rating factors and the
wind explain: here, by territory.

The calibration chart sorts the policies by their predicted frequency and cuts them into ten
groups of equal exposure. A calibrated model's observed frequency in each group sits on its
predicted one, within the observed count's exact Poisson 95% interval.
"""
import numpy as np
import statsmodels.api as sm
from scipy import stats

from blocks import ui
from rating import TERMS, design

METRICS = {"deviance": {"label": "deviance", "goal": "min"},
           "dispersion": {"label": "Pearson dispersion", "goal": "min"}, "aic": {"label": "AIC", "goal": "min"},
           "calibration_gap": {"label": "worst group's observed / predicted − 1", "goal": "min"}}
GROUPS = 10


def calibration(expected, claims, exposure):
    """Ten groups of equal exposure, by predicted frequency: predicted and observed claims per
    1,000 policy-years, and the observed rate's exact Poisson 95% interval."""
    order = np.argsort(expected / exposure, kind="stable")
    group = np.minimum((np.cumsum(exposure[order]) / exposure.sum() * GROUPS).astype(int), GROUPS - 1)
    rows = []
    for g in range(GROUPS):
        pick = order[group == g]
        years, e, a = exposure[pick].sum(), expected[pick].sum(), int(claims[pick].sum())
        low = stats.chi2.ppf(0.025, 2 * a) / 2 if a else 0.0
        high = stats.chi2.ppf(0.975, 2 * a + 2) / 2
        rows.append({"group": g + 1, "policy_years": float(years), "predicted": float(1000 * e / years),
                     "observed": float(1000 * a / years), "low_95": float(1000 * low / years),
                     "high_95": float(1000 * high / years), "claims": a})
    return rows


def glm(join, wind):
    t = join["table"]
    col = lambda name: t[name].to_numpy(zero_copy_only=False)
    X = design(col("construction"), col("roof_age"), col("deductible"), col("terrain"))
    fit = sm.GLM(col("claims"), X, family=sm.families.Poisson(), offset=np.log(col("exposure")) + wind["offset"]).fit()
    low, high = fit.conf_int().T
    groups = calibration(fit.mu, col("claims"), col("exposure"))
    return {"coefficients": [{"term": term, "estimate": float(b), "se": float(se), "low": float(lo), "high": float(hi)}
                             for term, b, se, lo, hi in zip(TERMS, fit.params, fit.bse, low, high)],
            "expected": fit.mu, "deviance": float(fit.deviance), "dispersion": float(fit.pearson_chi2 / fit.df_resid),
            "aic": float(fit.aic), "calibration": groups,
            "calibration_gap": max(abs(r["observed"] / r["predicted"] - 1) for r in groups)}


def view(out):
    rows = [{"term": c["term"], "estimate": c["estimate"], "95% low": c["low"], "95% high": c["high"],
             "relativity": float(np.exp(c["estimate"]))} for c in out["coefficients"]]
    return [
        ui.download("coefficients.csv", out["coefficients"], title="the fitted coefficients with standard errors and 95% intervals"),
        ui.metrics(),
        ui.table(rows, title="Coefficients (relativity = exp(estimate), against the base levels)"),
        ui.chart([r["predicted"] for r in out["calibration"]],
                 {"observed": [r["observed"] for r in out["calibration"]],
                  "observed = predicted": [r["predicted"] for r in out["calibration"]]},
                 kind={"observed": "scatter", "observed = predicted": "line"},
                 bands={"observed": ([r["low_95"] for r in out["calibration"]], [r["high_95"] for r in out["calibration"]])},
                 title="Calibration: observed against predicted frequency, in ten groups of equal exposure",
                 x_label="predicted claims per 1,000 policy-years", y_label="observed per 1,000"),
        ui.table(out["calibration"], title="Calibration groups", text=["group"]),
        ui.markdown(f"Pearson dispersion {out['dispersion']:.2f}: the claims vary "
                    + ("more than the rating factors and wind explain, the territory effect credibility will look for."
                       if out["dispersion"] > 1.05 else "about as a Poisson model expects.")),
    ]
