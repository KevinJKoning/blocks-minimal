"""The core without a browser: reading an app, running its graph, comparing runs, building a
page. A tiny app is written per test; the example apps are checked in the browser
(test_apps, `-m browser`)."""
import json
from pathlib import Path

import pytest

from blocks import graph, ui
from blocktool import build, spec

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
    assert first["double"]["blocks"][0]["items"][0] == {"key": "total", "label": "sum", "goal": "max", "value": 12}
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


def test_builds_one_page(app):
    page = build.build(app, inline=False)
    manifest = json.loads(page.split('id="manifest">')[1].split("</script>")[0])
    assert manifest["title"] == "Doubling" and manifest["runtime"] == "/_runtime/"
    assert set(manifest["files"]) == {"README.md", "nodes/double.py", "nodes/count.py"}
    assert manifest["spec"]["datasets"] == {"numbers": "data/numbers.txt"} and set(manifest["data"]["numbers"]) == {"key", "size", "bytes"}


def test_packages_follow_imports():
    assert "numpy" in build.packages(["pandas"]) and build.packages(["os", "blocks", "helpers"], {"helpers"}) == []
    with pytest.raises(ValueError, match="nosuchpackage"):
        build.packages(["nosuchpackage"])


@pytest.mark.browser
def test_example_apps_match_their_baselines():
    from blocktool import cli
    apps = cli.apps()
    server = cli.serve(0)
    records = cli.run_page([f"http://127.0.0.1:{server.server_port}/{a.name}/" for a in apps])
    assert all(cli.check(a, r) for a, r in zip(apps, records))
    server.shutdown()


def test_example_apps_are_present():
    assert {p.name for p in Path("projects").iterdir()} >= {"parcels", "sensor-calibration", "titanic", "windstorm"}


def test_map_takes_geojson_geometries():
    square = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}
    b = ui.map([square], [1.5], names=["a"], lines=[{"type": "LineString", "coordinates": [[0, 0], [20, 20]]}])
    assert b["bounds"] == [0, 0, 10, 10] and b["shapes"] == [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]]
    assert b["lines"] == [[[[0, 0], [20, 20]]]] and (b["values"], b["names"]) == ([1.5], ["a"])


def test_digest_ignores_memory_addresses():
    class Thing:
        pass
    assert graph.digest({"x": Thing()}) == graph.digest({"x": Thing()})
