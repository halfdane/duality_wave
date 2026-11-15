"""The visual wiring editor. It reads the wiring file as vertices, checks them and writes them back as plain coordinates."""

import shutil

import pytest

from duality_wave.paths import WIRING_FILE
from duality_wave.wiring.editor import Editor, EditorError, tidy_path
from tests.builds import make_context


@pytest.fixture(scope="module")
def ctx():
    return make_context()


@pytest.fixture(scope="module")
def shared_editor(ctx, tmp_path_factory):
    folder = tmp_path_factory.mktemp("wiring")
    path = folder / "wiring.yaml"
    shutil.copyfile(WIRING_FILE, path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("duality_wave.wiring.editor.BUILD_DIR", folder / "build")
        yield Editor(ctx, path)


@pytest.fixture
def editor(shared_editor):
    original = shared_editor.path.read_text()
    shared_editor.reload()
    yield shared_editor
    shared_editor.path.write_text(original)
    shared_editor.reload()


def test_saving_writes_what_changed_keeps_a_backup_and_leaves_the_rest(editor, monkeypatch):
    monkeypatch.setattr(editor, "analyze", lambda *args, **kwargs: {})
    before = editor.path.read_text()
    document = editor.document()
    path = document["sides"]["left"]["underside"]["col 3"][0]
    path[1][0] += 0.5
    editor.save(document)
    assert (editor.path.parent / "build" / "wiring.backup.yaml").read_text() == before
    assert editor.document()["sides"]["left"]["underside"]["col 3"][0][1][0] == pytest.approx(path[1][0], abs=0.001)
    assert len([a for a, b in zip(before.splitlines(), editor.path.read_text().splitlines()) if a != b]) == 1

    document = editor.document()
    path = document["sides"]["left"]["underside"]["col 3"][0]
    path[1][2], path[2][2] = None, 0.75
    editor.save(document)
    path = editor.document()["sides"]["left"]["underside"]["col 3"][0]
    assert path[1][2] is None and path[2][2] == 0.75


def test_a_state_that_breaks_the_analysis_is_not_written(editor):
    before = editor.path.read_text()
    document = editor.document()
    document["sides"]["left"]["notches"].pop("matrix_pinky_top")
    with pytest.raises(EditorError):
        editor.save(document)
    assert editor.path.read_text() == before


def test_tidy_takes_away_repeated_and_straight_vertices_and_keeps_the_ends_and_the_corners():
    path = [[0, 0, None], [0, 0, None], [5, 0, None], [10, 0, 0.75], [10, 5, None], [10, 5, None], [10, 5, None]]
    assert tidy_path(path) == [[0, 0, None], [10, 0, 0.75], [10, 5, None]]
    assert tidy_path([[0, 0, None], [5, 0, None]]) == [[0, 0, None], [5, 0, None]]
    assert len(tidy_path([[0, 0, None], [5, 0, None], [1, 0, None]])) == 3
    assert len(tidy_path([[0, 0, None], [5, 0.2, None], [10, 0, None]])) == 3
    assert len(tidy_path([[0, 0, None], [5, 0.001, None], [10, 0, None]])) == 2
