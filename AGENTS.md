# Working in this repo (for agents)

Read `README.md` first. Never run node code with native Python, its helpers included; it runs
in Pyodide, in the page (`blocks serve`) or headless (`blocks run APP`), and the venv has none of
its packages. A script in `data/` that makes or fetches a dataset is the exception: run it natively.

## Iterating on an app

Edit node files, then `blocks run APP` to see every node's status, metrics and errors. In
the page, reload `/<app>/` and drive it with `window.blocks`: `set({"node.param": v})`
marks what is stale, `run()` computes it and returns the run record, `output(node)` reads
an output, `state()` has every result and its blocks, `show(node)` opens a page. Changes
to apps (their `ui/` too), `src/blocks/ui/`, `graph.py`, `worker.js` and `page/` show on reload; after
changing `spec.py`, `build.py` or `cli.py`, restart `blocks serve`.

- One node per file in `nodes/`, named after the file. Keep nodes small, one concern
  each; a helper several nodes use goes outside `nodes/`. A node sees only its own
  settings: one that others need comes back in its output, or is a small node of its own.
- Return plain values (dicts of numbers and arrays, pandas or pyarrow tables), and label
  the numbers that matter in `METRICS`.
- The module docstring tops the node's page: what it does and why.
- A view sees only its own node's output: return what it needs to draw (a territory's
  geometry for a map, say), not just the numbers.
- `view(out)` returns blocks in the order a reader should see them. Anything meant to leave
  the app is a `ui.download`, first in its view: what a node hands over is usually what its
  reader came for.

## Keeping the core small

The core is `src/blocks/core/`: the executor, the build and the page's shell. Add to it only
what every app needs; anything else is a block or a node. A block is the files of its name
in `src/blocks/ui/` (or an app's `ui/`): `<name>.py` returns `{"type": "<name>", ...}`,
`<name>.js` adds `RENDER.<name> = (b, n) => element`, and an optional `<name>.css` styles it.
Growing a block stays out of the core:

- The core draws whatever `RENDER[type]` is and names two blocks: `metrics`, the view of a
  node without one, and `download`, which the overview gathers. Never a third.
- Python determines meaning, JavaScript presentation. `<name>.py` decides what the data
  means (a colour scale, its centre, what is missing, a year that is a name and not a
  quantity); the page never guesses it, and formats every number as a quantity. `<name>.js`
  decides layout (ticks, margins, sizes), with the kit listed above `// @blocks` in
  `page/app.js`.
- Same picture with more on it (a band on a chart): a parameter on that block. A different
  picture: a new block. A block only one app draws goes in `projects/<app>/ui/`, the same
  files, used as `from ui.<name> import <name>`; it moves to `src/blocks/ui/` when a second
  app wants it, with a line in `ui/__init__.py` and a row in README's table.
- A block that holds blocks keeps them in its `blocks` field (as `ui.row` does) and draws
  each with `paint` from the kit; the page looks there for downloads too.
- `ui` exports only blocks. A helper stays private to its block (each script gets its own
  scope) and moves to `ui/_kit.py` or `ui/_kit.js` once a second block needs it; block
  helpers never go in `core/`.
- A renderer's root element has the block's type as its class (`h("figure", { class:
  "map" })`). Block CSS sits under it (`.map .scale`, not `.scale`) and uses the theme's
  colours (`--ink`, `--ramp-hi`, `--better` and `--worse` for green and red, ...), never its
  own. `test_every_block_is_its_files` checks the scoping, and that each block has its
  renderer.

## Checks

- `blocks baseline APP` once it runs; `blocks verify` after every change (`blocks build`
  also verifies). Verify also draws every node's page, so a view that fails, in Python or
  in its renderer, fails it. Re-record the baseline only when results changed on purpose
  (a new node or output too).
- `.venv/bin/python -m pytest` (`-m "not browser"` for the fast tests).
- Packages must have a Pyodide build; they are found from the imports.
