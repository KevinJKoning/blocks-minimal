"""Drop every listing off the city's level, and keep the rest.

Safe: a listing that might be wrong is taken out whole. The cost is a neighbourhood with few
listings may lose most of them, and a real outlier that was only a little off stays in.
"""
from typing import Annotated

import pyarrow as pa

from blocks import Range, ui
from prices import off_band

METRICS = {"flagged": "listings off the city's level", "corrected": "corrected by a factor of 10",
           "dropped": "dropped", "kept": "listings kept"}


def outliers(clean, *, band: Annotated[float, Range(1.5, 10, 0.5)] = 4.0):
    b = off_band(clean, band)
    keep = ~b["off"]
    table = pa.table({"listing_id": [x for x, k in zip(b["listing_id"], keep) if k],
                      "neighbourhood": [x for x, k in zip(b["neighbourhood"], keep) if k],
                      "price_per_m2": b["price_per_m2"][keep], "flag": ["ok"] * int(keep.sum())})
    return {"table": table, "log_ratio": b["log_ratio"], "level": b["level"], "flagged": int(b["off"].sum()),
            "corrected": 0, "dropped": int(b["off"].sum()), "kept": table.num_rows}


def view(out):
    return [
        ui.metrics(),
        ui.histogram(out["log_ratio"], title="Every listing against the city's level (the dropped ones are the far tails)",
                     x_label="log10 of price per m² over the city's level", mark=0),
    ]
