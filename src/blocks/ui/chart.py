from ._kit import MAX_POINTS, block, plain


def chart(x, series, title=None, x_label=None, y_label=None, kind="line", bands=None, x_text=False):
    """series: {name: ys} over a shared x; kind: "line", "scatter" or {name: kind};
    bands: {name: (lows, highs)}, a shaded band around that series, in its colour;
    x_text: x names something (a year), so its ticks read as written (2024, not 2,024).
    A missing value (None or NaN) is a gap: a line breaks there. Past MAX_POINTS, every
    k-th point is kept, and the chart says so."""
    pick = (lambda n: kind.get(n, "line")) if isinstance(kind, dict) else (lambda n: kind)
    bands = bands or {}
    xs = plain(list(x))
    k = -(-len(xs) // MAX_POINTS) or 1
    thin = lambda v: plain(list(v))[::k]

    def one(n, ys):
        s = {"name": str(n), "y": thin(ys), "kind": pick(n)}
        if n in bands:
            s["band"] = [thin(b) for b in bands[n]]
        return s

    return block("chart", title=title, x=xs[::k], x_label=x_label, y_label=y_label, x_text=x_text or None,
                 series=[one(n, ys) for n, ys in series.items()], every=k if k > 1 else None, points=len(xs) if k > 1 else None)
