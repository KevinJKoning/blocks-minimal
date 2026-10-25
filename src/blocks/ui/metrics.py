from ._kit import block


def metrics():
    """The node's numbers, labelled by its METRICS (the page reads both from the run). An entry
    {"label": ..., "percent": True} marks a share, which then reads 70.6%, not 0.706."""
    return block("metrics")
