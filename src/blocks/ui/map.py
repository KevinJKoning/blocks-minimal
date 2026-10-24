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


def _shade(values, center=None, scale="linear"):
    """The theme's ramp: a CSS colour per value (None where unknown) and the legend
    {lo, hi, stops, scale, center, unshaded}. With a center, colours diverge from it:
    --ramp-neg below, --ramp-hi above. On a log scale a value of 0 or less has no place, so
    it stays unshaded and the legend counts it."""
    if scale not in ("linear", "log"):
        raise ValueError(f"ui.map: scale is linear or log, not {scale!r}")
    if scale == "log" and center is not None:
        raise ValueError("ui.map: a log scale has no center")
    vals = [v if isinstance(v, (int, float)) and math.isfinite(v) else None for v in list(plain(values))]
    unshaded = sum(v is not None and v <= 0 for v in vals) if scale == "log" else 0
    if unshaded:
        vals = [None if v is not None and v <= 0 else v for v in vals]
    known = [v for v in vals if v is not None]
    if not known:
        return vals, None
    at = math.log10 if scale == "log" else (lambda v: v)
    lo, hi = min(known), max(known)
    mix = lambda end, t: f"color-mix(in oklab, var(--ramp-{end}) {round(100 * t)}%, var(--ramp-lo))"
    legend = {"scale": scale, "unshaded": unshaded or None}
    if center is None:
        span = at(hi) - at(lo) or 1
        return ([v if v is None else mix("hi", (at(v) - at(lo)) / span) for v in vals],
                {**legend, "lo": lo, "hi": hi, "stops": ["var(--ramp-lo)", "var(--ramp-hi)"]})
    m = max(abs(lo - center), abs(hi - center)) or 1
    return ([v if v is None else mix("neg" if v < center else "hi", abs(v - center) / m) for v in vals],
            {**legend, "lo": center - m, "hi": center + m, "center": center,
             "stops": ["var(--ramp-neg)", "var(--ramp-lo)", "var(--ramp-hi)"]})


def map(shapes, values=None, names=None, title=None, label=None, lines=None, center=None, scale="linear"):  # noqa: A001 - ui.map reads best
    """Polygons (shapely geometries, WKB, or GeoJSON geometry dicts; a pyarrow column of WKB
    too) coloured by values, in their own coordinates (a projected CRS draws true to scale).
    values: one value per shape, or layers {name: values}, which the reader switches between.
    label, center and scale then apply to every layer, or take {name: ...} for each.
    center: the value meaning "no change" (0 for a change); colours then diverge from it.
    scale: "log" for values spread over orders of magnitude (policy-years, populations).
    lines: geometries drawn on top, such as a coastline."""
    shapes, lines = [_rings(s) for s in plain(shapes)], [_rings(g) for g in plain(lines or [])]
    xs, ys = zip(*(p for s in shapes for r in s for p in r))
    bounds = [min(xs), min(ys), max(xs), max(ys)]
    digits = max(0, 4 - len(str(int(max(bounds[2] - bounds[0], bounds[3] - bounds[1], 1)))))   # about 1/10,000 of the extent
    rnd = lambda rings: [[[round(x, digits), round(y, digits)] for x, y in r] for r in rings]
    named = isinstance(values, dict)
    given = values if named else {} if values is None else {None: values}
    for arg, what in ((label, "label"), (center, "center"), (scale, "scale")):
        if isinstance(arg, dict) and (not named or set(arg) - set(given)):
            raise ValueError(f"ui.map: {what} by layer needs values by layer, and only names those layers")
    pick = lambda arg, name, default=None: arg.get(name, default) if isinstance(arg, dict) else arg
    layers = []
    for name, vals in given.items():
        vals = list(plain(vals))
        if len(vals) != len(shapes):
            raise ValueError(f"ui.map: {len(shapes)} shapes but {len(vals)} values" + (f" in {name!r}" if named else ""))
        fills, legend = _shade(vals, pick(center, name), pick(scale, name, "linear"))
        layers.append({"name": None if name is None else str(name), "label": pick(label, name), "values": vals, "fills": fills, "legend": legend})
    return block("map", title=title, bounds=bounds, layers=layers, shapes=[rnd(s) for s in shapes], lines=[rnd(g) for g in lines],
                 names=[str(n) for n in plain(names)] if names is not None else None)
