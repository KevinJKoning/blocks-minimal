import math

from ._kit import block, known, plain


def _nice(step):
    """The 1, 2 or 5 times a power of ten nearest above step."""
    p = 10 ** math.floor(math.log10(step))
    return next(m * p for m in (1, 2, 5, 10) if m * p >= step * (1 - 1e-9))


def histogram(values, bins=None, title=None, x_label=None, mark=None):
    """How values are distributed: counts in equal bins of a round width, on edges that are
    multiples of it. values: one set, or groups {name: values} on shared edges, each drawn as
    its share of its own group per bin, so groups of any size compare (leaks and not, two
    models' scores). bins: roughly how many (default √n, between 5 and 40); unknown values
    are left out and counted. mark: a value to draw a line at (0 for residuals, a target)."""
    given = values if isinstance(values, dict) else {None: values}
    sets = {n: list(plain(v)) for n, v in given.items()}
    vals = {n: [float(v) for v in vs if known(v) is not None] for n, vs in sets.items()}
    missing = sum(len(sets[n]) - len(vals[n]) for n in sets)
    every = [v for vs in vals.values() for v in vs]
    if not every:
        return block("histogram", title=title, x_label=x_label, edges=[], groups=[], missing=missing)
    lo, hi = min(every), max(every)
    if mark is not None:   # the bins reach the mark, so it is always drawn
        lo, hi = min(lo, float(mark)), max(hi, float(mark))
    target = bins or min(40, max(5, round(math.sqrt(len(every) / len(vals)))))
    width = _nice((hi - lo) / target) if hi > lo else 1.0
    start = math.floor(lo / width) * width
    n = max(1, math.floor((hi - start) / width) + 1)
    groups = []
    for name, vs in vals.items():
        counts = [0] * n
        for v in vs:
            counts[min(n - 1, int((v - start) // width))] += 1
        groups.append({"name": None if name is None else str(name), "counts": counts})
    edges = [round(start + k * width, 12) for k in range(n + 1)]
    return block("histogram", title=title, x_label=x_label, edges=edges, groups=groups, missing=missing or None,
                 mark=float(mark) if mark is not None else None)
