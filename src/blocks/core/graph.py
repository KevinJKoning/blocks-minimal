"""The graph, run in Pyodide: nodes are functions, values pass in memory, and every output is
cached by a key over the node's code, its settings and its inputs' keys. Run computes only
the nodes whose key changed; the rest come from the cache.

spec (core/spec.py): {order, datasets: {name: path}, nodes: {name: {file, deps, settings:
{param: {default}}, metrics: [{key, label, goal}], view}}}

A run record is what a run leaves: {made, settings, data, nodes: {name: {status, key,
metrics, digest, error, view_error}}}. Verification compares one with the baseline (compare).
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import traceback
import types


def plain(v):
    """numpy, pandas and pyarrow values as plain Python (JSON) values."""
    if hasattr(v, "to_pylist"):
        return v.to_pylist()
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    return v


def numbers(o, prefix=""):
    """The numbers in an output (a dict or dataclass, nested), as (dotted key, value)."""
    if hasattr(o, "__dataclass_fields__"):
        o = {f: getattr(o, f) for f in o.__dataclass_fields__}
    if not isinstance(o, dict):
        return
    for k, v in o.items():
        if isinstance(v, dict) or hasattr(v, "__dataclass_fields__"):
            yield from numbers(v, f"{prefix}{k}.")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            yield f"{prefix}{k}", v
        elif getattr(v, "shape", None) == () and hasattr(v, "item"):   # numpy scalar
            yield f"{prefix}{k}", v.item()


def canon(h, v):
    """Feed a value into a hash deterministically: two outputs are the same when this is."""
    if v is None or isinstance(v, (bool, int, str)):
        h.update(json.dumps(v).encode())
    elif isinstance(v, float):
        h.update(("f" + ("nan" if math.isnan(v) else repr(v))).encode())
    elif isinstance(v, (bytes, bytearray)):
        h.update(b"b" + bytes(v))
    elif isinstance(v, dict):
        h.update(b"{")
        for k in sorted(v, key=str):
            canon(h, str(k)); canon(h, v[k])
        h.update(b"}")
    elif isinstance(v, (list, tuple)):
        h.update(b"[")
        for x in v:
            canon(h, x)
        h.update(b"]")
    elif hasattr(v, "__dataclass_fields__"):
        canon(h, {f: getattr(v, f) for f in v.__dataclass_fields__})
    elif hasattr(v, "dtype") and getattr(v.dtype, "hasobject", False):     # numpy of Python objects: their bytes are addresses
        h.update(f"nd{v.shape}".encode()); canon(h, v.tolist())
    elif hasattr(v, "dtype") and hasattr(v, "tobytes"):                   # numpy
        h.update(f"nd{v.dtype.str}{v.shape}".encode() + v.tobytes())
    elif hasattr(v, "to_pydict"):                                         # pyarrow table
        canon(h, v.to_pydict())
    elif hasattr(v, "to_pylist"):                                         # pyarrow array
        canon(h, v.to_pylist())
    elif hasattr(v, "columns") and hasattr(v, "to_numpy"):                # pandas
        canon(h, {str(c): v[c].to_numpy() for c in v.columns})
    elif hasattr(v, "item"):
        canon(h, v.item())
    else:   # an object's default repr holds its address, which differs from run to run
        h.update(re.sub(r" at 0x[0-9a-fA-F]+", "", repr(v)).encode())


def digest(v) -> str:
    h = hashlib.sha256()
    canon(h, v)
    return h.hexdigest()


def to_json(o) -> str:
    """JSON for the page: non-finite numbers as strings, since JSON has none."""
    def clean(v):
        if isinstance(v, float) and not math.isfinite(v):
            return "NaN" if math.isnan(v) else ("Infinity" if v > 0 else "-Infinity")
        if isinstance(v, dict):
            return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [clean(x) for x in v]
        return v
    return json.dumps(clean(plain(o)), default=str)


class Graph:
    def __init__(self, root: str, spec: dict):
        self.root, self.spec = os.path.abspath(root), spec
        self.cache: dict[str, tuple[str, object, dict]] = {}   # node -> (key, output, result)
        self.modules: dict[str, types.ModuleType] = {}
        helpers = sorted(os.path.join(d, n) for d, _, ns in os.walk(self.root) for n in ns
                         if n.endswith(".py") and "nodes" not in os.path.relpath(d, self.root).split(os.sep))
        self.helpers = hashlib.sha256(b"".join(self._read(p) for p in helpers)).hexdigest()
        if self.root not in sys.path:
            sys.path.insert(0, self.root)

    def _read(self, path):
        with open(os.path.join(self.root, path), "rb") as f:
            return f.read()

    def module(self, name):
        if name not in self.modules:
            path = os.path.join(self.root, self.spec["nodes"][name]["file"])
            mod = types.ModuleType(f"node_{name}")
            mod.__file__ = path
            exec(compile(self._read(path), path, "exec"), mod.__dict__)
            self.modules[name] = mod
        return self.modules[name]

    def run(self, settings: dict, data: dict) -> dict:
        """settings {"node.param": value}, data {dataset: key}. Returns {node: result}."""
        results, keys = {}, {}
        for name in self.spec["order"]:
            node = self.spec["nodes"][name]
            failed = next((d for d in node["deps"] if d in results and results[d]["status"] != "done"), None)
            if failed:
                results[name] = {"status": "blocked", "error": f"{failed} did not run"}
                continue
            mine = {p: settings.get(f"{name}.{p}", s["default"]) for p, s in node["settings"].items()}
            parts = [hashlib.sha256(self._read(node["file"])).hexdigest(), self.helpers, json.dumps(mine, sort_keys=True, default=repr)]
            parts += [data.get(d, "") if d in self.spec["datasets"] else keys[d] for d in node["deps"]]
            key = keys[name] = hashlib.sha256("\0".join(parts).encode()).hexdigest()
            if name in self.cache and self.cache[name][0] == key:
                results[name] = {**self.cache[name][2], "cached": True}
                continue
            args = [os.path.join(self.root, self.spec["datasets"][d]) if d in self.spec["datasets"] else self.cache[d][1]
                    for d in node["deps"]]
            log, t0 = io.StringIO(), time.perf_counter()
            try:
                with contextlib.chdir(self.root), contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    value = getattr(self.module(name), name)(*args, **mine)
            except Exception:  # noqa: BLE001 - a node's failure is reported, never raised
                self.cache.pop(name, None)
                results[name] = {"status": "error", "key": key, "error": traceback.format_exc(), "log": log.getvalue()[-20000:]}
                continue
            blocks, view_error = self.blocks(name, value)
            result = {"status": "done", "key": key, "seconds": round(time.perf_counter() - t0, 4), "settings": mine,
                      "metrics": dict(numbers(value)), "digest": digest(value), "blocks": blocks, "view_error": view_error,
                      "log": log.getvalue()[-20000:]}
            self.cache[name] = (key, value, result)
            results[name] = {**result, "cached": False}
        return results

    def blocks(self, name, value):
        """The node's view of its output (without a view, its metrics), and the traceback when
        the view failed."""
        node = self.spec["nodes"][name]
        try:
            with contextlib.chdir(self.root):
                if node["view"]:
                    raw = list(self.module(name).view(value) or [])
                else:
                    raw = [{"type": "metrics"}] if node["metrics"] or any(numbers(value)) else []
        except Exception:  # noqa: BLE001 - the node ran; only its view failed
            return [], traceback.format_exc()
        return raw, None

    def output(self, name):
        if name not in self.cache:
            raise KeyError(f"{name} has not run")
        return self.cache[name][1]


def record(results: dict, settings: dict, data: dict) -> dict:
    keep = ("status", "key", "metrics", "digest", "error", "view_error")
    return {"made": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "settings": settings, "data": data,
            "nodes": {n: {k: r[k] for k in keep if r.get(k) is not None} for n, r in results.items()}}


def compare(run: dict, ref: dict, rel_tol=1e-9, abs_tol=1e-12) -> dict:
    """{node: [what differs]} between a run and its reference (the baseline); empty: they match."""
    def same(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
        return a == b
    show = lambda v: f"{v:.6g}" if isinstance(v, float) else v
    out = {}
    for n in set(run["nodes"]) | set(ref["nodes"]):
        a, b = run["nodes"].get(n), ref["nodes"].get(n)
        if not a or not b:
            out[n] = ["only in the baseline" if b else "not in the baseline"]
        elif a["status"] != "done":
            out[n] = [(a.get("error") or a["status"]).strip().splitlines()[-1]]
        else:
            bad = [f"{k}: {show(b['metrics'].get(k))} → {show(a['metrics'].get(k))}" for k in set(a["metrics"]) | set(b["metrics"])
                   if not same(a["metrics"].get(k), b["metrics"].get(k))]
            out[n] = bad + (["output differs"] if a["digest"] != b["digest"] else [])
            if a.get("view_error"):   # a failed view fails the run, whatever the baseline holds
                out[n].append("view failed: " + a["view_error"].strip().splitlines()[-1])
    return {n: v for n, v in out.items() if v}


# ------------------------------------------------------------------ what the worker calls
_graph: Graph | None = None
_baseline: dict | None = None


def start(root, spec_json, baseline_json):
    global _graph, _baseline
    _graph, _baseline = Graph(root, json.loads(spec_json)), json.loads(baseline_json)


def run_json(settings_json, data_json):
    """The run's results, its record, and how it differs from the baseline (None: no baseline)."""
    settings, data = json.loads(settings_json), json.loads(data_json)
    results = _graph.run(settings, data)
    rec = json.loads(to_json(record(results, settings, data)))   # as a baseline file holds it
    return to_json({"nodes": results, "record": rec, "differs": _baseline and compare(rec, _baseline)})


def output_json(name):
    return to_json(_graph.output(name))
