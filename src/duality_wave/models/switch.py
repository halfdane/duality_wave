from dataclasses import dataclass
from build123d import *
from duality_wave.models.model_types import RectDimensions

@dataclass
class HasDimensions:
    d: RectDimensions

class Switch:
    cap: HasDimensions
    above: HasDimensions
    below: HasDimensions
    stem: HasDimensions
    bottom_housing: HasDimensions
    upper_housing: HasDimensions
    base: HasDimensions
    clamp_clearance_z: float

    def split_cap(self) -> tuple[Part, Part]:
        """The switch without its keycap, and the keycap alone."""
        raise NotImplementedError