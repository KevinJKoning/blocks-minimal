"""blocks COMMAND [APP ...], run from the repository root; no APP means every app in projects/.

serve      the apps at http://127.0.0.1:8765/<app>/, rebuilt on every request
run        run each app headlessly and print every node: its status, metrics and errors
             --set NAME=VALUE   with a setting other than its default (VALUE is JSON, else text)
             --output NODE      print that node's output instead, as JSON
             --shots DIR [NODE ...]  save a picture of those pages (_overview is the overview's),
                                or of every page, as DIR/<app>/<node>.png
baseline   run, and keep the run as projects/<app>/baseline.json if nothing failed
verify     run, and compare with the baseline (graph.compare)
build      dist/<app>.html, one offline file, verified from file:// with the network blocked
             --no-data          leave its datasets out, for whoever opens it to choose
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import build, spec
from .graph import compare

PROJECTS = Path("projects")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Only this machine's own names: another site rebound to 127.0.0.1 must not read the apps.
        if self.headers.get("Host") not in {f"{h}:{self.server.server_port}" for h in ("127.0.0.1", "localhost")}:
            return self.send_error(403, "unexpected Host")
        path = self.path.split("?")[0].split("#")[0]
        parts = [p for p in path.split("/") if p]
        try:
            if len(parts) == 2 and parts[0] == "_runtime":
                body, kind = build.runtime_file(parts[1]), "application/wasm" if parts[1].endswith(".wasm") else "application/octet-stream"
            # The app's folder as projects/ lists it, never a path from the request: "/../" is no app.
            elif len(parts) == 1 and (app := next((p for p in apps() if p.name == parts[0]), None)):
                if not path.endswith("/"):
                    self.send_response(301); self.send_header("Location", f"/{app.name}/"); self.end_headers()
                    return
                body, kind = build.build(app, inline=False, origin=f"http://{self.headers['Host']}").encode(), "text/html"
            else:
                return self.send_error(404)
        except Exception as e:  # noqa: BLE001 - show the error instead of a blank page
            if parts[0] == "_runtime":   # a runtime file that failed is an error, never a page in its place
                return self.send_error(502, f"{type(e).__name__}: {e}")
            body, kind = f"<pre>{html.escape(why(e))}</pre>".encode(), "text/html"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def why(e: Exception) -> str:
    """A build's error, in one message; a syntax error with its file, line and text."""
    if isinstance(e, SyntaxError):
        return f"SyntaxError in {e.filename}, line {e.lineno}: {e.msg}\n    {(e.text or '').strip()}"
    return f"{type(e).__name__}: {e}"


def apps(names=None) -> list[Path]:
    found = sorted(p for p in PROJECTS.iterdir() if (p / "nodes").is_dir())
    if names:
        unknown = set(names) - {p.name for p in found}
        if unknown:
            sys.exit(f"no app {', '.join(sorted(unknown))} in {PROJECTS}/")
        found = [p for p in found if p.name in names]
    return found


def serve(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


RUN = """async (settings) => {
  try { await window.blocks.ready; } catch (e) { return { failed: `Python did not start: ${e.message}` }; }
  try { window.blocks.set(settings || {}); return await window.blocks.run(); } catch (e) { return { failed: e.message }; }
}"""
FAILED = "() => [...document.querySelectorAll('[data-failed]')].map((e) => e.textContent).join('\\n')"

# A block's script, parsed (not run) in a blank page: its syntax error, at the file's own line.
PARSE = """(src) => {
  let got = null;
  const on = (e) => { got ??= `line ${e.lineno}, column ${e.colno}: ${e.message.replace(/^.*Element': /, "")}`; e.preventDefault(); };
  window.addEventListener("error", on);
  const s = document.createElement("script");
  s.textContent = `(function () { "use strict"; ${src}\n});`;
  document.head.append(s);
  window.removeEventListener("error", on);
  return got;
}"""


def unloaded(browser, page, errors: list[str], app: Path) -> str:
    """Why a page never set up window.blocks: the app did not build (the dev server answers
    with the error instead), or a script failed; for a syntax error, the block file and line."""
    if not errors:
        return "the app did not build: " + page.inner_text("body").strip()
    blank = browser.new_page()
    found = [f"{os.path.relpath(f)}, {err}" for f in [build.PACKAGE / "ui" / "_kit.js", *build.block_files(app, ".js")]
             if (err := blank.evaluate(PARSE, f.read_text()))]
    return "the page's script failed: " + "; ".join(errors) + "".join(f"\n  {f}" for f in found)


def run_page(url: str, app: Path, offline=False, settings=None, choose=None, shots=None, pages=(), output=None) -> dict:
    """The run record of the app's page in headless Edge: settings set, Run pressed, then
    every node's page drawn (a block marked data-failed is a failed view), and a picture saved
    in the folder shots of each page named in pages (of every page, when none is). The page runs
    untrusted packages, so the browser keeps its sandbox and the page reaches no server but its
    own (offline: none). choose: {dataset: [files]} for a page built without its data."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", chromium_sandbox=True)
        allowed = ("data:", "blob:", "file:") + (() if offline else ("{0.scheme}://{0.netloc}/".format(urlsplit(url)),))
        context = browser.new_context()   # its route covers the page's worker too
        context.route("**/*", lambda route, request: route.continue_() if request.url.startswith(allowed) else route.abort())
        page, errors = context.new_page(), []
        page.on("pageerror", lambda e: errors.append(f"{e.name}: {e.message}"))
        page.goto(url)
        if not page.evaluate("() => !!window.blocks"):
            return {"failed": unloaded(browser, page, errors, app)}
        if choose:   # as a reader would, through each dataset's file input
            page.evaluate("() => window.blocks.ready")
            for d, files in choose.items():
                page.locator(f'input[data-dataset="{d}"]').first.set_input_files(files)
            page.wait_for_function("() => window.blocks.state().missing.length === 0")
        record = page.evaluate(RUN, settings or {})
        if "failed" in record:
            return record
        unknown = set(pages) - {*record["nodes"], "_overview"}
        if unknown:
            return {"failed": f"--shots names no page {', '.join(sorted(unknown))} (the pages: _overview, {', '.join(record['nodes'])})"}
        for n in [*record["nodes"], None]:
            page.evaluate("(n) => window.blocks.show(n)", n)
            failed = page.evaluate(FAILED)
            if n and failed:
                record["nodes"][n].setdefault("view_error", failed)
            if shots and (not pages or (n or "_overview") in pages):
                shots.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shots / f"{n or '_overview'}.png"), full_page=True)
        if record["nodes"].get(output, {}).get("status") == "done":
            record["output"] = page.evaluate("(n) => window.blocks.output(n)", output)
    return record


def show(app: Path, record: dict) -> bool:
    """Print a run, node by node, with each failure in full; True when nothing failed."""
    if "failed" in record:
        print(f"{app.name}: the run failed: {record['failed']}")
        return False
    print(f"{app.name}:")
    ok = True
    for n, r in record["nodes"].items():
        metrics = ", ".join(f"{k}={v:.6g}" if isinstance(v, float) else f"{k}={v}" for k, v in r.get("metrics", {}).items())
        print(f"  {n}  {r['status']}  {metrics}")
        if r.get("error") or r.get("view_error"):
            failure = r.get("error") or "its view failed:\n" + r["view_error"]
            print("    " + failure.strip().replace("\n", "\n    "))
            ok = False
    return ok


def verify(app: Path, record: dict) -> bool:
    if "failed" in record:
        return show(app, record)
    path = app / "baseline.json"
    if not path.exists():
        print(f"{app.name}: no baseline yet (blocks baseline {app.name} records one)")
        return False
    differs = compare(record, json.loads(path.read_text()))
    print(f"{app.name}: " + ("DIFFERS from the baseline:" if differs else "matches the baseline"))
    for n, what in differs.items():
        print(f"  {n}: " + "; ".join(what))
    return not differs


def baseline(app: Path, record: dict) -> bool:
    """Keep the run as the app's baseline, if every node and view succeeded."""
    if not show(app, record):
        print(f"{app.name}: no baseline recorded")
        return False
    (app / "baseline.json").write_text(json.dumps(record, indent=1) + "\n")
    print(f"{app.name}: baseline recorded")
    return True


def setting(text: str):
    """NAME=VALUE as (name, value), the value read as JSON (3, 0.5, true) or else as text."""
    name, _, value = text.partition("=")
    try:
        return name, json.loads(value)
    except json.JSONDecodeError:
        return name, value


def main(argv=None):
    try:
        commands(argv)
    except BrokenPipeError:   # its reader stopped (| head): end quietly, as other tools do
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())   # or Python's flush at exit complains again
        sys.exit(1)


def commands(argv):
    ap = argparse.ArgumentParser(prog="blocks", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["serve", "run", "baseline", "verify", "build"])
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--set", action="append", default=[], type=setting)
    ap.add_argument("--output")
    ap.add_argument("--shots", nargs="+", metavar=("DIR", "NODE"))
    ap.add_argument("--no-data", action="store_true")
    a = ap.parse_args(argv)
    if a.command == "serve":
        try:
            serve(a.port)
        except OSError as e:
            sys.exit(f"blocks serve: port {a.port} is taken ({e.strerror}); pick another with --port")
        print(f"http://127.0.0.1:{a.port}/<app>/")
        threading.Event().wait()
    if (a.set or a.output or a.shots) and a.command != "run":
        sys.exit("blocks: --set, --output and --shots are for run; baseline, verify and build use the settings' defaults")
    shots, pages = (Path(a.shots[0]), a.shots[1:]) if a.shots else (None, [])
    server, ok = serve(0), True
    for app in apps(a.apps):
        url, choose = f"http://127.0.0.1:{server.server_port}/{app.name}/", None
        if a.command == "build":   # one offline file, verified as it will be opened
            page = Path("dist") / f"{app.name}.html"
            page.parent.mkdir(exist_ok=True)
            try:
                page.write_text(build.build(app, inline=True, data=not a.no_data))
            except (ValueError, SyntaxError) as e:
                print(f"{app.name}: the app did not build: {why(e)}")
                ok = False
                continue
            print(f"{page}  {page.stat().st_size / 1e6:.1f} MB")
            url = page.resolve().as_uri()
            if a.no_data:
                choose = {d: [str((app / p).resolve()) for p in v["files"]] for d, v in spec.load(app)["datasets"].items()}
        record = run_page(url, app, offline=a.command == "build", settings=dict(a.set), choose=choose,
                          shots=shots and shots / app.name, pages=pages, output=a.output)
        if a.command == "run" and "output" in record:
            print(json.dumps(record["output"], indent=1))
        elif a.command == "run":
            ok &= show(app, record)
        elif a.command == "baseline":
            ok &= baseline(app, record)
        else:
            ok &= verify(app, record)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
