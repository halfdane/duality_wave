import time

import pytest

from tests import PERF_FACTOR
from tests.builds import compact_case, full_case, quiet_case

UNIT_CPU_BUDGET = 1.0 * PERF_FACTOR
BUDGET_EXEMPT_MARKERS = ("integration", "perf")


def pytest_collection_modifyitems(items):
    """Integration tests share the cached builds, so a module runs on one xdist worker."""
    for item in items:
        if item.get_closest_marker("integration") is not None:
            item.add_marker(pytest.mark.xdist_group("coupons" if "coupons" in item.module.__name__ else "cases"))


@pytest.fixture(autouse=True)
def unit_tests_build_no_case(request, monkeypatch):
    """A test without the integration marker must not build a case. This keeps the fast tier fast."""
    if request.node.get_closest_marker("integration") is not None:
        return

    def refuse(*args, **kwargs):
        raise AssertionError("This test builds a whole case. Mark it with @pytest.mark.integration.")

    monkeypatch.setattr("duality_wave.case.WaveCase.__init__", refuse)


@pytest.fixture(autouse=True)
def unit_tests_stay_in_the_cpu_budget(request):
    """A unit test uses at most UNIT_CPU_BUDGET seconds of CPU in its own thread. Fixtures with a wider scope are shared and do not count.

    Worker threads of the geometry kernel spin under load, so the CPU of the whole process would flake under xdist.
    """
    if any(request.node.get_closest_marker(name) is not None for name in BUDGET_EXEMPT_MARKERS):
        yield
        return
    start = time.thread_time()
    yield
    used = time.thread_time() - start
    if used > UNIT_CPU_BUDGET:
        pytest.fail(
            f"This unit test used {used:.1f} s of CPU. The budget is {UNIT_CPU_BUDGET:.1f} s. "
            "Test a smaller shape or one builder alone. Do not add a marker or raise the budget.",
            pytrace=False,
        )


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
