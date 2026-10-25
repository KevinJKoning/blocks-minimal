import math

from ._kit import block, plain


def _nice(step):
    """The 1, 2 or 5 times a power of ten nearest above step."""
    p = 10 ** math.floor(math.log10(step))
    return next(m * p for m in (1, 2, 5, 10) if m * p >= step * (1 - 1e-9))


def histogram(values, bins=None, title=None, x_label=None, mark=None):
    """How values are distributed: counts in equal bins of a round width, on edges that are
    multiples of it. bins: roughly how many (default √n, between 5 and 40); unknown values
    are left out and counted. mark: a value to draw a line at (0 for residuals, a target)."""
    vals = [float(v) for v in plain(list(values)) if isinstance(v, (int, float)) and math.isfinite(v)]
    missing = len(list(plain(list(values)))) - len(vals)
    if not vals:
        return block("histogram", title=title, x_label=x_label, edges=[], counts=[], missing=missing)
    lo, hi = min(vals), max(vals)
    if mark is not None:   # the bins reach the mark, so it is always drawn
        lo, hi = min(lo, float(mark)), max(hi, float(mark))
    target = bins or min(40, max(5, round(math.sqrt(len(vals)))))
    width = _nice((hi - lo) / target) if hi > lo else 1.0
    start = math.floor(lo / width) * width
    n = max(1, math.floor((hi - start) / width) + 1)
    counts = [0] * n
    for v in vals:
        counts[min(n - 1, int((v - start) // width))] += 1
    edges = [round(start + k * width, 12) for k in range(n + 1)]
    return block("histogram", title=title, x_label=x_label, edges=edges, counts=counts, missing=missing or None,
                 mark=float(mark) if mark is not None else None)
