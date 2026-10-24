"""blocks serve | build | baseline | verify, run from the repository root.

serve     the apps at http://127.0.0.1:8765/<app>/, rebuilt on every request
build     dist/<app>.html, one offline file, verified from file:// with the network blocked
baseline  run each app headlessly and keep its run as projects/<app>/baseline.json
verify    run each app headlessly and compare with its baseline
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from blocks.graph import compare

from . import build

PROJECTS = Path("projects")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Only this machine's own names: another site rebound to 127.0.0.1 must not read the apps.
        if self.headers.get("Host") not in {f"{h}:{self.server.server_port}" for h in ("127.0.0.1", "localhost")}:
            return self.send_error(403, "unexpected Host")
        path = self.path.split("?")[0].split("#")[0]
        parts = [p for p in path.split("/") if p]
        try:
            if not parts:
                links = "".join(f'<li><a href="/{p.name}/">{html.escape(p.name)}</a></li>' for p in apps())
                body, kind = f"<!doctype html><title>blocks</title><h1>Apps</h1><ul>{links}</ul>".encode(), "text/html"
            elif parts[0] == "_runtime" and len(parts) == 2:
                body, kind = build.runtime_file(parts[1]), "application/wasm" if parts[1].endswith(".wasm") else "application/octet-stream"
            elif len(parts) == 1 and (PROJECTS / parts[0] / "nodes").is_dir():
                if not path.endswith("/"):
                    self.send_response(301); self.send_header("Location", path + "/"); self.end_headers()
                    return
                body, kind = build.build(PROJECTS / parts[0], inline=False).encode(), "text/html"
            else:
                return self.send_error(404)
        except Exception as e:  # noqa: BLE001 - show the error instead of a blank page
            body, kind = f"<pre>{html.escape(f'{type(e).__name__}: {e}')}</pre>".encode(), "text/html"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=31536000, immutable" if parts and parts[0] == "_runtime" else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


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


def run_page(urls: list[str], offline=False) -> list[dict]:
    """Open each page in headless Chromium, press Run, and return its run records. The page runs
    untrusted packages, so Chromium keeps its sandbox and the page reaches no server but its
    own (offline: none at all)."""
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(chromium_sandbox=True)
        for url in urls:
            context = browser.new_context()
            allowed = ("data:", "blob:", "file:") + (() if offline else ("{0.scheme}://{0.netloc}/".format(urlsplit(url)),))
            context.route("**/*", lambda route, request: route.continue_() if request.url.startswith(allowed) else route.abort())
            page = context.new_page()
            page.goto(url)
            out.append(page.evaluate("async () => { await window.blocks.ready; return await window.blocks.run(); }"))
            context.close()
        browser.close()
    return out


def check(app: Path, record: dict) -> bool:
    baseline = app / "baseline.json"
    if not baseline.exists():
        print(f"{app.name}: no baseline (blocks baseline {app.name})")
        return False
    bad = compare(record, json.loads(baseline.read_text()))
    print(f"{app.name}: " + ("matches the baseline" if not bad else "DIFFERS"))
    for n, why in bad.items():
        print(f"  {n}: " + "; ".join(why))
    return not bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog="blocks", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["serve", "build", "baseline", "verify"])
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-verify", action="store_true", help="build only")
    a = ap.parse_args(argv)
    if a.command == "serve":
        print(f"http://127.0.0.1:{a.port}/")
        serve(a.port)
        threading.Event().wait()
    targets = apps(a.apps)
    if a.command == "build":
        ok = True
        for app in targets:
            out = Path("dist") / f"{app.name}.html"
            out.parent.mkdir(exist_ok=True)
            out.write_text(build.build(app, inline=True))
            print(f"{out}  {out.stat().st_size / 1e6:.1f} MB")
            if not a.no_verify:
                ok &= check(app, run_page([out.resolve().as_uri()], offline=True)[0])
        sys.exit(0 if ok else 1)
    server = serve(0)
    records = run_page([f"http://127.0.0.1:{server.server_port}/{app.name}/" for app in targets])
    if a.command == "baseline":
        for app, record in zip(targets, records):
            (app / "baseline.json").write_text(json.dumps(record, indent=1) + "\n")
            print(f"{app.name}: baseline recorded" + "".join(f"\n  {n} failed" for n, r in record["nodes"].items() if r["status"] != "done"))
    else:
        sys.exit(0 if all([check(app, r) for app, r in zip(targets, records)]) else 1)


if __name__ == "__main__":
    main()
