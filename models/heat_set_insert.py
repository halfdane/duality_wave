from dataclasses import dataclass

from build123d import *

from models.model_types import RoundDimensions


@dataclass
class HeatSetInsertDimensions:
    d: RoundDimensions = RoundDimensions(1.75, 2.0)
    bore: RoundDimensions = RoundDimensions(1.0, 2.0)


@dataclass
class HeatSetInsertMountDimensions:
    pilot: RoundDimensions


class HeatSetInsert:
    dims = HeatSetInsertDimensions()

    def __init__(self, profile: str = "mjf_pa12"):
        pilot_radii = {
            "mjf_pa12": 1.6,
            "fdm": 1.5,
        }
        try:
            pilot_radius = pilot_radii[profile]
        except KeyError as error:
            supported = ", ".join(pilot_radii)
            raise ValueError(f"Unknown insert profile {profile!r}; expected one of: {supported}") from error

        self.mount = HeatSetInsertMountDimensions(
            pilot=RoundDimensions(pilot_radius, 2.2),
        )

        with BuildPart() as model:
            Cylinder(self.dims.d.radius, self.dims.d.Z)
            Cylinder(self.dims.bore.radius, self.dims.bore.Z, mode=Mode.SUBTRACT)
        self.model = model.part
