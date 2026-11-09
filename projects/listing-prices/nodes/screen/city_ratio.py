"""Screen out a listing whose price per square metre is more than `factor` away from the city's.

The city's median price per square metre is the yardstick: a listing is kept if it lies between
the median divided by `factor` and the median times `factor`. A factor-of-10 error is far outside
any sensible band, and a real neighbourhood's value is within a few times the city's, so the
band catches the errors and little else. Too tight a band cuts real expensive or cheap
neighbourhoods; too loose a one lets the errors through.
"""
import statistics
from typing import Annotated

from blocks import Range, ui
from prices import split

METRICS = {"dropped": "listings screened out", "kept": "listings kept"}


def screen(clean, *, factor: Annotated[float, Range(2, 10, 0.5)] = 3.0):
    rows = clean["rows"]
    city = statistics.median(r["per_m2"] for r in rows)
    kept, dropped = split(rows, lambda r: city / factor <= r["per_m2"] <= city * factor)
    return {"rows": kept, "dropped": len(dropped), "kept": len(kept), "dropped_rows": dropped}


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"**{out['dropped']:,}** listings sit more than the setting's factor away from the city's median and are "
                    "screened out; each is listed below."),
        *([ui.table(out["dropped_rows"], title="Listings screened out", limit=200)] if out["dropped_rows"] else []),
    ]
