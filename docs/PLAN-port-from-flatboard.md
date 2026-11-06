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
