"""Place every policy in its territory and measure how far inland it is.

The policies are a table of points; the territories are polygons. A spatial join puts each
policy in the territory that contains it, and its distance to the coastline is measured in
metres, in the data's own projection. This is the one dataset every later node analyses.

A policy can lie just outside every territory: the territories' coastal edges are drawn
with fewer points than the coastline itself, so a sliver of beach belongs to none. Such a
policy is given to the nearest territory, and counted.
"""
import json

import numpy as np
import pyarrow as pa
import pyarrow.csv as csv
import shapely

from blocks import ui

METRICS = {"policies": "policies", "policy_years": "policy-years", "claims": "claims",
           "placed_by_nearest": "placed in the nearest territory", "thin_territories": "territories under 25 policy-years"}


def join(policies, territories, coast):
    table = csv.read_csv(policies)
    with open(territories) as f:
        features = json.load(f)["features"]
    with open(coast) as f:
        line = shapely.geometry.shape(json.load(f)["geometry"])
    polygons = np.array([shapely.geometry.shape(f["geometry"]) for f in features])
    ids = np.array([f["properties"]["territory"] for f in features])
    terrain = np.array([f["properties"]["terrain"] for f in features])

    points = shapely.points(table["x"].to_numpy(), table["y"].to_numpy())
    tree = shapely.STRtree(polygons)
    which = np.full(len(points), -1)
    inside, territory = tree.query(points, predicate="within")
    which[inside] = territory
    outside = np.flatnonzero(which < 0)
    which[outside] = tree.nearest(points[outside])

    exposure, claims = table["exposure"].to_numpy(), table["claims"].to_numpy()
    years = np.bincount(which, weights=exposure, minlength=len(ids))
    table = (table.append_column("territory", pa.array(ids[which])).append_column("territory_index", pa.array(which))
             .append_column("terrain", pa.array(terrain[which]))
             .append_column("distance_km", pa.array(shapely.distance(points, line) / 1000)))
    return {
        "table": table,
        "territories": pa.table({"territory": ids, "terrain": terrain, "policy_years": years,
                                 "claims": np.bincount(which, weights=claims, minlength=len(ids)).astype(int),
                                 "distance_km": shapely.distance(shapely.centroid(polygons), line) / 1000,
                                 "wkb": shapely.to_wkb(polygons)}),
        "coast": shapely.to_wkb(line),
        "policies": table.num_rows, "policy_years": float(exposure.sum()), "claims": int(claims.sum()),
        "placed_by_nearest": len(outside), "thin_territories": int((years < 25).sum()),
    }


def view(out):
    t = out["territories"]
    years = t["policy_years"].to_numpy()
    return [
        ui.metrics(),
        ui.markdown(f"Territories range from {years.min():,.0f} to {years.max():,.0f} policy-years (median "
                    f"{np.median(years):,.0f}): a few are large enough to rate on their own experience, and "
                    f"{out['thin_territories']} have under 25 policy-years, too few to say anything alone."),
        ui.map(t["wkb"], years, names=t["territory"], lines=[out["coast"]], scale="log",
               title="Policy-years by territory", label="policy-years"),
        ui.table(out["table"], title="The joined data, one row per policy"),
    ]
