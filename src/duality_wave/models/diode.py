from dataclasses import dataclass

from duality_wave.print_profile import PrintProfile


@dataclass(frozen=True)
class Diode:
    """A through-hole diode of the DO-35 kind, for the matrix. These are upper limits: a smaller diode fits as well."""

    body_d: float = 2.0
    body_l: float = 4.2
    lead_d: float = 0.5


@dataclass(frozen=True)
class DiodeNotchSpec:
    """The pocket for one diode. The diode lies along the Y axis of its key, the cathode (the band) at the +Y end.

    The pocket is split between the keyplate and the bottom plate. The axis of the diode lies close to the
    interface of the two plates, so each plate holds a part of the body.
    """

    width: float
    # length of the pocket over the body, in total
    length: float
    # the pocket is this much longer at the anode end, so the anode lead can bend towards pin p2 inside the pocket
    lead_room: float
    # the lead leaves the body straight for this long and bends after that
    lead_straight: float
    # depth in the keyplate, measured from the underside, and in the bottom plate, measured from its top face
    keyplate_depth: float
    bottom_depth: float

    @staticmethod
    def of(diode: Diode, profile: PrintProfile, keyplate_z: float, bottom_plate_z: float) -> "DiodeNotchSpec":
        total = diode.body_d + profile.diode_depth_slack
        # the bottom plate takes half of the pocket, but keeps a floor of min_wall
        bottom_depth = min(profile.snap_up(total / 2), profile.snap_down(bottom_plate_z - profile.min_wall))
        bottom_depth = max(bottom_depth, 0.0)
        # the keyplate takes the rest, and keeps a skin of at least one layer
        keyplate_depth = min(profile.snap_up(total - bottom_depth), profile.snap_down(keyplate_z - profile.layer_height))
        return DiodeNotchSpec(
            width=diode.body_d + profile.diode_width_slack,
            length=diode.body_l + profile.diode_length_slack,
            lead_room=profile.diode_lead_room,
            lead_straight=profile.diode_lead_straight,
            keyplate_depth=keyplate_depth,
            bottom_depth=bottom_depth,
        )

    def pocket(self, cutout_half: float, side: int, y: float, overlap: float = 0.0) -> tuple[float, float, float, float]:
        """The pocket as a rectangle in the frame of its key: centre x, centre y, size x, size y.

        side is -1 for the -X side of the key and +1 for the other side, y is the Y of the centre of the diode.
        The pocket starts at the wall of the cutout and reaches `overlap` into it.
        """
        x = side * (cutout_half + self.width / 2 - overlap / 2)
        return x, y - self.lead_room / 2, self.width + overlap, self.total_length

    @property
    def total_length(self) -> float:
        return self.length + self.lead_room

    @property
    def depth(self) -> float:
        return self.keyplate_depth + self.bottom_depth
