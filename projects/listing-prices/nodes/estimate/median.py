"""A neighbourhood's estimate is the median of its listings' prices per square metre.

The median is set by where a listing falls among the others, not how far it is, so a listing
that survived screening but is still wrong moves it only by one place. The city's median is also
recorded here, for the pooling step.
"""
import statistics

from blocks import ui
from prices import by_neighbourhood

METRICS = {"city": "city-wide median per m²", "neighbourhoods": "neighbourhoods estimated",
           "listings_used": "listings the estimates use"}


def estimate(screen):
    groups = by_neighbourhood(screen["rows"])
    table = [{"neighbourhood": n, "listings": len(v), "estimate": statistics.median(v)} for n, v in groups.items()]
    return {"table": table, "city": statistics.median(r["per_m2"] for r in screen["rows"]),
            "neighbourhoods": len(table), "listings_used": len(screen["rows"])}


def view(out):
    t = out["table"]
    return [
        ui.download("estimates.csv", t, title="every neighbourhood's estimate, with its listings"),
        ui.metrics(),
        ui.bars([r["neighbourhood"] for r in t], {"median": [r["estimate"] for r in t]}, kind="dot",
                label="price per m²", reference=out["city"], title="Each neighbourhood's median price per square metre, "
                                                                    "against the city's median (the dashed line)"),
        ui.table(t, title="Estimates by neighbourhood", limit=200),
    ]
