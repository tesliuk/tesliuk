# Controller pin mapping

The PCB uses the **Pro Micro** footprint, so the netlist names pins by the
labels silkscreened on a Pro Micro. Your RP2040 controller exposes those same
physical positions as GPIO numbers.

## The matrix

5 columns × 5 rows per half, 23 of the 25 cells used. `COL2ROW` diode
direction (diode cathode toward the row).

| Net | Pro Micro pin | RP2040 GPIO | Carries |
|-----|---------------|-------------|---------|
| R1 | 2 | GP2 | bottom row |
| R2 | 3 | GP3 | home row |
| R3 | 4 | GP4 | top row |
| R4 | 5 | GP5 | number row |
| R5 | 6 | GP6 | thumb cluster |
| C1 | 7 | GP7 | pinky column + thumb t1 |
| C2 | 8 | GP8 | ring column + thumb t2 |
| C3 | 9 | GP9 | middle column + thumb t3 |
| C4 | A0 (18) | GP26 | index column + thumb t4 |
| C5 | A1 (19) | GP27 | inner column + thumb t5 |
| DATA | TXO (1) | GP0 | split serial link over TRRS |

Plus `VCC`, `GND` and `RST` (reset button to ground).

## Why these pins specifically

Pro Micro-footprint RP2040 boards — Sea-Picro, Elite-Pi, 0xCB Helios — all map
silk pins **2–9 to GP2–GP9** and **A0/A1 to GP26/GP27**. That correspondence is
consistent across every one of them.

Where those boards *do* differ is the block silkscreened 10, 14, 15 and 16;
different vendors wire those to different GPIOs. This design deliberately
avoids all four, so the table above should hold for whichever board you buy.

**Still verify it.** Pull up your controller's pinout diagram and confirm the
GPIO next to silk pins 2–9 and A0/A1 before you flash. If yours differs, edit
`PIN_ROWS` / `PIN_COLS` / `PIN_SERIAL` at the top of `firmware/gen_qmk.py` and
re-run `make firmware` — do not hand-edit `keyboard.json`, it is generated.

## The matrix cell map

Rows 0–4 are the left half, 5–9 the right. Columns 0–4 are C1–C5.

|        | C1 (pinky) | C2 (ring) | C3 (middle) | C4 (index) | C5 (inner) |
|--------|-----------|-----------|-------------|------------|------------|
| R1 bottom | *unused* | X | C | V | B |
| R2 home   | A | S | D | F | G |
| R3 top    | Q | W | E | R | T |
| R4 number | *unused* | 1 | 2 | 3 | 4 |
| R5 thumb  | t1 | t2 | t3 | t4 | t5 |

The two unused cells are the pinky's bottom and number positions — exactly the
keys the layout deliberately omits. If you later decide you do want a third
pinky key, the cell is already there: delete the `bottom.skip: true` line under
the pinky column in `src/config.yaml`, rebuild, and re-run `make check`.

## If every key reports in the wrong place

Two failure modes, both easy:

- **Rows and columns swapped** — every key types the wrong character in a
  regular pattern. Swap `cols` and `rows` in `gen_qmk.py`.
- **Nothing registers, or keys ghost in pairs** — diode direction is wrong.
  Change `diode_direction` to `ROW2COL` in `gen_qmk.py` and rebuild.

Use `qmk console` with `#define CONSOLE_ENABLE` to see raw matrix positions
while you debug.
