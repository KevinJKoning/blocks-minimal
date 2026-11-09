"""Each neighbourhood's typical price per square metre: the median of its own kept listings.

The median is the middle listing's price per square metre, so one listing still wrong moves it
little. Nothing is borrowed from the rest of the city: a neighbourhood with three listings is
estimated from those three.
"""
from prices import estimates, neighbourhoods, show_estimates

METRICS = {"neighbourhoods": "neighbourhoods estimated", "city_level": "city-wide median price per m²",
           "thinnest": "fewest listings in a neighbourhood"}


def estimate(outliers):
    rows, n, med, city = neighbourhoods(outliers)
    return estimates(rows, n, med, med, city)


def view(out):
    return show_estimates(out)
