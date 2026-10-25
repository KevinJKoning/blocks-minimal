"""The blocks: every name here is one, the files of its name in this folder (AGENTS.md has
the rules). A node's view(out) returns a list of them."""
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
