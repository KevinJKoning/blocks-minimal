# Working in this repo (for agents)

Read `README.md` first. Never run node code with native Python; it runs in Pyodide, in the
page (`blocks serve`) or headless (`blocks verify`).

## Iterating on an app

Edit node files, then reload `/<app>/` and drive it with `window.blocks`: `set({...})`
marks what is stale, `run()` computes it and returns the run record, `output(node)` reads
an output, `state()` has every result and its blocks.

- One function per file in `nodes/`, named after the file. Keep nodes small, one concern
  each; a helper several nodes use goes outside `nodes/`.
- Return plain values (dicts of numbers and arrays, pandas or pyarrow tables). Numbers at
  the top of a dict are metrics; label the ones that matter in `METRICS`.
- The docstring tops the node's page: what it does and why.
- `view(out)` returns blocks in the order a reader should see them. Anything meant to leave
  the app is a `ui.download`.

## Keeping the core small

The core is `graph.py`, `spec.py`, `build.py`, `cli.py` and the page. Add to it only what
every app needs. Anything else is a block (`ui.py` + its renderer in `app.js`) or a node.

## Checks

- `blocks baseline APP` once it runs; `blocks verify` after every change. Re-record the
  baseline only when results changed on purpose.
- `blocks build` writes `dist/<app>.html` and verifies it offline.
- `.venv/bin/python -m pytest` (`-m "not browser"` for the fast tests).
- Packages must have a Pyodide build; they are found from the imports.
