"""Fit a simple seasonal model to the history by least squares.

    demand(t) = trend · t + level[t mod season_length] + noise

A straight line for load growth and one level for each position in the season (with
`season_length` 12, one per calendar month), fitted in closed form. The residual standard
deviation, on the model's degrees of freedom, is what the forecast's interval is built
from. A season length that does not match the data's (try 6 or 11) shows at once as a
worse fit and wider intervals.
"""
from typing import Annotated

import numpy as np

from blocks import Range, ui
from seasonal import design

METRICS = {
    "rmse": {"label": "in-sample RMSE (GWh)", "goal": "min"},
    "mape": {"label": "in-sample MAPE", "goal": "min"},
    "sigma": {"label": "residual sd (GWh)", "goal": "min"},
    "trend_per_year": "trend (GWh per year)",
}


def fit(history, *, season_length: Annotated[int, Range(2, 24, 1)] = 12):
    y = history["gwh"]
    t = np.arange(len(y))
    X = design(t, season_length)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ coef
    resid = y - fitted
    dof = len(y) - X.shape[1]
    return {"coef": coef, "xtx_inv": np.linalg.pinv(X.T @ X), "dof": dof, "season_length": season_length,
            "fitted": fitted, "resid": resid,
            "rmse": float(np.sqrt(np.mean(resid ** 2))), "mape": float(np.mean(np.abs(resid / y))),
            "sigma": float(np.sqrt(resid @ resid / dof)), "trend_per_year": float(coef[0] * 12),
            "year": history["year"], "gwh": y}


def view(out):
    m = out["season_length"]
    return [
        ui.metrics(),
        ui.markdown(f"A trend of {out['trend_per_year']:.1f} GWh a year and {m} seasonal levels; the fit is off by "
                    f"{out['rmse']:.1f} GWh a month on average (RMSE), {out['mape']:.1%} of demand."),
        ui.chart(out["year"], {"demand": out["gwh"], "fitted": out["fitted"]},
                 kind={"demand": "scatter", "fitted": "line"}, title="Fit against history", x_label="year", y_label="GWh", x_text=True),
        ui.chart(out["year"], {"residual": out["resid"]}, kind="scatter", title="Residuals", x_label="year", y_label="GWh", x_text=True),
        ui.table({"position in season": np.arange(1, m + 1), "level (GWh)": out["coef"][1:]}, title="Seasonal levels"),
    ]
