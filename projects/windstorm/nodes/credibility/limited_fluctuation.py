"""Classical credibility: a territory counts in full once it is big enough to be stable.

Limited-fluctuation credibility asks how many claims a territory needs for its observed
frequency to be within 5% of its true one, 90% of the time. For Poisson claims that is
(1.645 / 0.05)² ≈ 1,082 expected claims, the **full credibility standard**. Below it,
credibility follows the square-root rule:

    Z = min(1, √(m / standard)),   θ = Z · X + (1 − Z) · X̄

It is the rule many rate filings still use. It looks only at how noisy a territory's own
experience is, never at how much territories truly differ, so it does not know whether
leaning on the GLM is safe.
"""
from typing import Annotated

import numpy as np

from blocks import Range, ui
from territories import blend, experience, pictures

METRICS = {"full_standard": "full credibility standard (expected claims)", "largest_z": "largest Z",
           "mostly_own": "territories with Z ≥ 0.9", "mostly_glm": "territories with Z < 0.1"}


def credibility(join, glm, *, full_standard: Annotated[float, Range(100, 3000, 1)] = 1082.0):
    m, A, X, mean, seen = experience(join, glm)
    Z = np.minimum(1, np.sqrt(m / full_standard))
    return blend(join, m, A, X, mean, Z, full_standard=float(full_standard), largest_z=float(Z.max()))


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"No territory comes near {out['full_standard']:,.0f} expected claims: the most credible gets "
                    f"Z = {out['largest_z']:.2f}." if out["largest_z"] < 1 else
                    f"Territories with {out['full_standard']:,.0f} expected claims or more are rated on their own experience."),
        *pictures(out),
    ]
