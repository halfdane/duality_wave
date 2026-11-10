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
R-44: Every face of every part of every built half can be meshed, so the exported mesh has no gap. A gap makes the slicer report reversed faces.
R-45: A STEP file of a printable part reads back as the same solid: one solid, the same number of faces and the same volume. The slicer reads the STEP file, so a lost face leaves a hole in the part.

## Geometry

R-04: The keyplate top is at z = 0. The keywell spans from z = -below_z to z = above_z. The bottom plate spans from z = -below_z to z = -keyplate_z. The one exception is the bump under the reset button of the XIAO: it rises to the button.
R-05: The keyplate fits inside the keywell in the XY plane.
R-06: No switch contact touches the bottom plate. The cutouts leave room for them.
R-16: The thumb cut is a tapered pocket that follows the thumb keys. It grows by `taper` from the floor to the top. The floor is the top of the switch housing. It does not move with the top of the keywell.
R-17: The outer edges of the keywell that are not vertical carry a chamfer of `rim_chamfer`. The keywell has no fillets. The chamfer keeps the envelope and the keywell stays one valid solid.
R-18: The Z levels come from one chain in `CaseDimensions`. The keyplate depth follows from the housing height. The depth of the case below the plate follows from the switch height below the plate. The roof of the keywell is `wall_over_cap` over the keycaps. The keycap is a model of its own. Its underside is `overlap` below the top of the stem, its legs stand in the holes of the stem, and its highest point sets `above`.
R-19: The contacts and the side posts of the switch are trimmed to `pin_len` and `side_post_len`. A post is never longer than its datasheet value. A post of length 0 does not exist. The depth of the switch below the housing is the longest contact or side post. The centre post does not count.
R-21: Nothing sticks out of the bed face by more than the bumpers do. This covers the centre post of the switch, the USB-C connector of the XIAO and the lever of the power switch. The screw is long enough to pass the insert and short enough to stay clear of the cap.
R-22: No fixture collides with a part. The inserts are pressed into the keywell and are the only exception. The power switch stays clear of the battery.
R-23: The bottom plate keeps a wall around every bumper pocket. Every contact has a floor under its tip. The centre post has a hole.
R-24: Every level of the case sits on a layer boundary, counted from the bed face in steps of `layer_height`. This covers `below_z`, `above_z`, the top of the bottom plate, the back of the XIAO, the power switch, the roof of the battery recess and the top of the magnets. A level moves only in the safe direction: the keywell top, the keyplate depth and the XIAO move up or out, the power switch, the battery roof and the top of the magnets move down. A level moves by less than one layer.
R-31: The screws, the magnets and the bumpers keep a wall of at least `min_wall` to each other, to the cutout of the keys, to the battery recess and to the edge of the plate. This is checked in the layer where both parts have a hole: the bottom plate for the head recesses and the bumper pockets, the keywell for the insert pilots and the magnet pockets. It is checked for the full variant. The compact variant is for test prints and is not placed by hand.
R-32: A magnet pocket opens into the cavity and ends under a skin. The skin is at least `magnet_skin` thick and the top face of the keywell has no hole over a magnet. The pocket holds two stacked magnets and the spacer disc.
R-33: A spacer disc fills the pocket between the keyplate and the magnets. It leaves `magnet_spacer_gap` free and is narrower than the pocket, so that it falls out by itself. The keyplate carries the whole disc.

R-34: Each half carries one emblem in the straight outer wall in front of the lowest key of the pinky column, left of the trackpad notch. The left half carries the symbol and the right half carries the invader. The emblem is a pocket in the wall, never in the top face or the bed face. It lies clear of the rim chamfers and ends its rows on layer boundaries, counted from the bed. The pocket is `engraving_lines` lines deep. The pixels of the invader are `engraving_gap` apart. The roof of every pocket slopes at 45 degrees when `engraving_roof_slope` is set, so no pocket needs a bridge or support. The wall behind a pocket keeps at least `min_wall`.
R-35: In the transport position the right half lies upside down on the left half. The tops of the two keywells meet at z = above_z. No part of one half overlaps a part of the other half. This covers the keycaps and all fixtures.

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

## Wiring

The full variant has a hand-wired matrix: one through-hole diode per key, enamelled wire in trenches.
The wiring is in `ergogen/wave.wiring.yaml`. A person edits this file with the visual editor (`task wiring-editor`) or by hand. The build reads it. The syntax is in `docs/WIRING.md`.
`task check` tests the file.
The compact variant has no wiring.

R-36: `ergogen/wave.wiring.yaml` passes every check of `duality_wave.wiring.check` for the current layout, dimensions, diode and print profile. Open the editor after a change of the layout, the dimensions, the diode or the print profile. The file holds plain coordinates of the blank: a vertex is `[x, y]` or `[x, y, r]`, the channel is two corners, a notch is `{side, y}`. The coordinates do not follow the layout. The check reports each trench end that misses its terminal. A mistake in the file stops the build with a message that names the half, the net and the trench. The check lists the diodes whose anode lead crosses the cutout of the switch (they need a sleeve).
R-37: Every key has a diode pocket. The pocket opens from the underside of the keyplate into the cutout of its key and continues in the top face of the bottom plate. The two plates share the depth of the diode body. A wall of at least `MIN_WALL` surrounds the pocket.
R-38: The matrix has one net per column and one per row. The thumb keys form the last row. Each thumb belongs to its own column. The file has trenches for every net.
R-39: The trenches of a net join every terminal of the net, and the net ends in the channel. A terminal is the contact p1 of a column or the cathode end of a diode. The trenches lie in the underside of the keyplate. A trench keeps a wall of at least `MIN_WALL` to the outline, the screws, the pockets and the power switch. Near its own terminal, a trench ends inside the pocket that holds the terminal, so only the wall to that one pocket does not count there.
R-40: No wire comes closer to a contact, a centre post or a lead tip of another net than its keep-out radius. Wires of different nets do not run side by side closer than 0.5 mm.
R-41: Two trenches in the top face of the keyplate lead from two pins of the power switch to the XIAO window. The pins reach the top face through the pin zone, which is a cut through the keyplate. The trenches keep clear of the key cutouts, the pockets and the body of the switch.
R-42: The underside of the keyplate has one channel. It is a shallow recess as deep as a trench. It runs along the top edge of the keyplate from the inner column to the XIAO pocket and opens into the pocket. The wires of all nets end in the channel. The channel keeps a wall of at least `MIN_WALL` to the outline, the screws, the diode pockets and the power switch.
R-43: The visual wiring editor (`task wiring-editor`) shows both halves of `ergogen/wave.wiring.yaml` in the browser. It moves, adds and deletes vertices and whole trenches, moves the channel and moves the diode notches within the range that keeps the pocket along the wall of the cutout. A button removes the vertices that do nothing, only when pressed. The editor marks the diodes that need a sleeve. It runs the checks of R-36 to R-42 on every change. It writes the file only if the text it writes reads back as the same vertices and the same channel as the editor shows. It keeps the old file in `build/`. The editor serves only the local computer and refuses requests from other pages.

## Debug mode

R-07: A build without debug builds no accessories and pushes nothing to the viewer. It builds the same parts as a build with debug.

## Performance

The limits below are for the development machine. Set `WAVE_PERF_FACTOR` to scale all of them.
The limits are about 2.5 times the measured time. Tighten them after a speed-up step.

R-10: A build of the full variant (both halves) takes at most 12 s.
R-11: A build of the compact variant takes at most 3 s.
R-12: A stage of the build stays under its limit: keywell 1.2 s, keyplate 1.6 s, bottom 0.7 s, each finish stage 5 s. A finish stage cuts the pockets and the trenches of the wiring. An outline with one inner outline takes at most 0.4 s.
