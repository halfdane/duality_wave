# Wiring the matrix

This file tells you how to wire one half.
The plan is in `ergogen/wave.wiring.yaml`.
You edit this file in the visual editor (see below).
Run `task check` to test it.
The file holds plain coordinates.
The vertices do not follow the layout.
After you change the layout, the dimensions or the diode, open the editor.
It reports each trench end that misses its terminal.
Then you move these vertices in the editor.

## The visual editor

Run `task wiring-editor`.
It starts a small server on your computer and opens the editor in the browser.
Use `--port`, `--no-browser` and `--file` with `python scripts/wiring_editor.py` to change the defaults.
The editor reads and writes `ergogen/wave.wiring.yaml`.

The picture shows one half at a time. Switch between Left and Right, and between Underside and Top.
The picture of the right half shows the half as it is built: the blank is mirrored.
The underside is seen from below, so it is mirrored too.
The checks run after every change. The list on the right names each problem. Click it to see where it is.
The list of walls shows the thinnest walls of the half.

| Tool | Use |
| --- | --- |
| Edit (key 1) | Drag a vertex. Drag a line sideways. Double-click a line to add a vertex. Press Delete, or right-click a vertex, to delete it. Drag the edges and corners of the channel. Set the radius of a corner in the panel. |
| Add trench (key 2) | Click a terminal or a trench of the net to start. Click to add vertices. Press Enter or double-click to end. |
| Move diodes (key 3) | Drag a diode body along its key. It jumps to the other side of the key at the middle. The row vertex at its cathode follows. The diode stops where its pocket would leave the wall of the cutout. |
| Tidy | Remove the vertices of this half that do nothing: a vertex on top of a neighbour, and a vertex on the straight line between its neighbours. The ends of a trench stay. Tidy runs only when you press it. Undo takes it back. The status bar shows how many vertices it removed. |

A square vertex is fixed to a terminal.
Shift keeps a line straight. Alt turns the grid and the snapping off.
Ctrl+Z undoes and Ctrl+Shift+Z redoes. Ctrl+S saves.

The list Sleeves shows the diodes of the half whose anode lead crosses the cutout of its switch.
The picture marks their leads in blue.
Put a sleeve on each of these leads.
The list changes when you move a diode to the other side of its key.

Save writes the file.
The editor checks first that the file reads back as the same vertices.
It copies the old file to `build/wave.wiring.backup.yaml`.
Comments between the lines of the file are lost on save. The comment at the top stays.
Both halves share one channel. The file has a channel for both halves at the top, not one for each half.

## The wiring file

All coordinates are in mm, in the frame of the blank (the left half).
The file always uses the frame of the blank, also for the right half.
In the pictures, +X points to the left in the underside of the left half and in the top of the right half.
The file has the diode, the channel, and one section per half.

A trench is a list of vertices.
A vertex is `[x, y]` or `[x, y, r]`.
Add `r` to set the radius of its corner.
Without `r` the corner gets the largest radius up to 1.5 mm that fits.
A corner with `r: 0` is sharp.
The first and the last vertex of a trench are sharp.
The editor writes 3 decimals.

The channel is two opposite corners, `from` and `to`, written as `[x, y]`.

A notch is `{side: -1, y: -1.5}`.
`side` is -1 for the -X side of the key and +1 for the other side.
`y` is the offset of the diode centre along the Y axis of the key, in mm.

The editor knows named points of the plate, for example `matrix_ring_top.p1` and `matrix_ring_top.cathode`.
The editor snaps to the contacts, the cathode ends and the pins of the power switch.
The file does not use names.
A mistake in the file stops the check with a message.
The message gives the half, the net, the trench and the vertex.

## Parts

- One through-hole diode per key. The assumed size is 2.0 mm by 4.2 mm with 0.5 mm leads. These are upper limits.
- Enamel wire, 0.3 mm.
- Solder only on the keyplate. Fit the bottom plate after you solder.

## Order of work

1. Put each diode in its pocket. The pocket is beside the cutout of the key, on the underside of the keyplate.
2. Put the black band (the cathode) at the end that points away from the contact p2.
3. Bend the anode lead to the contact p2 of the switch. Solder it.
4. Lay the row wire in its trench. Solder it to the cathode lead of each diode in the row.
5. Lay the column wire in its trench. Solder it to the contact p1 of each switch in the column.
6. Lead all wires along the channel to the XIAO pocket.
7. Solder each wire to the pad of the XIAO.

The thumb keys form the last row (row 4).
Some diodes have a bare anode lead that crosses the cutout. Put a sleeve on these leads.
The editor (list Sleeves) shows which diodes these are.

## Channel

The channel is one wide recess in the underside of the keyplate.
It runs along the top edge, from the inner column to the XIAO pocket.
It is as deep as a trench.
Every trench of the matrix ends in the channel.
The wires of the nets lie side by side in the channel.
Keep them apart with a drop of glue or tape.

Column 1 is the column with the highest X in the left half.
Row 1 is the top row.
You choose the pad for each wire.
Set the pins in the ZMK overlay to match (col2row: the diodes point from the column to the row).

## Power switch

The battery wires go from the battery to the XIAO by hand.
They do not use the keyplate.

Two trenches in the top face of the keyplate lead from the power switch to the XIAO window.
The pins of the switch reach the top face through the pin zone.
The pin zone is a cut through the keyplate.

The plan assumes this mapping:

| Wire | Pin of the switch | Pad of the XIAO |
| --- | --- | --- |
| power 1 | the pin with the lowest Y in the top row of pins | D3 (BAT+) |
| power 2 | the next pin in the top row | D2 |

Check this against your switch before you solder.

## Open points

- The model does not cut the drop from the channel to a pad. Do this by hand.
- A trench reaches about 0.2 mm into the XIAO pocket and into the XIAO window.
- The diode size is an assumption. Measure your diodes. Change `Diode` in `models/diode.py`, then move the notches in the wiring file until the editor shows no problem.
