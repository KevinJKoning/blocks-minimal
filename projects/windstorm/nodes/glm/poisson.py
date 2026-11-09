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
from frequency import fit, show

METRICS = {"deviance": {"label": "deviance", "goal": "min"},
           "dispersion": {"label": "Pearson dispersion", "goal": "min"}, "aic": {"label": "AIC", "goal": "min"},
           "calibration_gap": {"label": "worst group's observed / predicted − 1", "goal": "min"}}


def glm(join, wind):
    return fit(join, wind)


def view(out):
    return show(out)
