# Specification

This file lists the requirements of the duality_wave case.
A requirement states an outcome.
It does not state how the code reaches the outcome.
It names a parameter, not the value of the parameter, unless the value is the requirement.
Every requirement has an ID.
Every ID has at least one test in `tests/`.
A test can cite an ID in a comment.
A test does not need an ID.
Every ID that a test cites exists in this file.
`tests/test_spec.py` checks the last two rules.
Retired IDs are not used again.
Lengths are in millimetres. Times are in seconds.

## Scope

R-01: Each half has a switch for every key of the layout.
R-02: The right half is the left half mirrored.
R-03: Every part of every built half is one valid solid.

## Geometry

R-04: The keyplate top is at z = 0. The keywell spans from z = -below_z to z = above_z. The bottom plate spans from z = -below_z to z = -keyplate_z. The one exception is the bump under the reset button of the XIAO: it rises to the button.
R-05: The keyplate fits inside the keywell in the XY plane.
R-06: No switch contact touches the bottom plate. The cutouts leave room for them.
R-16: The thumb cut is a tapered pocket that follows the thumb keys. It grows by `taper` from the floor to the top. The floor is the top of the switch housing. It does not move with the top of the keywell.
R-17: The outer edges of the keywell that are not vertical carry a chamfer of `rim_chamfer`. The keywell has no fillets. The chamfer keeps the envelope and the keywell stays one valid solid.
R-18: The Z levels come from one chain in `CaseDimensions`. The keyplate depth follows from the housing height. The depth of the case below the plate follows from the switch height below the plate. The roof of the keywell is `wall_over_cap` over the keycaps.
R-19: The contacts and the side posts of the switch are trimmed to `pin_len` and `side_post_len`. A post is never longer than its datasheet value. A post of length 0 does not exist. The depth of the switch below the housing is the longest contact or side post. The centre post does not count.
R-21: Nothing sticks out of the bed face by more than the bumpers do. This covers the centre post of the switch, the USB-C connector of the XIAO and the lever of the power switch. The screw is long enough to pass the insert and short enough to stay clear of the cap.
R-22: No fixture collides with a part. The inserts are pressed into the keywell and are the only exception. The power switch stays clear of the battery.
R-23: The bottom plate keeps a wall around every bumper pocket. Every contact has a floor under its tip. The centre post has a hole.
R-24: Every level of the case sits on a layer boundary, counted from the bed face in steps of `layer_height`. This covers `below_z`, `above_z`, the top of the bottom plate, the back of the XIAO, the power switch and the roof of the battery recess. A level moves only in the safe direction: the keywell top, the keyplate depth and the XIAO move up or out, the power switch and the battery roof move down. A level moves by less than one layer.
R-31: The screws, the magnets and the bumpers keep a wall of at least `min_wall` to each other, to the cutout of the keys and to the edge of the plate. This is checked in the layer where both parts have a hole: the bottom plate for the head recesses and the bumper pockets, the keywell for the insert pilots and the magnet pockets. It is checked for the full variant. The compact variant is for test prints and is not placed by hand.

## Outline

R-25: The cutout of the keywell has no gap narrower than `bridge_gap` between key cells. Such a gap is closed with straight edges. A wider gap stays open.
R-26: No outline has a kink. This covers the cutout, the outer outline and the inner outlines. The corners of the cutout are rounded with `cutout_concave_radius` and `cutout_convex_radius`. The outer outline is rounded with `corner_radius`.
R-27: Every keycap and every switch body lies inside the cutout. The cutout lies inside the cavity. The cavity is the outer outline moved inwards by the wall thickness.
R-28: The round notch for the trackpad is cut only where it fits between a key and the thumb cluster. It keeps clear of the cutout. The inner outline keeps a thicker wall around it.
R-29: The right wall meets the thumb cluster in an arc. The radius of the arc is `sweep_ratio` times the height of the wall above the thumb cluster.

## Layout

R-08: The key positions come from ergogen. Each `ergogen/<name>.points.yaml` equals the output of ergogen for `ergogen/<name>.yml`. Run `task layout` to update it.
R-09: The loader reads x, y and r of every point in file order. It drops points that the layout marks as skip.
R-15: The cutout of the keywell does not change when a key position moves by 1e-7 mm or less. ergogen rounds the positions to 8 digits.

## Debug mode

R-07: A build without debug builds no accessories and pushes nothing to the viewer. It builds the same parts as a build with debug.

## Performance

The limits below are for the development machine. Set `WAVE_PERF_FACTOR` to scale all of them.
The limits are about 2.5 times the measured time. Tighten them after a speed-up step.

R-10: A build of the full variant (both halves) takes at most 6 s.
R-11: A build of the compact variant takes at most 3 s.
R-12: A stage of the build stays under its limit: keywell 1.2 s, keyplate 1.6 s, bottom 0.7 s, each finish stage 1.4 s. An outline with one inner outline takes at most 0.4 s.
