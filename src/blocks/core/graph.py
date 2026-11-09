"""The graph, run in Pyodide: nodes are functions, values pass in memory, and each output is
cached by its node's key (Graph.key). A fork is a node written more than one way; a run takes
one option at each (its choices), and since outputs are kept by key, the paths through the
forks share whatever they have in common (spread says how far they move the answer). A run
leaves a record, which verify compares with the baseline (compare).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import json
import math
import os
import re
import sys
import time
import traceback
import types
from pathlib import Path


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
    """The numbers in an output (a dict, nested), as (dotted key, value)."""
    if not isinstance(o, dict):
        return
    for k, v in o.items():
        if isinstance(v, dict):
            yield from numbers(v, f"{prefix}{k}.")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            yield f"{prefix}{k}", v
        elif getattr(v, "shape", None) == () and hasattr(v, "item"):   # numpy scalar
            yield f"{prefix}{k}", v.item()


def digest(v) -> str:
    """A value's sha256, fed in deterministically: two outputs are the same when their digests are."""
    h, seen = hashlib.sha256(), set()

    def feed(v):
        if v is None or isinstance(v, (bool, int, str)):
            h.update(json.dumps(v).encode())
        elif isinstance(v, float):
            h.update(("f" + ("nan" if math.isnan(v) else repr(v))).encode())
        elif isinstance(v, (bytes, bytearray)):
            h.update(b"b" + bytes(v))
        elif isinstance(v, type):   # a class (numpy's float64 has a dtype of its own): its name
            h.update(f"t{v.__module__}.{v.__qualname__}".encode())
        elif isinstance(v, dict):
            h.update(b"{")
            for k in sorted(v, key=str):
                feed(str(k)); feed(v[k])
            h.update(b"}")
        elif isinstance(v, (list, tuple)):
            h.update(b"[")
            for x in v:
                feed(x)
            h.update(b"]")
        elif hasattr(v, "dtype") and getattr(v.dtype, "hasobject", False):     # numpy of Python objects: their bytes are addresses
            h.update(f"nd{v.shape}".encode()); feed(v.tolist())
        elif hasattr(v, "dtype") and hasattr(v, "tobytes"):                   # numpy
            h.update(f"nd{v.dtype.str}{v.shape}".encode() + v.tobytes())
        elif hasattr(v, "to_pydict"):                                         # pyarrow table
            feed(v.to_pydict())
        elif hasattr(v, "to_pylist"):                                         # pyarrow array
            feed(v.to_pylist())
        elif hasattr(v, "columns") and hasattr(v, "to_numpy"):                # pandas
            feed({str(c): v[c].to_numpy() for c in v.columns})
        elif hasattr(v, "item"):
            feed(v.item())
        else:   # any other object: its class and what it would pickle (a fitted model's weights,
            # a geometry's WKB); its repr, less the address that differs run to run, if nothing
            try:
                state = None if id(v) in seen else v.__reduce_ex__(4)
            except Exception:  # noqa: BLE001 - it cannot be pickled
                state = None
            seen.add(id(v))
            h.update(f"o{type(v).__module__}.{type(v).__qualname__}".encode())
            if isinstance(state, tuple):
                feed(state[1:3])
            else:
                h.update(re.sub(r" at 0x[0-9a-fA-F]+", "", repr(v)).encode())

    feed(v)
    return h.hexdigest()


def to_json(o) -> str:
    """JSON for the page, of plain values: non-finite numbers as strings, since JSON has none."""
    def clean(v):
        if isinstance(v, float) and not math.isfinite(v):
            return "NaN" if math.isnan(v) else ("Infinity" if v > 0 else "-Infinity")
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        return v
    return json.dumps(clean(plain(o)), default=str)


class Graph:
    def __init__(self, root: str, spec: dict):
        self.root, self.spec = os.path.abspath(root), spec
        self.cache: dict[str, tuple[object, dict]] = {}   # key -> (output, result)
        self.used: dict[str, int] = {}                    # key -> the last round that read it
        self.round, self.inputs = 0, None                 # a round is the runs of one set of settings and data
        self.last: dict[str, str] = {}                    # node -> its key in the last run
        self.modules: dict[str, types.ModuleType] = {}
        # The app's helper modules: every .py outside nodes/ and data/. Any node may import them
        # (the app's folder is on sys.path), so they are part of every node's key.
        helpers = sorted(p for p in Path(self.root).rglob("*.py") if not {"nodes", "data"} & set(p.relative_to(self.root).parts))
        self.helpers = hashlib.sha256(b"".join(self._read(p) for p in helpers)).hexdigest()
        if self.root not in sys.path:
            sys.path.insert(0, self.root)

    def _read(self, path):
        with open(os.path.join(self.root, path), "rb") as f:
            return f.read()

    def at(self, name, choices):
        """The node as these choices have it: a fork's option (its chosen one, unless they say), or the node."""
        node = self.spec["nodes"][name]
        return node["options"][choices.get(name, node["chosen"])] if "options" in node else node

    def module(self, node):
        file = node["file"]
        if file not in self.modules:
            path = os.path.join(self.root, file)
            mod = types.ModuleType("node_" + re.sub(r"\W", "_", file.removeprefix("nodes/").removesuffix(".py")))
            mod.__file__ = path
            exec(compile(self._read(path), path, "exec"), mod.__dict__)
            self.modules[file] = mod
        return self.modules[file]

    def run(self, settings: dict, data: dict, choices: dict | None = None) -> dict:
        """settings {name: value}, data {dataset: key}, choices {fork: option}. Returns {node:
        result}. A setting is the app's, by its name: every node that declares it gets its value.
        The cache keeps every output of this round and the one before: other settings or data
        start a round, so the paths through the forks stay at hand, and a long session's do not pile up."""
        choices = choices or {}
        if (settings, data) != self.inputs:
            self.round, self.inputs = self.round + 1, (dict(settings), dict(data))
            for key in [k for k, r in self.used.items() if r < self.round - 1]:
                del self.cache[key], self.used[key]
        results, keys = {}, {}
        self.last = keys
        for name in self.spec["order"]:
            node = self.at(name, choices)
            failed = next((d for d in node["deps"] if d in results and results[d]["status"] != "done"), None)
            if failed:
                results[name] = {"status": "blocked", "error": f"{failed} did not run"}
                continue
            mine = {p: settings.get(p, s["default"]) for p, s in node["settings"].items()}
            key = keys[name] = self.key(name, mine, [data.get(d, "") if d in self.spec["datasets"] else keys[d] for d in node["deps"]], choices)
            if key in self.cache:
                self.used[key] = self.round
                results[name] = {**self.cache[key][1], "cached": True}
                continue
            args = [self.dataset(d) if d in self.spec["datasets"] else self.cache[keys[d]][0] for d in node["deps"]]
            log, t0 = io.StringIO(), time.perf_counter()
            try:
                with contextlib.chdir(self.root), contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    value = getattr(self.module(node), name)(*args, **mine)
            except Exception:  # noqa: BLE001 - a node's failure is reported, never raised
                results[name] = {"status": "error", "key": key, "error": traceback.format_exc(), "log": log.getvalue()[-20000:]}
                continue
            blocks, view_error = self.blocks(node, value)
            metrics = dict(numbers(value))
            unknown = [m["key"] for m in node["metrics"] if m["key"] not in metrics]
            if unknown and not view_error:   # a label for no number is a typo, and it fails the run like a broken view
                view_error = (f"METRICS labels {', '.join(unknown)}, but the output has no such number "
                              f"(its numbers: {', '.join(metrics) or 'none'})")
            result = {"status": "done", "key": key, "seconds": round(time.perf_counter() - t0, 4),
                      "metrics": metrics, "digest": digest(value), "blocks": blocks, "view_error": view_error,
                      "log": log.getvalue()[-20000:]}
            self.cache[key], self.used[key] = (value, result), self.round
            results[name] = {**result, "cached": False}
        return results

    def path(self, settings, data, choices) -> dict:
        """One path through the forks, run, as the page's map of them holds it: its choices,
        the answer it gives ({node.key: number}), each node's metrics, what failed and why
        (the first failure, in full: a path nobody is looking at has nowhere else to show it)."""
        last = self.last   # the page's own path is still the one whose outputs it can ask for
        results, self.last = self.run(settings, data, choices), last
        metrics = {n: r["metrics"] for n, r in results.items() if r["status"] == "done"}
        failed = [n for n, r in results.items() if r["status"] != "done" or r.get("view_error")]
        why = next((r.get("error") or r["view_error"] for r in results.values() if r["status"] == "error" or r.get("view_error")), None)
        return {"choices": choices, "metrics": metrics,
                "answer": {f"{a['node']}.{a['key']}": metrics.get(a["node"], {}).get(a["key"]) for a in self.spec["answer"]},
                "failed": failed, **({"error": why} if failed else {})}

    def key(self, name, settings, input_keys, choices=None):
        """A node's key: its file (a fork's: its option's), the app's helper modules, its settings
        and its inputs' keys (a dataset's is its data key). An output with this key comes from the cache."""
        parts = [hashlib.sha256(self._read(self.at(name, choices or {})["file"])).hexdigest(), self.helpers,
                 json.dumps(settings, sort_keys=True, default=repr), *input_keys]
        return hashlib.sha256("\0".join(parts).encode()).hexdigest()

    def dataset(self, d):
        """A dataset's path, or a folder's file paths in name order."""
        path = os.path.join(self.root, self.spec["datasets"][d])
        if not path.endswith("/"):
            return path
        return [os.path.join(path, f) for f in sorted(os.listdir(path))]

    def blocks(self, node, value):
        """The node's view of its output (without a view, its metrics), and the traceback when
        the view failed."""
        try:
            with contextlib.chdir(self.root):
                if node["view"]:
                    raw = list(self.module(node).view(value) or [])
                else:
                    raw = [{"type": "metrics"}] if node["metrics"] or any(numbers(value)) else []
        except Exception:  # noqa: BLE001 - the node ran; only its view failed
            return [], traceback.format_exc()
        return raw, None


def record(results: dict, settings: dict, data: dict, choices: dict | None = None) -> dict:
    """What a baseline keeps of a run: each node's status, metrics and output digest, or its error.
    No key and no timestamp, so a baseline changes only when a result does. An app with forks
    keeps the run's choices too, and the page adds the paths it explored: each one's answer."""
    keep = ("status", "metrics", "digest", "error", "view_error")
    return {"settings": settings, "data": data, **({"choices": choices} if choices else {}),
            "nodes": {n: {k: r[k] for k in keep if r.get(k) is not None} for n, r in results.items()}}


def paths(forks: dict, choices: dict, limit=64) -> list[dict]:
    """Every path through the forks ({fork: [options]}), as choices. Past the limit, only the
    path of these choices and its neighbours, which differ from it at one fork."""
    count = math.prod(len(o) for o in forks.values())
    if count <= limit:
        return [dict(zip(forks, combo)) for combo in itertools.product(*forks.values())]
    return [dict(choices)] + [{**choices, f: o} for f, options in forks.items() for o in options if o != choices[f]]


def path_name(choices: dict) -> str:
    """A path, as the command line takes it and a reader finds it."""
    return ", ".join(f"{f}={o}" for f, o in choices.items())


def finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def spread(found: list[dict], forks: list[str]) -> dict:
    """How far the paths move each answer: {answer: {lo, hi, forks: {fork: swing}}}. A fork's
    swing is how far the answer moves when only that fork changes: the range of the answer over
    its options, averaged over every setting of the other forks that was run. It is in the
    answer's own units, so a reader can weigh it against what the answer is for."""
    out = {}
    for a in (found[0]["answer"] if found else {}):
        values = [(p["choices"], p["answer"][a]) for p in found if finite(p["answer"].get(a))]
        if not values:
            continue
        swings = {}
        for f in forks:
            groups = {}
            for c, v in values:
                groups.setdefault(json.dumps({k: o for k, o in c.items() if k != f}, sort_keys=True), []).append(v)
            ranges = [max(g) - min(g) for g in groups.values() if len(g) > 1]
            swings[f] = sum(ranges) / len(ranges) if ranges else None
        out[a] = {"lo": min(v for _, v in values), "hi": max(v for _, v in values), "forks": swings}
    return out


def compare(run: dict, ref: dict, rel_tol=1e-9, abs_tol=1e-12) -> dict:
    """{node or dataset: [what differs]} between a run and its reference (the baseline); empty: they match."""
    def same(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol) or (math.isnan(a) and math.isnan(b))
        return a == b
    show = lambda v: f"{v:.6g}" if isinstance(v, float) else v
    out = {}
    for n in set(run["nodes"]) | set(ref["nodes"]):
        a, b = run["nodes"].get(n), ref["nodes"].get(n)
        if not a or not b:
            out[n] = ["only in the baseline" if b else "new, not in the baseline (blocks baseline records it)"]
        elif a["status"] != "done":
            out[n] = [(a.get("error") or a["status"]).strip().splitlines()[-1]]
        elif b["status"] != "done":
            out[n] = [f"{b['status']} in the baseline"]
        else:
            bad = [f"{k}: {show(b['metrics'].get(k))} → {show(a['metrics'].get(k))}" for k in set(a["metrics"]) | set(b["metrics"])
                   if not same(a["metrics"].get(k), b["metrics"].get(k))]
            out[n] = bad + (["output differs"] if a["digest"] != b["digest"] else [])
            if a.get("view_error"):   # a failed view fails the run, whatever the baseline holds
                out[n].append("view failed: " + a["view_error"].strip().splitlines()[-1])
    if run.get("choices", {}) != ref.get("choices", {}):   # another path than the baseline took: its nodes say how it differs
        out["choices"] = [f"{path_name(ref.get('choices', {})) or 'none'} in the baseline (blocks baseline records the path chosen now)"]
    got, kept = ({path_name(p["choices"]): p for p in r.get("paths", [])} for r in (run, ref))
    new, gone = len(got.keys() - kept.keys()), len(kept.keys() - got.keys())
    out["paths"] = ([f"{new} new, not in the baseline (blocks baseline records them)"] if new else []) + ([f"{gone} only in the baseline"] if gone else [])
    for n in got.keys() & kept.keys():
        a, b = got[n], kept[n]
        if a["failed"]:
            out[f"path {n}"] = [f"{', '.join(a['failed'])} failed (blocks run --choose shows why)"]
        else:
            out[f"path {n}"] = [f"{k}: {show(b['answer'].get(k))} → {show(a['answer'].get(k))}" for k in a["answer"].keys() | b["answer"].keys()
                                if not same(a["answer"].get(k), b["answer"].get(k))]
    data, ref_data = run.get("data", {}), ref.get("data", {})
    for d in set(data) | set(ref_data):   # a dataset's key: other data, even when no result moved
        if data.get(d) != ref_data.get(d):
            out[d] = ["its data differs from the baseline's"]
    return {n: v for n, v in out.items() if v}


# What the worker calls:
_graph: Graph | None = None


def start(root, spec_json):
    global _graph
    _graph = Graph(root, json.loads(spec_json))


def run_json(settings_json, data_json, choices_json):
    """The run's results and its record, as a baseline file holds it."""
    settings, data, choices = json.loads(settings_json), json.loads(data_json), json.loads(choices_json)
    results = _graph.run(settings, data, choices)
    return to_json({"nodes": results, "record": record(results, settings, data, choices)})


def path_json(settings_json, data_json, choices_json):
    return to_json(_graph.path(json.loads(settings_json), json.loads(data_json), json.loads(choices_json)))


def paths_json(choices_json):
    """The paths to explore from these choices, in the order the forks come."""
    forks = {f: list(_graph.spec["nodes"][f]["options"]) for f in _graph.spec["forks"]}
    return to_json(paths(forks, json.loads(choices_json)))


def spread_json(found_json):
    return to_json(spread(json.loads(found_json), _graph.spec["forks"]))


def compare_json(record_json, baseline_json):
    """How a record (its paths with it) differs from the baseline."""
    return to_json(compare(json.loads(record_json), json.loads(baseline_json)))


def output_json(name):
    if _graph.last.get(name) not in _graph.cache:
        raise KeyError(f"{name} has not run")
    return to_json(_graph.cache[_graph.last[name]][0])
