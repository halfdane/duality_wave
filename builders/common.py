from dataclasses import dataclass

from build123d import *

from models.heat_set_insert import HeatSetInsert
from models.keys import ErgoKeys
from models.model_types import WaveDimensions
from models.outline import Outline
from models.rubber_bumper import RubberBumper
from models.screw import LowProfileScrew
from models.switch import Switch


@dataclass(frozen=True)
class CaseContext:
    """Everything the part builders read. Builders never modify it."""

    switch: Switch
    keys: ErgoKeys
    dims: WaveDimensions
    outline: Outline
    bumper: RubberBumper
    insert: HeatSetInsert
    screw: LowProfileScrew


def powerswitch_plane(dims: WaveDimensions) -> Plane:
    return Plane(dims.powerswitch_position).rotated(dims.powerswitch_rotation)


def circle_sketch(positions: list[Vector], radius: float, plane: Plane = Plane.XY) -> BuildSketch:
    """Circles at positions on plane.

    build123d only hands a sketch to the enclosing BuildPart when both live in the same function,
    so extrude the result with to_extrude=sketch.sketch.
    """
    with BuildSketch(plane) as sketch:
        with Locations(positions):
            Circle(radius)
    return sketch
