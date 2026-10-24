from ._kit import MAX_ROWS, block, plain, tabulate


def table(rows, title=None, text=(), limit=MAX_ROWS):
    """text: the columns whose numbers name something (a year, a code); they read as written
    (2024, not 2,024). The rest are quantities. limit: the rows the page gets (the total is
    kept); a table that holds all its rows can be sorted by its headers."""
    cols, data = tabulate(rows)
    unknown = set(text) - set(cols)
    if unknown:
        raise ValueError(f"ui.table: no column {', '.join(sorted(map(str, unknown)))}")
    keep = [c in text for c in cols]
    shown = [[str(v) if k and v is not None else v for v, k in zip(r, keep)] for r in plain(data[:limit])]
    return block("table", title=title, columns=cols, rows=shown, total=len(data))
