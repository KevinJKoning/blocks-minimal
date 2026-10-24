"""Extend the seasonal model `horizon` months past the last month of history.

Each month's point forecast is the fitted trend plus its seasonal level. Its 80% prediction
interval is ± t₀.₉ · σ · √(1 + x′(X′X)⁻¹x), on the fit's degrees of freedom: the noise of a
new month plus the uncertainty in the fitted coefficients, which grows the further the
trend is extrapolated. The forecast is delivered as a CSV, one row per month.
"""
from typing import Annotated

import numpy as np
from scipy import stats

from blocks import Range, ui
from seasonal import design

LEVEL = 0.80
METRICS = {"months_ahead": "months forecast", "total_gwh": "total forecast (GWh)",
           "mean_width": {"label": "mean 80% interval width (GWh)", "goal": "min"}}


def forecast(history, fit, *, horizon: Annotated[int, Range(1, 60, 1)] = 24):
    n = len(history["gwh"])
    t = np.arange(n, n + horizon)
    X = design(t, fit["season_length"])
    point = X @ fit["coef"]
    se = fit["sigma"] * np.sqrt(1 + np.einsum("ij,jk,ik->i", X, fit["xtx_inv"], X))
    half = stats.t.ppf(0.5 + LEVEL / 2, fit["dof"]) * se
    y0, m0 = map(int, history["month"][-1].split("-"))
    month = [f"{y0 + (m0 - 1 + k) // 12}-{(m0 - 1 + k) % 12 + 1:02d}" for k in range(1, horizon + 1)]
    return {"table": {"month": month, "forecast_gwh": point.round(1), "lower_80_gwh": (point - half).round(1),
                      "upper_80_gwh": (point + half).round(1)},
            "year": history["year"][-1] + np.arange(1, horizon + 1) / 12,
            "history_year": history["year"], "history_gwh": history["gwh"],
            "months_ahead": horizon, "total_gwh": float(point.sum()), "mean_width": float(2 * half.mean())}


def view(out):
    tb = out["table"]
    n, k = len(out["history_year"]), out["months_ahead"]
    x = np.concatenate([out["history_year"], out["year"]])
    pad = np.full(n, np.nan)
    return [
        ui.download("forecast.csv", tb, title=f"{k} months of forecast demand with the 80% prediction interval"),
        ui.metrics(),
        ui.markdown(f"From {tb['month'][0]} to {tb['month'][-1]}: {out['total_gwh']:,.0f} GWh in all. The shaded band is "
                    f"the 80% prediction interval, {out['mean_width']:.0f} GWh wide on average: about four months in five "
                    "should fall inside it."),
        ui.chart(x, {"history": np.concatenate([out["history_gwh"], np.full(k, np.nan)]),
                     "forecast": np.concatenate([pad, tb["forecast_gwh"]])},
                 bands={"forecast": (np.concatenate([pad, tb["lower_80_gwh"]]), np.concatenate([pad, tb["upper_80_gwh"]]))},
                 title="Forecast with its 80% prediction interval", x_label="year", y_label="GWh", x_text=True),
        ui.table(tb, title="Forecast"),
    ]
