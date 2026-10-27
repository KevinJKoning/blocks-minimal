# blocks (minimal)

Apps as a graph of Python functions, with UI blocks on top, run in the browser (Pyodide)
and shipped as one offline HTML file. Made to be iterated in conversation with an agent:
the core is code that solves the problem; the page is a thin layer of blocks over its
outputs.

```python
# projects/sensor-calibration/nodes/train.py
"""Closed-form ridge regression of the reference value on the standardized features."""
from typing import Annotated
from blocks import Range, ui

METRICS = {"train_rmse": {"label": "train RMSE", "goal": "min"}}


def train(featurize, *, alpha: Annotated[float, Range(0.0001, 10, log=True)] = 0.1):
    ...                                     # featurize's output, in memory
    return {"coef": w, "intercept": b, "train_rmse": rmse}


def view(out):                              # optional: how its results look
    return [ui.metrics()]
```

- **The graph is the functions' signatures.** Positional parameters are inputs: another
  node by its name, or a file in `data/` by its stem. Keyword-only parameters are
  settings. There is no config file: the title and description are the README's, the
  packages are the imports: Pyodide's builds (numpy, pandas, scipy, statsmodels,
  scikit-learn, shapely and some 300 more), not the venv's.
- **Cached.** Each output is keyed by its node's code, settings and inputs' keys. Changing
  `alpha` makes `train` and what reads it stale; Run re-runs just those.
- **The page is blocks.** The graph is the table of contents. Each node is a page of its
  docstring, settings, results (its view) and code; each dataset, a page where it can be
  replaced, under what its `data/<name>.md` says it is; the overview gathers datasets and downloads.
- **Verified.** Every run leaves a record (settings, data keys, every node's metrics and
  output digest). `blocks baseline` keeps one; `blocks verify` and `blocks build` compare
  against it, and the page shows each metric against it. A view that fails, in Python or
  on the page, fails them too.

## Quick start

```sh
python3.13 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.txt
.venv/bin/pip install --no-deps --no-build-isolation -e . && .venv/bin/playwright install chromium
.venv/bin/blocks serve                    # http://127.0.0.1:8765/<app>/, rebuilt on every request
.venv/bin/blocks run parcels              # run headlessly; print each node's status, metrics and errors
.venv/bin/blocks baseline parcels         # the same, kept as projects/parcels/baseline.json if nothing failed
.venv/bin/blocks verify [APP ...]         # compare with the baseline (no APP: every app)
.venv/bin/blocks build [APP ...]          # dist/<app>.html (git-ignored, mostly Pyodide: 20-80 MB), verified offline from file://
                                          # --no-data: without its datasets; whoever opens it chooses them
.venv/bin/python -m pytest                # -m "not browser" for the fast ones
```

The apps' code is trusted; their packages are not. The page's Content-Security-Policy keeps
the worker off the network (a built page reaches nothing; a served one, only its dev server's runtime files),
the headless browser keeps its sandbox, the dev server answers only to `127.0.0.1` and
`localhost`, and the native dependencies are pinned with hashes in `requirements.txt`.

## An app

```
projects/<app>/
  README.md          "# Title", then what the app is for (the overview page)
  nodes/<name>.py    one node: def <name>(inputs..., *, settings...)
  data/<name>.*      a dataset; a node reads it with a parameter <name> and gets its path
  data/<name>/       a dataset of files (exports by month, say); the node gets their paths, by name
  data/<name>.md     what the dataset is (Markdown), atop its page: its format and columns, for whoever replaces it
  data/*.py          a script that makes or fetches a dataset; it runs natively, by hand, never in the app
  *.py               helpers the nodes import: code several nodes share (a node file is not one)
  ui/<name>.py|js|css  a block only this app draws (see Blocks)
  baseline.json      the run every check compares with
```

| in a node file | means |
|---|---|
| positional parameters | what it reads: a node's output, or a dataset's path (so no node and dataset share a name) |
| keyword-only parameters | its settings, each a literal default: a bool is a checkbox; `Annotated[float, Range(min, max)]` a slider; `Annotated[str, Choices("a", "b")]` a menu; any other number or string a box |
| the return value | its output, any Python value, passed in memory to the nodes that read it. Every number in its dicts (nested too, not in lists or tables) is a metric: recorded, compared with the baseline and shown, the unlabelled ones folded under "more numbers" (a setting the view needs to mention comes back this way too) |
| the docstring | the top of its page (Markdown) |
| `METRICS = {key: "label" \| {label, goal, percent}}` | labels for its numbers, in order, each key a number's path in the output (`fit.shape` for `{"fit": {"shape": ...}}`); `goal: "min" \| "max"` colours changes; `percent: True` marks a share |
| `def view(out)` | its results: a list of blocks |

## Blocks

| `blocks.ui` | draws |
|---|---|
| `markdown(text)` | Markdown |
| `metrics()` | the node's metrics, labelled, with the change since the last run and the baseline's value |
| `table(rows, ...)` | a DataFrame, pyarrow Table, `{column: values}` or list of dicts, sortable when shown whole; `percent` and `text` columns |
| `chart(x, series, ...)` | lines, steps or dots (`kind`) over x, with `bands` or error bars, reference lines (`x_lines`, `y_lines`), log axes (`x_scale`, `y_scale`) and shares (`x_percent`, `y_percent`) |
| `bars(categories, series, ...)` | a row per category: bars, or dots (`kind="dot"`) with `intervals` and a `reference` line (a forest plot) |
| `figure(image, caption=None)` | SVG text or PNG bytes |
| `histogram(values, ...)` | counts in round bins, of one set or of groups (`{name: values}`) compared |
| `heatmap(rows, columns, values, ...)` | a value per row and column, shaded: a confusion matrix, correlations |
| `map(shapes, values=None, ...)` | polygons and points shaded by value or coloured by name, in layers, over a `grid`, under unshaded `lines` and outlines; hover and zoom |
| `row(*blocks, title=None)` | blocks side by side, to compare |
| `download(name, value, title=None)` | a file to take away: a table as `.csv`, `.json` or `.parquet`, text, or bytes |

Each block's parameters are in its docstring, in `src/blocks/ui/<name>.py`. Every number is
drawn as a quantity; a share is marked `percent`, and a number that names something (a year)
`text`, where the block is made. A block is the files of one name in `src/blocks/ui/`, or in
an app's `ui/` when only that app draws it; AGENTS.md has the rules for writing one.

## Example apps

| app | shows |
|---|---|
| `sensor-calibration` | a modelling pipeline: cleaning, features, ridge regression, held-out evaluation, delivered files |
| `parcels` | a zipped Esri geodatabase read with GDAL in the browser, then areas and a summary |
| `windstorm` | geodata joined to policies; a Poisson GLM with a wind-load offset and Bühlmann–Straub credibility, checked against its synthetic truth; its own `tiles` block in `ui/` |
| `michigan-census` | official Census data fetched natively and analysed offline; settings shared through small nodes, county maps that diverge from zero |
| `electricity-demand` | a seasonal forecast of synthetic monthly demand, read from a folder of yearly exports: trend plus seasonal levels, an 80% prediction band, the forecast as CSV |

## Code

| path | role |
|---|---|
| `src/blocks/core/graph.py`, `worker.js` | the executor in Pyodide, and the page's bridge to it |
| `src/blocks/core/spec.py` | reads an app with `ast`: nodes, settings, metrics, datasets, order, imports |
| `src/blocks/core/build.py` | the page as one file, with every block's files; the pinned Pyodide runtime, cached in `.cache/` |
| `src/blocks/core/cli.py` | `serve`, `build`, `baseline`, `verify` (headless Edge: Run, then every node's page drawn) |
| `src/blocks/core/page/` | `app.js` (the graph, pages, settings and the kit blocks draw with), `app.css` (the one theme) |
| `src/blocks/ui/` | the blocks, each a `.py`, a `.js` and maybe a `.css`; `_kit.py` and `_kit.js`, what they share |

Derived from `blocks`, with its run browser, plugins, sandboxed views and more left out.
