from ._kit import block, plain, ramp, shade


def heatmap(rows, columns, values, title=None, label=None, center=None, scale="linear", percent=False):
    """A value for each row and column, shaded on the theme's ramp: a confusion matrix,
    correlations, crews by day. values[i][j] is row i's value in column j; unknown ones stay
    unshaded. center: the value meaning "no change" (0 for a correlation); colours then diverge
    from it. scale: "log" for values spread over orders of magnitude. percent: the values are
    shares. Rows and columns are names, read as written."""
    rows, columns = [str(r) for r in plain(rows)], [str(c) for c in plain(columns)]
    grid = [list(plain(r)) for r in values]
    if len(grid) != len(rows) or any(len(r) != len(columns) for r in grid):
        raise ValueError(f"ui.heatmap: {len(rows)} rows by {len(columns)} columns needs that many rows of that many values")
    ts, legend = shade([v for r in grid for v in r], center, scale, "ui.heatmap")
    n = len(columns)
    # Text on a cell past the ramp's middle reads in paper, not ink.
    return block("heatmap", title=title, label=label, rows=rows, columns=columns,
                 values=grid, fills=[[ramp(t) for t in ts[i * n:(i + 1) * n]] for i in range(len(rows))],
                 dark=[[t is not None and abs(t) > 0.55 for t in ts[i * n:(i + 1) * n]] for i in range(len(rows))],
                 legend=legend, percent=percent or None)
