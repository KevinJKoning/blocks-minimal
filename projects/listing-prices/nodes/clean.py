"""Read the listings, and set aside what cannot be priced: a listing with no area, and a repost.

A listing with no area has no price per square metre. A repost is the same neighbourhood,
month, price and area under another listing_id; the first is kept. Neither is a judgment
call: both would only distort the answer.
"""
import math

from blocks import ui
from prices import read

METRICS = {"listings": "listings in the file", "no_area": "without an area",
           "repeats": "reposts of another listing", "kept": "listings that can be priced"}


def clean(listings):
    rows = read(listings)
    seen, kept = set(), []
    for r in rows:
        if not r["area_m2"]:
            continue
        key = (r["neighbourhood"], r["listed"], r["price"], r["area_m2"])
        if key in seen:
            continue
        seen.add(key)
        kept.append({**r, "per_m2": r["price"] / r["area_m2"]})
    no_area = sum(r["area_m2"] is None for r in rows)
    return {"rows": kept, "listings": len(rows), "no_area": no_area,
            "repeats": len(rows) - no_area - len(kept), "kept": len(kept)}


def view(out):
    rows = out["rows"]
    return [
        ui.download("priced_listings.csv", rows, title="every listing that can be priced, with its price per square metre"),
        ui.metrics(),
        ui.markdown(f"**{out['kept']:,}** of {out['listings']:,} listings can be priced. The price per square metre runs from "
                    f"**{min(r['per_m2'] for r in rows):,.0f}** to **{max(r['per_m2'] for r in rows):,.0f}**: the spread is "
                    "wider than the neighbourhoods' true values, because of the factor-of-10 errors still in it."),
        ui.histogram([math.log10(r["per_m2"]) for r in rows], x_label="log10 of price per m²",
                     title="Every listing's price per square metre, on a log scale: the errors sit far out in both tails"),
        ui.table(rows, title="Listings that can be priced", limit=200),
    ]
