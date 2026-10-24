"""The core without a browser: reading an app, running its graph, comparing runs, building a
page. A tiny app is written per test; the example apps are checked in the browser
(test_apps, `-m browser`)."""
import io
import json
from pathlib import Path

import pytest

from blocks import ui
from blocks.core import build, graph, spec

NODES = {
    "double.py": '''"""Twice the numbers in the data."""
from typing import Annotated
from blocks import Range, ui

METRICS = {"total": {"label": "sum", "goal": "max"}}


def double(numbers, *, factor: Annotated[int, Range(1, 5)] = 2):
    values = [factor * int(x) for x in open(numbers).read().split()]
    return {"values": values, "total": sum(values)}


def view(out):
    return [ui.metrics(), ui.chart(range(len(out["values"])), {"values": out["values"]})]
''',
    "count.py": '''def count(double):
    return {"n": len(double["values"])}
''',
}


@pytest.fixture
def app(tmp_path):
    (tmp_path / "nodes").mkdir()
    (tmp_path / "data").mkdir()
    for name, src in NODES.items():
        (tmp_path / "nodes" / name).write_text(src)
    (tmp_path / "data" / "numbers.txt").write_text("1 2 3")
    (tmp_path / "README.md").write_text("# Doubling\n\nA test app.\n")
    return tmp_path


def graph_spec(a):
    return {"order": a["order"], "nodes": a["nodes"], "datasets": {d: v["path"] for d, v in a["datasets"].items()}}


def test_reads_the_graph_from_signatures(app):
    a = spec.load(app)
    assert (a["title"], a["about"]) == ("Doubling", "A test app.")
    assert a["order"] == ["double", "count"]
    assert a["nodes"]["double"]["deps"] == ["numbers"]
    assert a["nodes"]["double"]["settings"] == {"factor": {"default": 2, "min": 1, "max": 5, "type": "int"}}
    assert a["nodes"]["double"]["metrics"] == [{"key": "total", "label": "sum", "goal": "max"}]
    assert a["nodes"]["count"]["view"] is False
    assert list(a["datasets"]) == ["numbers"]


def test_unknown_input_is_an_error(app):
    (app / "nodes" / "bad.py").write_text("def bad(nothing):\n    return 1\n")
    with pytest.raises(ValueError, match="neither a node nor a file"):
        spec.load(app)


def test_runs_only_what_changed(app):
    g = graph.Graph(str(app), graph_spec(spec.load(app)))
    first = g.run({}, {"numbers": "k1"})
    assert first["double"]["metrics"] == {"total": 12} and first["count"]["metrics"] == {"n": 3}
    assert first["double"]["blocks"][0] == {"type": "metrics"} and first["count"]["blocks"] == [{"type": "metrics"}]
    again = g.run({}, {"numbers": "k1"})
    assert again["double"]["cached"] and again["count"]["cached"]
    changed = g.run({"double.factor": 3}, {"numbers": "k1"})
    assert not changed["double"]["cached"] and changed["double"]["metrics"]["total"] == 18
    assert not changed["count"]["cached"] and changed["count"]["digest"] == first["count"]["digest"]


def test_a_failure_blocks_what_reads_it(app):
    (app / "nodes" / "double.py").write_text("def double(numbers):\n    raise ValueError('no')\n")
    results = graph.Graph(str(app), graph_spec(spec.load(app))).run({}, {})
    assert results["double"]["status"] == "error" and "ValueError: no" in results["double"]["error"]
    assert results["count"]["status"] == "blocked"


def test_compare_with_the_baseline(app):
    g = graph.Graph(str(app), graph_spec(spec.load(app)))
    base = json.loads(graph.to_json(graph.record(g.run({}, {}), {}, {})))
    assert graph.compare(base, base) == {}
    other = graph.record(g.run({"double.factor": 3}, {}), {}, {})
    assert set(graph.compare(other, base)) == {"double"}
    (app / "nodes" / "count.py").write_text(NODES["count.py"] + "\n\ndef view(out):\n    return out['nope']\n")
    broken = graph.Graph(str(app), graph_spec(spec.load(app))).run({}, {})
    assert broken["count"]["blocks"] == [] and "KeyError" in broken["count"]["view_error"]
    assert graph.compare(graph.record(broken, {}, {}), base) == {"count": ["view failed: KeyError: 'nope'"]}


def test_builds_one_page(app):
    page = build.build(app, inline=False)
    manifest = json.loads(page.split('id="manifest">')[1].split("</script>")[0])
    assert manifest["title"] == "Doubling" and manifest["runtime"] == "/_runtime/"
    assert "connect-src data: 'self';" in page and "connect-src data:;" in build.build(app, inline=True)
    assert set(manifest["files"]) == {"README.md", "nodes/double.py", "nodes/count.py"}
    assert manifest["spec"]["datasets"] == {"numbers": "data/numbers.txt"} and set(manifest["data"]["numbers"]) == {"key", "size", "bytes"}


def test_packages_follow_imports():
    assert "numpy" in build.packages(["pandas"]) and build.packages(["os", "blocks", "helpers"], {"helpers"}) == []
    with pytest.raises(ValueError, match="nosuchpackage"):
        build.packages(["nosuchpackage"])


def test_runtime_rejects_corrupt_cache_and_download(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "CACHE", tmp_path)
    (tmp_path / "pyodide.mjs").write_bytes(b"corrupt cache")
    monkeypatch.setattr(build.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(b"corrupt download"))
    with pytest.raises(ValueError, match="sha256"):
        build.runtime_file("pyodide.mjs")
    assert (tmp_path / "pyodide.mjs").read_bytes() == b"corrupt cache"
    monkeypatch.setattr(build, "lock", lambda: {"packages": {}})
    with pytest.raises(KeyError):
        build.runtime_file("unlisted.whl")


@pytest.mark.browser
def test_example_apps_match_their_baselines():
    from blocks.core import cli
    apps = cli.apps()
    server = cli.serve(0)
    records = cli.run_page([f"http://127.0.0.1:{server.server_port}/{a.name}/" for a in apps])
    assert all(cli.check(a, r) for a, r in zip(apps, records))
    server.shutdown()


def blocks_are_their_files(folder, names):
    assert {p.stem for p in folder.glob("*.js") if not p.name.startswith("_")} == set(names)
    for name in names:
        assert f"RENDER.{name} = " in (folder / f"{name}.js").read_text()
        css = folder / f"{name}.css"
        selectors = [s.strip() for rule in (css.read_text().split("}") if css.exists() else []) if "{" in rule
                     for s in rule.split("{")[0].split(",")]
        assert all(s == f".{name}" or s.startswith((f".{name} ", f".{name}:")) for s in selectors), (name, selectors)


def test_every_block_is_its_files():
    """Each block made in Python, the library's or an app's, has a renderer of its name, and
    its CSS stays under its class."""
    blocks_are_their_files(build.PACKAGE / "ui", ui.__all__)
    for folder in (Path(__file__).parent.parent / "projects").glob("*/ui"):
        blocks_are_their_files(folder, {p.stem for p in folder.glob("*.py") if not p.name.startswith("_")})


def test_an_app_brings_its_own_block(app):
    (app / "ui").mkdir()
    (app / "ui" / "badge.py").write_text('def badge(text):\n    return {"type": "badge", "text": text}\n')
    (app / "ui" / "badge.js").write_text('RENDER.badge = (b) => h("span", { class: "badge" }, b.text);\n')
    (app / "ui" / "badge.css").write_text(".badge { color: var(--ink); }\n")
    (app / "nodes" / "count.py").write_text(NODES["count.py"] + "\n\ndef view(out):\n    from ui.badge import badge\n    return [badge(f\"{out['n']} values\")]\n")
    page = build.build(app, inline=False)
    assert "RENDER.badge = " in page and ".badge { color" in page and "ticks(" in page
    assert graph.Graph(str(app), graph_spec(spec.load(app))).run({}, {})["count"]["blocks"] == [{"type": "badge", "text": "3 values"}]
    (app / "ui" / "chart.js").write_text("")
    with pytest.raises(ValueError, match="redefines a library block"):
        build.build(app, inline=False)



def test_numbers_that_name_something_read_as_written():
    b = ui.table([{"year": 2024, "people": 1256}, {"year": None, "people": 2}], text=["year"])
    assert b["rows"] == [["2024", 1256], [None, 2]]
    with pytest.raises(ValueError, match="no column yr"):
        ui.table([{"year": 2024}], text=["yr"])


def test_map_takes_geojson_geometries():
    square = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}
    b = ui.map([square], [1.5], names=["a"], lines=[{"type": "LineString", "coordinates": [[0, 0], [20, 20]]}])
    assert b["bounds"] == [0, 0, 10, 10] and b["shapes"] == [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]]
    assert b["lines"] == [[[[0, 0], [20, 20]]]] and (b["values"], b["names"]) == ([1.5], ["a"])


def test_histogram_bins_on_round_edges():
    b = ui.histogram([-0.3, -0.1, 0.0, 0.05, 0.2, float("nan"), None], bins=5, mark=0)
    assert b["edges"][0] <= -0.3 and b["edges"][-1] > 0.2 and sum(b["counts"]) == 5 and b["missing"] == 2
    w = b["edges"][1] - b["edges"][0]
    assert abs(w - 0.1) < 1e-12 and all(abs(e / w - round(e / w)) < 1e-9 for e in b["edges"]) and b["mark"] == 0.0


def test_digest_ignores_memory_addresses():
    class Thing:
        pass
    assert graph.digest({"x": Thing()}) == graph.digest({"x": Thing()})


def test_chart_band_rides_on_its_series():
    b = ui.chart([0, 1], {"a": [1, 2], "b": [3, 4]}, bands={"b": ([2, 3], [4, 5])})
    assert "band" not in b["series"][0] and b["series"][1]["band"] == [[2, 3], [4, 5]]
