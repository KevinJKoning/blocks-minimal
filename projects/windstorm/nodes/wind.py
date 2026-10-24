"""The physics offset: the wind load each home sees, from how far inland it is.

There is no claims-by-wind-speed data to fit this from, but the physics is well known. A
hurricane's wind decays as it moves inland, from the design speed at the coast towards a
background speed,

    v(d) = v_background + (v_coast − v_background) · exp(−d / decay)

and the load wind puts on a building grows with the square of its speed. So a home's wind
load relative to one on the coast is (v(d) / v_coast)². Its log enters the GLM as an
**offset**: a term whose coefficient is fixed at 1, so the model takes the physics as given
rather than estimating it from claims that cannot separate it from everything else.
"""
from typing import Annotated

import numpy as np
import shapely

from blocks import Range, ui

METRICS = {"mean_load": "mean relative wind load", "load_at_50km": "relative load 50 km inland"}


def wind(join, *, coast_speed: Annotated[float, Range(40, 80, 1)] = 60.0,
         background_speed: Annotated[float, Range(10, 40, 1)] = 25.0,
         decay_km: Annotated[float, Range(10, 100, 5)] = 40.0):
    def offset(d):
        speed = background_speed + (coast_speed - background_speed) * np.exp(-np.asarray(d) / decay_km)
        return 2 * np.log(speed / coast_speed)
    distance = np.linspace(0, 150, 151)
    return {"offset": offset(join["table"]["distance_km"].to_numpy()),
            "territory_offset": offset(join["territories"]["distance_km"].to_numpy()),
            "curve": {"distance_km": distance, "speed": background_speed + (coast_speed - background_speed) * np.exp(-distance / decay_km),
                      "load": np.exp(offset(distance))},
            "mean_load": float(np.exp(offset(join["table"]["distance_km"].to_numpy())).mean()),
            "load_at_50km": float(np.exp(offset(50)))}


def view(out):
    c = out["curve"]
    return [
        ui.metrics(),
        ui.chart(c["distance_km"], {"wind speed (m/s)": c["speed"]}, title="Design wind speed inland", x_label="km inland"),
        ui.chart(c["distance_km"], {"relative load": c["load"]}, title="Wind load relative to the coast", x_label="km inland"),
    ]
