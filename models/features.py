from build123d import *

from models.model_types import RoundDimensions
from models.print_profile import PrintProfile
from models.switch import Switch


def switch_cutter(switch: Switch, profile: PrintProfile, placements: list[Location], plate_z: float) -> Part:
    """Cutter for the switch holes of a keyplate whose switch-side face is at z=0 and which extends down to -plate_z.

    The hole is switch-sized at the top and wider below, so the switch clamps can snap behind the plate.
    """
    size_x = switch.below.d.X + 2 * profile.switch_clearance
    size_y = switch.below.d.Y + 2 * profile.switch_clearance
    relief = profile.switch_corner_relief

    with BuildPart() as cutter:
        with BuildSketch() as holes:
            for placement in placements:
                with Locations(placement):
                    Rectangle(size_x, size_y)
                    if relief > 0:
                        with Locations((size_x / 2, size_y / 2), (-size_x / 2, size_y / 2),
                                       (size_x / 2, -size_y / 2), (-size_x / 2, -size_y / 2)):
                            Circle(relief)
        extrude(amount=-switch.clamp_clearance_z)

        with BuildSketch(Plane.XY.offset(-switch.clamp_clearance_z)):
            offset(holes.sketch, 0.5)
        extrude(amount=-plate_z)

        if profile.mouth_chamfer > 0:
            with BuildSketch():
                offset(holes.sketch, profile.mouth_chamfer)
            extrude(amount=-profile.mouth_chamfer, taper=45)
    return cutter.part


def magnet_recess_cutter(magnet: RoundDimensions, profile: PrintProfile, positions: list[Vector], top_z: float) -> Part:
    """Cutter for round magnet recesses that open at top_z and take two stacked magnets."""
    radius = magnet.radius + profile.magnet_clearance
    xy = [(position.X, position.Y) for position in positions]

    with BuildPart() as cutter:
        with BuildSketch(Plane.XY.offset(top_z)):
            with Locations(xy):
                Circle(radius)
        extrude(amount=-2 * magnet.Z)

        if profile.mouth_chamfer > 0:
            with BuildSketch(Plane.XY.offset(top_z)):
                with Locations(xy):
                    Circle(radius + profile.mouth_chamfer)
            extrude(amount=-profile.mouth_chamfer, taper=45)
    return cutter.part
