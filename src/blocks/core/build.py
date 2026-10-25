"""An app as one HTML page: the app's files, its data and the page's script, plus the Pyodide
runtime, embedded (`inline`, the offline file) or linked from the dev server's /_runtime/.

The runtime is downloaded once into .cache/ and checked: the core files against the pins
below, every wheel against the pinned pyodide-lock.json.
"""
from __future__ import annotations

import base64
import html
import json
import sys
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
CSP = ("default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; worker-src blob:; connect-src data:{self}; "
       "img-src data: blob:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")


def runtime_file(name: str) -> bytes:
    """A runtime file (core file or wheel) from the cache, or the CDN on first use."""
    want = CORE.get(name) or next((p["sha256"] for p in lock()["packages"].values() if p["file_name"] == name), None)
    if not want or "/" in name:
        raise KeyError(f"{name} is not part of Pyodide {PYODIDE}")
    path = CACHE / name
    data = path.read_bytes() if path.is_file() else b""
    if spec.sha256(data) != want:
        with urllib.request.urlopen(CDN + name, timeout=120) as r:  # noqa: S310 (pinned https URL)
            data = r.read()
        if spec.sha256(data) != want:
            raise ValueError(f"{name}: sha256 does not match the pin")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def lock() -> dict:
    return json.loads(runtime_file("pyodide-lock.json"))


def packages(imports: list[str], local=()) -> list[str]:
    """The Pyodide packages the app's imports need, with their dependencies. An import that
    is none of these, nor the standard library or the app's own module, is an error now
    rather than in the browser."""
    pk = lock()["packages"]
    if "zoneinfo" in imports:   # Pyodide has no system time zones; zoneinfo reads them from tzdata
        imports = [*imports, "tzdata"]
    by_import = {i: n for n, p in pk.items() for i in p.get("imports", [])}
    unknown = set(imports) - set(by_import) - sys.stdlib_module_names - {"blocks", "pyodide", "js", *local}
    if unknown:
        raise ValueError(f"no Pyodide {PYODIDE} package provides {', '.join(sorted(unknown))}")
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
    """Every block's .js or .css, the library's kit first. Each script is in its own scope, so
    a block's helpers stay its own; the kit's are every block's."""
    kit = PACKAGE / "ui" / f"_kit{ext}"
    files = block_files(app_dir, ext)
    parts = [f"{{ // {p.name}\n{p.read_text()}}}" if ext == ".js" else p.read_text() for p in files]
    return "\n".join(([kit.read_text()] if kit.exists() else []) + parts)


def page_script(app_dir: Path) -> str:
    app = template("page/app.js")
    if app.count("// @blocks\n") != 1:
        raise ValueError("page/app.js must mark once where the blocks' renderers go (// @blocks)")
    return app.replace("// @blocks\n", blocks(app_dir, ".js"))


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def build(app_dir: Path, inline: bool, data: bool = True) -> str:
    """The app's page. inline: the runtime is in it (an offline file), not served. data: its
    datasets are in it; without them, whoever opens it chooses them."""
    a = spec.load(app_dir)
    pkgs = packages(a["imports"], {p.split("/")[0].removesuffix(".py") for p in a["files"]})
    library = {f"blocks/{f}": (PACKAGE / f).read_bytes() for f in LIBRARY}
    baseline = Path(app_dir) / "baseline.json"
    manifest = {
        "title": a["title"], "about": a["about"], "packages": pkgs,
        "spec": {"order": a["order"], "nodes": a["nodes"], "datasets": {d: v["path"] for d, v in a["datasets"].items()}},
        "files": {p: b64(b) for p, b in a["files"].items()},
        "library": {p: b64(b) for p, b in library.items()},
        "data": {d: {"key": spec.data_key(v["path"], v["files"]), "size": sum(map(len, v["files"].values())),
                     "files": {p: b64(b) for p, b in v["files"].items()}} if data else {"key": None, "size": None, "files": None}
                 for d, v in a["datasets"].items()},
        "baseline": json.loads(baseline.read_text()) if baseline.exists() else None,
        "runtime": None if inline else "/_runtime/",
    }
    csp = CSP.format(self="" if inline else " 'self'")
    script = lambda type, body, attrs="": f'<script type="{type}"{attrs}>{body}</script>'
    parts = [
        "<!doctype html>", '<html lang="en">', '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(a['title'])}</title>", f"<style>{template('page/app.css')}\n{blocks(app_dir, '.css')}</style>",
        '<body><div id="app"></div>',
        script("application/json", json.dumps(manifest).replace("<", "\\u003c"), ' id="manifest"'),
        script("text/plain", template("worker.js"), ' id="worker"'),
    ]
    if inline:
        names = [*CORE, *(lock()["packages"][p]["file_name"] for p in pkgs)]
        parts += [script("application/octet-stream", b64(runtime_file(n)), f' data-runtime="{n}"') for n in names]
    parts.append(script("module", page_script(app_dir)))
    return "\n".join(parts) + "\n"
