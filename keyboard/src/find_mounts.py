#!/usr/bin/env python3
"""
Search the board for places a mounting screw can actually go.

The layout is dense - switch bodies in adjacent columns very nearly touch, and
a diode sits 5.5 mm below every key - so eyeballing screw positions produces
holes that clip a pad. This finds positions that are provably clear:

  * inside the board, at least EDGE_MARGIN from the edge
  * at least KEEPOUT from every pad on either face
  * spread out, so the plate is actually supported

Prints ergogen-ready shifts relative to matrix_pinky_home. The result is
pasted into config.yaml as a `mounts` zone, which puts the holes in
points.yaml - a single source of truth the PCB and the case both read.
"""

import sys
import math
from pathlib import Path

import math as _math

import yaml
from shapely.geometry import MultiPoint, Point as SPt, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_matrix import parse, modules      # noqa: E402
from check_fit import board_polygon, pad_points   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "build" / "pcbs" / "pinkyless46.kicad_pcb"

SWITCH_CUT = 13.8   # plate cutout - BIGGER than the switch pads, so a screw
                    # clear of every pad can still land in a switch hole
WEB = 1.6           # minimum plate material between a screw and any cutout
HOLE_R = 1.1        # M2 clearance hole
KEEPOUT = 3.2       # clearance from any pad, leaves room for a screw head
EDGE_MARGIN = 4.0   # keep the boss fully on the board
GRID = 1.0          # search resolution, mm
WANT = 6            # how many screws to place

REF = (60.0, -143.0)   # matrix_pinky_home


def main():
    board = board_polygon()
    tree = parse(PCB.read_text())

    blobs = []
    for m in modules(tree):
        pts = pad_points(m)
        if pts:
            blobs.append(MultiPoint([SPt(*p) for p in pts]).convex_hull)
    occupied = unary_union(blobs).buffer(KEEPOUT)

    # The switch plate cutouts are 13.8 mm square - wider than the pads in
    # some directions. A screw that is clear of all copper can still punch
    # through a switch hole, leaving the switch nothing to clip into, so the
    # cutouts have to be part of the keep-out too.
    raw = yaml.safe_load((ROOT / "build" / "points" / "points.yaml").read_text())
    cutouts = []
    for name, p in raw.items():
        if name.startswith("mirror_") or not name.startswith(("matrix_", "thumb_")):
            continue
        x, y, r = float(p["x"]), float(p["y"]), float(p.get("r", 0))
        a = _math.radians(r)
        ca, sa = _math.cos(a), _math.sin(a)
        h = SWITCH_CUT / 2.0
        cutouts.append(Polygon([(x + dx * ca - dy * sa, y + dx * sa + dy * ca)
                                for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h))]))
    occupied = unary_union([occupied,
                            unary_union(cutouts).buffer(WEB + HOLE_R)])

    free = board.buffer(-EDGE_MARGIN).difference(occupied)
    print(f"board {board.area/100:.1f} cm^2 -> "
          f"free area for screws {free.area/100:.2f} cm^2")
    if free.is_empty:
        print("no free area at all - relax KEEPOUT or open a gap in the layout")
        return 1

    # Candidate points on a grid inside the free area.
    minx, miny, maxx, maxy = free.bounds
    cands = []
    y = miny
    while y <= maxy:
        x = minx
        while x <= maxx:
            p = SPt(x, y)
            if free.contains(p):
                # distance to the nearest obstacle = how comfortable it is
                cands.append((p.distance(occupied.boundary)
                              if not occupied.is_empty else 99.0, x, y))
            x += GRID
        y += GRID
    if not cands:
        print("no candidate positions found")
        return 1
    print(f"{len(cands)} candidate positions\n")

    # Greedy farthest-point selection, biased toward roomy spots, so the
    # screws end up spread around the board instead of clustered.
    cands.sort(reverse=True)
    chosen = [cands[0]]
    while len(chosen) < WANT:
        best, best_score = None, -1.0
        for room, x, y in cands:
            d = min(math.hypot(x - cx, y - cy) for _, cx, cy in chosen)
            score = d + room * 1.5
            if score > best_score:
                best, best_score = (room, x, y), score
        if best is None or min(math.hypot(best[1] - cx, best[2] - cy)
                               for _, cx, cy in chosen) < 18:
            break
        chosen.append(best)

    print(f"placing {len(chosen)} mounting holes (M2, {HOLE_R*2:.1f} mm hole)\n")
    print("    mounts:")
    print("      anchor:")
    print(f"        ref: matrix_pinky_home")
    print("      columns:")
    for i, (room, x, y) in enumerate(
            sorted(chosen, key=lambda c: (-c[2], c[1])), start=1):
        dx, dy = x - REF[0], y - REF[1]
        print(f"        m{i}:")
        print(f"          key:")
        print(f"            spread: 0")
        print(f"            shift: [{dx:.1f}, {dy:.1f}]"
              f"   # clearance {room:.1f} mm")
    print("      rows:")
    print("        m:")
    return 0


if __name__ == "__main__":
    sys.exit(main())
