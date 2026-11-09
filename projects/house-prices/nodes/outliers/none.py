"""Keep every listing as it is: no outlier is looked for.

The option to beat. A listing ten times off the city's level counts in its neighbourhood's
estimate as if it were true, and a neighbourhood with a handful of listings feels it most.
"""
from typing import Annotated

import pyarrow as pa

from blocks import Range, ui
from prices import off_band

METRICS = {"flagged": "listings off the city's level", "corrected": "corrected by a factor of 10",
           "dropped": "dropped", "kept": "listings kept"}


def outliers(clean, *, band: Annotated[float, Range(1.5, 10, 0.5)] = 4.0):
    b = off_band(clean, band)
    flag = ["off" if o else "ok" for o in b["off"]]
    table = pa.table({"listing_id": b["listing_id"], "neighbourhood": b["neighbourhood"],
                      "price_per_m2": b["price_per_m2"], "flag": flag})
    return {"table": table, "log_ratio": b["log_ratio"], "level": b["level"], "flagged": int(b["off"].sum()),
            "corrected": 0, "dropped": 0, "kept": table.num_rows}


def view(out):
    return [
        ui.metrics(),
        ui.histogram(out["log_ratio"], title="Every listing against the city's level", x_label="log10 of price per m² over the city's level",
                     mark=0),
    ]
