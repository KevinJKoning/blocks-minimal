import math
from collections import Counter

from ._kit import MAX_CELLS, block, known, plain, ramp, shade

# The colours of names (land use, a yes or no), from the theme's series colours, softened to fill.
NAMED = [f"color-mix(in oklab, var(--s{k}) 65%, var(--paper))" for k in (3, 2, 5, 6, 4, 1)]
OTHER = "color-mix(in oklab, var(--faint) 35%, var(--paper))"


def _rings(geometry):
    """The rings (polygons), paths (lines) or one-point rings (points) of a shapely geometry,
    WKB or a GeoJSON geometry dict."""
    if isinstance(geometry, (bytes, bytearray)):
        import shapely
        geometry = shapely.from_wkb(bytes(geometry))
    g = getattr(geometry, "__geo_interface__", geometry)
    kind, c = g["type"], g["coordinates"]
    parts = {"Polygon": [c], "MultiPolygon": c, "LineString": [[c]], "MultiLineString": [[line] for line in c],
             "Point": [[[c]]], "MultiPoint": [[[p]] for p in c]}.get(kind)
    if parts is None:
        raise ValueError(f"ui.map draws polygons, lines and points, not {kind}")
    return [[(float(p[0]), float(p[1])) for p in ring] for part in parts for ring in part]


def _geometries(g):
    """A list of geometries, from one or many."""
    one = isinstance(g, (bytes, bytearray)) or hasattr(g, "__geo_interface__") or (isinstance(g, dict) and "type" in g)
    return [g] if one else list(plain(g))


def _names(values):
    """Values that name something: a colour each, in name order; past six names, the five most
    common keep theirs and the rest share one, as other."""
    names = [None if v is None or (isinstance(v, float) and math.isnan(v)) else str(v) for v in values]
    counts = Counter(n for n in names if n is not None)
    keep = sorted(counts) if len(counts) <= len(NAMED) else sorted(n for n, _ in counts.most_common(len(NAMED) - 1))
    colour = dict(zip(keep, NAMED))
    rest = sorted(set(counts) - set(colour))
    legend = {"names": [{"name": n, "fill": colour[n]} for n in keep]
              + ([{"name": f"other ({len(rest)} names)", "fill": OTHER}] if rest else [])}
    return names, [None if n is None else colour.get(n, OTHER) for n in names], legend


def _grid(grid):
    """A grid (xs, ys, values) as the page draws it: values[i][j] is the cell centred on
    (xs[j], ys[i]), on even steps, either way up; rows are put north first. Past MAX_CELLS,
    every k-th row and column is kept."""
    xs, ys, rows = grid
    xs, ys = [float(v) for v in plain(xs)], [float(v) for v in plain(ys)]
    rows = [list(plain(r)) for r in rows]
    if len(rows) != len(ys) or any(len(r) != len(xs) for r in rows):
        raise ValueError(f"ui.map: a grid of {len(ys)} ys by {len(xs)} xs needs that many rows of that many values")
    if len(ys) > 1 and ys[0] < ys[-1]:
        ys, rows = ys[::-1], rows[::-1]
    if len(xs) > 1 and xs[0] > xs[-1]:
        xs, rows = xs[::-1], [r[::-1] for r in rows]
    k = math.ceil(math.sqrt(len(xs) * len(ys) / MAX_CELLS)) or 1
    xs, ys, rows = xs[::k], ys[::k], [r[::k] for r in rows[::k]]
    dx = (xs[-1] - xs[0]) / (len(xs) - 1) if len(xs) > 1 else 1.0
    dy = (ys[0] - ys[-1]) / (len(ys) - 1) if len(ys) > 1 else 1.0
    return {"bounds": [xs[0] - dx / 2, ys[-1] - dy / 2, xs[-1] + dx / 2, ys[0] + dy / 2], "cols": len(xs),
            "values": [None if known(v) is None else float(f"{v:.4g}") for r in rows for v in r],
            "every": k if k > 1 else None}


def map(shapes, values=None, names=None, title=None, label=None, lines=None, grid=None, center=None, scale="linear"):  # noqa: A001 - ui.map reads best
    """Polygons or points (shapely geometries, WKB, or GeoJSON geometry dicts; a pyarrow column
    of WKB too) coloured by values, in their own coordinates (a projected CRS draws true to
    scale). A point is a dot of one size at any zoom.
    values: one value per shape: numbers, shaded on the ramp, or names (text, a yes or no),
    a colour each. Or layers {name: values}, which the reader switches between; label,
    center, scale and grid then apply to every layer, or take {name: ...} for each.
    center: the value meaning "no change" (0 for a change); colours then diverge from it.
    scale: "log" for values spread over orders of magnitude (policy-years, populations).
    lines: geometries drawn on top, unshaded, such as a coastline, roads or wells; or
    {name: geometries}, each in its own colour, named in a key.
    grid: (xs, ys, values), a surface beneath the shapes (an interpolation, a raster):
    values[i][j] is the cell centred on (xs[j], ys[i]). It shares its layer's ramp with the
    shapes' values, if any. The map's extent takes in shapes, lines and grid."""
    shapes = [_rings(s) for s in _geometries(shapes)]
    groups = lines.items() if isinstance(lines, dict) else [(None, lines or [])]
    groups = [(n, [_rings(g) for g in _geometries(gs)]) for n, gs in groups]
    if values is not None:
        given = values if isinstance(values, dict) else {None: values}
    else:   # a grid alone: its layers are the grid's
        given = dict.fromkeys(grid) if isinstance(grid, dict) else {} if grid is None else {None: None}
    named = None not in given and bool(given)
    for arg, what in ((label, "label"), (center, "center"), (scale, "scale"), (grid, "grid")):
        if isinstance(arg, dict) and (not named or set(arg) - set(given)):
            raise ValueError(f"ui.map: {what} by layer needs values by layer, and only names those layers")
    pick = lambda arg, name, default=None: arg.get(name, default) if isinstance(arg, dict) else arg

    layers, extent = [], [p for g in shapes + [r for _, gs in groups for r in gs] for r in g for p in r]
    for name, vals in given.items():
        vals = [None] * len(shapes) if vals is None else list(plain(vals))
        if len(vals) != len(shapes):
            raise ValueError(f"ui.map: {len(shapes)} shapes but {len(vals)} values" + (f" in {name!r}" if named else ""))
        surface = _grid(pick(grid, name)) if pick(grid, name) is not None else None
        layer = {"name": None if name is None else str(name), "label": pick(label, name)}
        if any(isinstance(v, (str, bool)) for v in vals):
            if any(known(v) is not None for v in vals) or surface:
                raise ValueError(f"ui.map: values are numbers or names, not both" + (f" (in {name!r})" if named else "")
                                 + ("; a grid is shaded by number" if surface else ""))
            layer["values"], layer["fills"], layer["legend"] = _names(vals)
        else:
            ts, legend = shade(vals + (surface["values"] if surface else []), pick(center, name), pick(scale, name, "linear"))
            layer.update(values=vals, fills=[ramp(t) for t in ts[:len(vals)]], legend=legend)
            if surface:   # its cells as indexes into the few colours they take, 1% of the ramp apart
                steps = [None if t is None else round(t * 100) for t in ts[len(vals):]]
                palette = sorted({s for s in steps if s is not None})
                index = {s: i for i, s in enumerate(palette)}
                layer["grid"] = {**surface, "fills": [ramp(s / 100) for s in palette], "cells": [-1 if s is None else index[s] for s in steps]}
                gx0, gy0, gx1, gy1 = surface["bounds"]
                extent += [(gx0, gy0), (gx1, gy1)]
        layers.append(layer)

    xs, ys = zip(*extent)
    bounds = [min(xs), min(ys), max(xs), max(ys)]
    digits = max(0, 4 - len(str(int(max(bounds[2] - bounds[0], bounds[3] - bounds[1], 1)))))   # about 1/10,000 of the extent
    rnd = lambda rings: [[[round(x, digits), round(y, digits)] for x, y in r] for r in rings]
    return block("map", title=title, bounds=bounds, layers=layers, shapes=[rnd(s) for s in shapes],
                 lines=[{"name": None if n is None else str(n), "shapes": [rnd(g) for g in gs]} for n, gs in groups if gs],
                 names=[str(n) for n in plain(names)] if names is not None else None)
