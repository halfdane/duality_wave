from dataclasses import dataclass, replace
from build123d import *
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
    
    a1: PosAndDims = PosAndDims(p=Vector(5.5,0), d=RoundDimensions(0.9, 2.65))
    a2: PosAndDims = PosAndDims(p=Vector(-5.5,0), d=RoundDimensions(0.9, 2.65))

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
    d: RectDimensions = RectDimensions(0.35, 3.154, 0.9)
    offset_between: float = 3.5

@dataclass
class UpperHousingDimensions:
    d: RectDimensions = RectDimensions(13.6, 13.8, 2.5)

@dataclass
class StemDimensions:
    d: RectDimensions = RectDimensions(10, 4.5, 2.5)    
    ext_d: RectDimensions = RectDimensions(3, 1.2, 0)

@dataclass
class CapDimensions:
    d: RectDimensions = RectDimensions(17.45, 16.45, 4.5)
    # how far the cap reaches down over the stem
    overlap: float = 2.28

@dataclass
class AboveDimensions:
    d: RectDimensions = RectDimensions(
        BaseDimensions.d.X,
        BaseDimensions.d.Y,
        BaseDimensions.d.Z + UpperHousingDimensions.d.Z + StemDimensions.d.Z + CapDimensions.d.Z - CapDimensions.overlap
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
    cap = CapDimensions()

    above = AboveDimensions()
    below = BelowDimensions()

    clamp_clearance_z: float = BottomHousingDimensions.d.Z - ClampDimensions.d.Z

    def __init__(self, show_model=False, pin_len: float = 2.0, side_post_len: float = 0.0):
        """pin_len: length of the two contacts under the housing. side_post_len: length of the two small side posts."""
        self.posts = PostDimensions().with_lengths(pin_len, side_post_len)
        self.below = BelowDimensions(RectDimensions(
            self.bottom_housing.d.X, self.bottom_housing.d.Y, self.bottom_housing.d.Z + self.posts.below_length))
        with BuildPart() as self.model:
            with BuildPart() as main_housing_base:
                with Locations((0, 0, +self.base.d.Z / 2)):
                    Box(self.base.d.X, self.base.d.Y, self.base.d.Z)

            with BuildPart(main_housing_base.faces().sort_by(Axis.Z)[0]) as bottom_housing:
                with Locations((0, 0, self.bottom_housing.d.Z / 2)):
                    Box(self.bottom_housing.d.X, self.bottom_housing.d.Y, self.bottom_housing.d.Z)

            # world coordinates: the underside is seen mirrored, so Y flips (like the post cutouts in the bottom plate)
            with BuildPart() as posts:
                for post in self.posts.posts:
                    with Locations((post.p.X, -post.p.Y, -self.bottom_housing.d.Z - post.d.Z / 2)):
                        Cylinder(post.d.radius, post.d.Z)

            with BuildPart(bottom_housing.faces().filter_by(Axis.X)) as snap_in_clamps:
                with Locations(((self.bottom_housing.d.Z-self.clamps.d.Z)/2, self.clamps.offset_between, self.clamps.d.X/2), 
                            ((self.bottom_housing.d.Z-self.clamps.d.Z)/2, -self.clamps.offset_between, self.clamps.d.X/2)):
                    Box(self.clamps.d.Z, self.clamps.d.Y, self.clamps.d.X)

            with BuildPart(main_housing_base.faces().sort_by(Axis.Z)[-1]) as upper_housing:
                with Locations((0, 0, self.upper_housing.d.Z / 2)):
                    Box(self.upper_housing.d.X, self.upper_housing.d.Y, self.upper_housing.d.Z)

            with BuildPart(upper_housing.faces().sort_by(Axis.Z)[-1]) as stem:
                with Locations((0, 0, self.stem.d.Z / 2)):
                    Box(self.stem.d.X, self.stem.d.Y, self.stem.d.Z)
                with Locations((0, -(self.stem.d.Y+self.stem.ext_d.Y)/2, self.stem.d.Z / 2)):
                    Box(self.stem.ext_d.X, self.stem.ext_d.Y, self.stem.d.Z)

            # simple stand-in for a keycap, same footprint and height as a Hattara cap
            with BuildPart() as cap_part:
                with Locations((0, 0, self.base.d.Z + self.upper_housing.d.Z + self.stem.d.Z - self.cap.overlap)):
                    Box(self.cap.d.X, self.cap.d.Y, self.cap.d.Z, align=(Align.CENTER, Align.CENTER, Align.MIN))
                fillet(cap_part.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[-1], radius=1.0)

        if show_model:
            from ocp_vscode import show_all
            show_all()

    @property
    def cap_start_z(self) -> float:
        """The keycap stand-in starts where the stem ends. Everything above this level is cap."""
        return self.base.d.Z + self.upper_housing.d.Z + self.stem.d.Z - self.cap.overlap

    def split_cap(self) -> tuple[Part, Part]:
        """The switch without its keycap, and the keycap alone. Both keep the position of the whole switch."""
        part = self.model.part
        above = Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)).translate((0, 0, self.cap_start_z))
        return part - above, part & above


# main method
if __name__ == "__main__":
    from ocp_vscode import set_defaults, Camera
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    switch = Choc(show_model=True)
    # show_object(switch.model, name="Kailh Choc Switch")
