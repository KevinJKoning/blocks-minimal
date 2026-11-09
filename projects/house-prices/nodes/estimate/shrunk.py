"""Each neighbourhood's estimate: its median pulled toward the city-wide median, more the fewer listings it has.

A neighbourhood with n listings gets the weight n / (n + shrink) on its own median and the rest on
the city's, so with shrink 5 a neighbourhood of five listings gets half its own median. This
trades bias for noise: it helps where neighbourhoods sit near the city's level, and hurts where
they do not.
"""
from typing import Annotated

from blocks import Range
from prices import estimates, neighbourhoods, show_estimates

METRICS = {"neighbourhoods": "neighbourhoods estimated", "city_level": "city-wide median price per m²",
           "thinnest": "fewest listings in a neighbourhood"}


def estimate(outliers, *, shrink: Annotated[float, Range(0, 20, 1)] = 5.0):
    rows, n, med, city = neighbourhoods(outliers)
    w = n / (n + shrink)
    return estimates(rows, n, med, w * med + (1 - w) * city, city)


def view(out):
    return show_estimates(out)
