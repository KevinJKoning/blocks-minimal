"""An app as one HTML page: the app's files, its data and the page's script, plus the Pyodide
runtime, embedded (`inline`, the offline file) or linked from the dev server's /_runtime/.

The runtime is downloaded once into .cache/ and checked: the core files against the pins
below, every wheel against the pinned pyodide-lock.json.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import sys
import threading
import urllib.request
from pathlib import Path

from . import spec

PYODIDE = "314.0.7"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full/"
CORE = {
    "pyodide.mjs": "6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109",
    "pyodide.asm.mjs": "f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635",
    "pyodide.asm.wasm": "cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6",
    "python_stdlib.zip": "fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a",
    "pyodide-lock.json": "5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010",
}
PACKAGE = Path(__file__).parent.parent                          # src/blocks
LIBRARY = ["__init__.py", "core/__init__.py", "core/graph.py", *sorted(p.relative_to(PACKAGE).as_posix() for p in (PACKAGE / "ui").glob("*.py"))]
CACHE = Path(".cache") / "pyodide" / PYODIDE
# The page's Content-Security-Policy, which the worker inherits: the packages are not trusted,
# so nothing on the page reaches the network but the dev server's /_runtime/ (linked builds).
CSP = ("default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; worker-src blob:; connect-src data:{runtime}; "
       "img-src data: blob:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")


def runtime_file(name: str) -> bytes:
    """A runtime file (core file or wheel) from the cache, or the CDN on first use."""
    want = CORE.get(name) or next((p["sha256"] for p in lock()["packages"].values() if p["file_name"] == name), None)
    if not want:
        raise KeyError(f"{name} is not part of Pyodide {PYODIDE}")
    path = CACHE / name
    data = path.read_bytes() if path.is_file() else b""
    if sha256(data) != want:
        with urllib.request.urlopen(CDN + name, timeout=120) as r:  # noqa: S310 (pinned https URL)
            data = r.read()
        if sha256(data) != want:
            raise ValueError(f"{name}: sha256 does not match the pin")
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(f".{name}.{os.getpid()}.{threading.get_ident()}")   # whole or not at all: the cache is shared
        part.write_bytes(data)
        os.replace(part, path)
    return data


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def lock() -> dict:
    return json.loads(runtime_file("pyodide-lock.json"))


def packages(imports: list[str], local=(), files=None) -> list[str]:
    """The Pyodide packages the app's imports need, with their dependencies. An import that
    is none of these, nor the standard library or the app's own module, is an error now
    rather than in the browser, naming the files (of files, {path: source}) that import it."""
    pk = lock()["packages"]
    by_import = {i: n for n, p in pk.items() for i in p.get("imports", [])}
    unknown = set(imports) - set(by_import) - sys.stdlib_module_names - {"blocks", "pyodide", "js", *local}
    if unknown:
        where = lambda i: [p for p, src in (files or {}).items() if p.endswith(".py") and i in spec.imports({p: src})]
        raise ValueError("; ".join(f"{' and '.join(where(i)) or 'the app'} imports {i}" for i in sorted(unknown))
                         + f", which is no package with a Pyodide {PYODIDE} build, nor the standard library, nor a module"
                         " of the app's own (a .py file or folder at its top level; a node is not one). Pyodide's packages,"
                         f" and the names each imports as, are in .cache/pyodide/{PYODIDE}/pyodide-lock.json")
    want, todo = set(), [by_import[i] for i in imports if i in by_import]
    while todo:
        n = todo.pop()
        if n not in want:
            want.add(n)
            todo += pk[n].get("depends", [])
    return sorted(want)


def template(name: str) -> str:
    return (PACKAGE / "core" / name).read_text()


def block_files(app_dir: Path, ext: str) -> list[Path]:
    """The library's blocks (src/blocks/ui/<name>.<ext>), then the app's own (<app>/ui/), whose
    names must be new."""
    ours = sorted(p for p in (PACKAGE / "ui").glob(f"*{ext}") if not p.name.startswith("_"))
    theirs = sorted(p for p in (Path(app_dir) / "ui").glob(f"*{ext}") if not p.name.startswith("_"))
    clash = {p.stem for p in ours} & {p.stem for p in theirs}
    if clash:
        raise ValueError(f"{', '.join(sorted(clash))}: the app's ui/ redefines a library block")
    return ours + theirs


def blocks(app_dir: Path, ext: str) -> str:
    """The kit (ui/_kit.js or ui/_kit.css), then every block's .js or .css. Each block script is
    in its own scope, so a block's helpers stay its own; the kit's are every block's."""
    parts = [f"{{ // {p.name}\n{p.read_text()}}}" if ext == ".js" else p.read_text() for p in block_files(app_dir, ext)]
    return "\n".join([(PACKAGE / "ui" / f"_kit{ext}").read_text(), *parts])


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def worker_script() -> str:
    """The worker: Pyodide's two ES modules joined into one classic script, then worker.js.
    Browsers refuse module workers from blob: URLs on file:// pages; Pyodide refuses classic
    workers, which it detects by importScripts working, so that is disabled first."""
    asm = runtime_file("pyodide.asm.mjs").decode().replace("export default _createPyodideModule;", "")
    asm = asm.replace("import.meta.url", "self.location.href")
    mjs = runtime_file("pyodide.mjs").decode()
    exports = re.search(r"export\s*\{([^}]*)\};?", mjs)
    fields = []
    for item in exports[1].split(","):   # "dt as loadPyodide" -> "loadPyodide: dt"
        name, _, alias = item.strip().partition(" as ")
        fields.append(f"{alias or name}: {name}")
    mjs = mjs.replace(exports[0], f"return {{ {', '.join(fields)} }};")
    return (f'globalThis.importScripts = () => {{ throw new Error("importScripts is disabled"); }};\n{asm}\n'
            f"const __pyodide = (() => {{\n{mjs}\n}})();\n{template('worker.js')}")


def build(app_dir: Path, inline: bool, data: bool = True, *, origin: str | None = None) -> str:
    """The app's page. inline: the runtime is in it (an offline file), not served. data: its
    datasets are in it; without them, whoever opens it chooses them. Linked pages require
    their server's origin so the CSP can allow /_runtime/ without exposing other apps."""
    if not inline and not origin:
        raise ValueError("a linked page needs its server's origin")
    a = spec.load(app_dir)
    pkgs = packages(a["imports"], {p.split("/")[0].removesuffix(".py") for p in a["files"]}, a["files"])
    library = {f"blocks/{f}": (PACKAGE / f).read_bytes() for f in LIBRARY}
    baseline = Path(app_dir) / "baseline.json"
    manifest = {
        "title": a["title"], "about": a["about"], "packages": pkgs,
        "spec": {"order": a["order"], "nodes": a["nodes"], "datasets": {d: v["path"] for d, v in a["datasets"].items()}},
        "files": {p: b64(b) for p, b in a["files"].items()},
        "library": {p: b64(b) for p, b in library.items()},
        # A page built without its data still says what each dataset is, for whoever chooses it.
        "data": {d: {"doc": v["doc"], "files": {p: b64(b) for p, b in v["files"].items()} if data else None}
                 for d, v in a["datasets"].items()},
        "baseline": json.loads(spec.inside(app_dir, baseline).read_text()) if baseline.exists() else None,
        "runtime": None if inline else "/_runtime/",
    }
    csp = CSP.format(runtime="" if inline else f" {origin}/_runtime/")
    script = lambda type, body, attrs="": f'<script type="{type}"{attrs}>{body}</script>'
    parts = [
        "<!doctype html>", '<html lang="en">', '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(a['title'])}</title>", f"<style>{template('page/app.css')}\n{blocks(app_dir, '.css')}</style>",
        '<body><div id="app"></div>',
        script("application/json", json.dumps(manifest).replace("<", "\\u003c"), ' id="manifest"'),
        script("text/plain", worker_script(), ' id="worker"'),
    ]
    if inline:   # what the worker fetches: the rest of the runtime, and the packages' wheels
        names = ["pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json", *(lock()["packages"][p]["file_name"] for p in pkgs)]
        parts += [script("application/octet-stream", b64(runtime_file(n)), f' data-runtime="{n}"') for n in names]
    parts.append(script("module", template("page/app.js").replace("// @blocks\n", blocks(app_dir, ".js"))))
    return "\n".join(parts) + "\n"
