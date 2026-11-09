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

from blocks import Range, ui
from territories import blend, experience, pictures

METRICS = {"k": "credibility constant k (expected claims)", "between_sd": "between-territory sd",
           "mostly_own": "territories with Z ≥ 0.9", "mostly_glm": "territories with Z < 0.1"}


def credibility(join, glm, *, k: Annotated[float, Range(0, 500, 5)] = 0.0):
    m, A, X, mean, seen = experience(join, glm)
    M = m.sum()
    a = (np.sum(m * (X - mean) ** 2) - (seen.sum() - 1) * mean) / (M - np.sum(m ** 2) / M)
    k_used = k or (mean / a if a > 0 else float("inf"))
    return blend(join, m, A, X, mean, m / (m + k_used), k=float(k_used), between_sd=float(np.sqrt(max(a, 0))))


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"With k = {out['k']:.1f}, a territory where the GLM expects {out['k']:.0f} claims gets Z = 0.5: "
                    f"half its own experience, half the GLM. The true variation between territories is estimated "
                    f"at {out['between_sd']:.0%} of the rate."),
        *pictures(out),
    ]
