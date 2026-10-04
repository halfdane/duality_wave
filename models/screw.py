if __name__ == "__main__":
    import sys, os
    # add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from dataclasses import dataclass

from build123d import *

from models.model_types import RoundDimensions


@dataclass
class ScrewDimensions:
    shaft: RoundDimensions = RoundDimensions(1.0, 8.0)
    head: RoundDimensions = RoundDimensions(2.25, 1)


@dataclass
class ScrewMountDimensions:
    clearance: RoundDimensions = RoundDimensions(ScrewDimensions().shaft.radius+0.2, 0)
    head_recess: RoundDimensions = RoundDimensions(radius=ScrewDimensions().head.radius+0.1, 
                                                   z=ScrewDimensions().head.Z)


class LowProfileScrew:
    dims = ScrewDimensions()
    mount = ScrewMountDimensions()

    def __init__(self):
        with BuildPart() as model:
            Cylinder(self.dims.shaft.radius, self.dims.shaft.Z)
            with BuildPart(Plane.XY.offset(self.dims.shaft.Z/2 + self.dims.head.Z/2)):
                Cylinder(self.dims.head.radius, self.dims.head.Z)
        self.model = model.part

if __name__ == "__main__":
    from ocp_vscode import *

    set_port(3939)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.seeded(colormap="rgb", alpha=1, seed_value="wave"))

    screw = LowProfileScrew()
    show_object(screw.model, name="screw")
