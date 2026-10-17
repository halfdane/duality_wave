from pathlib import Path

from build123d import *

from models.choc import Choc
from models.heat_set_insert import HeatSetInsert
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from models.power_switch import PowerSwitch
from models.rubber_bumper import BumperDimensions
from models.screw import LowProfileScrew
from models.xiao import Xiao


class Layout:
    def __init__(self, switch: Choc, keys: ErgoKeys, dimensions, outline: Outline):
        self.outline = outline
        self.dimensions = dimensions

        self.outline_sketch = outline.sketch
        self.keywell_sketch = outline.keywell_sketch

        with BuildSketch() as choc_key_holes:
            for key in keys.keys:
                with Locations(key.p):
                    Rectangle(switch.below.d.X, switch.below.d.Y, rotation=key.r)
        self.choc_key_holes = choc_key_holes.sketch

        screw = LowProfileScrew()
        insert = HeatSetInsert(dimensions.insert_profile)
        with BuildSketch() as screw_holes:
            with Locations(dimensions.fastener_positions):
                Circle(screw.mount.clearance.radius)
        self.screw_holes = screw_holes.sketch

        with BuildSketch() as heat_set:
            with Locations(dimensions.fastener_positions):
                Circle(insert.mount.pilot.radius)
        self.heat_set = heat_set.sketch

        with BuildSketch() as batteries:
            with Locations((dimensions.battery_pd.p.X, dimensions.battery_pd.p.Y)):
                Rectangle(dimensions.battery_pd.d.X, dimensions.battery_pd.d.Y)
        self.batteries = batteries.sketch

        with BuildSketch() as bumpers:
            with Locations(dimensions.bumper_locations):
                Circle(BumperDimensions.radius)
        self.bumpers = bumpers.sketch

        with BuildSketch() as xiao:
            with Locations((dimensions.xiao_position.X, dimensions.xiao_position.Y)):
                RectangleRounded(Xiao.dims.d.X, Xiao.dims.d.Y, 2)
        self.xiao = xiao.sketch

        with BuildSketch() as power_switch:
            with Locations((dimensions.powerswitch_position.X, dimensions.powerswitch_position.Y)):
                Rectangle(
                    PowerSwitch.dims.d.X,
                    PowerSwitch.dims.d.Y,
                    rotation=dimensions.powerswitch_rotation.Z,
                )
        self.power_switch = power_switch.sketch


if __name__ == "__main__":
    from ocp_vscode import set_defaults, set_port, show_clear, show_object, Camera
    from duality_wave import CaseDimensions

    switch = Choc()
    points = get_points(file_path=Path(__file__).parent / "ergogen" / "wave.yml")
    keys = ErgoKeys(points=points)
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dimensions = CaseDimensions(switch=switch, outline=outline, keys=keys)
    layout = Layout(switch=switch, keys=keys, dimensions=dimensions, outline=outline)

    bottom = outline.create_inner_outline(offset_by=-dimensions.wall_thickness - dimensions.clearance)


    set_port(3939)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    show_object({
        "outline": layout.outline_sketch,
        "keywell": layout.keywell_sketch,
        "bottom": bottom,
        "choc_key_holes": layout.choc_key_holes,
        "screw_holes": layout.screw_holes,
        "heat_set": layout.heat_set,
        "batteries": layout.batteries,
        "bumpers": layout.bumpers,
        "xiao": layout.xiao,
        "power_switch": layout.power_switch,
    }, name="layout")