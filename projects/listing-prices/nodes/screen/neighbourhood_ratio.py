"""Screen out a listing whose price per square metre is more than `factor` away from its own neighbourhood's.

The yardstick is the neighbourhood's own median, so the band follows each neighbourhood's
level, and a listing is kept if it lies between that median divided by `factor` and that median
times `factor`. It cannot be fooled by a city-wide error, but it leans on the neighbourhood's
own listings: with five or so of them, one or two errors can move the median they are judged
by.
"""
import statistics
from typing import Annotated

from blocks import Range, ui
from prices import by_neighbourhood, split

METRICS = {"dropped": "listings screened out", "kept": "listings kept"}


def screen(clean, *, factor: Annotated[float, Range(2, 10, 0.5)] = 3.0):
    rows = clean["rows"]
    median = {n: statistics.median(v) for n, v in by_neighbourhood(rows).items()}
    kept, dropped = split(rows, lambda r: median[r["neighbourhood"]] / factor <= r["per_m2"] <= median[r["neighbourhood"]] * factor)
    return {"rows": kept, "dropped": len(dropped), "kept": len(kept), "dropped_rows": dropped}


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"**{out['dropped']:,}** listings sit more than the setting's factor away from their own neighbourhood's "
                    "median and are screened out; each is listed below."),
        *([ui.table(out["dropped_rows"], title="Listings screened out", limit=200)] if out["dropped_rows"] else []),
    ]
