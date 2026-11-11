# Working in this repo (for agents)

Read `README.md`, then the code it points to: the core (`src/blocks/core/`) and a block or
two are short enough to read whole, and they are the reference.

## The loop

1. Edit an app's files. One node per file, one concern each.
2. `blocks run APP` prints each node's status, metrics and errors; `--set`, `--output` and
   `--shots` as README says. Once you have changed a view, look at its page, not every
   page: `--shots DIR NODE` draws only that one. A new app: check its numbers with `--output`
   first, then look at all its pages once.
3. `blocks baseline APP` when the results are right. A baseline holds each node's metrics
   and output digest, not its view: re-record it after adding a node or an output key, or
   changing results on purpose; a change to a view alone needs none.
4. `blocks verify APP` and `.venv/bin/python -m pytest -m "not browser"` must pass;
   `blocks build APP` verifies the offline page too.

The venv has none of the app's packages: check numbers natively with the standard library
only (a `data/` script is the one thing to run natively). In the page, `window.blocks`
(end of `page/app.js`) drives it.

## Nodes and views

- A view gets only its own node's output: work out what it needs from that output where
  you can (a share, a total); a new output key changes results and needs a re-recorded
  baseline. `view(out)` lists blocks in the order a reader should see them; downloads go
  first, since what a node hands over is usually what its reader came for.
- A part of a node's work that has a name of its own (a noun, one sentence, a result worth
  checking) is a step: a function at the top of the file with a docstring, its result in the
  output under its name. The view puts what shows that result in `ui.step(fn, ...)`, so the
  step's text, blocks and code read as one; what the step's docstring says, the node's does
  not repeat. Most nodes are one thought and have none; don't cut a derivation into steps to
  have some. Adding a step changes no results.
- To reuse a node's work under other inputs or settings, move it into a helper module and
  call it from both nodes; a node can't read another's settings but by sharing their name.

## Blocks

A block is the files of its name: `<name>.py` returns `{"type": "<name>", ...}` (with
`_kit.block`), `<name>.js` sets `RENDER.<name> = (b, node) => element`, whose root element
has the class `<name>`, and an optional `<name>.css` styles it, every rule under `.<name>`
(the test checks). A library block lives in `src/blocks/ui/` and is exported in
`ui/__init__.py`, with a row in README's table; a block only one app draws lives in
`projects/<app>/ui/`.

- More on the same picture (a band on a chart) is a parameter of that block; a different
  picture is a new block.
- Python decides meaning: colours on the ramp (`_kit.shade`, `_kit.ramp`), a centre, what is
  missing, which numbers are names (`text`) or shares (`percent`). The page formats every
  number as a quantity. JavaScript decides layout, with the page's kit (above `// @blocks`
  in `page/app.js`: `h`, `fmt`, `num`, `size`, `markdown`, `card`, `save`, `paint`,
  `records`, `S`) and `_kit.js` (`hue`, `ticks`, `logTicks`, `place`, `legend`).
- A block's own classes never reuse the page's (`page/app.css`): `card`, `cards`,
  `card-label`, `setting`, `settings`, `button`, `crumb`, `dag`, `nodes`, `prose`, `status`,
  `differs`, `secondary`, `dim`, `ok`, `about`, `title`; it may use `muted`, `small`, `note`
  and `error` as the page does.
- A helper stays in its block until a second block needs it; then it moves to `_kit.py`,
  `_kit.js` or `_kit.css`. Colours are the theme's variables (`--ink`, `--ramp-hi`,
  `--better`, `--worse`, ...).
- A block that holds blocks keeps them in `blocks`, and draws each with `paint`.
- The core never names a block but `metrics` (a node without a view) and `download` (the
  overview gathers them). Changing a block, or adding one, never touches `src/blocks/core/`.
