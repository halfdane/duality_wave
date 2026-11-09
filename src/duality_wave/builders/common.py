from dataclasses import dataclass

from build123d import *

from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.model_types import WaveDimensions
from duality_wave.models.outline import Outline
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from duality_wave.models.switch import Switch


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


def powerswitch_location(dims: WaveDimensions) -> Location:
    """Where the model of the power switch stands in the case: the same turns and the same shift as the fixture."""
    rotation = dims.powerswitch_rotation
    return Pos(dims.powerswitch_position) * Rot(Z=rotation.Z) * Rot(Y=rotation.Y)


def circle_sketch(positions: list[Vector], radius: float, plane: Plane = Plane.XY) -> BuildSketch:
    """Circles at positions on plane.

    build123d only hands a sketch to the enclosing BuildPart when both live in the same function,
    so extrude the result with to_extrude=sketch.sketch.
    """
    with BuildSketch(plane) as sketch:
        with Locations(positions):
            Circle(radius)
    return sketch
