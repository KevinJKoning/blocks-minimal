"""Read an app from its files (README.md has the layout) with ast, since node code never runs
natively: its nodes, their inputs, settings and metrics, its forks and their options, its
datasets, the order, the imports.
"""
from __future__ import annotations

import ast
import graphlib
import json
from pathlib import Path

SKIP = {"data", "__pycache__", "baseline.json"}


def _literal(node, where):
    try:
        return ast.literal_eval(node)
    except ValueError:
        raise ValueError(f"{where}: must be written out as a literal (an app is read as source, not run)") from None


def _setting(arg: ast.arg, default, where) -> dict:
    s = {"default": _literal(default, where)}
    ann = arg.annotation
    if isinstance(ann, ast.Subscript) and getattr(ann.value, "id", getattr(ann.value, "attr", "")) == "Annotated":
        ann, *marks = ann.slice.elts
        for m in marks:
            kind = getattr(m.func, "id", None) if isinstance(m, ast.Call) else None
            if kind == "Range":
                s |= dict(zip(("min", "max", "step"), (_literal(a, where) for a in m.args)))
                s |= {k.arg: _literal(k.value, where) for k in m.keywords}
            elif kind == "Choices":
                s["choices"] = [_literal(a, where) for a in m.args]
                if s["default"] not in s["choices"]:   # else the menu shows one choice while the node runs another
                    raise ValueError(f"{where}: its default {s['default']!r} is not one of its choices {s['choices']}")
    s["type"] = getattr(ann, "id", None) or type(s["default"]).__name__
    return s


def read_node(path: Path, name: str, file: str) -> dict:
    """The node name as path's file defines it; file is the path within the app."""
    tree = ast.parse(path.read_text(), str(path))
    fns = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    if name not in fns:
        raise ValueError(f"{path}: defines no function {name}()")
    a = fns[name].args
    if a.vararg or a.kwarg:
        raise ValueError(f"{path}: {name}() takes no *args or **kwargs")
    if None in a.kw_defaults:
        raise ValueError(f"{path}: every setting needs a default")
    if name in {x.asname or x.name.split(".")[0] for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for x in n.names}:
        raise ValueError(f"{path}: imports a name {name}, which the node's own function {name}() shadows; import it under another name")
    consts = {t.id: s.value for s in tree.body if isinstance(s, ast.Assign) for t in s.targets if isinstance(t, ast.Name)}
    metrics = _literal(consts["METRICS"], f"{path}: METRICS") if "METRICS" in consts else {}
    for k, m in metrics.items():
        if not isinstance(m, str) and (not isinstance(m, dict) or set(m) - {"label", "goal", "percent", "answer"}):
            raise ValueError(f"{path}: METRICS[{k!r}] is a label, or a dict of label, goal (\"min\" or \"max\"), percent (True for a "
                             "share) and answer (True for a number the app exists to produce)")
    doc = ast.get_docstring(tree) or ""
    return {
        "file": file,
        "doc": doc,
        "summary": " ".join(doc.split("\n\n")[0].split()),   # the first paragraph, on one line: the overview's
        "deps": [x.arg for x in a.posonlyargs + a.args],
        "settings": {x.arg: _setting(x, d, f"{path}: {x.arg}") for x, d in zip(a.kwonlyargs, a.kw_defaults)},
        "metrics": [{"key": k, **({"label": m} if isinstance(m, str) else {"label": k, **m})} for k, m in metrics.items()],
        "view": "view" in fns,
    }


def read_fork(folder: Path, chosen: str | None) -> dict:
    """A fork: the node folder.name, written more than one way. Each .py in the folder is an
    option, a whole node of that name; README.md asks the fork's question ("# ...") and says
    what bears on it. The node is its chosen option (choices.json's, else the first by name,
    and the fork is open: nobody has decided it), with every option beside it."""
    options = {p.stem: read_node(p, folder.name, f"nodes/{folder.name}/{p.name}") for p in sorted(folder.glob("*.py"))}
    if len(options) < 2:
        raise ValueError(f"{folder}: a fork needs two options or more; a node written one way is nodes/{folder.name}.py")
    if chosen is not None and chosen not in options:
        raise ValueError(f"choices.json: {folder.name} has no option {chosen} (its options: {', '.join(options)})")
    readme = (folder / "README.md").read_text() if (folder / "README.md").is_file() else ""
    head, _, about = readme.partition("\n")
    return {**options[chosen or next(iter(options))], "options": options, "chosen": chosen or next(iter(options)),
            "open": chosen is None, "question": head.lstrip("# ").strip(), "about": about.strip()}


def read_nodes(app_dir: Path) -> dict:
    """{name: node}: nodes/<name>.py, or a fork, nodes/<name>/<option>.py."""
    path = app_dir / "choices.json"
    choices = json.loads(inside(app_dir, path).read_text()) if path.exists() else {}
    nodes = {}
    for p in sorted((app_dir / "nodes").iterdir()):
        if p.name.startswith((".", "_")):
            continue
        if p.is_dir():
            if p.name in nodes:
                raise ValueError(f"{p}: both a node file and a fork's folder")
            nodes[p.name] = read_fork(p, choices.get(p.name))
        elif p.suffix == ".py":
            if p.stem in nodes:
                raise ValueError(f"{p}: both a node file and a fork's folder")
            nodes[p.stem] = read_node(p, p.stem, f"nodes/{p.name}")
    unknown = [f for f in choices if "options" not in nodes.get(f, {})]
    if unknown:
        raise ValueError(f"choices.json: {', '.join(unknown)} is no fork (the forks: {', '.join(n for n in nodes if 'options' in nodes[n]) or 'none'})")
    return nodes


def ways(node: dict) -> list[dict]:
    """Every way a node is written: its options, or itself."""
    return list(node["options"].values()) if "options" in node else [node]


def imports(files: dict[str, bytes]) -> set[str]:
    out = set()
    for path, src in files.items():
        if path.endswith(".py"):
            for n in ast.walk(ast.parse(src, path)):
                if isinstance(n, ast.Import):
                    out |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and not n.level:
                    out.add(n.module.split(".")[0])
    return out


def shared_settings(nodes: dict) -> dict:
    """{name: setting}. A setting is the app's, by its name: nodes that declare the same name
    share its value, so they must declare it alike."""
    out, owner = {}, {}
    for n, node in ((n, w) for n, v in nodes.items() for w in ways(v)):
        for p, s in node["settings"].items():
            if p in out and out[p] != s:
                raise ValueError(f"{node['file']}: the setting {p} is also {owner[p]}'s, declared differently; "
                                 f"nodes share a setting by its name, so declare it alike or rename one")
            out[p], owner[p] = s, n
    return out


def load(app_dir: Path) -> dict:
    app_dir = Path(app_dir)
    readme = (app_dir / "README.md").read_text() if (app_dir / "README.md").exists() else f"# {app_dir.name}\n"
    head, _, about = readme.partition("\n")
    nodes = read_nodes(app_dir)
    data = {p.name.split(".")[0]: p for p in sorted((app_dir / "data").glob("*"))
            if (p.is_dir() or p.suffix not in {".py", ".md"}) and not p.name.startswith(".")} if (app_dir / "data").is_dir() else {}
    if set(nodes) & set(data):
        raise ValueError(f"{', '.join(sorted(set(nodes) & set(data)))}: both a node and a file in data/")
    datasets = {}
    for node in (w for v in nodes.values() for w in ways(v)):
        for d in node["deps"]:
            if d not in nodes and d not in data:
                raise ValueError(f"{node['file']}: {d} is neither a node nor a file in data/ (settings go after the *)")
            if d not in nodes:
                datasets[d] = data[d]
    shared_settings(nodes)
    # An option may read what another does not: a fork comes after everything any of its options reads.
    order = list(graphlib.TopologicalSorter({n: [d for w in ways(v) for d in w["deps"] if d in nodes] for n, v in nodes.items()}).static_order())
    # A built page ships these: never what is hidden (in a folder like .secrets/ too), nor what a link leads to outside.
    files = {p.relative_to(app_dir).as_posix(): inside(app_dir, p).read_bytes() for p in sorted(app_dir.rglob("*"))
             if p.is_file() and not SKIP & set(p.relative_to(app_dir).parts) and not hidden(p.relative_to(app_dir))}
    return {
        "name": app_dir.name, "title": head.lstrip("# ").strip() or app_dir.name, "about": about.strip(),
        "order": order, "nodes": nodes, "forks": [n for n in order if "options" in nodes[n]],
        # The numbers the app exists to produce: the METRICS marked answer, as each node is chosen.
        "answer": [{"node": n, **{k: v for k, v in m.items() if k != "answer"}} for n in order for m in nodes[n]["metrics"] if m.get("answer")],
        "files": files, "imports": sorted(imports(files)),
        "datasets": {d: dataset(app_dir, p) for d, p in datasets.items()},
    }


def dataset(app_dir: Path, p: Path) -> dict:
    """{path, files: {path: bytes}, doc}: one file, or a folder's files (its path ends in /), and
    what data/<name>.md says it is, for whoever replaces it."""
    md = p.parent / f"{p.name.split('.')[0]}.md"
    doc = inside(app_dir, md).read_text().strip() if md.is_file() else ""
    if p.is_file():
        return {"path": f"data/{p.name}", "files": {f"data/{p.name}": inside(app_dir, p).read_bytes()}, "doc": doc}
    inside(app_dir, p)
    return {"path": f"data/{p.name}/", "files": {f.relative_to(app_dir).as_posix(): inside(app_dir, f).read_bytes()
                                                  for f in sorted(p.iterdir()) if f.is_file() and not f.name.startswith(".")}, "doc": doc}


def hidden(rel: Path) -> bool:
    return any(part.startswith(".") for part in rel.parts)


def inside(app_dir: Path, p: Path) -> Path:
    """p, unless a link takes it out of the app: a build would ship whatever it leads to."""
    if not p.resolve().is_relative_to(Path(app_dir).resolve()):
        raise ValueError(f"{p}: links outside the app, so a built page would carry what it leads to; copy the file into the app instead")
    return p

