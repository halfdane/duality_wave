from dataclasses import dataclass, field, InitVar

from build123d import *

from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.model_types import PosAndDims, RectDimensions, RoundDimensions, WaveDimensions
from duality_wave.models.outline import Outline
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.print_profile import PrintProfile
from duality_wave.models.rubber_bumper import BumperDimensions
from duality_wave.models.switch import Switch
from duality_wave.models.xiao import Xiao


@dataclass
class CaseDimensions(WaveDimensions):
    """Dimensions of the full wave case. Variants override the defaults and place_fixtures()."""

    switch: InitVar[Switch]
    outline: InitVar[Outline]
    keys: InitVar[ErgoKeys]

    print_profile: PrintProfile = field(default_factory=PrintProfile)
    wall_thickness: float = 1.8
    heat_insert_z: float = 3.5

    right_side_offset: float = 200

    bumper_base_offset = 2.5

    def __post_init__(self, switch: Switch, outline: Outline, keys: ErgoKeys):
        self.add_below_choc_posts: float = 0.7
        self.bottom_plate_z: float = 3.0
        self.above_z: float = switch.above.d.Z
        self.below_z: float = switch.below.d.Z + self.add_below_choc_posts
        self.keyplate_z: float = self.below_z - self.bottom_plate_z

        xiao_pos_x: float = outline.top_left.X + Xiao.dims.d.X/2 + 5
        xiao_pos_y: float = outline.top_left.Y - Xiao.dims.d.Y/2 - Xiao.usb.forward_y - self.wall_thickness - 2*self.clearance
        xiao_pos_z: float = -1.45
        self.xiao_position: Vector = Vector(xiao_pos_x, xiao_pos_y, xiao_pos_z)

        xiao_to_power_switch: float = PowerSwitch.dims.d.Y/2 + PowerSwitch.dims.pin_length/2
        self.powerswitch_rotation: Vector = Vector(0, 180, -90)
        self.powerswitch_position: Vector = Vector(
                xiao_pos_x + Xiao.dims.d.X/2 + xiao_to_power_switch,
                xiao_pos_y - 1,
                -(self.below_z - 0.75*PowerSwitch.lever.d.Z))

        battery_d: RectDimensions = RectDimensions(31, 17, 6)
        self.battery_pd = PosAndDims(
            d=battery_d,
            p=outline.top_left \
                + ((self.wall_thickness + self.clearance), -(self.wall_thickness + self.clearance)) \
                + (battery_d.X/2, - battery_d.Y/2, (self.above_z - battery_d.Z/2 - self.wall_thickness)))

        self.magnet_d: RoundDimensions = RoundDimensions(5, 2)

        self.place_fixtures(switch, outline, keys)

    @property
    def bumper_radius(self) -> float:
        return BumperDimensions.radius + self.bumper_base_offset

    @property
    def magnet_z(self) -> float:
        """Flush with the surface: 0mm gap when the halves are together."""
        return self.above_z

    def place_fixtures(self, switch: Switch, outline: Outline, keys: ErgoKeys) -> None:
        """Set fastener_positions, magnet_positions, bumper_locations and space_invader."""
        magnet_z = self.magnet_z
        bumpers_radius = self.bumper_radius

        self.fastener_positions = [
            Vector(-12, 2),
            Vector(22, 62),
            Vector(-12, 50),
            Vector(70, 65),
            Vector(86, 7),
            Vector(36, 6),
        ]

        self.magnet_positions: list[Vector] = (
            outline.top_right + (-self.wall_thickness - self.clearance - self.magnet_d.radius - 4, -self.wall_thickness - self.clearance - self.magnet_d.radius - 4, magnet_z),
            keys.finger_clusters[0][0][2].p + Vector(0, switch.cap.d.Y/2 + self.magnet_d.radius + 2, magnet_z).rotate(Axis.Z, keys.finger_clusters[0][0][2].r),
            keys.finger_clusters[0][2][2].p + Vector(0, switch.cap.d.Y/2 + self.magnet_d.radius + 1.5, magnet_z).rotate(Axis.Z, keys.finger_clusters[0][2][2].r),
            keys.finger_clusters[0][2][0].p + Vector(0, -switch.cap.d.Y/2 - self.magnet_d.radius - 4, magnet_z).rotate(Axis.Z, keys.finger_clusters[0][2][0].r),
        )

        self.bumper_locations = [
            keys.thumb_clusters[0][1][0].p + Vector(switch.cap.d.X/2 - bumpers_radius/2 - 0.5, -switch.cap.d.Y/2+bumpers_radius/2 + 0.5).rotate(Axis.Z, keys.thumb_clusters[0][1][0].r),
            outline.top_right + Vector(-bumpers_radius, -bumpers_radius),
            outline.bottom_left + Vector(bumpers_radius, bumpers_radius),
            outline.top_left + Vector(bumpers_radius, -bumpers_radius- 10),
            (keys.finger_clusters[0][2][0].p + keys.finger_clusters[0][2][1].p) / 2 + (8, 0),
        ]

        self.space_invader: Location = Location(
            outline.cirque_recess_position + (outline.cirque_recess_radius-2, outline.cirque_recess_radius),
            (0, 0, -40))


@dataclass
class CompactCaseDimensions(CaseDimensions):
    """The small variant for test prints."""

    heat_insert_z: float = HeatSetInsert.dims.d.Z
    right_side_offset: float = 100

    def place_fixtures(self, switch: Switch, outline: Outline, keys: ErgoKeys) -> None:
        magnet_z = self.magnet_z
        bumpers_radius = self.bumper_radius

        self.fastener_positions = [
            Vector(24, 23),
            Vector(34, -10),
            Vector(0, -14),
        ]

        self.magnet_positions: list[Vector] = [
            Vector(-3, -11, magnet_z),
        ]

        self.bumper_locations = [
            keys.thumb_clusters[0][1][0].p + Vector(switch.cap.d.X/2 - bumpers_radius/2 - 0.5, -switch.cap.d.Y/2+bumpers_radius/2 + 0.5).rotate(Axis.Z, keys.thumb_clusters[0][1][0].r),
            outline.top_right + Vector(-bumpers_radius, -bumpers_radius),
            outline.bottom_left + Vector(bumpers_radius, bumpers_radius-3),
            outline.top_left + Vector(bumpers_radius, -bumpers_radius -10),
        ]

        self.space_invader: Location = Location((24, -6), (0, 0, -50))
