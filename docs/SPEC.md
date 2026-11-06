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

## Debug mode

R-07: A build without debug builds no accessories and pushes nothing to the viewer. It builds the same parts as a build with debug.

## Performance

The limits below are for the development machine. Set `WAVE_PERF_FACTOR` to scale all of them.
The limits are about 2.5 times the measured time. Tighten them after a speed-up step.

R-10: A build of the full variant (both halves) takes at most 30 s.
R-11: A build of the compact variant takes at most 15 s.
R-12: A stage of the build stays under its limit: keywell 9 s, keyplate 7 s, bottom 2 s, each finish stage 8 s.
R-13: A test that is not marked `slow` builds no case. The fast tier stays fast.

## Process

R-14: Every requirement in this file is named by a test. Every requirement that a test names is in this file.
