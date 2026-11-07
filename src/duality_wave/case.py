from duality_wave.builders.accessories import build_fixtures
from duality_wave.builders.bottom import build_bottom
from duality_wave.builders.common import CaseContext
from duality_wave.builders.keyplate import build_keyplate
from duality_wave.builders.keywell import build_keywell
from duality_wave.builders.side import Blanks, BuiltSide, Side, finish_side
from duality_wave.builders.viewer import NullViewer, OcpViewer
from duality_wave.models.features import magnet_spacer
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.model_types import WaveDimensions
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from duality_wave.models.switch import Switch
from duality_wave.timing import StageTimings


class WaveCase:
    """Builds the keywell, keyplate and bottom for one or both halves of the keyboard.

    The parts are available as case.left and case.right (BuiltSide). case.right is None unless both_sides is set.
    With debug the accessories are built as well and everything is pushed to the viewer, the intermediate
    shapes last in a group that starts hidden. Pass a viewer to show the parts somewhere else.
    case.magnet_spacer is the one disc to print for every magnet pocket, or None without magnets.
    case.timings holds the seconds spent in each build stage.
    """

    def __init__(self, switch: Switch, keys: ErgoKeys, caseDimensions: WaveDimensions, outline, debug=False, both_sides=False, viewer=None):
        self.viewer = viewer if viewer is not None else (OcpViewer() if debug else NullViewer())
        self.ctx = ctx = CaseContext(
            switch, keys, caseDimensions, outline,
            RubberBumper(), HeatSetInsert(caseDimensions.print_profile.insert_pilot_radius), LowProfileScrew())

        self.magnet_spacer = magnet_spacer(caseDimensions.magnet_spacer) if caseDimensions.magnet_positions else None

        print("Creating case...")
        self.timings = StageTimings()
        with self.timings.stage("keywell"):
            keywell = build_keywell(ctx, self.viewer.debug.scope("keywell"))
        with self.timings.stage("keyplate"):
            keyplate = build_keyplate(ctx, self.viewer.debug.scope("keyplate"))
        with self.timings.stage("bottom"):
            bottom = build_bottom(ctx, self.viewer.debug.scope("bottom"))
        blanks = Blanks(keywell=keywell, keyplate=keyplate, bottom=bottom)
        with self.timings.stage("fixtures"):
            fixtures = build_fixtures(ctx) if self.viewer.enabled else None

        left = Side.left(ctx)
        with self.timings.stage("finish_left"):
            self.left: BuiltSide = finish_side(ctx, left, blanks, fixtures, self.viewer)
        self.right: BuiltSide | None = None
        if both_sides:
            with self.timings.stage("finish_right"):
                self.right = finish_side(ctx, Side.right(ctx, left), blanks, fixtures, self.viewer)

        self.viewer.push_debug()
        print("Done creating case.")
