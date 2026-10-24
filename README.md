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
  packages are the imports.
- **Cached.** Each output is keyed by its node's code, settings and inputs' keys. Changing
  `alpha` makes `train` and what reads it stale; Run re-runs just those.
- **The page is blocks.** The graph is the table of contents. Each node is one page: its
  docstring, its settings, its results (its view, in the order the view gives) and its
  code. Each dataset has a page too, where it can be replaced, and the overview gathers
  datasets and downloads.
- **Verified.** Every run leaves a record (settings, data keys, every node's metrics and
  output digest). `blocks baseline` keeps one; `blocks verify` and `blocks build` compare
  against it, and the page shows each metric against it. A view that fails, in Python or
  on the page, fails them too.

## Quick start

```sh
python3.13 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/pip install --no-deps --no-build-isolation -e . && .venv/bin/playwright install chromium
.venv/bin/blocks serve                    # http://127.0.0.1:8765/<app>/, rebuilt on every request
.venv/bin/blocks baseline parcels         # run headlessly, keep projects/parcels/baseline.json
.venv/bin/blocks verify                   # run every app, compare with its baseline
.venv/bin/blocks build                    # dist/<app>.html, verified offline from file://
.venv/bin/python -m pytest                # -m "not browser" for the fast ones
```

The apps' code is trusted; their packages are not. The page's Content-Security-Policy keeps
the worker off the network (a built page reaches nothing; a served one, only its dev server),
headless Chromium keeps its sandbox, the dev server answers only to `127.0.0.1` and
`localhost`, and the native dependencies are pinned with hashes in `requirements.lock`.

## An app

```
projects/<app>/
  README.md          "# Title", then what the app is for (the overview page)
  nodes/<name>.py    one node: def <name>(inputs..., *, settings...)
  data/<name>.*      a dataset; a node reads it with a parameter <name> and gets its path
  *.py               helpers the nodes import
  ui/<name>.py|js|css  a block only this app draws (see Blocks)
  baseline.json      the run every check compares with
```

| in a node file | means |
|---|---|
| positional parameters | what it reads: a node's output, or a dataset's path |
| keyword-only parameters | its settings: literal defaults, `Annotated[type, Range(min, max, step, log=)]` or `Choices(...)` |
| the return value | its output, any Python value, passed in memory to the nodes that read it; the numbers in it are its metrics |
| the docstring | the top of its page (Markdown) |
| `METRICS = {key: "label" \| {label, goal}}` | labels for its numbers, in order; `goal: "min" \| "max"` colours changes |
| `def view(out)` | its results: a list of blocks |

## Blocks

| `blocks.ui` | draws |
|---|---|
| `markdown(text)` | Markdown |
| `metrics()` | the node's metrics, labelled, with the change since the last run and the baseline's value |
| `table(rows, title=None, text=())` | a DataFrame, pyarrow Table, `{column: values}` or list of dicts (200 rows shown); `text` names the columns whose numbers name something (a year), read as written |
| `chart(x, series, title, x_label, y_label, kind, bands=None, x_text=False)` | `series` is `{name: ys}`; `kind` is `line`, `scatter` or `{name: kind}`; `bands` is `{name: (lows, highs)}`, shaded around that series; `x_text` when x is years |
| `figure(image, caption=None)` | SVG text or PNG bytes |
| `histogram(values, bins=None, title, x_label, mark=None)` | counts in equal bins of a round width (about √n of them unless `bins` says), a dashed line at `mark` (0 for residuals) |
| `map(shapes, values=None, names=None, title, label, lines=None, center=None)` | polygons (shapely, WKB or GeoJSON geometries) shaded by value, in their own coordinates, diverging from `center` if given; `lines` drawn on top (a coastline) |
| `download(name, value, title=None)` | a file to take away, as a card with a Download button: a table as `.csv`, `.json` or `.parquet`, text, or bytes |

A block is the files of one name in `src/blocks/ui/`, or in an app's `ui/` when only that app
draws it. Python determines meaning, JavaScript presentation: `<name>.py` returns the dict
`{"type": "<name>", ...}` and decides what the data means (a colour scale, its centre, what is
missing); `<name>.js` lays it out and draws it (`RENDER.<name>`, with the page's kit and
`ui/_kit.js`); `<name>.css`, if it needs one, styles it under `.<name>` in the theme's colours.
A node uses an app's block with `from ui.<name> import <name>`. A new block, or a new
parameter on one (the same picture with more on it, like a band on a chart), never changes
the core.

## Example apps

| app | shows |
|---|---|
| `sensor-calibration` | a modelling pipeline: cleaning, features, ridge regression, held-out evaluation, delivered files |
| `parcels` | a zipped Esri geodatabase read with GDAL in the browser, then areas and a summary |
| `windstorm` | geodata joined to policies; a Poisson GLM with a wind-load offset and Bühlmann–Straub credibility, checked against its synthetic truth; its own `tiles` block in `ui/` |
| `michigan-census` | official Census data fetched natively and analysed offline; settings shared through small nodes, county maps that diverge from zero |
| `electricity-demand` | a seasonal forecast of synthetic monthly demand: trend plus seasonal levels, an 80% prediction band, the forecast as CSV |

## Code

| path | role |
|---|---|
| `src/blocks/core/graph.py`, `worker.js` | the executor in Pyodide (load nodes, keys, cache, run, metrics, digests, views; run records and `compare`) and the page's bridge to it |
| `src/blocks/core/spec.py` | reads an app with `ast`: nodes, settings, metrics, datasets, order, imports |
| `src/blocks/core/build.py` | the page as one file, with every block's script and styles (the library's, then the app's); the pinned Pyodide runtime, cached in `.cache/` |
| `src/blocks/core/cli.py` | `serve`, `build`, `baseline`, `verify` (headless Chromium: Run, then every node's page drawn) |
| `src/blocks/core/page/` | `app.js` (the graph, pages, settings and the kit blocks draw with), `app.css` (the one theme) |
| `src/blocks/ui/` | the blocks, each a `.py`, a `.js` and maybe a `.css`; `_kit.py` and `_kit.js`, what they share |

Derived from `blocks`: the same idea with its run browser, plugins, sandboxed views,
schemas, themes, integrity manifest and dev-server APIs left out.
