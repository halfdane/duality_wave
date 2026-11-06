import pytest


@pytest.fixture(autouse=True)
def fast_tests_build_no_case(request, monkeypatch):
    """R-13: a test without the slow marker must not build a case."""
    if request.node.get_closest_marker("slow") is not None:
        return

    def refuse(*args, **kwargs):
        raise AssertionError("This test builds a whole case. Mark it with @pytest.mark.slow.")

    monkeypatch.setattr("duality_wave.case.WaveCase.__init__", refuse)
