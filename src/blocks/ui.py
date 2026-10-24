"""UI blocks. A block is a plain dict {"type": ..., ...}; a node's view(out) returns a list
of them and the page draws each with the renderer of the same name (templates/app.js,
RENDER). Adding a block type is one function here and one renderer there.
"""
from __future__ import annotations

import base64
import io
import json
import os

MAX_ROWS = 200      # a table shows at most this many rows (the total is kept)
MAX_POINTS = 5000   # a chart series keeps at most this many points


def plain(v):
    """numpy, pandas and pyarrow values as plain Python (JSON) values."""
    if hasattr(v, "to_pylist"):
        return v.to_pylist()
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    return v


def tabulate(rows, columns=None) -> tuple[list[str], list[list]]:
    """(columns, rows) of anything table-like: pyarrow, pandas, {column: values}, dicts, rows."""
    if hasattr(rows, "to_pydict"):
        d = rows.to_pydict()
        return list(d), [list(r) for r in zip(*d.values())]
    if hasattr(rows, "itertuples"):
        return [str(c) for c in rows.columns], [list(r) for r in rows.itertuples(index=False)]
    if isinstance(rows, dict):
        return [str(c) for c in rows], [list(r) for r in zip(*(plain(list(v)) for v in rows.values()))]
    rows = list(rows)
    if rows and isinstance(rows[0], dict):
        columns = columns or list(dict.fromkeys(k for r in rows for k in r))
        return [str(c) for c in columns], [[r.get(c) for c in columns] for r in rows]
    return list(columns or [f"c{i + 1}" for i in range(len(rows[0]) if rows else 0)]), [list(r) for r in rows]


def _block(type, **fields):
    return {"type": type, **{k: v for k, v in fields.items() if v is not None}}


def markdown(text):
    return _block("markdown", text=str(text))


def metrics(values=None, title=None):
    """Without values: the node's numbers, labelled by its METRICS (filled in by the graph)."""
    return _block("metrics", values=plain(values), title=title)


def table(rows, columns=None, title=None):
    cols, data = tabulate(rows, columns)
    return _block("table", title=title, columns=cols, rows=plain(data[:MAX_ROWS]), total=len(data))


def chart(x, series, title=None, x_label=None, y_label=None, kind="line"):
    """series: {name: ys} over a shared x; kind: "line", "scatter" or {name: kind}."""
    pick = (lambda n: kind.get(n, "line")) if isinstance(kind, dict) else (lambda n: kind)
    return _block("chart", title=title, x=plain(list(x))[:MAX_POINTS], x_label=x_label, y_label=y_label,
                  series=[{"name": str(n), "y": plain(list(ys))[:MAX_POINTS], "kind": pick(n)} for n, ys in series.items()])


def figure(image, caption=None):
    """SVG text, or PNG bytes (e.g. matplotlib's savefig into a BytesIO)."""
    if isinstance(image, (bytes, bytearray)):
        return _block("figure", media="image/png", data=base64.b64encode(bytes(image)).decode(), caption=caption)
    return _block("figure", media="image/svg+xml", data=str(image), caption=caption)


def _rings(geometry):
    """The rings (polygons) or paths (lines) of a shapely geometry or a GeoJSON geometry dict."""
    g = getattr(geometry, "__geo_interface__", geometry)
    kind, c = g["type"], g["coordinates"]
    parts = {"Polygon": [c], "MultiPolygon": c, "LineString": [[c]], "MultiLineString": [[line] for line in c]}.get(kind)
    if parts is None:
        raise ValueError(f"ui.map draws polygons and lines, not {kind}")
    return [[(float(p[0]), float(p[1])) for p in ring] for part in parts for ring in part]


def map(shapes, values=None, names=None, title=None, label=None, lines=None, points=None):  # noqa: A001 - ui.map reads best
    """Polygons (shapely geometries or GeoJSON geometry dicts) coloured by values, in their
    own coordinates (a projected CRS draws true to scale). lines: geometries drawn on top,
    such as a coastline; points: (xs, ys) drawn as dots (at most MAX_POINTS)."""
    shapes, lines = [_rings(s) for s in shapes], [_rings(g) for g in lines or []]
    xs, ys = zip(*(p for s in shapes for r in s for p in r))
    bounds = [min(xs), min(ys), max(xs), max(ys)]
    digits = max(0, 4 - len(str(int(max(bounds[2] - bounds[0], bounds[3] - bounds[1], 1)))))   # about 1/10,000 of the extent
    rnd = lambda rings: [[[round(x, digits), round(y, digits)] for x, y in r] for r in rings]
    return _block("map", title=title, label=label, bounds=bounds, shapes=[rnd(s) for s in shapes], lines=[rnd(g) for g in lines],
                  values=plain(list(values)) if values is not None else None, names=[str(n) for n in names] if names is not None else None,
                  points=[[round(float(x), digits), round(float(y), digits)] for x, y in zip(*points)][:MAX_POINTS] if points is not None else None)


TYPES = {".csv": "text/csv", ".json": "application/json", ".md": "text/markdown", ".txt": "text/plain",
         ".parquet": "application/vnd.apache.parquet", ".svg": "image/svg+xml", ".png": "image/png"}


def download(name, value, title=None):
    """A file to take away, by extension: a table as .csv, .json or .parquet; text; bytes."""
    ext = os.path.splitext(name)[1].lower()
    if isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    elif isinstance(value, str):
        data = value.encode()
    elif ext == ".parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq
        cols, rows = tabulate(value)
        buf = io.BytesIO()
        pq.write_table(pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)}), buf)
        data = buf.getvalue()
    elif ext == ".csv":
        import csv
        cols, rows = tabulate(value)
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        w.writerow(cols)
        w.writerows([["" if x is None or x != x else x for x in r] for r in plain(rows)])
        data = out.getvalue().encode()
    else:
        data = json.dumps(plain(value), indent=1, default=str).encode()
    return _block("download", name=str(name), title=title, media=TYPES.get(ext, "application/octet-stream"),
                  size=len(data), data=base64.b64encode(data).decode())
