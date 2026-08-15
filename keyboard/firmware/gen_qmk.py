#!/usr/bin/env python3
"""
Generate the QMK keyboard.json from the same key positions as the PCB.

Writing the matrix by hand is how keymaps end up subtly wrong - one
transposed [row, col] and a key types the wrong character with no clue why.
Everything here is derived from points.yaml and the matrix nets already
verified by src/check_matrix.py, so the firmware cannot disagree with the
board.

Key order in LAYOUT reads like the physical board: number row first, then
top, home, bottom, thumbs; within each row, left half left-to-right followed
by right half left-to-right.
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POINTS = ROOT / "build" / "points" / "points.yaml"
OUT = Path(__file__).resolve().parent / "pinkyless48" / "keyboard.json"

# Physical top-to-bottom order of the matrix rows.
ROW_ORDER = ["R4", "R3", "R2", "R1", "R5"]
ROW_LABEL = {"R4": "number", "R3": "top", "R2": "home",
             "R1": "bottom", "R5": "thumb"}
COLS = ["C1", "C2", "C3", "C4", "C5"]

ROWS_PER_HALF = 5

# See docs/PIN_MAPPING.md. Pro Micro silk 2-9 -> GP2-GP9 and A0/A1 ->
# GP26/GP27 on every Pro Micro-footprint RP2040 board.
PIN_ROWS = ["GP2", "GP3", "GP4", "GP5", "GP6"]     # R1..R5
PIN_COLS = ["GP7", "GP8", "GP9", "GP26", "GP27"]   # C1..C5
PIN_SERIAL = "GP0"


def main():
    if not POINTS.exists():
        print(f"error: {POINTS} not found - run the ergogen build first")
        return 1

    raw = yaml.safe_load(POINTS.read_text())
    keys = []
    for name, p in raw.items():
        meta = p.get("meta", {})
        if "column_net" not in meta or "row_net" not in meta:
            continue
        keys.append({
            "name": name,
            "right": name.startswith("mirror_"),
            "x": float(p["x"]),
            "y": float(p["y"]),
            "col": meta["column_net"],
            "row": meta["row_net"],
        })

    if not keys:
        print("error: no keys with matrix nets found")
        return 1

    minx = min(k["x"] for k in keys)
    maxy = max(k["y"] for k in keys)

    layout = []
    for rn in ROW_ORDER:
        for is_right in (False, True):
            row_keys = [k for k in keys if k["row"] == rn and k["right"] == is_right]
            if rn == "R5":
                # The thumb cluster is two sub-rows (arc t1-t3, island t4-t5),
                # so sorting purely by x interleaves them and makes keymap.c
                # unreadable. Order by column instead - that is arc then
                # island - and reverse it on the right half so the keymap
                # still reads left-to-right across the whole board.
                ordered = sorted(row_keys, key=lambda k: COLS.index(k["col"]),
                                 reverse=is_right)
            else:
                ordered = sorted(row_keys, key=lambda k: k["x"])
            for k in ordered:
                r = ROW_ORDER.index(rn)
                # matrix row index follows R1..R5, not the visual order
                mrow = int(rn[1:]) - 1 + (ROWS_PER_HALF if is_right else 0)
                mcol = COLS.index(k["col"])
                layout.append({
                    "matrix": [mrow, mcol],
                    "x": round((k["x"] - minx) / 18.0, 2),
                    "y": round((maxy - k["y"]) / 17.0, 2),
                })

    data = {
        "manufacturer": "tesliuk",
        "keyboard_name": "pinkyless48",
        "maintainer": "tesliuk",
        "processor": "RP2040",
        "bootloader": "rp2040",
        "url": "",
        "usb": {"vid": "0xFEED", "pid": "0x0046", "device_version": "0.0.1"},
        "diode_direction": "COL2ROW",
        "matrix_pins": {"cols": PIN_COLS, "rows": PIN_ROWS},
        "split": {
            "enabled": True,
            "soft_serial_pin": PIN_SERIAL,
            "bootmagic": {"matrix": [5, 0]},
        },
        "features": {
            "bootmagic": True,
            "extrakey": True,
            "mousekey": True,
            "nkro": True,
            "console": False,
            "command": False,
        },
        "layouts": {"LAYOUT": {"layout": layout}},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")

    print(f"wrote {OUT.relative_to(ROOT)} with {len(layout)} keys")
    per_row = {}
    for rn in ROW_ORDER:
        per_row[ROW_LABEL[rn]] = sum(1 for k in keys if k["row"] == rn)
    print("  keys per row:", ", ".join(f"{k}={v}" for k, v in per_row.items()))

    seen = {}
    for e in layout:
        key = tuple(e["matrix"])
        if key in seen:
            print(f"  ERROR duplicate matrix cell {key}")
            return 1
        seen[key] = True
    print(f"  {len(seen)} unique matrix cells, no duplicates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
