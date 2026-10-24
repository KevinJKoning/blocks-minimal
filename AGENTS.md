# Working in this repo (for agents)

Read `README.md` first. Never run node code with native Python; it runs in Pyodide, in the
page (`blocks serve`) or headless (`blocks verify`).

## Iterating on an app

Edit node files, then reload `/<app>/` and drive it with `window.blocks`: `set({...})`
marks what is stale, `run()` computes it and returns the run record, `output(node)` reads
an output, `state()` has every result and its blocks, `show(node)` opens a page. Changes
to apps, `src/blocks/ui/`, `graph.py`, `worker.js` and `page/` show on reload; after
changing `spec.py`, `build.py` or `cli.py`, restart `blocks serve`.

- One node per file in `nodes/`, named after the file. Keep nodes small, one concern
  each; a helper several nodes use goes outside `nodes/`.
- Return plain values (dicts of numbers and arrays, pandas or pyarrow tables). A dict's
  numbers are metrics; label the ones that matter in `METRICS`.
- The module docstring tops the node's page: what it does and why.
- A view sees only its own node's output: return what it needs to draw (a territory's
  geometry for a map, say), not just the numbers.
- `view(out)` returns blocks in the order a reader should see them, and the page keeps that
  order. Anything meant to leave the app is a `ui.download`; put a node's downloads first
  in its view, since what a node hands over is usually what its reader came for.

## Keeping the core small

The core is `src/blocks/core/`: the executor, the build and the page's shell. Add to it only
what every app needs; anything else is a block or a node. A block is its files in
`src/blocks/ui/`, and growing it stays out of the core:

- The core never names a content block: it draws whatever `RENDER[type]` is, and knows only
  that the overview gathers `download`s.
- `<name>.py` settles every choice (a colour scale, its centre); the page never guesses what
  data means. `<name>.js` only lays out and paints, with the kit (`h`, `fmt`, `card`, ...).
- `ui` exports only blocks. A helper stays private to its block (each script gets its own
  scope) and moves to `_kit.py`, or into the page's kit, only once a second block needs it.
- Block CSS uses the theme's colours (`--ink`, `--ramp-hi`, ...), never its own.

## Checks

- `blocks baseline APP` once it runs; `blocks verify` after every change (`blocks build`
  also verifies). Re-record the baseline only when results changed on purpose.
- `.venv/bin/python -m pytest` (`-m "not browser"` for the fast tests).
- Packages must have a Pyodide build; they are found from the imports.
