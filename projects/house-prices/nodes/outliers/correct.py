"""Rescale a listing off the city's level by a factor of 10, and drop it if that is not enough.

The data's errors are factors of 10: a price typed with an extra zero, or an area ten times
too big or too small. A listing ten times above the level has its price per square metre
divided by 10; one ten times below, multiplied by 10. The rescaled value is kept only if it
then lies in the band; otherwise the listing is dropped.
"""
from typing import Annotated

import numpy as np
import pyarrow as pa

from blocks import Range, ui
from prices import off_band

METRICS = {"flagged": "listings off the city's level", "corrected": "corrected by a factor of 10",
           "dropped": "dropped", "kept": "listings kept"}


def outliers(clean, *, band: Annotated[float, Range(1.5, 10, 0.5)] = 4.0):
    b = off_band(clean, band)
    price = b["price_per_m2"].astype(float).copy()
    ratio = price / b["level"]
    high, low = b["off"] & (ratio > 1), b["off"] & (ratio < 1)
    price[high] /= 10
    price[low] *= 10
    still_off = b["off"] & ((price / b["level"] > band) | (price / b["level"] < 1 / band))
    keep = ~still_off
    corrected = b["off"] & ~still_off
    table = pa.table({"listing_id": [x for x, k in zip(b["listing_id"], keep) if k],
                      "neighbourhood": [x for x, k in zip(b["neighbourhood"], keep) if k],
                      "price_per_m2": price[keep],
                      "flag": ["corrected" if c else "ok" for c in corrected[keep]]})
    return {"table": table, "log_ratio": b["log_ratio"], "level": b["level"], "flagged": int(b["off"].sum()),
            "corrected": int(corrected.sum()), "dropped": int(still_off.sum()), "kept": table.num_rows}


def view(out):
    return [
        ui.metrics(),
        ui.histogram(out["log_ratio"], title="Every listing against the city's level, before correction",
                     x_label="log10 of price per m² over the city's level", mark=0),
    ]
