"""A neighbourhood's estimate is the mean of its listings' prices per square metre.

Every listing counts equally, so a listing that survived screening but is still wrong moves the
mean by its full amount. The city's median is also recorded here, for the pooling step.
"""
import statistics

from blocks import ui
from prices import by_neighbourhood

METRICS = {"city": "city-wide median per m²", "neighbourhoods": "neighbourhoods estimated",
           "listings_used": "listings the estimates use"}


def estimate(screen):
    groups = by_neighbourhood(screen["rows"])
    table = [{"neighbourhood": n, "listings": len(v), "estimate": statistics.fmean(v)} for n, v in groups.items()]
    return {"table": table, "city": statistics.median(r["per_m2"] for r in screen["rows"]),
            "neighbourhoods": len(table), "listings_used": len(screen["rows"])}


def view(out):
    t = out["table"]
    return [
        ui.download("estimates.csv", t, title="every neighbourhood's estimate, with its listings"),
        ui.metrics(),
        ui.bars([r["neighbourhood"] for r in t], {"mean": [r["estimate"] for r in t]}, kind="dot",
                label="price per m²", reference=out["city"], title="Each neighbourhood's mean price per square metre, "
                                                                  "against the city's median (the dashed line)"),
        ui.table(t, title="Estimates by neighbourhood", limit=200),
    ]
