from ._kit import MAX_POINTS, block, known, plain

KINDS = ("line", "scatter", "step")


def _own(v):
    """Whether a series is (xs, ys), with an x of its own, rather than ys."""
    return isinstance(v, tuple) and len(v) == 2 and all(hasattr(e, "__len__") and not isinstance(e, str) for e in v)


def chart(x, series, title=None, x_label=None, y_label=None, kind="line", bands=None, x_text=False,
          x_lines=None, y_lines=None, x_scale="linear", y_scale="linear", x_percent=False, y_percent=False):
    """series: {name: ys} over a shared x, or {name: (xs, ys)} for a series on its own x (a
    curve per model or per group); with every series on its own, x is None.
    kind: "line", "scatter", "step" (a line that holds each value until the next x: a
    survival curve, a running count) or {name: kind}.
    bands: {name: (lows, highs)}, a shaded band around that series, in its colour.
    x_lines, y_lines: {name: value}, reference lines across the chart (a control limit, a
    threshold), dashed and named.
    x_scale, y_scale: "log" for values spread over orders of magnitude; values of 0 or less
    have no place on it, so they are left out and counted.
    x_percent, y_percent: that axis holds shares, which read 70.6%, not 0.706.
    x_text: x names something (a year), so its ticks read as written (2024, not 2,024).
    A missing value (None or NaN) is a gap: a line breaks there. Past MAX_POINTS, every
    k-th point is kept, and the chart says so."""
    for scale, what in ((x_scale, "x_scale"), (y_scale, "y_scale")):
        if scale not in ("linear", "log"):
            raise ValueError(f"ui.chart: {what} is linear or log, not {scale!r}")
    pick = (lambda n: kind.get(n, "line")) if isinstance(kind, dict) else (lambda n: kind)
    for n in series:
        if pick(n) not in KINDS:
            raise ValueError(f"ui.chart: kind is {', '.join(KINDS)}, not {pick(n)!r}")
    if x is None and not all(_own(v) for v in series.values()):
        raise ValueError("ui.chart: with x None, every series is (xs, ys), on its own x")
    bands, dropped, thinned = bands or {}, [0], []

    def placed(vals, scale, count=True):   # on a log axis, values of 0 or less are left out, and counted
        vals = list(plain(vals))
        if scale != "log":
            return vals
        out = [None if known(v) is not None and v <= 0 else v for v in vals]
        dropped[0] += count * sum(a is not b for a, b in zip(vals, out))
        return out

    def every(n):
        k = -(-n // MAX_POINTS) or 1
        if k > 1:
            thinned.append((k, n))
        return k

    xs = None if x is None else placed(x, x_scale)
    k0 = every(len(xs)) if xs is not None else 1

    def one(n, v):
        own = _own(v)
        sx, ys = (placed(v[0], x_scale), v[1]) if own else (None, v)
        k = every(len(sx)) if own else k0
        thin = lambda vals, count=True: placed(vals, y_scale, count)[::k]
        s = {"name": str(n), "y": thin(ys), "kind": pick(n)}
        if own:
            s["x"] = sx[::k]
        if n in bands:
            s["band"] = [thin(b, False) for b in bands[n]]
        return s

    lines = lambda given: [{"name": str(n), "value": float(v)} for n, v in (given or {}).items()] or None
    out = [one(n, v) for n, v in series.items()]
    k, points = max(thinned) if thinned else (None, None)
    return block("chart", title=title, x=xs[::k0] if xs is not None else None, x_label=x_label, y_label=y_label,
                 x_text=x_text or None, series=out, x_lines=lines(x_lines), y_lines=lines(y_lines),
                 x_scale="log" if x_scale == "log" else None, y_scale="log" if y_scale == "log" else None,
                 x_percent=x_percent or None, y_percent=y_percent or None, dropped=dropped[0] or None,
                 every=k, points=points)
