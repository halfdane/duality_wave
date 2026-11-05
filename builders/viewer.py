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

    def push(self, obj, name: str) -> None:
        pass

    def push_debug(self) -> None:
        pass


class OcpViewer:
    """Pushes parts to the OCP CAD Viewer. The collected debug group is pushed last and starts hidden."""

    enabled = True

    def __init__(self):
        self.debug = DebugScope()

    def push(self, obj, name: str) -> None:
        from ocp_vscode import push_object

        push_object(obj, name=name)

    def push_debug(self) -> None:
        from ocp_vscode import Render, push_object

        push_object(self.debug.content, name="debug", mode=Render.NONE)


def show_in_viewer(port: int = 3939) -> None:
    """Display everything that was pushed to the OCP CAD Viewer."""
    from ocp_vscode import Camera, ColorMap, set_colormap, set_defaults, set_port, show_clear, show_objects

    set_port(port)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.seeded(colormap="rgb", alpha=1, seed_value="wave"))
    show_objects()
