"""The blocks. A block is a plain dict {"type": ..., ...}; a node's view(out) returns a list
of them and the page draws each with the renderer of the same name.

Every name here is a block, and a block is the files of its name in this folder:
<name>.py decides what the data means (a colour, a scale's centre) and returns the dict;
<name>.js lays it out and draws it (`RENDER.<name> = (b, n) => ...`, with the page's kit);
an optional <name>.css styles it under .<name>, in the theme's colours. A helper stays
private to its block, or moves to _kit.py or _kit.js once a second block needs it. An app's
own blocks are the same files in its ui/ folder.
"""
from .bars import bars
from .chart import chart
from .download import download
from .figure import figure
from .heatmap import heatmap
from .histogram import histogram
from .map import map  # noqa: A004 - ui.map reads best
from .markdown import markdown
from .metrics import metrics
from .row import row
from .table import table

__all__ = ["bars", "chart", "download", "figure", "heatmap", "histogram", "map", "markdown", "metrics", "row", "table"]
