"""What the store-week panel's nodes share: the rows as arrays, the fixed-effects fit (store,
week and promotion effects on log sales, with its standard error clustered by store), the
outlier screen, and the page's picture of an estimate. Numpy only, as Pyodide has it.
"""
import numpy as np
import pyarrow as pa

from blocks import ui

WEEKS = 52
FLAG = 4.0                              # a store-week is flagged past this many robust standard deviations
WEEK_AXIS = list(range(1, WEEKS + 1))


def rows(t):
    """A store-week table as arrays: store as an index into names, week, promo, treated, sales and
    use (every row, unless an earlier node dropped some)."""
    names = sorted(set(t["store"].to_pylist()))
    index = {s: i for i, s in enumerate(names)}
    use = np.asarray(t["use"].to_numpy(), dtype=bool) if "use" in t.column_names else np.ones(t.num_rows, bool)
    return {"names": names, "store": np.array([index[s] for s in t["store"].to_pylist()]),
            "week": np.asarray(t["week"].to_numpy()), "promo": np.asarray(t["promo"].to_numpy(), dtype=float),
            "treated": np.asarray(t["treated"].to_numpy(), dtype=bool),
            "sales": np.asarray(t["sales"].to_numpy(), dtype=float), "use": use}


def fixed_effects(r, y, use):
    """y = a store effect + a week effect + β · promo, by least squares on the rows in use.
    Returns β, its standard error clustered by store, the fitted values and the promotion's part of
    them (every row, in use or not)."""
    stores = len(r["names"])
    X = np.column_stack([np.eye(stores)[r["store"]], np.eye(WEEKS)[r["week"] - 1][:, 1:], r["promo"]])
    beta = np.linalg.lstsq(X[use], y[use], rcond=None)[0]
    e = y - X @ beta
    bread = np.linalg.pinv(X[use].T @ X[use])
    meat = np.zeros((X.shape[1], X.shape[1]))
    for s in range(stores):
        m = use & (r["store"] == s)
        g = X[m].T @ e[m]
        meat += np.outer(g, g)
    V = bread @ meat @ bread
    return {"beta": float(beta[-1]), "se": float(np.sqrt(V[-1, -1])), "fitted": y - e, "promo_part": r["promo"] * beta[-1]}


def screen(r, k=FLAG):
    """Each row's log residual from the store, week and promotion effects fitted to every row, the
    robust scale of those residuals (1.4826 × their median absolute deviation), and the flags: the
    rows past k scales."""
    y = np.log(r["sales"])
    everything = np.ones(len(y), bool)
    e = y - fixed_effects(r, y, everything)["fitted"]
    scale = 1.4826 * np.median(np.abs(e - np.median(e)))
    return {"y": y, "resid": e, "scale": float(scale), "flag": np.abs(e) > k * scale}


def replace(t, **columns):
    """The table with these columns replaced or added (arrays, or pyarrow columns kept as they are)."""
    cols = {n: t[n] for n in t.column_names}
    cols.update({n: v if isinstance(v, (pa.Array, pa.ChunkedArray)) else pa.array(v) for n, v in columns.items()})
    return pa.table(cols)


def finish(t, r, s, use, sales, changed):
    """A clean option's output: the table with its use and sales, the flags, and the numbers the
    options share (how many are flagged, the largest flagged residual, how many were changed)."""
    flag, e = s["flag"], s["resid"]
    idx = np.flatnonzero(flag)
    idx = idx[np.argsort(-np.abs(e[idx]))]
    flags = pa.table({"store": [r["names"][i] for i in r["store"][idx]], "week": r["week"][idx],
                      "promo": r["promo"][idx].astype(int), "sales": r["sales"][idx], "log residual": e[idx]})
    return {"table": replace(t, use=use, sales=sales), "flagged": int(flag.sum()),
            "largest": float(np.abs(e[flag]).max()) if flag.any() else 0.0, "changed": int(changed),
            "flags": flags, "resid": e}


def week_means(r, mask, values):
    """The mean of values in each of the fifty-two weeks, over the rows in mask (NaN where none)."""
    out = np.full(WEEKS, np.nan)
    for w in range(1, WEEKS + 1):
        m = mask & (r["week"] == w)
        if m.any():
            out[w - 1] = values[m].mean()
    return out


def levels(v):
    """Weekly log values as sales (geometric means), with None where there are none: a chart's gap."""
    return [None if not np.isfinite(x) else float(np.exp(x)) for x in v]


def answer(gain, se, stores, r, y, use, without):
    """An estimate, as the page takes it. gain is the promotion's effect on log sales, with standard
    error se; without is the log of what the option expects the treated stores to sell in each week
    with no promotion. The output: the uplift as a share, its 95% interval, the treated stores' count,
    and the weekly sales, actual and without."""
    actual = week_means(r, r["treated"] & use, y)
    return {"uplift": float(np.exp(gain) - 1), "low": float(np.exp(gain - 1.96 * se) - 1),
            "high": float(np.exp(gain + 1.96 * se) - 1), "stores": int(stores),
            "weekly": {"actual": levels(actual), "without": levels(without)}}


def clean_view(out, note):
    """The page of a clean option: its numbers, what it did, the residuals and the flagged rows."""
    return [
        ui.metrics(),
        ui.markdown(note),
        ui.histogram(out["resid"], title="Every store-week's log residual from its store, week and promotion",
                     x_label="log residual", mark=0),
        ui.table(out["flags"], title="Flagged store-weeks, largest residual first", limit=50),
    ]


def estimate_view(out, note):
    """The page of an estimate option: the uplift, its interval, and the treated stores' weekly sales
    against what the option expects without the promotion."""
    w = out["weekly"]
    return [
        ui.metrics(),
        ui.markdown(f"Weekly sales in the treated stores rose by **{out['uplift']:.1%}** in the promotion weeks "
                    f"(95% interval {out['low']:.1%} to {out['high']:.1%}). {note}"),
        ui.chart(WEEK_AXIS, {"treated stores, actual": w["actual"], "without the promotion": w["without"]},
                 title="Weekly sales per treated store, actual and without the promotion", x_label="week",
                 y_label="sales per store"),
    ]
