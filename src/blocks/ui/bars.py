from ._kit import block, plain


def bars(categories, series, title=None, label=None, kind="bar", intervals=None, reference=None):
    """Values per named category, one row each, in the order given: series is {name: values};
    kind "bar" draws bars from the reference (or 0), "dot" draws dots, for estimates;
    intervals {name: (lows, highs)} draws error bars; reference is a value to draw a line at
    (0 for a change, 1 for a relativity)."""
    if kind not in ("bar", "dot"):
        raise ValueError(f"ui.bars: kind is bar or dot, not {kind!r}")
    cats, intervals = [str(c) for c in plain(list(categories))], intervals or {}
    out = []
    for name, values in series.items():
        values = plain(list(values))
        if len(values) != len(cats):
            raise ValueError(f"ui.bars: {name} has {len(values)} values for {len(cats)} categories")
        s = {"name": str(name), "values": values}
        if name in intervals:
            s["interval"] = [plain(list(intervals[name][0])), plain(list(intervals[name][1]))]
        out.append(s)
    return block("bars", title=title, label=label, kind=kind, categories=cats, series=out, reference=reference)
