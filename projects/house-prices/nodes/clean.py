"""Keep one row per listing with a floor area, and give each its price per square metre.

A portal scrape repeats an advert, so a listing can appear more than once under different ids:
a row is a repeat when every field but its id matches an earlier row. A listing with no floor
area has no price per square metre, so it is left out and counted.
"""
import csv

import pyarrow as pa

from blocks import ui

METRICS = {"listings": "listings in the file", "repeats": "repeated rows dropped",
           "no_area": "listings with no area, dropped", "kept": "listings kept"}


def clean(listings):
    with open(listings, newline="") as f:
        rows = list(csv.DictReader(f))
    seen, kept, repeats, no_area = set(), [], 0, 0
    for r in rows:
        key = tuple(v for k, v in r.items() if k != "listing_id")
        if key in seen:
            repeats += 1
            continue
        seen.add(key)
        if not r["area_m2"]:
            no_area += 1
            continue
        kept.append((r["listing_id"], r["neighbourhood"], float(r["price"]), float(r["area_m2"])))
    table = pa.table({"listing_id": [k[0] for k in kept], "neighbourhood": [k[1] for k in kept],
                      "price": [k[2] for k in kept], "area_m2": [k[3] for k in kept],
                      "price_per_m2": [k[2] / k[3] for k in kept]})
    return {"table": table, "listings": len(rows), "repeats": repeats, "no_area": no_area, "kept": table.num_rows}


def view(out):
    t = out["table"]
    return [
        ui.metrics(),
        ui.markdown(f"{out['repeats']} repeated rows and {out['no_area']} listings with no area are left out, "
                    f"leaving {out['kept']:,} listings. Some prices per square metre are ten times too high or "
                    "too low: the histogram's far tails."),
        ui.histogram(t["price_per_m2"].to_pylist(), title="Every listing's price per square metre", x_label="price per m²"),
        ui.table(t, title="The listings kept, with their price per square metre", limit=200),
    ]
