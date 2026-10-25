"""What the blocks share: plain values, tables of anything, the ramp, and the block dict itself."""
from __future__ import annotations

import math

from ..core.graph import plain  # noqa: F401 - the blocks import it from here

MAX_ROWS = 200      # a table shows at most this many rows (the total is kept)
MAX_POINTS = 5000   # a chart series keeps at most this many points
MAX_CELLS = 40000   # a map's grid keeps at most this many cells


def tabulate(rows) -> tuple[list[str], list[list]]:
    """(columns, rows) of anything table-like: pyarrow, pandas, {column: values}, dicts, rows."""
    if hasattr(rows, "to_pydict"):
        d = rows.to_pydict()
        return list(d), [list(r) for r in zip(*d.values())]
    if hasattr(rows, "itertuples"):
        if any(n is not None for n in rows.index.names):   # a named index (a groupby's) is data
            rows = rows.reset_index()
        return [str(c) for c in rows.columns], [list(r) for r in rows.itertuples(index=False)]
    if isinstance(rows, dict):
        return [str(c) for c in rows], [list(r) for r in zip(*(list(plain(v)) for v in rows.values()))]
    rows = list(rows)
    if rows and isinstance(rows[0], dict):
        columns = list(dict.fromkeys(k for r in rows for k in r))
        return [str(c) for c in columns], [[r.get(c) for c in columns] for r in rows]
    return [f"c{i + 1}" for i in range(len(rows[0]) if rows else 0)], [list(r) for r in rows]


def known(v):
    """v, if it is a finite number; None for anything else (None, NaN, text)."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def shade(values, center=None, scale="linear", who="ui.map"):
    """Each value's place on the theme's ramp and the ramp's legend {lo, hi, stops, scale,
    center, unshaded}. A place t runs from 0 (--ramp-lo) to 1 (--ramp-hi); with a center,
    values below it run to -1 (--ramp-neg). None where a value is unknown. On a log scale a
    value of 0 or less has no place, so it stays unshaded and the legend counts it."""
    if scale not in ("linear", "log"):
        raise ValueError(f"{who}: scale is linear or log, not {scale!r}")
    if scale == "log" and center is not None:
        raise ValueError(f"{who}: a log scale has no center")
    vals = [known(v) for v in values]
    unshaded = sum(v is not None and v <= 0 for v in vals) if scale == "log" else 0
    if unshaded:
        vals = [None if v is not None and v <= 0 else v for v in vals]
    found = [v for v in vals if v is not None]
    if not found:
        return vals, None
    at = math.log10 if scale == "log" else (lambda v: v)
    lo, hi = min(found), max(found)
    legend = {"scale": scale, "unshaded": unshaded or None}
    if center is None:
        span = at(hi) - at(lo) or 1
        return ([v if v is None else (at(v) - at(lo)) / span for v in vals],
                {**legend, "lo": lo, "hi": hi, "stops": ["var(--ramp-lo)", "var(--ramp-hi)"]})
    m = max(abs(lo - center), abs(hi - center)) or 1
    return ([v if v is None else (v - center) / m for v in vals],
            {**legend, "lo": center - m, "hi": center + m, "center": center,
             "stops": ["var(--ramp-neg)", "var(--ramp-lo)", "var(--ramp-hi)"]})


def ramp(t):
    """The CSS colour at place t on the ramp (see shade); None for None."""
    if t is None:
        return None
    return f"color-mix(in oklab, var(--ramp-{'neg' if t < 0 else 'hi'}) {round(100 * abs(t))}%, var(--ramp-lo))"


def block(type, **fields):
    return {"type": type, **{k: v for k, v in fields.items() if v is not None}}
