from dataclasses import dataclass
from functools import cached_property

from build123d import *

from duality_wave.models.model_types import RectDimensions


@dataclass
class Keycap:
    """A low profile keycap for the Choc v1 stem (measured on the Hattara cap).

    The model stands on z = 0 and is centred on x and y. d is the footprint at the bottom and the height of the highest
    point. The dished top is lowest in the centre and highest at the corners.
    """

    d: RectDimensions = RectDimensions(17.45, 16.45, 4.5)
    # how far the cap reaches down over the stem. This is the depth of the cavity.
    overlap: float = 2.3
    corner_radius: float = 1.5
    # the walls lean inwards by this angle
    taper: float = 4.0
    # the top is a sphere dish. Its lowest point is in the centre, this far over the bottom.
    dish_radius: float = 40.0
    dish_low: float = 3.5
    edge_radius: float = 1.2
    cavity: RectDimensions = RectDimensions(15.11, 14.24, 0)
    # the two legs go into the stem
    leg: RectDimensions = RectDimensions(1.2, 3.0, 0)
    leg_pitch: float = 5.7

    @cached_property
    def model(self) -> Part:
        with BuildPart() as cap:
            with BuildSketch():
                Rectangle(self.d.X, self.d.Y)
                fillet(vertices(), radius=self.corner_radius)
            extrude(amount=self.d.Z, taper=self.taper)
            with Locations((0, 0, self.dish_low + self.dish_radius)):
                Sphere(self.dish_radius, mode=Mode.SUBTRACT)
            fillet(cap.edges().filter_by(lambda edge: edge.center().Z > self.dish_low), radius=self.edge_radius)
            with BuildSketch():
                Rectangle(self.cavity.X, self.cavity.Y)
            extrude(amount=self.overlap, mode=Mode.SUBTRACT)
            with BuildSketch():
                with Locations((self.leg_pitch / 2, 0), (-self.leg_pitch / 2, 0)):
                    Rectangle(self.leg.X, self.leg.Y)
            extrude(amount=self.overlap)
        return cap.part
