from dataclasses import dataclass, replace
from build123d import *
from duality_wave.models.keycap import Keycap
from duality_wave.models.model_types import RectDimensions, RoundDimensions, PosAndDims
from duality_wave.models.switch import Switch

@dataclass
class BaseDimensions:
    d : RectDimensions = RectDimensions(15, 15, 0.8)

@dataclass
class BottomHousingDimensions:
    d : RectDimensions = RectDimensions(13.8, 13.8, 2.2)

@dataclass
class PostDimensions:
    center : PosAndDims = PosAndDims(p=Vector(0,0), d=RoundDimensions(1.6, 2.65))
    
    a1: PosAndDims = PosAndDims(p=Vector(5.5,0), d=RoundDimensions(0.825, 2.65))
    a2: PosAndDims = PosAndDims(p=Vector(-5.5,0), d=RoundDimensions(0.825, 2.65))

    p1: PosAndDims = PosAndDims(p=Vector(0,5.9), d=RoundDimensions(0.2, 3))
    p2: PosAndDims = PosAndDims(p=Vector(-5,3.8), d=RoundDimensions(0.2, 3))

    @property
    def posts(self) -> tuple[PosAndDims, ...]:
        """The posts that exist. A post of length 0 is left out."""
        return tuple(post for post in (self.center, self.a1, self.a2, self.p1, self.p2) if post.d.Z > 0)

    def with_lengths(self, pin_len: float, side_post_len: float) -> "PostDimensions":
        """Trim the contacts and the side posts. The centre post keeps its length. A post is never longer than its datasheet value."""

        def trimmed(post: PosAndDims, length: float) -> PosAndDims:
            return replace(post, d=RoundDimensions(post.d.radius, max(0.0, min(length, post.d.Z))))

        return replace(
            self,
            a1=trimmed(self.a1, side_post_len),
            a2=trimmed(self.a2, side_post_len),
            p1=trimmed(self.p1, pin_len),
            p2=trimmed(self.p2, pin_len),
        )

    @property
    def below_length(self) -> float:
        """How far the posts reach under the housing. The centre post is not counted: it passes through the bottom plate."""
        return max([post.d.Z for post in self.posts if post is not self.center], default=0.0)


@dataclass
class ClampDimensions:
    d: RectDimensions = RectDimensions(0.35, 3.27, 0.9)
    offset_between: float = 3.5

@dataclass
class UpperHousingDimensions:
    d: RectDimensions = RectDimensions(13.6, 13.62, 2.5)

@dataclass
class StemDimensions:
    d: RectDimensions = RectDimensions(10, 4.5, 2.5)    
    ext_d: RectDimensions = RectDimensions(3, 1.2, 0)

@dataclass
class AboveDimensions:
    d: RectDimensions = RectDimensions(
        BaseDimensions.d.X,
        BaseDimensions.d.Y,
        BaseDimensions.d.Z + UpperHousingDimensions.d.Z + StemDimensions.d.Z + Keycap.d.Z - Keycap.overlap
    )


@dataclass
class BelowDimensions:
    d: RectDimensions = RectDimensions(
        BottomHousingDimensions.d.X,
        BottomHousingDimensions.d.Y,
        BottomHousingDimensions.d.Z + max(post.d.Z for post in PostDimensions().posts)
    )

class Choc(Switch):
    base = BaseDimensions()
    bottom_housing = BottomHousingDimensions()
    posts = PostDimensions()
    clamps = ClampDimensions()
    upper_housing = UpperHousingDimensions()
    stem = StemDimensions()
    cap = Keycap()

    above = AboveDimensions()
    below = BelowDimensions()

    clamp_clearance_z: float = BottomHousingDimensions.d.Z - ClampDimensions.d.Z

    def __init__(self, show_model=False, pin_len: float = 2.0, side_post_len: float = 0.0):
        """pin_len: length of the two contacts under the housing. side_post_len: length of the two small side posts."""
        self.posts = PostDimensions().with_lengths(pin_len, side_post_len)
        self.below = BelowDimensions(RectDimensions(
            self.bottom_housing.d.X, self.bottom_housing.d.Y, self.bottom_housing.d.Z + self.posts.below_length))
        # the switch without its keycap, in world coordinates: the underside of the flange is z = 0
        upper_z = self.base.d.Z
        stem_z = upper_z + self.upper_housing.d.Z
        stem_leg_pitch = self.cap.leg_pitch / 2
        with BuildPart() as self.model:
            with Locations((0, 0, self.base.d.Z / 2)):
                Box(self.base.d.X, self.base.d.Y, self.base.d.Z)

            with Locations((0, 0, -self.bottom_housing.d.Z / 2)):
                Box(self.bottom_housing.d.X, self.bottom_housing.d.Y, self.bottom_housing.d.Z)

            # the underside is seen mirrored, so Y flips (like the post cutouts in the bottom plate)
            for post in self.posts.posts:
                with Locations((post.p.X, -post.p.Y, -self.bottom_housing.d.Z - post.d.Z / 2)):
                    Cylinder(post.d.radius, post.d.Z)

            # the hooks of the snap-in clamps sit on the two sides, and the plate fits between hook and flange
            clamp_x = (self.bottom_housing.d.X + self.clamps.d.X) / 2
            clamp_z = -(self.clamp_clearance_z + self.clamps.d.Z / 2)
            with Locations(*[(side * clamp_x, y, clamp_z) for side in (-1, 1) for y in (-self.clamps.offset_between, self.clamps.offset_between)]):
                Box(self.clamps.d.X, self.clamps.d.Y, self.clamps.d.Z)

            with Locations((0, 0, upper_z + self.upper_housing.d.Z / 2)):
                Box(self.upper_housing.d.X, self.upper_housing.d.Y, self.upper_housing.d.Z)

            with Locations((0, 0, stem_z + self.stem.d.Z / 2)):
                Box(self.stem.d.X, self.stem.d.Y, self.stem.d.Z)
            with Locations((0, -(self.stem.d.Y + self.stem.ext_d.Y) / 2, stem_z + self.stem.d.Z / 2)):
                Box(self.stem.ext_d.X, self.stem.ext_d.Y, self.stem.d.Z)
            # the holes for the legs of the keycap
            with Locations((stem_leg_pitch, 0, stem_z + self.stem.d.Z / 2), (-stem_leg_pitch, 0, stem_z + self.stem.d.Z / 2)):
                Box(self.cap.leg.X, self.cap.leg.Y, self.stem.d.Z, mode=Mode.SUBTRACT)

        if show_model:
            from ocp_vscode import show_all
            show_all()

    @property
    def cap_start_z(self) -> float:
        """The underside of the keycap. The cap reaches down over the stem."""
        return self.base.d.Z + self.upper_housing.d.Z + self.stem.d.Z - self.cap.overlap

    @property
    def cap_model(self) -> Part:
        """The keycap in its place on the switch."""
        return Pos(0, 0, self.cap_start_z) * self.cap.model


# main method
if __name__ == "__main__":
    from ocp_vscode import set_defaults, Camera
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    switch = Choc(show_model=True)
    # show_object(switch.model, name="Kailh Choc Switch")
