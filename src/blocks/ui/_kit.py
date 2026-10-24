"""What the blocks share: plain values, tables of anything, and the block dict itself."""
from __future__ import annotations

from ..core.graph import plain  # noqa: F401 - the blocks import it from here

MAX_ROWS = 200      # a table shows at most this many rows (the total is kept)
MAX_POINTS = 5000   # a chart series keeps at most this many points


def tabulate(rows) -> tuple[list[str], list[list]]:
    """(columns, rows) of anything table-like: pyarrow, pandas, {column: values}, dicts, rows."""
    if hasattr(rows, "to_pydict"):
        d = rows.to_pydict()
        return list(d), [list(r) for r in zip(*d.values())]
    if hasattr(rows, "itertuples"):
        return [str(c) for c in rows.columns], [list(r) for r in rows.itertuples(index=False)]
    if isinstance(rows, dict):
        return [str(c) for c in rows], [list(r) for r in zip(*(plain(list(v)) for v in rows.values()))]
    rows = list(rows)
    if rows and isinstance(rows[0], dict):
        columns = list(dict.fromkeys(k for r in rows for k in r))
        return [str(c) for c in columns], [[r.get(c) for c in columns] for r in rows]
    return [f"c{i + 1}" for i in range(len(rows[0]) if rows else 0)], [list(r) for r in rows]


def block(type, **fields):
    return {"type": type, **{k: v for k, v in fields.items() if v is not None}}
