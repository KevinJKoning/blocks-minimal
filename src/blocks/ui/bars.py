from ._kit import block, plain


def bars(categories, series, title=None, label=None, kind="bar", intervals=None, reference=None, percent=False):
    """Values per named category, one row each, in the order given: series is {name: values};
    kind "bar" draws bars from the reference (or 0), "dot" draws dots, for estimates;
    intervals {name: (lows, highs)} draws error bars; reference is a value to draw a line at
    (0 for a change, 1 for a relativity); percent: the values are shares, which read 70.6%,
    not 0.706."""
    if kind not in ("bar", "dot"):
        raise ValueError(f"ui.bars: kind is bar or dot, not {kind!r}")
    cats, intervals = [str(c) for c in plain(categories)], intervals or {}
    out = []
    for name, values in series.items():
        values = list(plain(values))
        if len(values) != len(cats):
            raise ValueError(f"ui.bars: {name} has {len(values)} values for {len(cats)} categories")
        s = {"name": str(name), "values": values}
        if name in intervals:
            s["interval"] = [list(plain(intervals[name][0])), list(plain(intervals[name][1]))]
        out.append(s)
    return block("bars", title=title, label=label, kind=kind, categories=cats, series=out, reference=reference, percent=percent or None)
