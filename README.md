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
  against it, and the page shows each metric against it.

## Quick start

```sh
python3.13 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/pip install --no-deps --no-build-isolation -e . && .venv/bin/playwright install chromium
.venv/bin/blocks serve                    # http://127.0.0.1:8765/<app>/, rebuilt on every request
.venv/bin/blocks baseline titanic         # run headlessly, keep projects/titanic/baseline.json
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
  *.py, lib/...      helpers the nodes import
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
| `metrics(values=None, title=None)` | the node's metrics, labelled, with the change since the last run and the baseline's value |
| `table(rows, columns=None, title=None)` | a DataFrame, pyarrow Table, `{column: values}` or list of dicts (200 rows shown) |
| `chart(x, series, title, x_label, y_label, kind)` | `series` is `{name: ys}`; `kind` is `line`, `scatter` or `{name: kind}` |
| `figure(image, caption=None)` | SVG text or PNG bytes |
| `map(shapes, values=None, names=None, title, label, lines=None, points=None)` | polygons (shapely or GeoJSON geometries) shaded by value, in their own coordinates; `lines` drawn on top (a coastline), `points` as dots |
| `download(name, value, title=None)` | a file to take away, as a card with a Download button: a table as `.csv`, `.json` or `.parquet`, text, or bytes |

A block is a dict made by a function in `src/blocks/ui.py` and drawn by the function of
the same name in `RENDER` (`src/blocktool/templates/app.js`). A new block is one of each,
plus a few CSS rules only if it draws something new. A block that shades by value uses the
theme's ramp: `ramp(v, lo, hi)` for a colour and `scale(lo, hi, label)` for its legend.

## Example apps

| app | shows |
|---|---|
| `sensor-calibration` | a modelling pipeline: cleaning, features, ridge regression, held-out evaluation, delivered files |
| `titanic` | three analyses of one dataset side by side, with their caveats |
| `parcels` | a zipped Esri geodatabase read with GDAL in the browser, then areas and a summary |
| `windstorm` | geodata joined to policies; a Poisson GLM with a wind-load offset and Bühlmann–Straub credibility, checked against its synthetic truth |

## Code

| file | role |
|---|---|
| `src/blocks/graph.py` | the executor (in Pyodide): load nodes, keys, cache, run, metrics, digests, views; run records and `compare` |
| `src/blocks/ui.py` | the blocks |
| `src/blocktool/spec.py` | reads an app with `ast`: nodes, settings, metrics, datasets, order, imports |
| `src/blocktool/build.py` | the page as one file; the pinned Pyodide runtime, cached in `.cache/` |
| `src/blocktool/cli.py` | `serve`, `build`, `baseline`, `verify` (headless Chromium) |
| `src/blocktool/templates/` | `app.js` (graph, pages, blocks, settings, worker bridge), `worker.js`, `app.css` (the one theme) |

Derived from `blocks`: the same idea with its run browser, plugins, sandboxed views,
schemas, themes, integrity manifest and dev-server APIs left out.
