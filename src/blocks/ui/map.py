import math

from ._kit import block, plain


def _rings(geometry):
    """The rings (polygons) or paths (lines) of a shapely geometry, WKB or a GeoJSON geometry dict."""
    if isinstance(geometry, (bytes, bytearray)):
        import shapely
        geometry = shapely.from_wkb(bytes(geometry))
    g = getattr(geometry, "__geo_interface__", geometry)
    kind, c = g["type"], g["coordinates"]
    parts = {"Polygon": [c], "MultiPolygon": c, "LineString": [[c]], "MultiLineString": [[line] for line in c]}.get(kind)
    if parts is None:
        raise ValueError(f"ui.map draws polygons and lines, not {kind}")
    return [[(float(p[0]), float(p[1])) for p in ring] for part in parts for ring in part]


def _shade(values, center=None):
    """The theme's ramp: a CSS colour per value (None where unknown) and the legend
    {lo, hi, stops}. With a center, colours diverge from it: --ramp-neg below, --ramp-hi above."""
    vals = [v if isinstance(v, (int, float)) and math.isfinite(v) else None for v in list(plain(values))]
    known = [v for v in vals if v is not None]
    if not known:
        return vals, None
    lo, hi = min(known), max(known)
    mix = lambda end, t: f"color-mix(in oklab, var(--ramp-{end}) {round(100 * t)}%, var(--ramp-lo))"
    if center is None:
        return ([v if v is None else mix("hi", (v - lo) / (hi - lo or 1)) for v in vals],
                {"lo": lo, "hi": hi, "stops": ["var(--ramp-lo)", "var(--ramp-hi)"]})
    m = max(abs(lo - center), abs(hi - center)) or 1
    return ([v if v is None else mix("neg" if v < center else "hi", abs(v - center) / m) for v in vals],
            {"lo": center - m, "hi": center + m, "stops": ["var(--ramp-neg)", "var(--ramp-lo)", "var(--ramp-hi)"]})


def map(shapes, values=None, names=None, title=None, label=None, lines=None, center=None):  # noqa: A001 - ui.map reads best
    """Polygons (shapely geometries, WKB, or GeoJSON geometry dicts; a pyarrow column of WKB
    too) coloured by values, in their own coordinates (a projected CRS draws true to scale).
    center: the value meaning "no change" (0 for a change); colours then diverge from it.
    lines: geometries drawn on top, such as a coastline."""
    shapes, lines = [_rings(s) for s in plain(shapes)], [_rings(g) for g in plain(lines or [])]
    xs, ys = zip(*(p for s in shapes for r in s for p in r))
    bounds = [min(xs), min(ys), max(xs), max(ys)]
    digits = max(0, 4 - len(str(int(max(bounds[2] - bounds[0], bounds[3] - bounds[1], 1)))))   # about 1/10,000 of the extent
    rnd = lambda rings: [[[round(x, digits), round(y, digits)] for x, y in r] for r in rings]
    fills, legend = _shade(values, center) if values is not None else (None, None)
    return block("map", title=title, label=label, bounds=bounds, fills=fills, legend=legend, shapes=[rnd(s) for s in shapes], lines=[rnd(g) for g in lines],
                 values=list(plain(values)) if values is not None else None, names=[str(n) for n in plain(names)] if names is not None else None)
