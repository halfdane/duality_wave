# Proposal: alignment pin for the transport pose

Status: idea, not started.
Wait for the magnet tests with the coupons before you start.

## Problem

In the transport pose the right half lies flipped on the left half.
The magnets hold the halves together.
The magnets resist a straight pull well.
They resist sliding much less, because sliding is held by friction only.
A hard shock in a backpack can shift the halves against each other.

## Idea

Put one pin between the halves.
The pin blocks all sliding.
The halves can still turn about the pin.
This is also the way to open the halves: turn, then lift.

Both halves get a blind hole in the key-side face of the keywell.
The hole opens towards the print bed.
The keywell prints upside down, so the hole needs no support.
Its roof is a short bridge.

A rod is glued into the hole of one half.
The rod stands out of the face and enters the hole of the other half.

## Why not other solutions

- A pin or lip printed on the face is not possible.
  The face lies on the print bed.
- A rail blocks only one direction, and it needs more room.
- A second magnet stack has little room, and it adds only about 25 percent of pull.
- Rubber pads raise the friction, but they widen the magnet gap.

## Design

### Location

Use the point below the bottom key of the ring column.
In the case frame of the left half it is at about x = 16 mm and y = -0.6 mm.
The right half gets the mirrored point, so the two holes meet in the transport pose.

At this point:

- The free material is about 6 mm to the front edge and to the cutout of the keys.
- The nearest magnet is about 20 mm away.
- The nearest insert pilot is about 29 mm away.
- The slab above the keyplate is 8.2 mm thick.
- The keyplate and the bottom plate are not touched.
- The other three magnets are 50 mm or more away, so the turning torque stays large.

The check was done in 2D only.
It covered the cutout, the outer edge, the magnet pockets and the insert pilots.
Check the emblem and the rim chamfer again when you build it.

### Pin

- A rod of 3 mm diameter.
- Use brass, stainless steel 304 or 316, or carbon.
  Do not use plain steel.
  Plain steel is pulled by the magnets.
- Length about 7 mm.

### Holes

- The same hole in both halves.
  This keeps the right half the mirror of the left half (R-02).
- Diameter: pin diameter plus 2 times `pin_clearance`.
  Start with 0.15 mm per side.
- Depth: 3.5 mm, snapped to whole layers (R-24).
- The material around the hole is at least `min_wall` thick.
- Use `mouth_chamfer` on the mouth of the hole.
  Elephant foot narrows the mouth otherwise.

### Fit

The hole has a sliding fit in both halves.
Glue the rod into one half with epoxy or CA glue.
The glue fills the gap of about 0.15 mm.
A press fit in a printed hole is not reliable.
Small holes print 0.1 to 0.2 mm too small, and the error varies.

## Work to do

1. Add `pin_clearance` to `PrintProfile`.
2. Add the pin dimensions and the pin position to `CaseDimensions`.
3. Cut the blind hole in the keywell from the face on the print bed.
4. Add coupon H to the hardware plate.
   It holds holes from 3.0 to 3.4 mm in steps of 0.05 mm.
   Test them with the real rod.
5. Add a requirement to `docs/SPEC.md` and tests.
   - Both halves have the hole at mirrored points.
   - The hole keeps `min_wall` to all other holes (extend R-31).
   - The STEP files still read back as the same solid (R-45).
6. Add a build step to the README: glue the rod into one half.

## Open questions

- Is a 3 mm rod the right size?
- How far may the pin stand out of the face?
  About 3 mm is planned.
  The pin sits at the front edge of the key side, so check that it does not touch the wrist.
- Does a decorative cap on the empty hole look better than the open hole?
- Which half gets the glued rod?

## Risks

- The pin blocks sliding, but not turning.
  Turning is still held by magnet friction only.
  Measure the turning force of the halves before you rely on it.
- The pin stands out of the face when you use the keyboard.
- The empty hole in the other half is visible.
