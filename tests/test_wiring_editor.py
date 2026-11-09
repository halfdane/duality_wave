"""R-43: the visual wiring editor. It reads the wiring file as vertices, checks them and writes them back as plain coordinates."""

import copy
from dataclasses import replace
import importlib.util
import json
import shutil
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

from duality_wave.paths import ROOT, WIRING_FILE
from duality_wave.wiring import check
from duality_wave.wiring.editor import Editor, EditorError, tidy_path
from duality_wave.wiring.geometry import inside, inside_points
from duality_wave.wiring.plan import LAYERS, WiringFileError
from tests.builds import make_context


@pytest.fixture(scope="module")
def ctx():
    return make_context()


@pytest.fixture
def editor(ctx, tmp_path, monkeypatch):
    monkeypatch.setattr("duality_wave.wiring.editor.BUILD_DIR", tmp_path / "build")
    path = tmp_path / "wiring.yaml"
    shutil.copyfile(WIRING_FILE, path)
    return Editor(ctx, path)


def state_of(document: dict, side: str = "left") -> dict:
    return {**document["sides"][side], "channel": document["channel"]}


def test_the_file_survives_a_round_trip_through_the_vertices_of_the_editor(editor):  # R-43
    before = editor.path.read_text()
    editor.save(editor.document())
    assert editor.path.read_text() == before


def test_saving_writes_the_moved_vertex_keeps_a_backup_and_leaves_the_rest(editor, tmp_path):  # R-43
    before = editor.path.read_text()
    document = editor.document()
    vertex = document["sides"]["left"]["underside"]["col 3"][0][1]
    vertex[0] += 0.5
    editor.save(document)
    assert (tmp_path / "build" / "wiring.backup.yaml").read_text() == before
    assert editor.document()["sides"]["left"]["underside"]["col 3"][0][1][0] == pytest.approx(vertex[0], abs=0.001)
    changed = [a for a, b in zip(before.splitlines(), editor.path.read_text().splitlines()) if a != b]
    assert len(changed) == 1


def test_a_radius_is_written_only_for_a_corner_that_has_one(editor):  # R-43
    document = editor.document()
    path = document["sides"]["left"]["underside"]["col 3"][0]
    path[1][2], path[2][2] = None, 0.75
    editor.save(document)
    path = editor.document()["sides"]["left"]["underside"]["col 3"][0]
    assert path[1][2] is None and path[2][2] == 0.75


def test_a_state_that_breaks_the_analysis_is_not_written(editor):  # R-43
    before = editor.path.read_text()
    document = editor.document()
    document["sides"]["left"]["notches"].pop("matrix_pinky_top")
    with pytest.raises(EditorError):
        editor.save(document)
    assert editor.path.read_text() == before


def test_tidy_takes_away_repeated_and_straight_vertices_and_keeps_the_ends_and_the_corners(editor):  # R-43
    path = [[0, 0, None], [0, 0, None], [5, 0, None], [10, 0, 0.75], [10, 5, None], [10, 5, None], [10, 5, None]]
    assert tidy_path(path) == [[0, 0, None], [10, 0, 0.75], [10, 5, None]]
    assert tidy_path([[0, 0, None], [5, 0, None]]) == [[0, 0, None], [5, 0, None]]
    assert len(tidy_path([[0, 0, None], [5, 0, None], [1, 0, None]])) == 3
    assert len(tidy_path([[0, 0, None], [5, 0.2, None], [10, 0, None]])) == 3
    assert len(tidy_path([[0, 0, None], [5, 0.001, None], [10, 0, None]])) == 2
    document = editor.document()
    state = state_of(document)
    net = next(iter(state["underside"]))
    first = state["underside"][net][0]
    first.insert(1, list(first[0]))
    paths, removed = editor.tidy(state)

    def count(layers):
        return sum(len(p) for layer in LAYERS for ps in layers[layer].values() for p in ps)

    assert removed == count(state) - count(paths) > 0
    assert paths["underside"].keys() == state["underside"].keys()
    for layer in LAYERS:
        for net, ps in state[layer].items():
            for before, after in zip(ps, paths[layer][net]):
                assert after[0] == before[0] and after[-1] == before[-1]
    again, more = editor.tidy(paths)
    assert more == 0 and again == paths
    editor_state = {**state, **paths}
    assert editor.analyze("left", editor_state)["problems"] == editor.analyze("left", state)["problems"]


def test_the_notches_say_which_diodes_need_a_sleeve_and_how_far_a_diode_may_move(editor):  # R-37, R-43
    document = editor.document()
    for side in ("left", "right"):
        answer = editor.analyze(side, state_of(document, side), fast=True)
        crossing = sorted(name for name, n in answer["notches"].items() if n["sleeve"])
        plate = editor.plate(side)
        assert crossing == sorted(name for name, (s, _) in document["sides"][side]["notches"].items() if s != plate.default_side)
        low, high = editor.geometry(side)["diode_y"]
        assert low == pytest.approx(plate.y_range()[0], abs=0.001) and low < high
    state = state_of(document)
    before = editor.analyze("left", state, fast=True)["notches"]["matrix_index_top"]["sleeve"]
    side, y = state["notches"]["matrix_index_top"]
    state["notches"]["matrix_index_top"] = [-side, y]
    assert editor.analyze("left", state, fast=True)["notches"]["matrix_index_top"]["sleeve"] != before


def test_the_checks_of_the_editor_give_the_place_of_each_problem(editor):  # R-43
    document = editor.document()
    clean = editor.analyze("left", state_of(document))
    assert clean["problems"] == []
    assert set(clean) >= {"notches", "nets", "discs", "anchors", "walls", "trench_length"}
    document["sides"]["left"]["underside"]["col 3"] = []
    answer = editor.analyze("left", state_of(document))
    assert answer["problems"]
    assert all(p["at"] is not None for p in answer["problems"] if p["layer"] == "underside")


def test_moving_a_diode_moves_its_cathode_and_a_fast_answer_has_no_checks(editor):  # R-43
    document = editor.document()
    state = state_of(document)
    tip = editor.analyze("left", state, fast=True)["anchors"]["matrix_index_home.cathode"]
    side, y = state["notches"]["matrix_index_home"]
    state["notches"]["matrix_index_home"] = [side, y + 1.0]
    answer = editor.analyze("left", state, fast=True)
    assert "problems" not in answer
    assert np.linalg.norm(np.array(answer["anchors"]["matrix_index_home.cathode"]) - tip) == pytest.approx(1.0, abs=0.05)


def test_a_power_wire_that_stops_short_of_the_xiao_window_is_reported(editor):  # R-43
    half = check.Half.of(editor.ctx, editor.plan, "left")
    assert check.check_top(half) == []
    name, paths = next(iter(half.plan.top.items()))
    short = copy.deepcopy(paths)
    short[-1] = [*short[-1][:-2], (20.0, short[-1][-1][1], 0.0)]
    top = {**half.plan.top, name: short}
    problems = check.check_top(replace(half, plan=replace(half.plan, top=top)))
    assert any("window" in p for p in problems)
    assert all(p.layer == "top" and p.at is not None for p in problems)


def test_the_editor_refuses_a_file_with_a_channel_for_each_half(editor):  # R-43
    editor.path.write_text(editor.path.read_text().replace("\nright:\n", "\nright:\n  channel: {from: [0, 0], to: [5, 5]}\n", 1))
    with pytest.raises(WiringFileError, match="channel"):
        editor.reload()


def test_the_point_in_polygon_test_for_many_points_agrees_with_the_test_for_one():  # R-43
    polygon = np.array([[0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [4, 3], [4, 4], [0, 4]], dtype=float)
    points = np.random.default_rng(1).uniform(-1, 5, (400, 2))
    assert list(inside_points(points, polygon)) == [inside(p, polygon) for p in points]


def load_server():
    spec = importlib.util.spec_from_file_location("wiring_editor_script", ROOT / "scripts" / "wiring_editor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_server_refuses_requests_without_the_guard_header_or_from_another_host(editor):  # R-43
    module = load_server()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), module.make_handler(editor, port))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"

        def get(path, headers):
            request = urllib.request.Request(base + path, headers=headers)
            try:
                with urllib.request.urlopen(request) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as error:
                return error.code, b""

        assert get("/", {})[0] == 200
        assert get("/api/document", {})[0] == 403
        assert get("/", {"Host": "evil.example"})[0] == 403
        status, body = get("/api/document", {"X-Wiring-Editor": "1"})
        assert status == 200 and set(json.loads(body)) == {"document", "geometry"}
        tidy = urllib.request.Request(base + "/api/tidy", data=json.dumps({"state": {"underside": {"col 1": [[[0, 0, None], [1, 0, None], [2, 0, None]]]}, "top": {}}}).encode(),
                                      headers={"X-Wiring-Editor": "1"}, method="POST")
        with urllib.request.urlopen(tidy) as response:
            assert json.loads(response.read())["removed"] == 1
        post = urllib.request.Request(base + "/api/save", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(post)
        assert refused.value.code == 403
    finally:
        server.shutdown()
        server.server_close()


def test_a_corner_without_an_arc_is_sharp_and_does_not_break_the_checks(editor):  # R-43
    from duality_wave.wiring.rounded import normalize, sample

    straight = normalize([[0, 0], [5, 0, 0.75], [10, 0]])
    folded = normalize([[0, 0], [5, 0, 0.75], [2, 0]])
    doubled = normalize([[0, 0], [5, 0], [5, 0, 1.0], [10, 5]])
    assert straight[1][2] == folded[1][2] == doubled[2][2] == 0.0
    assert np.isfinite(sample(straight)).all() and np.isfinite(sample(folded)).all() and np.isfinite(sample(doubled)).all()
    document = editor.document()
    path = document["sides"]["left"]["underside"]["col 3"][0]
    path[1][1] = path[0][1]
    path[1][2] = 0.75
    path[2][:2] = [path[1][0] + 5, path[0][1]]
    assert "problems" in editor.analyze("left", state_of(document))
