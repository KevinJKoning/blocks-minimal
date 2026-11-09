# blocks

Apps as a graph of Python functions, with UI blocks on top, run in the browser (Pyodide) and
shipped as one offline HTML file. The framework is small enough to read whole, and its code
is the reference: this page says what the code can't, and where to look.

```python
# projects/<app>/nodes/train.py
"""Ridge regression of the reference on the features."""   # the top of the node's page (Markdown)
from typing import Annotated
from blocks import Range, ui

METRICS = {"rmse": {"label": "train RMSE", "goal": "min"}}   # labels for the output's numbers


def train(featurize, *, alpha: Annotated[float, Range(0.0001, 10, log=True)] = 0.1):
    ...                                    # featurize: that node's output, in memory
    return {"coef": w, "rmse": rmse}


def view(out):                             # optional: the node's results, in order
    return [ui.metrics(), ui.table(...)]
```

## An app

```
projects/<app>/
  README.md        "# Title", then the overview's text
  nodes/<name>.py  one node: def <name>(inputs..., *, settings...)
  nodes/<name>/    a fork: the node written more than one way, <option>.py each; README.md asks its question
  choices.json     {fork: option}: the app's choice at each fork it has decided
  data/<name>.*    a dataset, read by a parameter <name>: its path
  data/<name>/     a dataset of files (exports by month, say): their paths, in name order
  data/<name>.md   what the dataset is, atop its page, for whoever replaces it
  data/*.py        a script that makes or fetches data; run natively, by hand, never in the app
  <helper>.py      code the nodes share (`from helper import f`); nodes can't import each other
  ui/<name>.*      a block only this app draws, used as `from ui.<name> import <name>`
  baseline.json    the run that verify compares with
```

- **Inputs** are positional parameters: another node's output, or a dataset, by name. So a
  node never shares its name with a dataset, nor with a module its file imports.
- **Settings** are keyword-only parameters with literal defaults, and become controls: a
  bool a checkbox, `Annotated[float, Range(min, max)]` a slider, `Annotated[str,
  Choices("a", "b")]` a menu, any other number or string a box. A setting is the app's, by
  its name: every node that declares it reads one value, so each declares it identically.
- **Every number in the output's dicts** (nested too, not in lists or tables) is a metric:
  recorded, compared with the baseline, shown. `METRICS = {key: "label" | {label, goal,
  percent}}` labels the ones that matter, in order (`fit.shape` for `{"fit": {"shape": ...}}`);
  `goal: "min"` or `"max"` colours changes, `percent: True` marks a share, and `answer: True`
  marks a number the app exists to produce: the overview leads with it.
- **Packages** are found from the imports, and come from Pyodide, not the venv: the names
  they import as are in `.cache/pyodide/<version>/pyodide-lock.json`. Node code runs only in
  the page, never with native Python.
- **Run computes only what is stale**: `Graph.key` in `core/graph.py` is what makes a node
  stale: its file, its settings, its inputs' keys, and every helper module, so editing a
  helper re-runs every node.
- **The page**: the graph is its table of contents, in the graph's order (`spec.load`'s
  `order`, graphlib's): a node after the nodes it reads; beyond that the order is
  graphlib's, not the file names'. A node's page is its docstring (its first paragraph is its summary on the
  overview, on one line), settings, results and code; a dataset's page lets a reader replace it.

## Forks

An analysis is a string of judgment calls, and a reader shown one path through them can only
second-guess each from the code. So a judgment call is written both ways: a **fork** is a
folder `nodes/<name>/` whose files are each a whole node `<name>`, an **option**, with its own
docstring, settings, `METRICS` and view; what the options share is a helper module's. The
folder's `README.md` asks the fork's question (`# ...`) and says what bears on it.

- **A run takes one option at each fork**: the app's choice (`choices.json`), else the first
  by name, and the fork is *open*, for a person to decide. `blocks choose` records a choice.
- **Run explores every path** through the forks when the app has an answer (`answer: True`).
  Outputs are kept by key, so paths share all they have in common: a hundred paths cost a
  few runs of each node, and moving the page to another path costs nothing. Past 64 paths,
  only the page's path and those one fork away from it are run (`graph.paths`).
- **The overview is the map**: the answer on the page's path, a dot for every path's answer,
  and the forks, the one that moves the answer most first (`graph.spread`: how far the answer
  moves when that fork alone changes, in the answer's units); the forks that barely move it
  are folded away. A fork's page sets its options side by side.
- **A fork is decided on evidence about the fork**, its options' own numbers and views, not
  by which answer pleases; an answer scored against a known truth (windstorm's `recovery`)
  is evidence too. The page always shows the spread, whatever is chosen.
- **The baseline keeps every path's answer**, and `verify` compares them all: an option
  nobody is looking at still has to run.
- **Each option writes its own `METRICS`**, a literal in its file, never imported from the
  helper, and where the fork's node holds an answer every option marks the same keys.
- An option may read other inputs than its siblings do. What a fork cannot do yet is change
  which nodes come after it.

## Commands

```sh
.venv/bin/blocks run APP          # headless: every node's status, metrics and errors
    --set NAME=VALUE              #   with another setting (VALUE is JSON, else text)
    --choose FORK=OPTION          #   along another path; every path's answer is printed either way
    --output NODE                 #   print only that node's output, as JSON
    --shots DIR [NODE ...]        #   a PNG of those pages (_overview too), else of all: DIR/<app>/<node>.png
.venv/bin/blocks choose APP FORK=OPTION ...   # record the app's choice in choices.json
.venv/bin/blocks baseline APP     # keep the run as baseline.json, if nothing failed
.venv/bin/blocks verify [APP]     # compare with the baseline (graph.compare): metrics, digests, data keys, paths; a failed view fails it
.venv/bin/blocks build [APP]      # dist/<app>.html, offline, verified; --no-data leaves the data out
.venv/bin/blocks serve            # http://127.0.0.1:8765/<app>/, rebuilt on every request
.venv/bin/python -m pytest -m "not browser"
```

Set up with `python3.13 -m venv .venv`, `.venv/bin/pip install --require-hashes -r
requirements.txt`, `.venv/bin/pip install --no-deps --no-build-isolation -e .` and
`.venv/bin/playwright install chromium`.

The apps' code is trusted; their packages are not. The page's Content-Security-Policy keeps
Python off the network (a built page reaches nothing; a served one, only its dev server's
runtime files), the headless browser keeps its sandbox, the dev server answers only to
localhost, and native dependencies are pinned with hashes.

## Blocks

| `blocks.ui` | draws |
|---|---|
| `markdown(text)` | Markdown |
| `metrics()` | the node's metrics, with the change since the last run and the baseline's value |
| `table(rows, ...)` | a DataFrame, pyarrow Table, `{column: values}` or list of dicts |
| `chart(x, series, ...)` | lines, steps or dots, with bands, error bars, reference lines, log axes |
| `bars(categories, series, ...)` | a bar or dot per category, with intervals and a reference (a forest plot) |
| `figure(image, caption=None)` | SVG text or PNG bytes |
| `histogram(values, ...)` | counts in round bins, of one set or of groups compared |
| `heatmap(rows, columns, values, ...)` | a value per row and column, shaded |
| `map(shapes, values=None, ...)` | polygons and points shaded or named, in layers, over a grid, under lines |
| `row(*blocks, title=None)` | blocks side by side |
| `download(name, value, title=None)` | a file to take away: a table as `.csv`, `.json` or `.parquet`, text, bytes |

Each one's parameters are its docstring, in `src/blocks/ui/<name>.py`; how it draws is
`<name>.js`. AGENTS.md says how to add one.

## Code

| path | what |
|---|---|
| `src/blocks/core/spec.py` | reads an app with `ast`: nodes, inputs, settings, metrics, datasets, order |
| `src/blocks/core/graph.py`, `worker.js` | runs the graph in Pyodide: keys, cache, metrics, digest, views, `record`, `compare` |
| `src/blocks/core/build.py` | the page as one file, and its worker's script; Pyodide pinned and cached in `.cache/` |
| `src/blocks/core/cli.py` | the commands; `run_page` drives the page headlessly |
| `src/blocks/core/page/` | `app.js`, the page and `window.blocks`; `app.css`, the theme |
| `src/blocks/ui/` | the blocks; `_kit.py`, `_kit.js` and `_kit.css`, what they share |

Example apps: `sensor-calibration` (a modelling pipeline, with delivered files), `parcels`
(a geodatabase read with GDAL), `windstorm` (a GLM and credibility; its own `tiles` block),
`michigan-census` (Census data, county maps) and `electricity-demand` (a forecast from a
folder of exports).
