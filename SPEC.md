# Blocks workbench: spec (draft)

Status: a draft for discussion. It is written to be built **from `main`**, not from the
branch it sits on (`claude/ecstatic-galileo-ejeb11`), which is a prototype to borrow from:
"Carried over" below says what.

## Why

`main` does one thing: an agent, in chat, turns a question into an elegant offline page. The
person reviews the result. That is still right for some work, and stays (direct mode).

What it does not give is a way for a person to be hands-on while the analysis takes shape:
to be at every decision point, see several results and choose among them, and change the
computation themselves. The more a person tinkers directly, the more they learn; the goal
is to make that tinkering very fast. The prototype showed two things: the idea of forks
works (four Haiku agents built forked apps from the docs alone), and putting the process
and the artifact in one page confuses both.

## Three things, kept apart

| | What it is | Where it lives |
|---|---|---|
| **Blocks** | The tool: the workbench, the compilers, the runtime and the block library | This repo. It holds no project but small examples and tests |
| **A project** | One analysis being worked out: nodes, forks, data, decisions | Its own git repo. Git is its trail |
| **Targets** | What a project compiles into, for its readers | Build output; never edited by hand |

Rules that follow:

- **Process is not artifact.** The workbench is where learning happens. A target is good
  documentation: it shows the result is reproducible and lets a reader try other data or
  settings. It is not a place to explore.
- **Lean on git.** A project's history of what was tried, rejected and why is its git
  history. Blocks writes no journal, keeps no archive of retired options, and invents no way
  to browse the past.
- **The person decides and accepts.** An agent proposes; choosing an option and accepting a
  state as the reference are the person's acts.
- **A target never needs the workbench**, and the workbench is never mistaken for a target:
  it has its own look.

## A project repo

```
README.md          "# Title", then the question and what the project is
nodes/<name>.py    a node, as on main
nodes/<name>/      a fork: <option>.py each a whole node; README.md asks its question
data/              datasets and the scripts that make them, as on main
<helper>.py        code that nodes share
decisions.json     {fork: {option, why}}: what the person chose, and their reason
accepted.json      the run the person last accepted (main's baseline.json, renamed for whose it is)
```

- A fork with no entry in `decisions.json` is **open**.
- The answer is marked in `METRICS` (`answer: True`), as in the prototype.
- Accepting and deciding change files; committing them is ordinary git. The workbench may
  offer to commit, with the reason as the message, but the repo is the person's.
- Retiring an option is deleting its file. It is still in git.
- A project with no forks is a direct-mode project. Nothing else distinguishes the modes.

## The workbench

A local server over a project repo, with the pipeline running in the browser (Pyodide), so
most tools answer in seconds without an agent.

**It opens on movement, not on the document**: what changed since the accepted state
(numbers before and after, views that differ, forks that appeared), then what is waiting on
the person (open forks, each with the agent's recommendation), then the map of paths and
the nodes.

**It has a tray of tools**, acting on the selected node or result:

| Tool | Does | Agent needed |
|---|---|---|
| Edit | Change a node's code in the page; what reads it reruns | No |
| Fork here | Copy the node as a new option to change, leaving the original | No |
| Compare | Pin a result and view another against it: views, numbers, a diff of the code | No |
| Inspect | Open any input or output as a table or distribution; run an expression on it | No |
| Decide | Close a fork, with a reason | No |
| Accept | Make the current state the reference | No |
| Ask | Send a note about this chart, option or line to the agent | Yes |

- **Every path is run** and kept by key, so switching and comparing cost nothing (prototype).
- **It writes only inside the project repo** (`nodes/`, helpers, `decisions.json`,
  `accepted.json`), only on localhost, and only in workbench mode.
- **It looks different on purpose**: its own colour scheme, the tray, a standing label that
  this is work in progress.
- **The agent's part**: draft the first version, propose forks with a recommendation, answer
  notes. It does not decide or accept. The workbench has its own short agent guide; an agent
  in direct mode never reads it.

## Targets

`blocks compile --target ...` reads a project and writes a target. Both targets hold **one
path**: each fork's chosen option as a plain node, nothing of the others but the record of
the decision. A project with an open fork does not compile.

### `html`: for people

Main's offline page: one self-contained file, verified offline, with settings and data a
reader can change and rerun. Added: the answer first, and each decision with its question,
the choice, the reason, and what each alternative gave when accepted.

### `repo`: for agents at a command line

A directory that is a git repo of plain files, in the manner of DVC: nothing to render,
everything greppable.

```
README.md            the question, the answer, how to reproduce and verify
pipeline.yaml        stages: each node's command, deps, params, outs, metrics
params.yaml          the settings
nodes/<name>.py      the chosen path's code, plain
data/                the datasets, or pointers with their hashes
results/<node>/      metrics.json, outputs as files (csv, parquet), view.md
decisions.md         each question, choice, reason, and the alternatives' answers
lock.json            every stage's input and output digests
```

- `view.md` is the node's view as Markdown: text, tables as tables, a chart as its data
  file plus a sentence saying what it shows.
- An agent reproduces with one command, verifies against `lock.json`, changes a param or a
  dataset and reruns only what is stale.

## Blocks, the tool

```
src/blocks/core/        spec, graph (keyed cache), record and compare
src/blocks/ui/          the block library
src/blocks/workbench/   server, page, tray, its own styles and agent guide
src/blocks/targets/     html, repo
examples/               small projects for tests and docs
```

Commands: `blocks new`, `blocks bench` (the workbench), `blocks run`, `blocks compile
--target html|repo`, `blocks verify`.

The core stays near main's size. Forks are read by the workbench and the compilers; a
target's runtime knows nothing of them.

## Carried over from the prototype

- Forks as folders, options as whole nodes, the fork's `README.md` as its question.
- `answer: True`; running every path; `spread` (how far each fork alone moves the answer);
  the overview's strip and ranked fork list, which become the workbench's map.
- The cache keyed by content, and the cap past 64 paths.
- The guards the Haiku trial motivated: `METRICS` must be a literal in each option, options
  mark the same answers, a failed path prints its error, a fork that moves no answer is noted.
- Compiling one path with decisions shown from the accepted record.

Not carried over: fork UI in the artifact's page; the agent recording the baseline and the
choice; choices without reasons.

## Open questions

1. **How the `repo` target runs.** Natively (pinned requirements, real files, fast for an
   agent) or through headless Pyodide (identical to the page, slow to start). Native is the
   natural fit; digests may then differ from the page's in the last bits, so `verify` needs
   a stated tolerance or the two targets need separate locks.
2. **DVC itself or its shape.** Emit real `dvc.yaml`/`dvc.lock` so DVC users get its tooling,
   or our own files with no dependency.
3. **How Ask reaches the agent.** Text for the chat the person is already in, or a file in
   the repo the agent watches. Depends on where people sit while working.
4. **An open fork's default.** The prototype takes the first option by name, which put one
   trial app on the option its own agent argued against. Likely: the agent's recommendation,
   recorded as such and shown as not yet decided.
5. **Settings.** Left as they are. A value worth memorialising becomes a fork.
6. **Charts in `view.md`.** Data and a sentence, or a rendered image as well.
7. **Where projects are created**, and whether `blocks new` initialises the git repo.

## Order of work

1. From main: split the repo layout (core, ui, workbench, targets, examples) with nothing new.
2. Forks, paths and the keyed cache in core and workbench; the `html` target compiling one path.
3. The workbench's own look and first screen; Decide and Accept with reasons.
4. Compare; then Edit and Fork here (the server's writes); then Inspect; then Ask.
5. The `repo` target, once question 1 is settled.
6. A trial as on main: agents build projects from the docs; success is a project that
   compiles to both targets with every fork decided by a (simulated) person, not the agent.
