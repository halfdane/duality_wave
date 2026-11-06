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
    clamp_clearance_z: float