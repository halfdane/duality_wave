from build123d import *

from models.heat_set_insert import HeatSetInsert


def create_insert_coupon(
    pilot_diameters: tuple[float, ...] = (2.9, 3.0, 3.1, 3.2, 3.3),
) -> Part:
    insert = HeatSetInsert()
    spacing = 9
    margin = 5
    length = 2 * margin + spacing * (len(pilot_diameters) - 1)

    with BuildPart() as coupon:
        Box(length, 10, 4)
        with BuildSketch(coupon.faces().sort_by(Axis.Z)[-1]):
            for index, pilot_diameter in enumerate(pilot_diameters):
                x = (index - (len(pilot_diameters) - 1) / 2) * spacing
                with Locations((x, 0)):
                    Circle(pilot_diameter / 2)
        extrude(amount=-insert.mount.pilot.Z, mode=Mode.SUBTRACT)

    return coupon.part


if __name__ == "__main__":
    export_stl(create_insert_coupon(), "m2_insert_coupon.stl")
