from build123d import *

PATTERN = [
    [0,0,1,0,0,0,0,0,1,0,0],
    [0,0,0,1,0,0,0,1,0,0,0],
    [0,0,1,1,1,1,1,1,1,0,0],
    [0,1,1,0,1,1,1,0,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1],
    [1,0,1,1,1,1,1,1,1,0,1],
    [1,0,1,0,0,0,0,0,1,0,1],
    [0,0,0,1,1,0,1,1,0,0,0]
]


class SpaceInvader:
    """The invader as separate square pixels, centered on the origin.

    pitch is the distance between the centers of two pixels. Each pixel is gap smaller than the pitch,
    so neighbours do not touch, not even at a corner.
    """

    rows = len(PATTERN)
    columns = len(PATTERN[0])

    def __init__(self, pitch=1.2, gap=0.4):
        self.pitch = pitch
        half_cols = self.columns / 2 - 0.5
        half_rows = self.rows / 2 - 0.5

        with BuildSketch() as space_invader:
            locs = [((col - half_cols) * pitch, (half_rows - row) * pitch)
                    for row in range(self.rows)
                    for col in range(self.columns)
                    if PATTERN[row][col]]
            with Locations(locs):
                Rectangle(pitch - gap, pitch - gap)

        self.sketch = space_invader.sketch

    @property
    def height(self) -> float:
        return self.rows * self.pitch

# main method
if __name__ == "__main__":
    from ocp_viewer import show_object, set_defaults, Camera
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    space_invader = SpaceInvader()
    show_object(space_invader.sketch, name="Space Invader")
