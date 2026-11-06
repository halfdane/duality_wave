from functools import reduce
from build123d import *
from duality_wave.models.switch import Switch
from duality_wave.layout import Point, get_points
from collections import OrderedDict

class ErgoKeys:
    def __init__(self, points: dict[str, Point]):
        self.points = points
        self.thumb_clusters, self.finger_clusters = self._nest_points(self.points)
        self.clusters = self.finger_clusters + self.thumb_clusters

        self.finger_keys = [k for c in self.finger_clusters for r in c for k in r]
        self.thumb_keys = [k for c in self.thumb_clusters for r in c for k in r]
        self.keys = self.finger_keys + self.thumb_keys

    def _nest_points(self, points: dict[str, Point]) -> tuple[list[list[list[Point]]], list[list[list[Point]]]]:
        def nest():
            return OrderedDict()
            
        def reducer(acc, item):
            key, point = item
            parts = key.split('_')
            cluster = parts[0]
            column = parts[1] if len(parts) > 1 else "0"
            row = parts[2] if len(parts) > 2 else "0"
            if cluster not in acc:
                acc[cluster] = nest()
            if column not in acc[cluster]:
                acc[cluster][column] = nest()
            acc[cluster][column][row] = point
            return acc

        def dict_to_nested_list(nested):
            return [
                [
                    [col[row] for row in col]
                    for col in cluster.values()
                ]
                for cluster in nested.values()
            ]
        
        thumb_points = OrderedDict((k, v) for k, v in points.items() if k.startswith('thumb'))
        finger_points = OrderedDict((k, v) for k, v in points.items() if not k.startswith('thumb'))

        thumb_nested = dict_to_nested_list(reduce(reducer, thumb_points.items(), OrderedDict()))
        finger_nested = dict_to_nested_list(reduce(reducer, finger_points.items(), OrderedDict()))

        return thumb_nested, finger_nested

# main method
if __name__ == "__main__":
    from ocp_vscode import *

    set_port(3939)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.seeded(colormap="rgb", alpha=1, seed_value="wave"))

    from duality_wave.models.choc import Choc
    from duality_wave.paths import LAYOUT_DIR

    config_path = LAYOUT_DIR / 'compact.points.yaml'
    points = get_points(file_path=config_path)

    def create_sizing(switch: Switch):
        keys = ErgoKeys(points=points)
        with BuildSketch() as sizing:
            for key in keys.finger_keys:
                with Locations(key.p) as l:
                    Rectangle(switch.below.d.X, switch.below.d.Y, rotation=key.r)
                    Circle(1, mode=Mode.SUBTRACT)
        return sizing.sketch


    choc_sizing = create_sizing(switch=Choc())


    show_all()
