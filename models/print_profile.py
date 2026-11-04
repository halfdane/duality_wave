from dataclasses import dataclass


@dataclass(frozen=True)
class PrintProfile:
    """Fit constants for one printer/material/slicer combination.

    All clearances are per side, in mm. The defaults reproduce the geometry that was
    validated on a Bambu Lab printer with PLA.
    """
    name: str = "default"

    # everything that is not listed below (xiao pocket, usb, power switch, pin, positions)
    clearance: float = 0.02
    # plate perimeter against the keywell cavity wall
    plate_clearance: float = 0.02
    # switch cutouts in the keyplate
    switch_clearance: float = 0.01
    magnet_clearance: float = 0.02
    weight_clearance: float = 0.02
    battery_clearance: float = 0.02

    insert_pilot_radius: float = 1.6
