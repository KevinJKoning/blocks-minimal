"""No physics: every home is taken to see the same wind, however far inland it is.

The offset is zero everywhere, so the GLM knows nothing of distance to the coast. Whatever
the coast does to claims is then left for each territory's own experience to show, and
`credibility` to believe or not: a territory with little experience is rated as if it stood
anywhere.

This is what the analysis would be without the engineering argument: the option to beat.
"""
import numpy as np

from blocks import ui

METRICS = {"mean_load": "mean relative wind load", "load_at_50km": "relative load 50 km inland"}


def wind(join):
    distance = np.linspace(0, 150, 151)
    return {"offset": np.zeros(join["table"].num_rows), "territory_offset": np.zeros(join["territories"].num_rows),
            "curve": {"distance_km": distance, "load": np.ones_like(distance)}, "mean_load": 1.0, "load_at_50km": 1.0}


def view(out):
    c = out["curve"]
    return [
        ui.metrics(),
        ui.chart(c["distance_km"], {"relative load": c["load"]}, title="Wind load relative to the coast: the same everywhere",
                 x_label="km inland"),
    ]
