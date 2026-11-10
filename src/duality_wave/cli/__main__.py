"""The commands of duality_wave. Run `python -m duality_wave.cli <command>`; the tasks in Taskfile.yml do this for you.

  view           show the case in a pose, or a coupon plate, in the OCP viewer
  export-case    write the STEP files of the case to build/case
  export-coupon  write the STL of every coupon plate to build/coupons
  render         write the meshes and render the README images
"""
import sys

from duality_wave.cli import export_case, export_coupon, render, view

COMMANDS = {"view": view.main, "export-case": export_case.main, "export-coupon": export_coupon.main, "render": render.main}


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        sys.exit(f"Usage: python -m duality_wave.cli {{{'|'.join(COMMANDS)}}} [arguments]")
    COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    main()
