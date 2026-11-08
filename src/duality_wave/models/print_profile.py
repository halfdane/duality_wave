import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PrintProfile:
    """Fit constants for one printer/material/slicer combination.

    All clearances are per side, in mm. The defaults reproduce the geometry that was
    validated on a Bambu Lab printer with PLA.
    """
    name: str = "default"

    # height of one printed layer. The levels of the case snap to whole layers, counted from the print bed
    layer_height: float = 0.2

    # everything that is not listed below (xiao pocket, usb, power switch, pin, positions)
    clearance: float = 0.02
    # plate perimeter against the keywell cavity wall
    plate_clearance: float = 0.02
    # switch cutouts in the keyplate
    switch_clearance: float = 0.01
    # XIAO pocket in the keyplate
    xiao_clearance: float = 0.02
    magnet_clearance: float = 0.02
    # material between a magnet and the top face of the keywell: two layers, which the keywell prints on the bed
    magnet_skin: float = 0.4
    # the spacer disc under the magnets is this much shorter than the pocket it fills, so the keyplate always seats
    magnet_spacer_gap: float = 0.2
    battery_clearance: float = 0.02
    bumper_clearance: float = 0.1
    # holes in the bottom plate: around a switch post, around the screw shaft, around the screw head
    post_clearance: float = 0.2
    screw_clearance: float = 0.2
    screw_head_clearance: float = 0.1

    insert_pilot_radius: float = 1.6

    # thinnest wall between two holes or between a hole and an edge: two perimeters of a 0.4 mm nozzle
    min_wall: float = 0.8

    # width of one extruded line
    line_width: float = 0.4
    # depth of the emblems in the outer wall, in lines. A whole number of lines leaves the perimeters unsqueezed
    engraving_lines: int = 1
    # pitch of the pixels of the emblems. It rounds up to a whole number of layers, so the rows end on layer boundaries
    engraving_pitch: float = 1.2
    # roof of every engraved pocket slopes at 45 degrees, so the pocket needs no bridge and no support
    engraving_roof_slope: bool = True

    # radius of the circles that relieve the corners of the switch cutouts (0 = no relief)
    switch_corner_relief: float = 0.3

    # chamfers that counter elephant foot on the side of a part that faces the print bed
    plate_bed_chamfer: float = 0.25
    # chamfer on the plate edges that do not face the print bed
    plate_edge_chamfer: float = 0.1
    # chamfer where a hole opens towards the print bed (switch cutouts) and where the magnets enter their pockets
    mouth_chamfer: float = 0.2

    @property
    def engraving_depth(self) -> float:
        return self.engraving_lines * self.line_width

    @property
    def engraving_gap(self) -> float:
        """The pixels of an emblem are one line apart. A narrower ridge does not print."""
        return self.line_width

    def snap_up(self, height: float) -> float:
        """Round a height up to a whole number of layers."""
        return round(math.ceil(height / self.layer_height - 1e-9) * self.layer_height, 6)

    def snap_down(self, height: float) -> float:
        """Round a height down to a whole number of layers."""
        return round(math.floor(height / self.layer_height + 1e-9) * self.layer_height, 6)
