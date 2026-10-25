"""Read an app from its files, with ast (node code never runs natively).

    projects/<app>/README.md        "# Title", then what the app is for (Markdown)
    projects/<app>/nodes/<name>.py  one node: def <name>(inputs..., *, settings...)
    projects/<app>/data/<name>.*    a dataset, read by a node with a parameter <name>, which
                                    gets its path (a .py there makes or fetches one, natively,
                                    and is not one)
    projects/<app>/data/<name>/     a dataset of files: the node gets their paths, by name
    projects/<app>/*.py             helpers the nodes import
    projects/<app>/baseline.json    the run every check compares with (blocks baseline)

A positional parameter names another node or a dataset; a keyword-only one is a setting
with a literal default, optionally Annotated[type, Range(...)] or Choices(...).
"""
from __future__ import annotations

import ast
import graphlib
import hashlib
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
                vals = dict(zip(("min", "max", "step"), (_literal(a, where) for a in m.args)))
                vals |= {k.arg: _literal(k.value, where) for k in m.keywords}
                s |= vals
            elif kind == "Choices":
                s["choices"] = [_literal(a, where) for a in m.args]
    s["type"] = getattr(ann, "id", None) or type(s["default"]).__name__
    return s


def read_node(path: Path) -> dict:
    name, tree = path.stem, ast.parse(path.read_text(), str(path))
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
        if not isinstance(m, str) and (not isinstance(m, dict) or set(m) - {"label", "goal", "percent"}):
            raise ValueError(f"{path}: METRICS[{k!r}] is a label, or a dict of label, goal (\"min\" or \"max\") and percent (True for a share)")
    return {
        "file": f"nodes/{path.name}",
        "doc": ast.get_docstring(tree) or "",
        "deps": [x.arg for x in a.posonlyargs + a.args],
        "settings": {x.arg: _setting(x, d, f"{path}: {x.arg}") for x, d in zip(a.kwonlyargs, a.kw_defaults)},
        "metrics": [{"key": k, **({"label": m} if isinstance(m, str) else {"label": k, **m})} for k, m in metrics.items()],
        "view": "view" in fns,
        "downloads": any(isinstance(n, ast.Attribute) and n.attr == "download" for n in ast.walk(tree)),
    }


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


def load(app_dir: Path) -> dict:
    app_dir = Path(app_dir)
    readme = (app_dir / "README.md").read_text() if (app_dir / "README.md").exists() else f"# {app_dir.name}\n"
    head, _, about = readme.partition("\n")
    nodes = {p.stem: read_node(p) for p in sorted((app_dir / "nodes").glob("*.py"))}
    data = {p.name.split(".")[0]: p for p in sorted((app_dir / "data").glob("*"))
            if p.is_dir() or p.suffix != ".py"} if (app_dir / "data").is_dir() else {}
    if set(nodes) & set(data):
        raise ValueError(f"{', '.join(sorted(set(nodes) & set(data)))}: both a node and a file in data/")
    datasets = {}
    for n, node in nodes.items():
        for d in node["deps"]:
            if d not in nodes and d not in data:
                raise ValueError(f"{node['file']}: {d} is neither a node nor a file in data/")
            if d not in nodes:
                datasets[d] = data[d]
    order = list(graphlib.TopologicalSorter({n: [d for d in v["deps"] if d in nodes] for n, v in nodes.items()}).static_order())
    files = {p.relative_to(app_dir).as_posix(): p.read_bytes() for p in sorted(app_dir.rglob("*"))
             if p.is_file() and not SKIP & set(p.relative_to(app_dir).parts) and not p.name.startswith(".")}
    return {
        "name": app_dir.name, "title": head.lstrip("# ").strip() or app_dir.name, "about": about.strip(),
        "order": order, "nodes": nodes, "files": files, "imports": sorted(imports(files)),
        "datasets": {d: dataset(app_dir, p) for d, p in datasets.items()},
    }


def dataset(app_dir: Path, p: Path) -> dict:
    """{path, files: {path: bytes}}: one file, or a folder's files (its path ends in /)."""
    if p.is_file():
        return {"path": f"data/{p.name}", "files": {f"data/{p.name}": p.read_bytes()}}
    return {"path": f"data/{p.name}/", "files": {f.relative_to(app_dir).as_posix(): f.read_bytes()
                                                  for f in sorted(p.iterdir()) if f.is_file() and not f.name.startswith(".")}}


def data_key(path: str, files: dict[str, bytes]) -> str:
    """A dataset's key: a file's sha256, or a folder's over each file's name and sha256. The page
    computes the same for a replacement (page/app.js dataKey)."""
    if not path.endswith("/"):
        return sha256(files[path])
    return sha256("".join(f"{p[len(path):]}\0{sha256(b)}\n" for p, b in sorted(files.items())).encode())


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
