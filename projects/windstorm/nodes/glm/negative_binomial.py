"""A negative binomial GLM of claim frequency: Poisson, with room for extra variation.

    claims ~ NegBin(mean μ = exposure · load · exp(Xβ), variance μ + α μ²)

The same rating factors, link and offset as the Poisson option. A Poisson model's variance
equals its mean; claims that share an unmodelled cause (here, their territory) vary more,
and the negative binomial gives that a parameter, α, which widens the intervals and weighs
the large-mean policies a little less. α is estimated by moments from the Poisson fit's
expected claims μ, α = Σ((y − μ)² − μ) / Σ μ², and then held fixed.

With about 0.03 claims per policy, α μ² is tiny beside μ: expect nearly the Poisson answer.
"""
import numpy as np
import statsmodels.api as sm

from frequency import fit, show

METRICS = {"deviance": {"label": "deviance", "goal": "min"},
           "dispersion": {"label": "Pearson dispersion", "goal": "min"}, "aic": {"label": "AIC", "goal": "min"},
           "alpha": "overdispersion α",
           "calibration_gap": {"label": "worst group's observed / predicted − 1", "goal": "min"}}


def overdispersion(y, mu):
    return max(float(np.sum((y - mu) ** 2 - mu) / np.sum(mu ** 2)), 1e-8)


def glm(join, wind):
    alpha = []   # the family is made from the Poisson fit: keep the α it was given
    out = fit(join, wind, lambda y, mu: alpha.append(overdispersion(y, mu)) or sm.families.NegativeBinomial(alpha=alpha[0]))
    return {**out, "alpha": alpha[0]}


def view(out):
    return show(out)
