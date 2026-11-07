from dataclasses import dataclass
from build123d import *

from duality_wave.models.print_profile import PrintProfile

class RectDimensions(Vector):
    pass

class RoundDimensions(Vector):
    def __init__(self, radius: float, z: float):
        super().__init__(radius, 0, z)

    @property
    def radius(self):
        return self.X

@dataclass(frozen=True)
class PosAndDims:
    p: Vector
    d: RectDimensions | RoundDimensions

class WaveDimensions:
    print_profile: PrintProfile
    wall_thickness: float
    additional_top_space: float

    above_z: float
    keyplate_under_housing: float
    floor_under_pins: float
    xiao_ledge: float
    lever_protrusion: float
    below_z: float
    bottom_plate_z: float
    keyplate_z: float

    heat_insert_z: float
    fastener_positions: list[Vector]

    xiao_position: Vector

    powerswitch_position: Vector
    powerswitch_rotation: Vector

    battery_pd: PosAndDims

    magnet_d: RoundDimensions
    magnet_spacer: RoundDimensions
    magnet_z: float
    magnet_positions: list[Vector]

    bumper_locations: list[Vector]

    space_invader: Location = None

    @property
    def clearance(self) -> float:
        return self.print_profile.clearance
