"""Each territory's experience against the GLM, shared by the options of `credibility`: what
was observed and expected, the blend a credibility Z makes of them, and the pictures."""
import numpy as np
import pyarrow as pa

from blocks import ui


def experience(join, glm):
    """m, the claims the GLM expects in each territory; A, those it had; X = A / m (the
    overall ratio where the GLM expects none); that overall ratio; and which have any."""
    t = join["territories"]
    m = np.bincount(join["table"]["territory_index"].to_numpy(), weights=glm["expected"], minlength=t.num_rows)
    A = t["claims"].to_numpy().astype(float)
    seen = m > 0
    mean = A.sum() / m.sum()
    return m, A, np.where(seen, A / np.where(seen, m, 1), mean), mean, seen


def blend(join, m, A, X, mean, Z, **numbers):
    """A credibility option's output: θ = Z · X + (1 − Z) · X̄ for every territory, and its own numbers."""
    t = join["territories"]
    return {"table": pa.table({"territory": t["territory"], "wkb": t["wkb"], "expected": m, "claims": A, "ratio": X, "z": Z,
                               "theta": Z * X + (1 - Z) * mean}),
            **numbers, "mean": float(mean), "mostly_own": int((Z >= 0.9).sum()), "mostly_glm": int((Z < 0.1).sum())}


def pictures(out):
    t = out["table"]
    m, X, theta, Z = (t[c].to_numpy() for c in ("expected", "ratio", "theta", "z"))
    seen = m > 0
    return [
        ui.map(t["wkb"], Z, names=t["territory"],
               title="Credibility by territory", label="Z"),
        ui.chart(m[seen], {"own experience A / m": X[seen], "credibility-weighted θ": theta[seen]}, kind="scatter",
                 title="Each territory's experience, and what credibility makes of it", x_label="expected claims",
                 x_scale="log", y_lines={"as the GLM expects": 1}),
    ]
