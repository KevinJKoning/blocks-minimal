from ._kit import MAX_ROWS, block, plain, tabulate


def table(rows, title=None, text=(), percent=(), limit=MAX_ROWS):
    """text: the columns whose numbers name something (a year, a code); they read as written.
    percent: the columns of shares. The rest are quantities. limit: the rows the page gets (the
    total is kept); a table that holds all its rows can be sorted by its headers."""
    cols, data = tabulate(rows)
    unknown = (set(text) | set(percent)) - set(cols)
    if unknown:
        raise ValueError(f"ui.table: no column {', '.join(sorted(map(str, unknown)))}")
    if set(text) & set(percent):
        raise ValueError(f"ui.table: {', '.join(sorted(set(text) & set(percent)))} cannot be both text and percent")
    keep = [c in text for c in cols]
    shown = [[str(v) if k and v is not None else v for v, k in zip(r, keep)] for r in plain(data[:limit])]
    return block("table", title=title, columns=cols, rows=shown, total=len(data), percent=[c for c in cols if c in percent] or None)
