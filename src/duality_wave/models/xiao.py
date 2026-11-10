from dataclasses import dataclass
from build123d import *
from duality_wave.models.model_types import RectDimensions, PosAndDims

@dataclass
class BoardDimensions:
    d: RectDimensions = RectDimensions(17.8, 21.0, 1.250)

@dataclass
class ProcessorDimensions:
    d: RectDimensions = RectDimensions(12.5, 10.6, 2.0)
    forward_y: float = 1.8

@dataclass
class UsbDimensions:
    d: RectDimensions = RectDimensions(8.940, 7.0, 3.21)
    radius: float = 1.25
    forward_y: float = 1

@dataclass
class SolderHoleDimensions:
    radius: float = 0.375
    spacing: float = 2.54
    holes_per_side: int = 7

@dataclass
class ComponentDimensions:
    reset_button_d: PosAndDims = PosAndDims(p=Vector(5.749, -8.6, 0.73/2), d=RectDimensions(1.6, 2.6, 0.73))
    led_d: PosAndDims = PosAndDims(p=Vector(-5.7, -7.7, 0.3/2), d=RectDimensions(1.0, 1.0, 0.3))
    loading_light_d: PosAndDims = PosAndDims(p=Vector(-5.65, -9.7, 0.1/2), d=RectDimensions(1.1, 0.5, 0.1))

@dataclass
class ResetButtonLeverDimensions:
    p: Vector = ComponentDimensions.reset_button_d.p
    d: RectDimensions = RectDimensions(2.4, 6)
    gap: float = 0.5
    # how far the slot reaches from the centre of the button towards the outer wall
    head_length: float = 1.8
    # the bump stays this far inside the head of the arm. A bump edge that runs along the edge of the head leaves a sliver that cannot be meshed
    bump_margin: float = 0.1

class Xiao:
    dims = BoardDimensions()
    processor = ProcessorDimensions()
    usb = UsbDimensions()
    solder_holes = SolderHoleDimensions()
    components = ComponentDimensions()
    reset_lever_dims = ResetButtonLeverDimensions()

    plane: Plane

    def __init__(self, plane=Plane.XY):
        self.plane = plane

        self.model = self._create_model()
        self.reset_button_bump = self._create_reset_button_bump()
        self.usb_cut_sketch_plane = self._create_usb_cut_sketch_plane(self.model)


    def _create_model(self):
        with BuildPart() as model:
            with BuildPart() as board:
                with BuildSketch():
                    RectangleRounded(self.dims.d.X, self.dims.d.Y, 2)
                    solder_hole_offset_y = -self.dims.d.Y / 2 + self.solder_holes.radius + self.solder_holes.spacing
                    for i in range(self.solder_holes.holes_per_side):
                        y = i * self.solder_holes.spacing + solder_hole_offset_y
                        with Locations((-self.dims.d.X / 2 + 2*self.solder_holes.radius - 0.7, y), 
                                       (-self.dims.d.X / 2 + 2*self.solder_holes.radius + 0.5, y), 
                                       (self.dims.d.X / 2 - 2*self.solder_holes.radius - 0.5, y), 
                                       (self.dims.d.X / 2 - 2*self.solder_holes.radius + 0.7, y)):
                            Circle(self.solder_holes.radius, mode=Mode.SUBTRACT)
                extrude(amount=self.dims.d.Z)
            
            with BuildPart(Plane.XY.offset(self.dims.d.Z)) as usb:
                with Locations((0, self.usb.d.Y/2-self.dims.d.Y/2-self.usb.forward_y, self.usb.d.Z/2)):
                    Box(self.usb.d.X, self.usb.d.Y, self.usb.d.Z)
                fillet(edges().filter_by(Axis.Y), self.usb.radius)


            with BuildPart(Plane.XY.offset(self.dims.d.Z)) as parts:

                with Locations((0, self.processor.forward_y, self.processor.d.Z/2)) as processor:
                    Box(self.processor.d.X, self.processor.d.Y, self.processor.d.Z)

                with Locations(self.components.reset_button_d.p):
                    self.reset_button = Box(self.components.reset_button_d.d.X, self.components.reset_button_d.d.Y, self.components.reset_button_d.d.Z)

                with Locations(self.components.led_d.p) as led:
                    Box(self.components.led_d.d.X, self.components.led_d.d.Y, self.components.led_d.d.Z)

                with Locations(self.components.loading_light_d.p) as loading_light:
                    Box(self.components.loading_light_d.d.X, self.components.loading_light_d.d.Y, self.components.loading_light_d.d.Z)
        self.usb_connector = self.plane * usb.part
        return self.plane * model.part

    def _create_reset_button_lever_sketch(self):
        length = self.reset_lever_dims.d.Y
        lever_width = self.reset_lever_dims.d.X
        lever_gap = self.reset_lever_dims.gap
        p = self.reset_lever_dims.p        
        with BuildSketch() as reset_sketch:
            with BuildLine() as line2:
                f3 = Line(p+(-lever_width/2 -lever_gap, 0),
                          p+(-lever_width/2 -lever_gap, length))
                g3 = Line(p+(lever_width/2 +lever_gap, 0),
                          p+(lever_width/2 +lever_gap, length))
                h2 = EllipticalCenterArc((f3@0 + g3@0)/2, lever_width/2 + lever_gap, self.reset_lever_dims.head_length, start_angle=180, arc_size=180)
                i = Line(f3@1+(lever_gap/2, lever_gap/2), g3@1+(-lever_gap/2, lever_gap/2))
                j = Line(f3@1, g3@1)
            make_face()

        return reset_sketch.sketch

    def _create_reset_button_arm_sketch(self):
        """The arm in the slot of the lever. It is as wide as the lever without the gap and ends in the wall of the plate.

        The head is an ellipse and no offset of the slot, because STEP files lose the faces that have an offset curve as edge.
        """
        width = self.reset_lever_dims.d.X
        length = self.reset_lever_dims.d.Y
        p = self.reset_lever_dims.p
        with BuildSketch() as arm:
            with BuildLine():
                left = Line(p + (-width/2, 0), p + (-width/2, length))
                right = Line(p + (width/2, 0), p + (width/2, length))
                EllipticalCenterArc(p, width/2, self.reset_lever_dims.head_length - self.reset_lever_dims.gap, start_angle=180, arc_size=180)
                Line(left@1, right@1)
            make_face()
        return arm.sketch

    def _create_reset_button_bump(self):
        lever = self.reset_lever_dims
        with BuildSketch() as reset_bump:
            with Locations(lever.p):
                Ellipse(lever.d.X/2 - lever.bump_margin, 
                        lever.head_length - lever.gap - lever.bump_margin)

        return reset_bump.sketch

    def _create_usb_cut_sketch(self, clearance: float):
        with BuildSketch() as usb_sketch:
            with Locations((0, Xiao.dims.d.Z/2)):
                with Locations((0, Xiao.usb.d.Z/2)):
                    RectangleRounded(Xiao.usb.d.X + 2*clearance, Xiao.usb.d.Z+2*clearance, radius=Xiao.usb.radius+clearance)
        return usb_sketch.sketch

    def _create_free_usb_space_sketch(self, clearance: float):
        with BuildSketch() as usb_sketch:
            with Locations((0, Xiao.dims.d.Z/2)):
                with Locations((0, Xiao.usb.d.Z/2)):
                    RectangleRounded(Xiao.usb.d.X + 2*clearance, Xiao.usb.d.Z+2*clearance, radius=Xiao.usb.radius+clearance)
                with Locations((0, 0.25*Xiao.usb.d.Z)):
                    Rectangle(Xiao.usb.d.X + 2*clearance, Xiao.usb.d.Z/2+2*clearance)
        return usb_sketch.sketch
    
    def _create_usb_cut_sketch_plane(self, model):
        front_dir_axis = Axis(origin=self.plane.origin, direction=self.plane.y_dir)
        boardfront:Face = model.faces().sort_by(front_dir_axis).filter_by(Axis.Y)[1]
        return boardfront
    
    def _usb_cutter(self, sketch: Sketch, clearance: float) -> Part:
        """The tunnel for the USB plug. It runs from the board front into the case and out to the wall."""
        with BuildPart() as cutter:
            with BuildSketch(self.usb_cut_sketch_plane) as cut_sketch:
                insert(sketch)
            extrude(to_extrude=cut_sketch.sketch, amount=7)
            extrude(to_extrude=cut_sketch.sketch, amount=-(self.usb.d.Y - self.usb.forward_y + clearance))
        return cutter.part

    def add_usb_cutouts(self, part: Part, clearance: float):
        """Cut the USB tunnel. The clearance is per side: it widens the plug outline on every side."""
        return part.cut(self._usb_cutter(self._create_usb_cut_sketch(clearance), clearance))

    def add_large_usb_cutouts(self, part: Part, clearance: float):
        return part.cut(self._usb_cutter(self._create_free_usb_space_sketch(clearance), clearance))

    def add_reset_lever(self, part: Part, plane: Plane):
        # from the current z, down to the bottom of the board
        # plus the height of the board and the reset button
        dist = plane.origin.Z - self.plane.origin.Z + self.dims.d.Z + self.components.reset_button_d.d.Z
        # make bump a bit higher, so the lever is preloaded
        dist += 0.1 
        lever = self._create_reset_button_lever_sketch()
        with BuildPart() as removal:
            with BuildSketch(plane):
                insert(lever)
            extrude(dir=-plane.z_dir, amount=10)

        with BuildPart() as addition:
            with BuildSketch(plane):
                insert(self._create_reset_button_arm_sketch())
            extrude(dir=-plane.z_dir, amount=1.18)

            with BuildSketch(plane):
                insert(self.reset_button_bump)
            extrude(amount=dist)

        return part.cut(removal.part).fuse(addition.part)


# main method
if __name__ == "__main__":
    from ocp_viewer import *

    xiao_plane = Plane.XY
    xiao_plane = xiao_plane.rotated((180,0,0)).move(Location((18.9, 71.7, -0.74)))
    xiao = Xiao(xiao_plane)

    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.accent())

    model = xiao.model
    reset_button_lever_sketch = xiao._create_reset_button_lever_sketch()
    reset_button_bump = xiao.reset_button_bump
    free_usb_space_sketch = xiao._create_free_usb_space_sketch(clearance=0.02)

    with BuildPart(xiao_plane) as usb_cut_3d:
        with BuildSketch(xiao.usb_cut_sketch_plane) as cut_sketch:
            cut = xiao._create_usb_cut_sketch(clearance=0.02)
            insert(cut)
        extrude(amount=7, mode=Mode.ADD)
    # usb_cut.part = xiao.plane * usb_cut.part

    bumper_plane = xiao_plane.offset(Xiao.dims.d.Z + Xiao.usb.d.Z)
    # reset_lever = xiao.add_reset_lever(model, bumper_plane)

    with BuildSketch(xiao_plane, bumper_plane) as plane_sketch:
        Circle(10)

    show_all()
