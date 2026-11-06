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
    battery_clearance: float = 0.02

    insert_pilot_radius: float = 1.6

    # radius of the circles that relieve the corners of the switch cutouts (0 = no relief)
    switch_corner_relief: float = 0.3

    # chamfers that counter elephant foot on the side of a part that faces the print bed
    plate_bed_chamfer: float = 0.25
    # chamfer on the plate edges that do not face the print bed
    plate_edge_chamfer: float = 0.1
    # chamfer where a hole opens towards the print bed (switch cutouts, magnet recesses)
    mouth_chamfer: float = 0.2

    def snap_up(self, height: float) -> float:
        """Round a height up to a whole number of layers."""
        return round(math.ceil(height / self.layer_height - 1e-9) * self.layer_height, 6)

    def snap_down(self, height: float) -> float:
        """Round a height down to a whole number of layers."""
        return round(math.floor(height / self.layer_height + 1e-9) * self.layer_height, 6)
