from build123d import BuildLine, BuildPart, BuildSketch


def plain_shape(value):
    """The shape inside a builder. The viewer would show a builder as a group with a second, local copy."""
    if isinstance(value, BuildSketch):
        return value.sketch
    if isinstance(value, BuildPart):
        return value.part
    if isinstance(value, BuildLine):
        return value.line
    return value


class DebugScope:
    """Collects intermediate shapes in a nested dict that the viewer shows as one group."""

    def __init__(self):
        self.content: dict = {}

    def note(self, name: str, value):
        self.content[name] = plain_shape(value)
        return value

    def scope(self, name: str) -> "DebugScope":
        child = DebugScope()
        self.content[name] = child.content
        return child


class NullScope:
    def note(self, name: str, value):
        return value

    def scope(self, name: str) -> "NullScope":
        return self


class NullViewer:
    """Builds only the printable parts and shows nothing."""

    enabled = False

    def __init__(self):
        self.debug = NullScope()

    def push(self, obj, name: str, color: str | None = None, alpha: float | None = None) -> None:
        pass

    def push_debug(self) -> None:
        pass


class SilentViewer:
    """Builds the accessories as well, but shows nothing. The caller takes the parts from the case.

    With collect_debug it keeps the intermediate shapes in viewer.debug.
    """

    enabled = True

    def __init__(self, collect_debug: bool = False):
        self.debug = DebugScope() if collect_debug else NullScope()

    def push(self, obj, name: str, color: str | None = None, alpha: float | None = None) -> None:
        pass

    def push_debug(self) -> None:
        pass


class OcpViewer:
    """Pushes parts to the OCP CAD Viewer. The collected debug group is pushed last and starts hidden."""

    enabled = True

    def __init__(self):
        self.debug = DebugScope()

    def push(self, obj, name: str, color: str | None = None, alpha: float | None = None) -> None:
        from ocp_vscode import push_object

        options = {key: value for key, value in (("color", color), ("alpha", alpha)) if value is not None}
        push_object(obj, name=name, **options)

    def clear(self) -> None:
        """Remove everything the viewer shows."""
        from ocp_vscode import show_clear

        show_clear()

    def push_debug(self) -> None:
        """The debug group starts hidden. A mode overrides the visibility the user set in the viewer, so it is only
        passed when the viewer does not know the group yet."""
        from ocp_vscode import Render, push_object

        known = _viewer_knows_debug_group()
        push_object(self.debug.content, name="debug", mode=None if known else Render.NONE)


def _viewer_knows_debug_group() -> bool:
    from ocp_vscode import status

    try:
        states = status().get("states") or {}
    except Exception:
        return False
    return any("debug" in str(path) for path in states)


def show_in_viewer(port: int = 3939) -> None:
    """Display everything that was pushed to the OCP CAD Viewer."""
    from ocp_vscode import Camera, ColorMap, set_colormap, set_defaults, set_port, show_objects

    set_port(port)
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.seeded(colormap="rgb", alpha=1, seed_value="wave"))
    show_objects()
