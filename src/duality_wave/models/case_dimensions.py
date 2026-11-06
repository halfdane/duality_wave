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
    # the wall of the keywell reaches this far above the keycaps
    wall_over_cap: float = 0.18

    right_side_offset: float = 200

    bumper_base_offset = 2.5
    # the keyplate reaches this far below the switch housing
    keyplate_under_housing: float = 0.7
    # material under the pin tips
    floor_under_pins: float = 0.4
    # the keyplate ledge that holds the XIAO: from the top of the keyplate to the back of the board.
    # The USB-C connector reaches 4.46 mm below the board back and may stand out of the bed face.
    xiao_ledge: float = 0.6
    # how far the lever of the power switch stands out of the bed face. The bumpers stand out further.
    lever_protrusion: float = 0.8

    def __post_init__(self, switch: Switch, outline: Outline, keys: ErgoKeys):
        # Z chain, top to bottom. All levels are measured from the keyplate top (z = 0).
        # The bed face is at z = -below_z. Every level snaps to a whole number of layers above the bed face.
        profile = self.print_profile
        self.below_z: float = profile.snap_up(switch.below.d.Z + self.floor_under_pins)
        # the top of the keywell stands at least wall_over_cap over the caps
        self.above_z: float = self.snap_z(switch.above.d.Z + self.wall_over_cap)
        # the keyplate reaches at least keyplate_under_housing under the housing: the plate gets thinner, not the keyplate
        plate = profile.snap_down(self.below_z - (switch.bottom_housing.d.Z + self.keyplate_under_housing))
        self.keyplate_z: float = round(self.below_z - plate, 6)
        self.bottom_plate_z: float = plate

        xiao_pos_x: float = outline.top_left.X + Xiao.dims.d.X/2 + 5
        xiao_pos_y: float = outline.top_left.Y - Xiao.dims.d.Y/2 - Xiao.usb.forward_y - self.wall_thickness - 2*self.clearance
        # up, so the USB-C connector never stands out further than the ledge asks
        xiao_pos_z: float = self.snap_z(-self.xiao_ledge)
        self.xiao_position: Vector = Vector(xiao_pos_x, xiao_pos_y, xiao_pos_z)

        xiao_to_power_switch: float = PowerSwitch.dims.d.Y/2 + PowerSwitch.dims.pin_length/2
        self.powerswitch_rotation: Vector = Vector(0, 180, -90)
        # down, so the body keeps clear of the battery
        self.powerswitch_position: Vector = Vector(
                xiao_pos_x + Xiao.dims.d.X/2 + xiao_to_power_switch,
                xiao_pos_y - 1,
                self.snap_z(-(self.below_z - PowerSwitch.lever.reach + self.lever_protrusion), up=False))

        battery_d: RectDimensions = RectDimensions(31, 17, 6)
        self.battery_pd = PosAndDims(
            d=battery_d,
            p=outline.top_left \
                + ((self.wall_thickness + self.clearance), -(self.wall_thickness + self.clearance)) \
                + (battery_d.X/2, - battery_d.Y/2, (self.snap_z(self.above_z - self.wall_thickness, up=False) - battery_d.Z/2)))

        self.magnet_d: RoundDimensions = RoundDimensions(5, 2)

        self.place_fixtures(switch, outline, keys)

    def snap_z(self, z: float, up: bool = True) -> float:
        """Move z to a whole number of layers above the bed face (z = -below_z)."""
        snap = self.print_profile.snap_up if up else self.print_profile.snap_down
        return round(snap(z + self.below_z) - self.below_z, 6)

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
            keys.thumb_clusters[0][1][0].p + Vector(switch.cap.d.X/2 - bumpers_radius/2 - 0.5, -switch.cap.d.Y/2+bumpers_radius/2 + 0.5).rotate(Axis.Z, keys.thumb_clusters[0][1][0].r) + (1.5, 8.5),
            outline.top_right + Vector(-bumpers_radius, -bumpers_radius),
            outline.bottom_left + Vector(bumpers_radius, bumpers_radius),
            # clear of the XIAO processor pocket, which sits at the same depth
            outline.top_left + Vector(bumpers_radius + 6, -bumpers_radius - 20),
            (keys.finger_clusters[0][2][0].p + keys.finger_clusters[0][2][1].p) / 2 + (7, -3),
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
            keys.thumb_clusters[0][1][0].p + Vector(switch.cap.d.X/2 - bumpers_radius/2 - 0.5, -switch.cap.d.Y/2+bumpers_radius/2 + 0.5).rotate(Axis.Z, keys.thumb_clusters[0][1][0].r) + (-11, 8),
            outline.top_right + Vector(-bumpers_radius, -bumpers_radius),
            outline.bottom_left + Vector(bumpers_radius, bumpers_radius-3),
            outline.top_left + Vector(bumpers_radius + 1, -bumpers_radius - 20),
        ]

        self.space_invader: Location = Location((24, -6), (0, 0, -50))
