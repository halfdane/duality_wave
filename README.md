# Duality Wave

How **low profile** can your case really get with **ChocV1 switches**? While still being **wireless first** and with a **reset button** accessible without opening the case?  **Magnetically sandwiching** the halves together for transport?

Turns out pretty darn low: **14mm** from table to the top of the keycap, and the case itself is just **12.8mm**.
In comparison, most low profile cases with bumpers and keycaps usually end up around 15.5 mm to 17 mm.
So if you're keen on the lowest profile possible with ChocV1 switches, this might be your chance.

Oh, and if you don't like the layout, just bring your own [ergogen](https://ergogen.xyz/) file.

---

**Introducing the Duality Wave**, a split, hand-wired, ultra-low-profile keyboard with a 3D-printed case:
- It's tiny: about 113 x 97 x 12.8 mm per half
- Agressive stagger, and a bit of pinkie-splay
- 34 keys: sports a 3x5+2 layout using ChocV1 switches
- Wireless first: thanks to the Seeed XIAO nRF52840 and [ZMK](https://zmk.dev)
- Battery saving: if the already impressive power saving mechanisms of ZMK aren't enough for you, use the integrated sliding power switch to turn it completely off
- Handwired: no need to buy or order a PCB; no fiddly soldering with too small pads
- XIAO can be easily reset: A flexible lever in the bottom plate presses the reset button
- Rock solid: rubber bumpers keep it from sliding around on the table
- Easy transport: Halves snap together magnetically
- Safe transport: Protective walls around the keys 
- Optimized for [Pelicram's Hattara keycaps](https://github.com/Pelicram/Hattara-Printable-Low-Profile-Keycaps) and easily adjustable for your favorite ones
- Based on an [ergogen](https://ergogen.xyz/) layout I made a few years ago for the Duality Particle, so the layout can be change quite easily
- The case is generated from python code (build123d)

![The two halves of the keyboard](docs/images/hero.jpg)

## Status

The case design is in progress, but nobody has printed or assembled the full case yet.
I'm currently in the process of adjusting clearances, and there is no firmware yet.
Just in case you didn't realize: **The images are renders, not photos.**

## Sandwiched transport position
8 magnets hold the halves in place for easy and safe transportation. The rised walls are surrounding the keys like a protective wall.

![The halves snap together for safe transport](docs/images/transport.jpg)

## Other layouts

The case generator also works with other key layouts, for example Corne, Absolem or layouts with extra rows or columns as well as double-rowed thumb clusters. See [docs/LAYOUTS.md](docs/LAYOUTS.md).

![A large layout with extra rows and a big thumb cluster](docs/images/layouts/big_thumb_cluster.jpg)

## Bill of materials

Quantities are for both halves.

- 34 Kailh Choc v1 switches
- 34 low-profile keycaps with Choc spacing (17.45 x 16.45 mm), for example [Hattara](https://github.com/Pelicram/Hattara-Printable-Low-Profile-Keycaps)
- 2 Seeed XIAO nRF52840
- 2 LiPo batteries, 31 x 17 x 6 mm
- 2 slide power switches, 9 x 3.4 x 4 mm
- 16 magnets, 10 mm diameter, 2 mm thick (two stacked in each of 8 pockets)
- 12 M2 heat-set inserts, 3.5 mm outer diameter, 2 mm long
- 12 low-profile M2 screws, 6 mm long
- 10 rubber bumpers, 8 mm diameter
- 34 diodes, one per key
- 0.1 mm to 0.3 mm enamelled wire

All of that fits into the tiny case:

![See-through shell shows how all features are crammed into a tiny case](docs/images/ghost.jpg)

## Printing

Each half has three printed parts.
The magnet spacers are a fourth kind of part, and both halves share them.

- `keywell` is the top shell.
- `keyplate` holds the switches.
- `bottom` closes the case.
- `magnet_spacer` is a small disc that push the magnets against the top. Print 8 of them, 4 for each half.

If you own a Bambu Lab a1 mini printer with PLA, it's your lucky day: the settings in the repository are optimized for that, otherwise you probably need to adjust the clearances etc.: See [Fit Calibration](#fit-calibration)

If you use `nix`, the dependencies are prepared in the devshell created by the `flake.nix`.  
Otherwise you need `python 3.13`,  `uv` and [`task`](https://taskfile.dev/) and install the dependencies with `uv sync --frozen` .

After the [fit calibration](#fit-calibration) (if necessary):

- Run `task export-case` to create the STEP files for all parts
- Each STEP file is in its print orientation, so you do not flip it in the slicer.
- The keywell and the keyplate print upside down compared to the assembled case.

![Exploded view of one half](docs/images/exploded.jpg)

## Assembly

1. Press an M2 heat-set insert into each of the six holes of the keywell. Press each insert in until it is flush with the keywell face.
2. Lay the keywell upside down. Glue two magnets on top of each other and put each pair into a magnet pocket from below. A thin skin of the keywell covers the magnets on the outside. See the section about polarity. Put a spacer disc on each pair of magnets.
3. Cut the posts from the Choc. No really: in order to keep the bottom plate stable, the amount of holes and cutouts need to be reduced. That's why only the center post is extending all the way through it. The electrical contacts are cut to 2mm length, and all other posts are removed completely.
3. Wire the switches, the diodes, the XIAO, the power switch and the battery. Wiring is your choice. The keyplate has channels for the wire and the bottom plate has recesses for the switch pins and the diodes.  
If you don't know what you're doing, these are good starting points (but honestly, maybe start with an easier handwire first - the space restrictions make this build a challenge):  
    - [A modern handwiring guide - stronger, cleaner, easier](https://geekhack.org/index.php?topic=87689.0)
    - [QMK Hand-Wiring Guide](https://docs.qmk.fm/hand_wire)
    - [Instructables: Building a Handwired Keyboard](https://www.instructables.com/Building-a-Handwired-Keyboard/)
    - [Joe Scotto: How to Build a Handwired Keyboard](https://www.youtube.com/watch?v=hjml-K-pV4E)
4. Put the keyplate into the keywell. It holds the spacers and the magnets. Then put the bottom plate on top. Fasten the six M2 screws from the bottom.
5. Put the rubber bumpers into their recesses.

The halves are almost perfect mirror images of each other.

### Magnet polarity

Only the relative polarity matters, so you can place the magnets in one half however you want. Then use a magnetized tool to make sure the magnets in the other half face the opposite way.
Bring the halves together before you fit the keyplate: if you did something wrong, the magnets will repel each other and be pushed out of their pockets. That gives you the opportunity to try again until you get the polarity right.

![Underside of both halves](docs/images/bottom.jpg)

## Fit calibration

All fit constants live in [`PrintProfile`](src/duality_wave/models/print_profile.py).
Design and layout constants live in [`CaseDimensions`](src/duality_wave/case_dimensions.py).
The defaults match a Bambu Lab a1 mini printer with PLA.
Change the profile for every new printer, material or slicer.

1. Run `task export-coupon`.
2. Print all coupon stl-files (`build/coupons/*.stl`) with the same settings as the final case.
3. Find the tightest fit that still goes together by hand.
4. Copy the winning values into a [`PrintProfile`](src/duality_wave/models/print_profile.py).

The coupons are built in their real print orientation.
The plates fit the usable area of a Bambu Lab A1 mini: 170 x 170 mm of the 180 x 180 mm bed.

| Coupon | Question |
| --- | --- |
| A, switch plate | Which switch cutout size is right? Does corner relief help? |
| B, plate in cavity | Which plate clearance is right? Try each plate both ways round. |
| C, insert pilots | Which insert pilot size is right? Press an insert into each hole. |
| D, pockets | Which XIAO pocket clearance is right? Which battery pocket clearance is right? Test the real battery. |
| E, magnet pockets | Which magnet pocket size is right? The label is the pocket diameter. Push a stack of two magnets into each pocket. The pull through two skins is the pull between the two halves. Choose the thickest skin that still holds the halves as firmly as you want. |
| E, skin and mate | How thick can the skin over the magnets be? The label is the skin in mm. Put a stack of two magnets in a pocket, then hold a loose magnet on the skin side. |
| F, trenches | Which trench width and depth is right for your enamelled wire? Rows are the width in mm, columns the depth. Press a wire into each trench. |
| G, diode pockets | How much slack does the diode pocket need? The label is the slack in mm (the pocket is that much wider, twice as much longer and that much deeper than the body). Lay a real diode into each pocket. |
| Emblem depth | Which depth and roof design work best for the emblems debossed into the side walls? The label under an invader is its pixel gap. The label under the symbol is the depth in mm and the roof (45 is sloped). Choose the shallowest depth that you can still read, and the roof and gap that print without strings. |

To change the code, read `CONTRIBUTING.md`.

## License and credits

The code is licensed under the GPL-3.0. See `LICENSE`.

