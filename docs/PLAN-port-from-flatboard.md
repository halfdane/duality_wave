# Plan: bring flat_keyboard (FK) ideas into duality_wave (DW)

Status: in progress. Update the progress list at the end of this file after each step.
Do not consolidate FK and DW into one repository. FK stays a reference.

## Paths

- FK: /home/user/private/flat_keyboard
- DW: /home/user/private/duality_wave (reach it through the symlink /home/user/private/flat_keyboard/duality_wave, because direct access is denied).
- Scratch scripts: /tmp/opencode (time_dw.py, time_fb.py, time_thumb.py).
- This file lives in DW: docs/PLAN-port-from-flatboard.md. It was not committed when written.

## Known hazards

- A nested nix devshell leaks UV_PROJECT_ENVIRONMENT from the outer direnv.
- Running DW's `nix develop` from a session that loaded FK's direnv writes DW packages into FK/.venv.
- This happened twice. FK/.venv holds build123d 0.11.1 right now. It must hold 0.13.0.
- Repair: run `uv sync --frozen` in FK.
- Never run `nix develop` of one project from a session that has the other project's direnv loaded. Use a clean shell, or unset UV_PROJECT_ENVIRONMENT first.
- Run commands like this: `nix develop path:. -c <cmd> 2>&1 | grep -v -E "^evaluation|^  task|Fontc"`.
- Use PYTHONDONTWRITEBYTECODE=1 and `pytest -p no:cacheprovider` when you want no cache files.

## Decisions made by the user

- Take the logic of FK's flake.nix, especially the shellHook and the fontconfig.
- Set UV_PROJECT_ENVIRONMENT in both flakes. The agent recommends it.
- Use `uv sync --frozen` in both FK and DW.
- Make the trim length of the electric contacts a configurable parameter. The default is 2 mm.
- Remove the two small plastic side posts (a1, a2) completely. The side post length parameter defaults to 0.
- Keep the centre post (2.65 mm). The stem and the spring run in it, so it cannot be clipped.
- The centre post pokes through the bottom plate. Bumpers must stand out further than the post tip.
- The cap height in the OCP render is correct. The render is the source of truth.
- Replace the thumb cut fillets with the `grow` approach. Start with a chamfer on the rims.
- The user decides about the rim treatment later, after runtime profiling and visual inspection.
- Use real ergogen for the points. Remove the sympy re-implementation.
- Write specs and tests. Test performance is a required feature.
- Update the versions in DW.
- Add whole-layer snapping.

## Facts found in DW (cap height)

- models/choc.py builds the stand-in cap. Its top is at 0.8 + 2.5 + 2.5 - 2.28 + 4.5 = 8.02 mm above the plate top (z = 0).
- models/choc.py also defines CapDimensions.d.Z = 2.5 and AboveDimensions.d.Z = 0.8 + 2.5 + 2.5 + 2.5 = 8.3.
- case_dimensions.py uses above_z = 8.3 as the wall top. The wall is 0.28 mm above the rendered cap.
- builders/thumb_cut.py uses thumb_depth = cap.d.Z + stem.d.Z = 5.0. It depends on the unrealistic 2.5 mm cap value.
- FK uses 7.5 mm for the cap top. This value was never verified. If the DW render is right, FK is 0.52 mm too low.
- Consolidation target: one value cap_top (8.02, derived from the cap model) plus one parameter wall_over_cap. above_z = cap_top + wall_over_cap.

## Facts found in DW (height stack)

- Total height is 14.2 mm: above 8.3 plus below 5.9.
- below_z = housing 2.2 + longest post or contact 3.0 + 0.7 margin.
- The keyplate is 2.9 mm thick. The bottom plate is 3.0 mm thick.
- With contacts trimmed to 2.0 mm and no side posts: housing 2.2 + contacts 2.0 + floor 0.4 = 4.6 mm below.
- The centre post ends 2.2 + 2.65 = 4.85 mm below the plate top. It pokes 0.25 mm out of the 4.6 mm case bottom.
- The centre post is not part of the below_z calculation. It needs a through hole in the bottom plate instead.
- 12.8 mm total needs the wall top at 8.2 (wall_over_cap about 0.18) and a floor of 0.4 mm.
- With wall_over_cap 0.28 the wall top snaps up to 8.4 and the total is 13.0 mm.
- DW parts print upside down. The origin z = 0 is the plate top, not the print bed.
- Snapping must count layers from the bed face (z = -below_z), not from z = 0.

## Order of work

Each step ends with a commit by the user. The agent does not commit.
Each step adds its own R-IDs to docs/SPEC.md and its own tests.

### Step 0. Baseline

- Repair FK/.venv with `uv sync --frozen`.
- Record DW numbers per part and variant (full, compact): validity, solid count, volume, bounding box.
- Record per-stage build times. Reference: both halves about 13.9 s, thumb fillets about 2.6 s per half.
- Store the baseline in a file that later steps compare against.

### Step 1. Tooling

- Rewrite DW flake.nix from FK's structure: fixed fontconfig, env block, shellHook echoes.
- Keep from DW: UV_PYTHON_DOWNLOADS=never and the stale-venv Python version check.
- Set UV_PROJECT_ENVIRONMENT="$PWD/.venv" in both flakes.
- Run `uv sync --frozen` in the shellHook of both projects.
- Run `uv sync --locked` in `task check` of both projects, so a stale lock fails.
- Add ergogen, ruff and pytest to the DW shell.
- Update the nixpkgs lock of DW. Do it separately from the Python packages.
- Add an `update` task that runs `uv lock --upgrade` on purpose.
- Acceptance: both shells start from a clean checkout, and a nested shell does not touch the other project's .venv.

### Step 2. Spec and test frame

- Create DW docs/SPEC.md with R-IDs.
- Run tests with pytest. Keep the existing unittest cases as they are.
- Add characterization tests for the current behaviour: valid single solids, bounding boxes, height 14.2 mm.
- Test performance rules:
  - Two tiers. `task check` has no CAD builds. `task test` has the full set.
  - Build each variant once per session in a shared fixture.
  - Always show `--durations`.
  - Add a stage timer to the build. Tests assert a budget per stage with a wide margin.
  - Add deterministic proxies, for example "no fillet on B-spline edges" and a limit on boolean operations.
- Add ruff to `task check`.

### Step 3. Version upgrade

- Run `uv lock --upgrade` in DW. Target build123d 0.13 and OCP 8.
- Make no other change in this step.
- Compare with the baseline. Explain every geometry difference.
- If the thumb fillets break, do not repair them. Go to step 5.
- FK's grow() breaks on build123d 0.11.1 (Shape.cast returns None for a wire). Remember this when porting grow().

### Step 4. Real ergogen points

- First compare FK's layout/points.yaml with the DW layout.py output. This proves equivalence.
- Generate the points with ergogen from DW's ergogen/wave.yml and compact.yml.
- Commit the generated points. Add `task layout`.
- Delete layout.py and the sympy dependency.
- Acceptance: no geometry change against the baseline.

### Step 5. Thumb cut without expensive operations

- Keep the loft (0.06 s).
- Build one zone and offset it with grow(), as in FK src/flatboard/thumb.py.
- Port grow() with a version-safe wire conversion.
- Remove fillet_thumb_edges and its B-spline logic.
- Round the outer corners in the 2D outline with round_convex().
- Use a chamfer on the rims for now.
- Tests: valid solid, thumb floor depth, no fillet on slope edges, and a stage budget.

### Step 6. Profile

- Run the stage timers and cProfile again.
- Compare with step 0. Record the numbers.
- Look for the next hot spots (connectors, XIAO pocket, boolean cuts).
- The user decides the rim treatment (chamfer, none, fillet) from these numbers and from visual inspection.

### Step 7. Z-stack rework

- 7a. Move all Z levels into one derived chain in CaseDimensions, like FK params.py. Values stay the same. Tests pin them.
- 7b. Add parameters to the switch model: pin_len (default 2.0) and side_post_len (default 0). below_z comes from the longer of pin_len and side_post_len. The centre post keeps its length and is excluded from below_z. Remove the side post models, or keep them only when side_post_len is greater than 0.
- 7c. Consolidate the cap height (see facts above). Make thumb_depth use the real cap. Add wall_over_cap.
- 7d. Reduce the bottom plate thickness. It comes from the stack: pin recess depth plus the floor of 0.4 mm. Cut a through hole for the centre post. Compute the poke-through (centre post length minus the room below the housing). Test that the bumpers stand out further than the poke-through. Check the screw head recess, the bumper pocket and the reset lever.
- 7e. Add layer_height to PrintProfile. Add snap_up(). Count layers from the bed face. Apply it to all levels. Test that every level is a whole number of layers.
- Run all of step 7 for the full and the compact variant.

### Step 8. Final pass

- Profile again. Set the final stage budgets.
- Update README (it says 113 x 97 x 14 mm), the BOM and the coupons.
- Decide what happens to FK (archive as reference).

## Reminders for later

- Remind the user about the screw length when step 7d is done. A thinner stack may change the BOM.
- Remind the user to decide the rim treatment after step 6.
- Tell the user that FK's cap value 7.5 mm contradicts the DW render (8.02 mm).
- Ask for a real measurement of switch plus cap if the render and the real part ever disagree.
- The UNVERIFIED values of FK stay in FK/README.md. They do not move to DW.

## Progress

- Plan moved from /home/user/.opencode/plan into this file. The old copy there cannot be deleted by the agent. Delete it by hand.
- Step 0 done. Script: scripts/baseline.py. Record: docs/baseline/step0.json (build123d 0.11.1).
  - Full variant (both halves): 12.4 s. Stages: keywell 3.4 s, keyplate 2.4 s, bottom 0.4 s, finish_side 6.2 s.
  - Compact variant (left half): 6.0 s. The keywell takes 3.3 s of it.
  - Existing unittest suite: 45 tests, 58 s.
  - Finding: finish_side takes half of the full build. Look at it in step 6.
- Step 1 done (not committed).
  - DW flake.nix rewritten from FK. DW and FK use the same nixpkgs revision (2026-11-03). Python is 3.13.16 now.
  - Both shellHooks set UV_PROJECT_ENVIRONMENT, run `uv sync --frozen`, and rebuild a venv with a wrong Python version.
  - `task check` runs `uv lock --check`. `task update` upgrades the packages on purpose.
  - DW got pytest and ruff as a dev dependency group, and ergogen in the shell. uv.lock changed only by these four packages.
  - Verified: DW's shell started inside FK's direnv session uses DW/.venv and leaves FK/.venv alone.
  - Verified: geometry is identical to the baseline and the 45 unit tests pass.
- Step 2 done.
  - docs/SPEC.md has R-01 to R-14. tests/test_spec.py checks that every ID has a test and every cited ID exists (R-14).
  - Tests run with pytest. The unittest cases stay unchanged. 55 tests pass.
  - Fast tier: `task check` runs `uv lock --check`, ruff and `pytest -m "not slow"`. It takes about 7 s.
  - R-13: a test without the `slow` marker cannot build a case (tests/conftest.py).
  - Full tier: `task test` runs check, then all tests in parallel with xdist. It takes about 36 s (serial: 62 s).
  - WaveCase records `case.timings` (src/duality_wave/timing.py). R-10 to R-12 hold the build budgets. WAVE_PERF_FACTOR scales them.
  - ruff checks real errors only (E4, E7, E9, F). Star imports and `as name` context variables stay allowed.
  - tests/builds.py builds each case once per process. It also builds the compact variant.
- Commits: the user asked for delineated commits along the way. The agent commits per step from now on.
- Step 3 done. build123d 0.11.1 -> 0.13.0, OCP 7.9.3 -> 8.0.1, ocp-vscode 3.4.0 -> 4.2.0. pyproject requires build123d>=0.13.
  - Full build: 12.4 s -> 7.7 s. Compact build: 6.0 s -> 4.3 s. Same code, only the new library.
  - Break 1: 0.13 rejects `Line` in a BuildSketch. Wrapped in BuildLine (keyplate.py).
  - Break 2 (silent): 0.13 applies an enclosing `Locations` to a builder that is created inside it. The symbol and the space invader were cut at twice the position and missed the part. Fix: build them outside `Locations`. Look for this pattern in new code.
  - Change: the XIAO connector line had a z offset (xiao_position.Z). It is flat now. The keyplate volume changes by 0.2 mm3 (full) and 0.006 mm3 (compact).
  - Keywell, bottom and thumb cut are identical to step 0 (volume, bbox, validity).
  - `add()` renamed to `insert()` (deprecated in 0.13).
  - New baseline for later steps: docs/baseline/step3.json.
- Step 4 done. The key positions come from real ergogen.
  - The sympy port gave the same positions as ergogen for wave.yml and compact.yml (largest difference 7e-8 mm, same names, same order). FK's ergogen.yaml has the same layout.
  - `task layout` runs ergogen and writes ergogen/wave.points.yaml and ergogen/compact.points.yaml. They are committed. tests/test_layout.py fails when they are out of date (R-08).
  - layout.py shrank from 471 lines to 20. It reads the points file (R-09). sympy is no longer a direct dependency (build123d still pulls it in).
  - Finding: ergogen rounds to 8 digits. Two thumb rectangles that were exactly aligned are now 1e-8 apart. clean() keeps their edges apart. The acute-angle fillets in `create_keywell_outline` then acted on another corner. The keywell cutout lost 6.3 mm2. Fix: `merge_aligned_edges` in outline.py (R-15). Geometry is identical to step3.json again.
- Step 5 done. The thumb cut has no expensive operations.
  - One thumb zone (old layer-0 rectangles, merged, corners rounded with radius 2). Layers are `grow(zone, taper * progress)` with a cosine ease in z. `ThumbCutSpec`: taper 15, inset_inner 7, inset_outer 3, corner_radius 2, layers 16, rim_chamfer 0.8.
  - The B-spline fillets are gone. A chamfer of 0.8 on the outer non-vertical keywell edges replaces them (R-16, R-17). Chamfer 1.0 fails (near-tangent slope top edges). 0.9 is the limit.
  - The old run_inner (5) and run_outer (15) are replaced by one taper. The slope tops now sit +8 inner and +12 outer past the old floor edge, so the slope shape changed. Check it visually.
  - Keywell stage: 2.89 s -> 0.59 s (full), 2.78 s -> 0.49 s (compact). Full build 7.7 s -> 5.5 s, compact 4.3 s -> 2.1 s.
  - Keywell volume: -85 mm3 (full), -47 mm3 (compact). Bounding boxes, validity and solid counts are unchanged.
  - Limit: the loft needs sections with the same edge count. A synthetic layout with a notch that fills up can fail. Both project layouts loft for taper 5..20 and layers 4..32.
  - Budgets tightened (R-10 to R-12). New baseline: docs/baseline/step5.json.
- Step 6 done. Profile and speed-up. Geometry is identical to step5.json (volume, bbox, validity, solids).
  - cProfile does not see the OCP calls (pybind11), so the stages were timed with wrappers.
  - Finding 1: a BuildPart with `insert(part)` and several `mode=SUBTRACT` ops is slow (about 2.4x). Build the cutters in their own BuildPart, then do one `part.cut(cutter)`. Done for the XIAO USB tunnels, the reset lever and the switch post cutouts. finish_side: 1.6 s -> 0.75 s per half.
  - Finding 2: fusing 17 switch holes (85 shapes) costs 0.3 s. Build one hole and place 17 copies in a Compound. Keyplate: 1.35 s -> 0.8 s.
  - Pitfall: `extrude(sketch, ...)` called inside an active BuildPart adds to that part. Wrap cutter code in its own BuildPart.
  - Full build: 7.7 s (step 3) -> 5.5 s (step 5) -> 3.2 s. Compact: 4.3 s -> 2.1 s -> 1.5 s.
  - Left for later: add_large_usb_cutouts 0.1 s x4, post cutouts 0.19 s x2, keywell cavity 0.26 s, connectors 0.23 s.
  - Budgets tightened again (R-10 to R-12). New baseline: docs/baseline/step6.json.
- Step 7a done. `CaseDimensions` derives keyplate_z, below_z and bottom_plate_z in one chain. Values are the same (8.3, 2.9, 5.9, 3.0). `add_below_choc_posts` is now `floor_under_pins`. New parameter `keyplate_under_housing` (0.7). R-18 pins the chain. Geometry is identical to step6.json.
- Step 7b done. `Choc(pin_len=2.0, side_post_len=0.0)`. Contacts are trimmed, side posts are gone, a post of length 0 does not exist (R-19). below_z falls from 5.9 to 4.9 and the bottom plate from 3.0 to 2.0. The stack is 1 mm thinner. The bottom volume drops by a third.
  - Bug fixed on the way: the posts of the preview model sat inside the housing, because `faces().sort_by(Axis.Z)[0]` of a nested BuildPart picks a face in local coordinates. The posts are now placed in world coordinates (X, -Y), like the cutouts.
  - Known for 7d: the cutouts of the centre post now stop 0.05 mm above the bottom face. 7d changes this.
- Step 7c done. The cap height has one source: `CapDimensions` (height 4.5, overlap 2.28), so the cap top is 8.02 (R-20). The top of the keywell is `wall_over_cap` (0.18) above it: above_z falls from 8.3 to 8.2. The thumb floor is the top of the switch housing (3.3), not a depth below the top. `thumb_depth(switch, top_z)` and `thumb_floor_z(switch)` changed. `Choc.cap_model_z` and `cap_model_overlap` are gone.
- Step 7d done. Stack decision by the user: below_z 4.6 (floor under pins 0.4), bottom plate 1.7, about 12.8 mm in total.
  - Post cutouts: each post has a hole from the plate top (-keyplate_z) to its tip. The centre post has a through hole and pokes 0.25 mm out of the bed face. The terminal channel is 0.8 deep.
  - XIAO ledge 0.6 (`xiao_ledge`). The USB-C connector stands 0.46 out of the bed face. The power switch lever stands 0.8 out (`lever_protrusion`). The bumper dome is 1.0, so the bumpers stay the lowest point (R-21).
  - Screw 8 mm -> 6 mm. The tip ends at z 2.4, above the insert top (2.0). BOM and README still say 8 mm: fix in step 8.
  - Bumpers 0, 3, 4 (full) and 0, 3 (compact) moved: the old spots hit the XIAO processor pocket or the pin channels at the new depth.
  - Reset lever bump now rises above the plate up to the XIAO button: R-04 has this exception.
  - New requirements R-21 to R-23 (protrusions, collisions, plate webs). Geometry baseline moves on purpose. The new baseline comes in 7e.
- Step 7e done. `PrintProfile.layer_height` (0.2), `snap_up` and `snap_down`. `CaseDimensions.snap_z` counts layers from the bed face (R-24).
  - Snapped: below_z (4.6), top of the keywell (8.2, total 12.8 = 64 layers), plate top (the plate gets thinner: keyplate_z 3.0, plate 1.6), XIAO back (up), power switch (down, lever stands 0.95 out, body 0.2 under the battery), battery roof (down).
  - Tests run for layer heights 0.2, 0.16, 0.12 and 0.28 and for both variants.
  - Not snapped: the thumb floor (housing top, 3.3) and the magnet recess.
  - Found on the way: with the plate bottom at -3.0, the LED recess of the XIAO cutter left a film of 0.075 mm (a second solid in the keyplate). The recess is now 0.1 mm taller.
  - New baseline: docs/baseline/step7.json. Full build 3.1 s, compact 1.4 s. The budgets stay for step 8.
- Step 8 done. Final numbers against step 0: full build 12.4 s -> 3.1 s, compact 6.1 s -> 1.4 s. Budgets (R-10 to R-12) are now about 2x the measured times: full 6 s, compact 3 s, keywell 1.2, keyplate 1.6, bottom 0.7, each finish 1.4.
  - README: size 113 x 97 x 12.8 mm, screws 6 mm. The coupons take their values from CaseDimensions and need no change.
  - Open for the user: the rim treatment (chamfer 0.8, taper 15) and what happens to FK. FK stays untouched as a reference.
- Step 9 done (not committed). The outline uses `grow`, `close_concave` and `round_convex` from `geometry2d`. The fillet code is gone.
  - New: `OutlineSpec` with `corner_radius`, `sweep_radius`, `bridge_gap`, `cutout_concave_radius`, `cutout_convex_radius`. R-25 to R-30.
  - The keywell cutout comes from key cells, `bridge_gaps` (4.4), a closing (2.0) and an opening (0.5). It has no gap that a 2 mm disc cannot enter.
  - The user chose the closing. The tangent arc is gone. The disc radius is `sweep_ratio` (0.5) times the wall height above the thumb cluster. Full: 36.8 mm, within 2 mm2 of the old arc. Compact: 23.7 mm.
  - A radius from the finger cluster height gives 10.6 mm on compact. The compact fastener at (34, -10) then leaves the cavity. So the rule uses the wall height.
  - The user set `corner_radius` 5 and `cutout_concave_radius` 0.5. R-27 got small tolerances for this.
  - `create_keywell_outline()` returns one Sketch. The inner outlines have no kinks.
  - Keywell volume: full -738 mm3, compact -283 mm3. Keywell stage 0.51 s -> 0.32 s. Outline build 0.18 s -> 0.14 s.
- Step 10 done (not committed). Test diet and spec cleanup.
  - The cutout is clipped to the cavity in `Outline`. It no longer pokes into the wall at a rounded corner. Keywell volume +0.56 mm3. New baseline: docs/baseline/step10.json.
  - The spec states outcomes. R-13, R-14, R-20 and R-30 are retired (R-20 is part of R-18, R-30 is part of R-12). R-27 now says the cutout lies inside the cavity, without tolerances.
  - Tests take their numbers from `dims`, specs and the layout. `tests/test_outline.py` runs on seven outline cases: both variants, other radii and gaps, an extra column and an extra row. Small layouts for the bridge and the notch live in the test file.
  - Found on the way: a `corner_radius` above about 6 cuts the keycap of the last thumb key. The test with a large radius guards this.
  - Removed: pinned areas and coordinates, duplicate time budgets, trivial determinism test. The development notes moved from the README to CONTRIBUTING.md.
  - Test tiers: the marker `integration` replaces `slow`. Integration tests share three builds (`full`, `compact`, `quiet`) from `tests/conftest.py`. R-22 battery clearance and R-23 walls are unit tests now. The marker `perf` holds the wall-clock limits. `task test` runs them alone at the end.
  - Open for the user: the screw head measurement and what happens to FK. The rim chamfer is decided: keep it.
