# pinkyless46

A 46-key column-staggered split keyboard, designed around not using your
pinkies. Kailh Choc v1 low-profile, hotswap, wired, RP2040 + QMK.

![plate](build/case/plate_left.png)

## The layout

23 keys per half:

```
 pinky  ring   mid   idx  inner
   ·      O     O     O     O                  number row
   O      O     O     O     O                  top row
   O      O     O     O     O                  home row
   ·      O     O     O     O                  bottom row

                            O     O     O      thumb arc
                               O     O         thumb island
```

The thumb cluster starts where the finger matrix ends: the nearest thumb key
sits directly below the innermost finger column, and the cluster runs inboard
from there rather than being tucked back underneath the fingers.

The pinky gets **two keys only** — top and home, the two it can reach without
the hand moving. Everything a pinky normally carries (Z, Shift, Ctrl, Tab,
Esc, Enter, Backspace) moved to the thumbs and to home-row mods.

Five thumb keys per half, in two groups: a 3-key arc that follows the thumb's
natural sweep inboard and down, and a 2-key island tucked below it for the
keys you press less often. The furthest is 42 mm from the thumb home key,
inside the ~45 mm a relaxed thumb can sweep without the hand leaving position.

Column stagger follows finger length: middle furthest forward, then ring,
index, pinky, and the inner column pulled *back* because the index reaches
inward and down, not inward and forward.

Board: **136 × 163 mm** per half. Case: **8.9 mm** tall before switches.
The width comes from the thumb cluster reaching ~37 mm inboard of the matrix.

## What is in here

```
src/config.yaml        the single source of truth - layout, nets, footprints
src/check_*.py         five verification passes, run by `make check`
src/find_mounts.py     searches the board for valid screw positions
case/gen_case.py       plate + tray STLs, generated from the same key positions
firmware/gen_qmk.py    generates keyboard.json from the same key positions
firmware/pinkyless46/  QMK keymap
build/                 generated outputs (committed - they are the deliverable)
docs/ORDERING.md       how to get it made with almost no soldering
docs/PIN_MAPPING.md    controller pins, matrix cells, debugging a bad matrix
```

Everything downstream — PCB, case, firmware — is derived from `src/config.yaml`.
Change a dimension there, run `make`, and the board, the STLs and the keymap
all follow. Nothing is hand-maintained in two places.

## Build it

```sh
make deps      # npm install + python deps
make           # build, check, case, firmware
```

`make check` runs five passes and fails loudly:

| Check | Catches |
|-------|---------|
| `layout` | keycaps or switch bodies colliding; thumb keys out of reach |
| `outline` | board in disconnected pieces; stray voids; missing screw holes |
| `matrix` | miswired switch/diode; **two keys sharing a matrix cell** |
| `fit` | components or screws hanging off the board edge |
| `shorts` | **pads on different nets overlapping**; copper clearance |

These are not decoration. Building this design, they caught the thumb cluster
coming out as four disconnected board fragments, and seven genuine short
circuits where the controller and TRRS jack overlapped the number-row
switches. Both would have produced dead boards at full cost.

## Before you order boards

**The PCB is placed and netlisted but not routed.** Ergogen does not route
traces. Open the board in KiCad, route the matrix, pour ground, run DRC, and
plot gerbers. Full instructions in [docs/ORDERING.md](docs/ORDERING.md) —
please read it before spending money.

## Printing the case

Four STLs in `build/case/`: `plate_left`, `plate_right`, `tray_left`,
`tray_right`. All watertight, all flat-bottomed, no supports needed.

- **Plate** — 1.3 mm, prints on its back. Choc switches clip into the 13.8 mm
  cutouts. Print in PETG or ABS if you can; 1.3 mm of PLA is a little brittle
  around the cutouts.
- **Tray** — 0.2 mm layers, 3 perimeters, 20 % infill.

Stack, from the tray floor: 2 mm floor, 4 mm gap for the hotswap sockets,
1.6 mm PCB, 1.3 mm plate. Six M2 × 6 mm self-tapping screws go down through
the plate and PCB into the printed bosses.

The controller and TRRS jack sit *above* the plate, through the opening at the
top of the board — the controller is socketed on headers, so it stands proud.
That is normal for a DIY split and keeps the USB port and jack accessible
without any wall cutouts.

## Adjusting it

The pinky rows, thumb positions and column stagger are all named values at the
top of `src/config.yaml`. Three things worth knowing before you edit:

- Ergogen's `stagger` is **cumulative**, not absolute. The config works around
  this by writing each column as `st_this - st_previous`, so you can edit the
  absolute numbers and the deltas take care of themselves.
- The thumb cluster is anchored to `matrix_inner_bottom` with t1 at an
  x-shift of exactly 0, so the nearest thumb key stays aligned with the last
  finger column and the cluster always begins where the matrix ends. Add or
  remove a finger column and the cluster follows. To slide the whole cluster,
  change that one x-shift rather than editing all five.
- After moving anything, run `make mounts` to re-derive screw positions and
  paste the result back into the `mounts` zone. Screw positions depend on the
  layout, and a screw that lands in a switch cutout leaves that switch with
  nothing to clip into.

Then `make check`. Do not order boards from a red tree.
