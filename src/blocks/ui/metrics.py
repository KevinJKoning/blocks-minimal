from ._kit import block


def metrics(under=None):
    """The node's numbers, labelled by its METRICS (the page reads both from the run). With
    `under`, only those of that key of the output: under="fit" shows fit.rmse, fit.shape, ..."""
    return block("metrics", under=under)
