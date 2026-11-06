# Specification

This file lists the requirements of the duality_wave case.
Every requirement has an ID.
Every ID is named by at least one test in `tests/`.
Every ID that a test names exists in this file.
`tests/test_spec.py` checks both rules.
Lengths are in millimetres. Times are in seconds.

Many requirements describe the behaviour of the code at the start of the port from flatboard.
They keep the later steps honest.
See `docs/PLAN-port-from-flatboard.md` for the plan.

## Scope

R-01: Each half of the full variant has 17 Choc V1 keys.
R-02: The right half is the left half mirrored.
R-03: Every part of every built half is one valid solid.

## Geometry

R-04: The keyplate top is at z = 0. The keywell spans from z = -below_z to z = above_z. The bottom plate spans from z = -below_z to z = -keyplate_z.
R-05: The keyplate fits inside the keywell in the XY plane.
R-06: No switch contact touches the bottom plate. The cutouts leave room for them.
R-16: The thumb cut is a loft of one zone. The zone is one face with round corners. The loft grows the zone by `taper` while it rises from the floor to the top. The floor is the top of the switch housing. It does not move with the top of the keywell.
R-17: The outer edges of the keywell that are not vertical carry a chamfer of `rim_chamfer`. The keywell has no fillets. The chamfer keeps the envelope and the keywell stays one valid solid.
R-18: The Z levels come from one chain in `CaseDimensions`. `keyplate_z` is the housing height plus `keyplate_under_housing`. `below_z` is the switch height below the plate plus `floor_under_pins`. `bottom_plate_z` is `below_z` minus `keyplate_z`.
R-19: The switch model has the parameters `pin_len` (default 2.0) and `side_post_len` (default 0). A post is never longer than its datasheet value. A post of length 0 does not exist. The centre post keeps its length. The depth of the switch below the housing is the longest contact or side post. The centre post does not count.
R-20: The top of the keywell is `wall_over_cap` (0.18) above the top of the keycaps. The cap top is the stack of base, upper housing, stem and cap, minus the overlap of cap and stem (8.02 in total).

## Layout

R-08: The key positions come from ergogen. Each `ergogen/<name>.points.yaml` equals the output of ergogen for `ergogen/<name>.yml`. Run `task layout` to update it.
R-09: The loader reads x, y and r of every point in file order. It drops points that the layout marks as skip.
R-15: The outline of the keywell cutout does not change when a key position moves by 1e-7 mm or less. ergogen rounds the positions to 8 digits.

## Debug mode

R-07: A build without debug builds no accessories and pushes nothing to the viewer. It builds the same parts as a build with debug.

## Performance

The limits below are for the development machine. Set `WAVE_PERF_FACTOR` to scale all of them.
The limits are about 2.5 times the measured time. Tighten them after a speed-up step.

R-10: A build of the full variant (both halves) takes at most 8 s.
R-11: A build of the compact variant takes at most 4 s.
R-12: A stage of the build stays under its limit: keywell 1.5 s, keyplate 2 s, bottom 1 s, each finish stage 2 s.
R-13: A test that is not marked `slow` builds no case. The fast tier stays fast.

## Process

R-14: Every requirement in this file is named by a test. Every requirement that a test names is in this file.
