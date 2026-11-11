from ._kit import block


def step(fn, *blocks):
    """One of the node's steps, as a unit: what it says it is, these blocks, and its code, bound
    by a line down the side. `fn` is the step itself: a function at the top of the node's file
    with a docstring (the page has both from the app's spec, under the function's name)."""
    if not callable(fn) or not (getattr(fn, "__doc__", None) or "").strip():
        raise ValueError("ui.step takes the step's function, which has a docstring, then its blocks: ui.step(calibration, ui.chart(...))")
    if not all(isinstance(b, dict) and "type" in b for b in blocks):
        raise ValueError("ui.step takes blocks after the function, like ui.step(calibration, ui.chart(...), ui.table(...))")
    return block("step", name=fn.__name__, blocks=list(blocks))
