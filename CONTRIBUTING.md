# Contributing

This file is for people who change the code of duality_wave.
The README is for people who print the keyboard or change the layout.

## Set up

Install nix (the package manager, not nixOS the operating system)
Run `direnv allow` or `nix develop`.
The dev shell installs the locked Python packages with `uv`.
Use `task update` to upgrade the packages on purpose.

## Checks and tests

- `task check` verifies `uv.lock`, runs `ruff` and runs the unit tests. It builds no case.
- `task test` checks the lock file, runs `ruff`, runs all tests in parallel, then runs the tests with a time limit alone. This takes about 35 s.

A unit test is fast and builds no case.
A test that builds a whole case or the coupons is an integration test. It carries `@pytest.mark.integration`.
A test without that marker fails when it builds a case.
Integration tests use the fixtures `full`, `compact` and `quiet` from `tests/conftest.py`.
These three cases are built once per test process.
Do not add a fourth build for a single check. Check it on one of the three, or test the builder alone with `make_context()`.
The integration tests of the cases run on one xdist worker, so they share these builds. The coupon tests run on another.

A test with a wall-clock limit carries `@pytest.mark.perf`. `task test` runs these tests alone at the end, because load changes the times.
Set `WAVE_PERF_FACTOR` to scale all time limits, for example on a slow machine.
The time limits are in `docs/SPEC.md`.

`task layout` runs ergogen and writes `ergogen/*.points.yaml`.
A test fails when a points file is out of date.
The test is skipped when ergogen is not installed.

## Specification and tests

`docs/SPEC.md` lists what the case must do.
A requirement states an outcome, not how the code reaches it.
Every requirement has at least one test.
A test cites its requirement in a comment, for example `# R-27`.
A test does not need a requirement.
Tests for a mechanism, for example a helper that offsets a face, need none.
`tests/test_spec.py` checks that every requirement has a test and that every cited ID exists.
Do not reuse a retired ID.

Write tests that check logic and mechanisms, not the current numbers of the design.
A change of `corner_radius`, or a new row or column in ergogen, must not break most tests.
Take numbers from `dims`, from the specs and from the layout.
If none of them covers a case, build a small dimension, spec or layout inside the test file.
Do not add test-only code to the package.
A test may break when you move a hand-placed part, for example a screw.
That is intended.

## Baseline

`scripts/baseline.py` records the volume and the bounding box of every part and the time of every build stage.

    PYTHONPATH=. python scripts/baseline.py write build/baseline.json
    PYTHONPATH=. python scripts/baseline.py compare build/baseline.json

Write the record before a change and compare after it, to see what the change did to the geometry.
The record is not kept in the repository.
Tests do not pin these numbers.

## Print tags

Every print should get an annotated git tag named `print/<name>-<n>`, for example `print/coupons-1`.
Commit your changes before you export and slice.
Tag the commit that you exported from.
Write the printer, the material, the fit values and the STL hashes in the tag message.
Write what you learned from the print in the tag message of the next print, or in the commit that changes the values.
Push the tag with `git push origin print/<name>-<n>`.
Look up the values of a print with `git show print/<name>-<n>` and `git show print/<name>-<n>:src/duality_wave/models/print_profile.py`.
The tag message holds the STL hashes that identify them.

## Debug mode

`WaveCase(debug=True)` builds the accessory models and sends everything to the viewer.
The intermediate shapes arrive last, in a group named `debug` that starts hidden.
`WaveCase(debug=False)` builds only the printable parts.
The finished halves are `case.left` and `case.right`.

## Code map

The Python code is the package `duality_wave` in `src/duality_wave/`.

- `cli/__main__.py` selects the command: `view`, `export` or `render`. The tasks in `Taskfile.yml` call it.
- `cli/view.py` shows a pose of the case, or a coupon plate, in the viewer. It writes no files.
- `cli/export_case.py` writes the STEP files of the case and `cli/export_coupon.py` writes the STL of every coupon plate. Both print the paths they wrote and show nothing.
- `cli/common.py` builds the case and the coupon plates for the commands.
- `cli/render.py` exports the meshes of each pose and a `scene.json` with the colours for the images.
- `scripts/render_blender.py` renders the images inside Blender. It reads the meshes and the colours and does not move anything.
- `case.py` has `WaveCase`, which builds the three parts for each half.
- `builders/` holds one builder per part (`keywell.py`, `keyplate.py`, `bottom.py`).
- `builders/thumb_cut.py` builds the sculpted thumb slope of the keywell and chamfers its rim.
- `builders/wiring_cuts.py` cuts the diode pockets, the trenches and the channel of the wiring file into the keyplate and the bottom plate.
- `wiring/` holds the diode pockets, the nets and the checks for `ergogen/wave.wiring.yaml` (`plate.py`, `nets.py`, `anchors.py`, `rounded.py`, `plan.py`, `check.py`, `export.py`, `editor.py`). The file holds plain coordinates. It is edited with the visual editor (`task wiring-editor`, `scripts/wiring_editor.py` and `scripts/wiring_editor.html`). The coordinates do not follow the layout, so open the editor after you change the layout, the dimensions, the diode or the print profile, and move the vertices that it reports.
- `builders/side.py` places the parts on the left or right half.
- `builders/accessories.py` builds the models that are only shown in the viewer.
- `builders/viewer.py` decides what is pushed to the viewer.
- `builders/parts.py` lists the part groups with their colour, their metal flag and their layer in the exploded view.
- `builders/poses.py` moves the finished parts into the transport position and the exploded view.
- `geometry2d.py` holds the 2D helpers: `grow`, `close_concave`, `round_convex` and `bridge_gaps`.
- `layout.py` reads the `*.points.yaml` files that ergogen writes.
- `models/` holds the part models and the outline.
- `models/outline.py` builds the outer outline, the inner outlines and the cutout of the keywell.
- `models/case_dimensions.py` holds the case dimensions of the main case and the compact variant.
- `models/features.py` holds the cutters that the case and the coupons share.
- `coupons.py` builds the calibration coupons.
- `paths.py` has the paths to the layouts and the `build` directory.
- `tests/` holds the tests.

This project is the descendant of the duality_particle.
Some names, for example `cirque_recess_*` in `models/outline.py`, still show that origin.
