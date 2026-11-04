# duality_wave

Parametric case generator for a hand-wired, 17-key split keyboard.
The case is modelled with build123d.
The layout comes from an ergogen config.
This repository only contains the case.
There is no PCB and no firmware here.
The keyboard is wired by hand with 0.1 mm to 0.2 mm enamelled wire.
The case is the descendant of the duality_particle.
Some names, for example `cirque_recess_*` in `models/outline.py`, still show that origin.

## Setup

Run `direnv allow` or `nix develop`.
The dev shell installs the Python dependencies with `uv`.

## Tasks

| Command | What it does |
| --- | --- |
| `task viewer` | Starts the OCP CAD viewer on port 3939. |
| `task build` | Builds the case with `duality_wave.py` and exports STEP files. |
| `task snapfit` | Builds the compact variant with `snap_fit.py`. |
| `task coupons` | Exports `coupons.stl`, the fit calibration coupons. |
| `task test` | Runs the unit tests. This takes about a minute. |

The exported `*.step` and `*.stl` files are not tracked by git.

## Parts

Each half has three printed parts.

- `keywell` is the top shell. It is printed upside down.
- `keyplate` holds the switches. It is printed upside down.
- `bottom` closes the case. It is printed right side up.

The keyplate and the bottom plate sit inside the keywell cavity.
Six M2 screws pull them against the keywell.
Each screw runs into an M2 heat-set insert in the keywell.
Press each insert in until it is flush with the keywell face at z=0.
The right half is the mirror image of the left half.

## Bill of materials

- 34 Kailh Choc v1 switches
- 34 keycaps (the model uses `models/hattara.step`)
- 2 Seeed XIAO nRF52840
- 2 LiPo battery, 31 x 17 x 6 mm
- 2 slide power switch, 9 x 3.4 x 4 mm
- 16 magnets, 5 x 2 mm (two stacked in each of the 4 recesses)
- 12 M2 heat-set inserts, 3.5 mm outer diameter, 2 mm long
- 12 low-profile M2 screws, 8 mm long
- 2 weights, 22.9 x 12 x 4.4 mm
- 10 rubber bumpers, 8 mm diameter
- 2 pin, 1.2 mm diameter, 13 mm long
- 34 diode per key and 
- enamelled wire

## Magnet polarity

Only the relative polarity matters.
Place the magnets in one half however you want.
Use a magnetized tool to make sure the magnets in the other half face the opposite way.

You cannot dry-fit the halves, because the magnets pull out of their recesses.

## Fit and print settings

All fit constants live in `PrintProfile` in `models/print_profile.py`.
`CaseDimensions` carries one profile in `print_profile`.
The defaults match a Bambu Lab printer with PLA.
Change the profile for every new printer, material or slicer.

1. Run `task coupons`.
2. Print `coupons.stl` with the same settings as the final case.
3. Find the tightest fit that still goes together by hand.
4. Copy the winning values into a `PrintProfile`.

The coupons are built in their real print orientation.
They reuse the cutters from `models/features.py`.

| Coupon | Question |
| --- | --- |
| A, switch plate | Which switch cutout size is right? Does corner relief help? |
| B, plate in cavity | Which plate clearance is right? Try each plate both ways round. |
| C, round holes | Which magnet recess size and which insert pilot size is right? |
| D, pockets | Which weight pocket clearance is right? Does the battery fit? |

The case counters elephant foot with chamfers on the side that faces the print bed.
`plate_bed_chamfer` sets the chamfer on the plate faces.
`mouth_chamfer` sets the chamfer where switch cutouts and magnet recesses open towards the bed.
Sanding the plate edges along the z axis removes the layer ridges that rub on insertion.

## Layout

- `duality_wave.py` holds the case dimensions and the main build.
- `wave_generator.py` builds the three parts and the accessories.
- `snap_fit.py` is a compact variant for test prints. The snap-fit feature itself was removed.
- `ergogen/wave.yml` and `ergogen/snap_fit.yml` define the key layouts.
- `ergogen.py` is a small Python port of the ergogen layout code.
- `models/` holds the part models and the outline.
- `models/features.py` holds the cutters that the case and the coupons share.
- `coupons.py` builds the calibration coupons.
- `part_packing.py` packs the parts with sprues for a JLC3DP order.

