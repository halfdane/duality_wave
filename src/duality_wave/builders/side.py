from dataclasses import dataclass

from build123d import *

from duality_wave.builders.accessories import Accessories, Fixtures, build_switches
from duality_wave.builders.bottom import add_switch_post_cutouts
from duality_wave.builders.common import CaseContext
from duality_wave.models.xiao import Xiao


@dataclass(frozen=True)
class Blanks:
    """The parts as built once for the left half, before anything specific to a side is cut."""

    keywell: Part
    keyplate: Part
    bottom: Part


@dataclass(frozen=True)
class Side:
    """What differs between the two halves: where the keys and the XIAO sit, and the mirror that maps the left half onto it."""

    name: str
    mirror_plane: Plane | None
    switch_locations: list[Location]
    xiao_plane: Plane

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
        )


@dataclass(frozen=True)
class BuiltSide:
    side: Side
    xiao: Xiao
    keywell: Part
    keyplate: Part
    bottom: Part
    accessories: Accessories | None


def finish_side(ctx: CaseContext, side: Side, blanks: Blanks, fixtures: Fixtures | None, viewer) -> BuiltSide:
    """Place the blanks on the side and cut everything that depends on where the keys and the XIAO are.

    fixtures are the accessories of the left half, or None when nobody wants to see them.
    """
    dims = ctx.dims
    xiao = Xiao(side.xiao_plane, clearance=dims.clearance)

    accessories = None
    if fixtures is not None:
        side_fixtures = fixtures if side.mirror_plane is None else fixtures.mirrored(side.mirror_plane)
        accessories = Accessories(build_switches(ctx, side.switch_locations), xiao.model, side_fixtures)
        viewer.push(accessories.as_dict(side.suffix), name=f"accessories_{side.name}")

    keywell = xiao.add_usb_cutouts(side.mirrored(blanks.keywell))
    viewer.push(keywell, name=f"keywell_{side.name}")

    keyplate = xiao.add_large_usb_cutouts(side.mirrored(blanks.keyplate))
    viewer.push(keyplate, name=f"keyplate_{side.name}")

    bottom = add_switch_post_cutouts(side.mirrored(blanks.bottom), ctx.switch, dims.bottom_plate_z, side.switch_locations)
    bottom = xiao.add_large_usb_cutouts(bottom)
    bottom = xiao.add_reset_lever(
        bottom, side.xiao_plane.offset(dims.keyplate_z + dims.bottom_plate_z + dims.xiao_position.Z))
    viewer.push(bottom, name=f"bottom_{side.name}")

    return BuiltSide(side, xiao, keywell, keyplate, bottom, accessories)
