import pytest

from tests.builds import compact_case, full_case, quiet_case


def pytest_collection_modifyitems(items):
    """Integration tests share the cached builds, so a module runs on one xdist worker."""
    for item in items:
        if item.get_closest_marker("integration") is not None:
            item.add_marker(pytest.mark.xdist_group("coupons" if item.module.__name__.endswith("coupons") else "cases"))


@pytest.fixture(autouse=True)
def unit_tests_build_no_case(request, monkeypatch):
    """A test without the integration marker must not build a case. This keeps the fast tier fast."""
    if request.node.get_closest_marker("integration") is not None:
        return

    def refuse(*args, **kwargs):
        raise AssertionError("This test builds a whole case. Mark it with @pytest.mark.integration.")

    monkeypatch.setattr("duality_wave.case.WaveCase.__init__", refuse)


@pytest.fixture
def full():
    """The full variant, both halves, with debug."""
    return full_case()


@pytest.fixture
def compact():
    """The compact variant, left half only, with debug."""
    return compact_case()


@pytest.fixture
def quiet():
    """The full variant, left half only, without debug. Returns the case and the mock that got its viewer pushes."""
    return quiet_case()
