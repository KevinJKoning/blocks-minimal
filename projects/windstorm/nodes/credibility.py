"""Blend each territory's own experience with the GLM: Bühlmann–Straub credibility.

For a territory with A claims where the GLM expects m, its experience says the GLM is off
by X = A / m. Credibility trusts that in proportion to how much experience there is:

    Z = m / (m + k),   θ = Z · X + (1 − Z) · X̄

A territory with many expected claims keeps close to its own experience (Z near 1); one
with a handful is predicted by the GLM (Z near 0). The constant k is the ratio of the noise
within a territory (Poisson: X̄) to the true variation between territories (a), both
estimated from the data:

    a = (Σ m (X − X̄)² − (n − 1) · X̄) / (M − Σ m² / M),   k = X̄ / a

where M is the total expected claims. Set `k` to override the estimate (0 estimates it).
"""
from typing import Annotated

import numpy as np
import pyarrow as pa
import shapely

from blocks import Range, ui

METRICS = {"k": "credibility constant k (expected claims)", "between_sd": "between-territory sd",
           "mostly_own": "territories with Z ≥ 0.9", "mostly_glm": "territories with Z < 0.1"}


def credibility(join, glm, *, k: Annotated[float, Range(0, 500, 5)] = 0.0):
    t = join["territories"]
    m = np.bincount(join["table"]["territory_index"].to_numpy(), weights=glm["expected"], minlength=t.num_rows)
    A = t["claims"].to_numpy().astype(float)
    seen = m > 0
    mean = A.sum() / m.sum()
    X = np.where(seen, A / np.where(seen, m, 1), mean)
    M = m.sum()
    a = (np.sum(m * (X - mean) ** 2) - (seen.sum() - 1) * mean) / (M - np.sum(m ** 2) / M)
    k_used = k or (mean / a if a > 0 else float("inf"))
    Z = m / (m + k_used)
    return {"table": pa.table({"territory": t["territory"], "wkb": t["wkb"], "expected": m, "claims": A, "ratio": X, "z": Z,
                               "theta": Z * X + (1 - Z) * mean}),
            "k": float(k_used), "between_sd": float(np.sqrt(max(a, 0))), "mean": float(mean),
            "mostly_own": int((Z >= 0.9).sum()), "mostly_glm": int((Z < 0.1).sum())}


def view(out):
    t = out["table"]
    m, X, theta, Z = (t[c].to_numpy() for c in ("expected", "ratio", "theta", "z"))
    seen = m > 0
    return [
        ui.metrics(),
        ui.markdown(f"With k = {out['k']:.1f}, a territory where the GLM expects {out['k']:.0f} claims gets Z = 0.5: "
                    f"half its own experience, half the GLM. The true variation between territories is estimated "
                    f"at {out['between_sd']:.0%} of the rate."),
        ui.map(shapely.from_wkb(t["wkb"].to_numpy(zero_copy_only=False)), Z, names=t["territory"].to_pylist(),
               title="Credibility by territory", label="Z"),
        ui.chart(np.log10(m[seen]), {"own experience A / m": X[seen], "credibility-weighted θ": theta[seen]}, kind="scatter",
                 title="Each territory's experience, and what credibility makes of it", x_label="log₁₀ expected claims"),
    ]
