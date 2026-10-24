from ._kit import MAX_ROWS, block, plain, tabulate


def table(rows, title=None):
    cols, data = tabulate(rows)
    return block("table", title=title, columns=cols, rows=plain(data[:MAX_ROWS]), total=len(data))
