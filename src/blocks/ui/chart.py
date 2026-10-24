from ._kit import MAX_POINTS, block, plain


def chart(x, series, title=None, x_label=None, y_label=None, kind="line"):
    """series: {name: ys} over a shared x; kind: "line", "scatter" or {name: kind}."""
    pick = (lambda n: kind.get(n, "line")) if isinstance(kind, dict) else (lambda n: kind)
    return block("chart", title=title, x=plain(list(x))[:MAX_POINTS], x_label=x_label, y_label=y_label,
                 series=[{"name": str(n), "y": plain(list(ys))[:MAX_POINTS], "kind": pick(n)} for n, ys in series.items()])
