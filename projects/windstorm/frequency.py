"""The claim-frequency GLM, shared by the options of `glm`: the fit with a given family, the
calibration groups, and the view."""
import numpy as np
import statsmodels.api as sm
from scipy import stats

from blocks import ui
from rating import TERMS, design

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


def fit(join, wind, family=None):
    """The GLM's output with this family: family(mu) makes it from the Poisson fit's
    expected claims (None: the Poisson fit itself)."""
    t = join["table"]
    col = lambda name: t[name].to_numpy(zero_copy_only=False)
    X = design(col("construction"), col("roof_age"), col("deductible"), col("terrain"))
    offset = np.log(col("exposure")) + wind["offset"]
    fit = sm.GLM(col("claims"), X, family=sm.families.Poisson(), offset=offset).fit()
    if family:
        fit = sm.GLM(col("claims"), X, family=family(col("claims"), fit.mu), offset=offset).fit(start_params=fit.params)
    low, high = fit.conf_int().T
    groups = calibration(fit.mu, col("claims"), col("exposure"))
    return {"coefficients": [{"term": term, "estimate": float(b), "se": float(se), "low": float(lo), "high": float(hi)}
                             for term, b, se, lo, hi in zip(TERMS, fit.params, fit.bse, low, high)],
            "expected": fit.mu, "deviance": float(fit.deviance), "dispersion": float(fit.pearson_chi2 / fit.df_resid),
            "aic": float(fit.aic), "calibration": groups,
            "calibration_gap": max(abs(r["observed"] / r["predicted"] - 1) for r in groups)}


def show(out):
    rows = [{"term": c["term"], "estimate": c["estimate"], "95% low": c["low"], "95% high": c["high"],
             "relativity": float(np.exp(c["estimate"]))} for c in out["coefficients"]]
    groups, terms = out["calibration"], rows[1:]   # the intercept left out
    return [
        ui.download("coefficients.csv", out["coefficients"], title="the fitted coefficients with standard errors and 95% intervals"),
        ui.metrics(),
        ui.bars([r["term"] for r in terms], {"relativity": [r["relativity"] for r in terms]}, kind="dot",
                intervals={"relativity": ([np.exp(r["95% low"]) for r in terms], [np.exp(r["95% high"]) for r in terms])},
                reference=1, title="Relativities with 95% intervals (the intercept left out)", label="× the base level"),
        ui.table(rows, title="Coefficients (relativity = exp(estimate), against the base levels)"),
        ui.chart([r["predicted"] for r in groups],
                 {"observed": [r["observed"] for r in groups], "observed = predicted": [r["predicted"] for r in groups]},
                 kind={"observed": "scatter", "observed = predicted": "line"},
                 bands={"observed": ([r["low_95"] for r in groups], [r["high_95"] for r in groups])},
                 title="Calibration: observed against predicted frequency, in ten groups of equal exposure",
                 x_label="predicted claims per 1,000 policy-years", y_label="observed per 1,000"),
        ui.table(groups, title="Calibration groups", text=["group"]),
        ui.markdown(f"Pearson dispersion {out['dispersion']:.2f}: the claims vary "
                    + ("more than the rating factors and wind explain, the territory effect credibility will look for."
                       if out["dispersion"] > 1.05 else "about as the model expects.")),
    ]
