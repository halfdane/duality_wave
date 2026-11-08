from dataclasses import dataclass, fields, replace

from build123d import *

from duality_wave.builders.common import CaseContext
from duality_wave.models.features import magnet_spacer
from duality_wave.models.power_switch import PowerSwitch


@dataclass(frozen=True)
class Fixtures:
    """Everything that sits inside the case besides the switches and the XIAO, placed for the left half."""

    bumpers: Part
    power_switch: Part
    battery: Part
    inserts: Part
    screws: Part
    magnets: Part | None
    spacers: Part | None

    def mirrored(self, about: Plane) -> "Fixtures":
        return replace(self, **{
            f.name: None if getattr(self, f.name) is None else mirror(getattr(self, f.name), about=about)
            for f in fields(self)
        })


@dataclass(frozen=True)
class Accessories:
    """The fixtures plus the switches, the keycaps and the XIAO of one half."""

    switches: Part
    keycaps: Part
    xiao: Part
    fixtures: Fixtures

    def as_dict(self, suffix: str = "") -> dict:
        """The parts by name for the viewer. Parts that do not exist are left out."""
        named = {
            "switches": self.switches,
            "keycaps": self.keycaps,
            "xiao": self.xiao,
            "bumpers": self.fixtures.bumpers,
            "power_switch": self.fixtures.power_switch,
            "battery": self.fixtures.battery,
            "magnets": self.fixtures.magnets,
            "magnet_spacers": self.fixtures.spacers,
            "inserts": self.fixtures.inserts,
            "screws": self.fixtures.screws,
        }
        return {name + suffix: part for name, part in named.items() if part is not None}


def build_fixtures(ctx: CaseContext) -> Fixtures:
    dims = ctx.dims

    # build the model upside down on a copy, the shared bumper model stays untouched
    bumper_model = ctx.bumper.model.rotate(Axis.X, 180).translate((0, 0, -dims.below_z + ctx.bumper.dims.base_z))
    with BuildPart() as bumpers:
        with Locations(dims.bumper_locations):
            insert(bumper_model)

    power_switch = PowerSwitch().model\
        .rotate(Axis.Y, dims.powerswitch_rotation.Y)\
        .rotate(Axis.Z, dims.powerswitch_rotation.Z)\
        .translate(dims.powerswitch_position)

    with BuildPart() as inserts:
        with Locations([
            Vector(position.X, position.Y, ctx.insert.dims.d.Z / 2)  # pressed in flush with the face at z=0
            for position in dims.fastener_positions
        ]):
            insert(ctx.insert.model)

    with BuildPart() as screws:
        with Locations([
            Vector(position.X, position.Y, -dims.below_z + ctx.screw.dims.shaft.Z / 2 + ctx.screw.dims.head.Z)
            for position in dims.fastener_positions
        ]):
            insert(ctx.screw.model.rotate(Axis.X, 180))

    battery = Box(dims.battery_pd.d.X, dims.battery_pd.d.Y, dims.battery_pd.d.Z).translate(dims.battery_pd.p)

    magnets = spacers = None
    if dims.magnet_positions:
        # two stacked magnets, pushed against the skin
        with BuildPart() as magnet_part:
            with BuildSketch(Plane.XY.offset(dims.magnet_positions[0].Z)):
                with Locations(dims.magnet_positions):
                    Circle(dims.magnet_d.radius)
            extrude(amount=-2 * dims.magnet_d.Z)
        magnets = magnet_part.part

        spacer = magnet_spacer(dims.magnet_spacer)
        spacers = Part() + [Pos(position.X, position.Y, 0) * spacer for position in dims.magnet_positions]

    return Fixtures(
        bumpers=bumpers.part,
        power_switch=power_switch,
        battery=battery,
        inserts=inserts.part,
        screws=screws.part,
        magnets=magnets,
        spacers=spacers,
    )


def build_switches(ctx: CaseContext, placements: list[Location]) -> tuple[Part, Part]:
    """The switch bodies and the keycaps of one half, as two parts."""
    placed = []
    for part in (ctx.switch.model.part, ctx.switch.cap_model):
        with BuildPart() as all_of_them:
            with Locations(placements):
                insert(part)
        placed.append(all_of_them.part)
    return placed[0], placed[1]
