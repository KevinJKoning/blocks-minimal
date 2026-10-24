"""blocks: what a node file imports.

    from typing import Annotated
    from blocks import Range, ui

    def train(featurize, *, alpha: Annotated[float, Range(0.0001, 10, log=True)] = 0.1):
        ...
        return {"rmse": rmse, "coef": w}

    def view(out):
        return [ui.metrics(), ui.chart(out["x"], {"fit": out["y"]})]

Range and Choices are read from the source to draw a setting's control; at run time they
are plain metadata.
"""
from . import ui


class Range:
    def __init__(self, min, max, step=None, log=False):
        self.min, self.max, self.step, self.log = min, max, step, log


class Choices:
    def __init__(self, *values):
        self.values = list(values)


__all__ = ["Choices", "Range", "ui"]
