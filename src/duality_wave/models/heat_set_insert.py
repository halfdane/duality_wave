from dataclasses import dataclass

from build123d import *

from duality_wave.models.model_types import RoundDimensions


@dataclass
class HeatSetInsertDimensions:
    d: RoundDimensions = RoundDimensions(1.75, 2.0)
    bore: RoundDimensions = RoundDimensions(1.0, 2.0)


class HeatSetInsert:
    dims = HeatSetInsertDimensions()

    def __init__(self):
        with BuildPart() as model:
            Cylinder(self.dims.d.radius, self.dims.d.Z)
            Cylinder(self.dims.bore.radius, self.dims.bore.Z, mode=Mode.SUBTRACT)
        self.model = model.part
