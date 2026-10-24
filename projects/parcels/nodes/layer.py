"""Read the Parcels feature class from the zipped file geodatabase.

The parcels arrive the way GIS teams share them: a `Parcels.gdb/` folder zipped on Windows.
GDAL (bundled with fiona) reads the `name` feature class straight from the zip; each
feature's attributes become columns and its polygon becomes WKB.
"""
import zipfile

import fiona
import pyarrow as pa
import shapely

METRICS = {"features": "features read"}


def layer(parcels, *, name="Parcels"):
    gdb = next(n.split(".gdb/")[0] + ".gdb" for n in zipfile.ZipFile(parcels).namelist() if ".gdb/" in n)
    with fiona.open(f"zip://{parcels}!{gdb}", layer=name) as src:
        rows = [{**dict(f.properties), "geometry": shapely.to_wkb(shapely.geometry.shape(f.geometry))} for f in src]
        crs = src.crs.to_epsg()
    return {"table": pa.Table.from_pylist(rows), "features": len(rows), "crs": crs}
