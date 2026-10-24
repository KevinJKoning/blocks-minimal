"""The blocks. A block is a plain dict {"type": ..., ...}; a node's view(out) returns a list
of them and the page draws each with the renderer of the same name.

Every name here is a block, and a block is the files of its name in this folder:
<name>.py makes every choice (a colour, a scale's centre) and returns the dict; <name>.js
only paints it (`RENDER.<name> = (b, n) => ...`, using the page's kit); an optional
<name>.css lays it out in the theme's colours. A helper stays private to its block, or
moves to _kit.py once a second block needs it.
"""
from .chart import chart
from .download import download
from .figure import figure
from .map import map  # noqa: A004 - ui.map reads best
from .markdown import markdown
from .metrics import metrics
from .table import table

__all__ = ["chart", "download", "figure", "map", "markdown", "metrics", "table"]
