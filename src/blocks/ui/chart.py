from ._kit import MAX_POINTS, block, plain


def chart(x, series, title=None, x_label=None, y_label=None, kind="line", bands=None, x_text=False):
    """series: {name: ys} over a shared x; kind: "line", "scatter" or {name: kind};
    bands: {name: (lows, highs)}, a shaded band around that series, in its colour;
    x_text: x names something (a year), so its ticks read as written (2024, not 2,024)."""
    pick = (lambda n: kind.get(n, "line")) if isinstance(kind, dict) else (lambda n: kind)
    bands = bands or {}

    def one(n, ys):
        s = {"name": str(n), "y": plain(list(ys))[:MAX_POINTS], "kind": pick(n)}
        if n in bands:
            lo, hi = bands[n]
            s["band"] = [plain(list(lo))[:MAX_POINTS], plain(list(hi))[:MAX_POINTS]]
        return s

    return block("chart", title=title, x=plain(list(x))[:MAX_POINTS], x_label=x_label, y_label=y_label, x_text=x_text or None,
                 series=[one(n, ys) for n, ys in series.items()])
