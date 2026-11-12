from dataclasses import dataclass

from build123d import *
from build123d import Shape

from duality_wave.builders.accessories import Accessories, Fixtures, build_switches
from duality_wave.builders.bottom import add_switch_post_cutouts
from duality_wave.builders.common import CaseContext
from duality_wave.builders.face_emblems import face_emblems
from duality_wave.builders.wall_engraving import WallSpot, engrave_emblem, find_wall_spot
from duality_wave.builders.wiring_cuts import cut_bottom, cut_keyplate
from duality_wave.models.xiao import Xiao
from duality_wave.wiring.plan import WiringPlan


@dataclass(frozen=True)
class Blanks:
    """The parts as built once for the left half, before anything specific to a side is cut."""

    keywell: Part
    keyplate: Part
    bottom: Part


@dataclass(frozen=True)
class Side:
    """What differs between the two halves: where the keys and the XIAO sit, the mirror that maps the left half onto it,
    and the emblem in the front wall."""

    name: str
    mirror_plane: Plane | None
    switch_locations: list[Location]
    xiao_plane: Plane
    emblem: str
    emblem_spot: WallSpot

    @property
    def suffix(self) -> str:
        return "" if self.name == "left" else f"_{self.name}"

    def mirrored(self, shape):
        return shape if self.mirror_plane is None else mirror(shape, about=self.mirror_plane)

    @staticmethod
    def left(ctx: CaseContext) -> "Side":
        # Plane.move() applies the Location in the plane's own (already-rotated) frame, so
        # rotating then moving flips the sign of any axis touched by the rotation. Rotate at
        # the origin first, then rebuild the plane with the absolute target origin instead.
        rotated = Plane.XY.rotated((180, 0, 0))
        return Side(
            name="left",
            mirror_plane=None,
            switch_locations=[Location(key.p, (0, 0, key.r)) for key in ctx.keys.keys],
            xiao_plane=Plane(ctx.dims.xiao_position, x_dir=rotated.x_dir, z_dir=rotated.z_dir),
            emblem="symbol",
            emblem_spot=find_wall_spot(ctx.outline.sketch),
        )

    @staticmethod
    def right(ctx: CaseContext, left: "Side") -> "Side":
        offset = ctx.dims.right_side_offset
        origin = left.xiao_plane.origin
        return Side(
            name="right",
            mirror_plane=Plane((offset / 2, 0, 0), x_dir=Plane.YZ.x_dir, z_dir=Plane.YZ.z_dir),
            switch_locations=[
                Location((offset - key.p.X, key.p.Y, key.p.Z), (0, 0, -key.r))
                for key in ctx.keys.keys
            ],
            xiao_plane=Plane((offset - origin.X, origin.Y, origin.Z), x_dir=left.xiao_plane.x_dir, z_dir=left.xiao_plane.z_dir),
            emblem="invader",
            emblem_spot=left.emblem_spot.mirrored(offset),
        )


@dataclass(frozen=True)
class BuiltSide:
    side: Side
    xiao: Xiao
    keywell: Part
    keyplate: Part
    bottom: Part
    accessories: Accessories | None
    emblems: dict[str, Shape]


def finish_side(ctx: CaseContext, side: Side, blanks: Blanks, fixtures: Fixtures | None, viewer,
                wiring: WiringPlan | None = None) -> BuiltSide:
    """Place the blanks on the side and cut everything that depends on where the keys and the XIAO are.

    fixtures are the accessories of the left half, or None when nobody wants to see them.
    With a wiring plan the diode pockets and the trenches of the side are cut into the blanks first, in the frame of the blank.
    """
    dims = ctx.dims
    xiao = Xiao(side.xiao_plane)

    accessories = None
    if fixtures is not None:
        side_fixtures = fixtures if side.mirror_plane is None else fixtures.mirrored(side.mirror_plane)
        switches, keycaps = build_switches(ctx, side.switch_locations)
        accessories = Accessories(switches, keycaps, xiao.model, side_fixtures)
        viewer.push(accessories.as_dict(side.suffix), name=f"accessories_{side.name}")

    emblems = {name: side.mirrored(emblem) for name, emblem in face_emblems(ctx).items()}

    keywell = engrave_emblem(side.mirrored(blanks.keywell), dims, side.emblem_spot, side.emblem)
    keywell = xiao.add_usb_cutouts(keywell, dims.clearance)
    viewer.push(keywell, name=f"keywell_{side.name}")

    keyplate_blank, bottom_blank = blanks.keyplate, blanks.bottom
    if wiring is not None:
        plan = wiring.side(side.name)

        try:
            keyplate_blank = cut_keyplate(ctx, keyplate_blank, plan, wiring.diode)
        except Exception as e:
            print(f"Error while cutting keyplate or bottom for side {side.name}: {e}")

        try:
            bottom_blank = cut_bottom(ctx, bottom_blank, plan, wiring.diode)
        except Exception as e:
            print(f"Error while cutting keyplate or bottom for side {side.name}: {e}")
    
    keyplate = xiao.add_large_usb_cutouts(side.mirrored(keyplate_blank), dims.clearance)
    viewer.push(keyplate, name=f"keyplate_{side.name}")

    bottom = add_switch_post_cutouts(
        side.mirrored(bottom_blank), ctx.switch, dims.keyplate_z, side.switch_locations, dims.print_profile.post_clearance)
    bottom = xiao.add_large_usb_cutouts(bottom, dims.clearance)
    bottom = xiao.add_reset_lever(
        bottom, side.xiao_plane.offset(dims.keyplate_z + dims.bottom_plate_z + dims.xiao_position.Z))
    viewer.push(bottom, name=f"bottom_{side.name}")

    return BuiltSide(side, xiao, keywell, keyplate, bottom, accessories, emblems)
