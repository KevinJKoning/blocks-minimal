"""Every parcel's planar area, with slivers dropped.

Computes each polygon's area with shapely, in the layer's coordinate system. Parcels
smaller than `min_area_m2` are slivers left by digitizing and are dropped.
"""
from typing import Annotated

import pyarrow as pa
import pyarrow.compute as pc
import shapely

from blocks import Range, ui

METRICS = {"parcels": "parcels kept", "slivers_dropped": "slivers dropped"}


def areas(layer, *, min_area_m2: Annotated[int, Range(0, 5000, 100)] = 1000):
    table = layer["table"]
    area = shapely.area(shapely.from_wkb(table["geometry"].to_numpy(zero_copy_only=False)))
    keep = pa.array(area >= min_area_m2)
    kept = pa.table({"land_use": pc.filter(table["LANDUSE"], keep),
                     "assessed": pc.filter(pc.fill_null(table["ASSESSED"], 0), keep),
                     "area_m2": pa.array(area[area >= min_area_m2]), "geometry": pc.filter(table["geometry"], keep)})
    return {"table": kept, "parcels": kept.num_rows, "slivers_dropped": len(area) - kept.num_rows, "crs": layer["crs"]}


def view(out):
    t = out["table"]
    return [
        ui.metrics(),
        ui.markdown(f"Areas in EPSG:{out['crs']} square metres; {out['slivers_dropped']} slivers dropped."),
        ui.map(t["geometry"], t["land_use"], title="Parcels kept, by land use"),
        ui.histogram(t["area_m2"], title="Parcels by area", x_label="area (m²)"),
        ui.table(t.drop_columns(["geometry"]), title="Parcels kept"),
    ]
