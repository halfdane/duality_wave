import time
from contextlib import contextmanager


class StageTimings(dict):
    """Wall-clock seconds per build stage. Stages with the same name add up."""

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self[name] = self.get(name, 0.0) + time.perf_counter() - start

    @property
    def total(self) -> float:
        return sum(self.values())
