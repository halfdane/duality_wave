from duality_wave.builders.export import export_steps
from duality_wave.builders.viewer import show_in_viewer
from duality_wave.cli.common import build_full_case


if __name__ == "__main__":
    case = build_full_case(debug=True)
    show_in_viewer()
    export_steps(case)
