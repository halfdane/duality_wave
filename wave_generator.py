from builders.accessories import build_fixtures
from builders.bottom import build_bottom
from builders.common import CaseContext
from builders.keyplate import build_keyplate
from builders.keywell import build_keywell
from builders.side import Blanks, BuiltSide, Side, finish_side
from builders.viewer import NullViewer, OcpViewer
from models.heat_set_insert import HeatSetInsert
from models.keys import ErgoKeys
from models.model_types import WaveDimensions
from models.rubber_bumper import RubberBumper
from models.screw import LowProfileScrew
from models.switch import Switch


class WaveCase:
    """Builds the keywell, keyplate and bottom for one or both halves of the keyboard.

    The parts are available as case.left and case.right (BuiltSide). case.right is None unless both_sides is set.
    With debug the accessories are built as well and everything is pushed to the viewer, the intermediate
    shapes last in a group that starts hidden. Pass a viewer to show the parts somewhere else.
    """

    def __init__(self, switch: Switch, keys: ErgoKeys, caseDimensions: WaveDimensions, outline, debug=False, both_sides=False, viewer=None):
        self.viewer = viewer if viewer is not None else (OcpViewer() if debug else NullViewer())
        self.ctx = ctx = CaseContext(
            switch, keys, caseDimensions, outline,
            RubberBumper(), HeatSetInsert(caseDimensions.print_profile.insert_pilot_radius), LowProfileScrew())

        print("Creating case...")
        blanks = Blanks(
            keywell=build_keywell(ctx, self.viewer.debug.scope("keywell")),
            keyplate=build_keyplate(ctx, self.viewer.debug.scope("keyplate")),
            bottom=build_bottom(ctx, self.viewer.debug.scope("bottom")),
        )
        fixtures = build_fixtures(ctx) if self.viewer.enabled else None

        left = Side.left(ctx)
        self.left: BuiltSide = finish_side(ctx, left, blanks, fixtures, self.viewer)
        self.right: BuiltSide | None = None
        if both_sides:
            self.right = finish_side(ctx, Side.right(ctx, left), blanks, fixtures, self.viewer)

        self.viewer.push_debug()
        print("Done creating case.")
