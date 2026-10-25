"""What a node file imports: ui, the blocks, and Range and Choices, which mark a setting's
control. They are read from the source; at run time they are plain metadata."""
from . import ui


class Range:
    """A slider from min to max. step defaults to 1 for an int and any value for a float; log
    slides evenly in orders of magnitude, and ignores step."""

    def __init__(self, min, max, step=None, log=False):
        self.min, self.max, self.step, self.log = min, max, step, log


class Choices:
    """A menu of these literals."""

    def __init__(self, *values):
        self.values = list(values)


__all__ = ["Choices", "Range", "ui"]
