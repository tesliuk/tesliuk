#!/usr/bin/env python3
"""
Geometry sanity checks for the generated key layout.

A keyboard PCB is unforgiving: two keycaps that overlap by 0.3 mm produce a
board you cannot type on, and you only find out after paying for fabrication.
This script reads the key positions ergogen produced and refuses to let that
happen, checking:

  1. Keycap collisions   - no two caps may overlap, anywhere.
  2. Switch-body clearance - Choc bodies need room even where caps clear.
  3. Half separation      - the left and right board outlines must not touch.
  4. Reachability         - flags keys that sit implausibly far from home row.

Run via `make check` or directly. Exit code is non-zero if anything fails,
so it can gate a build.
"""

import re
import sys
import math
import yaml
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union

BUILD = Path(__file__).resolve().parent.parent / "build"
POINTS = BUILD / "points" / "points.yaml"

# Kailh Choc v1 dimensions, millimetres.
CAP_W, CAP_H = 17.5, 16.5      # low-profile keycap envelope
BODY_W, BODY_H = 15.0, 15.0    # switch body incl. latches
MIN_HALF_GAP = 8.0             # minimum clear space between the two halves


def rect(x, y, r, w, h):
    """Axis-aligned rect of size w*h centred at (x, y), rotated r degrees."""
    a = math.radians(r)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = w / 2.0, h / 2.0
    corners = []
    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        corners.append((x + dx * ca - dy * sa, y + dx * sa + dy * ca))
    return Polygon(corners)


def load_points():
    with open(POINTS) as fh:
        raw = yaml.safe_load(fh)
    # Only real keys. The config also declares points for the controller,
    # the jack, the reset button and the mounting holes; they are not keys
    # and must not be collision-checked as if they were.
    pts = {}
    for name, p in raw.items():
        if not re.match(r"^(mirror_)?(matrix|thumb)_", name):
            continue
        pts[name] = (float(p["x"]), float(p["y"]), float(p.get("r", 0)))
    return pts


def check_overlaps(pts, w, h, label, tol=0.05):
    """Report every pair of keys whose w*h envelopes intersect."""
    polys = {n: rect(x, y, r, w, h) for n, (x, y, r) in pts.items()}
    names = sorted(polys)
    bad = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            inter = polys[a].intersection(polys[b])
            if inter.area > tol:
                bad.append((a, b, inter.area))
    if bad:
        print(f"  FAIL  {label}: {len(bad)} overlapping pair(s)")
        for a, b, area in sorted(bad, key=lambda t: -t[2])[:12]:
            print(f"          {a} <-> {b}   overlap {area:.2f} mm^2")
    else:
        print(f"  ok    {label}: no collisions")
    return not bad


def check_half_gap(pts):
    """The two halves are separate physical boards; they must not touch."""
    left = {n: v for n, v in pts.items() if not n.startswith("mirror_")}
    right = {n: v for n, v in pts.items() if n.startswith("mirror_")}
    if not right:
        print("  WARN  half gap: no mirrored points found")
        return True

    lb = unary_union([rect(*v, CAP_W, CAP_H) for v in left.values()])
    rb = unary_union([rect(*v, CAP_W, CAP_H) for v in right.values()])
    gap = lb.distance(rb)

    lx = [v[0] for v in left.values()]
    ly = [v[1] for v in left.values()]
    print(f"  info  left half bbox: {max(lx)-min(lx):.1f} x {max(ly)-min(ly):.1f} mm")

    if gap < MIN_HALF_GAP:
        print(f"  FAIL  half gap: halves are {gap:.1f} mm apart "
              f"(need >= {MIN_HALF_GAP})")
        return False
    print(f"  ok    half gap: {gap:.1f} mm clear between halves")
    return True


def check_reach(pts):
    """
    Flag thumb keys the thumb cannot actually reach.

    Measured from the thumb HOME key (the cluster key nearest the index
    column), not from the finger home row - the thumb pivots from its own
    resting position, so distance-from-home-row would be the wrong metric
    and would condemn every perfectly good thumb cluster.

    A relaxed thumb sweeps roughly 45 mm before the hand has to move.
    """
    thumbs = {n: v for n, v in pts.items()
              if "thumb" in n and not n.startswith("mirror_")}
    if not thumbs:
        return True

    index_keys = [v for n, v in pts.items()
                  if n.startswith("matrix_index_") and not n.startswith("mirror_")]
    ix = sum(v[0] for v in index_keys) / len(index_keys)
    iy = sum(v[1] for v in index_keys) / len(index_keys)

    # thumb home = cluster key closest to the index column
    home_name = min(thumbs, key=lambda n: math.hypot(thumbs[n][0] - ix,
                                                     thumbs[n][1] - iy))
    hx, hy, _ = thumbs[home_name]
    print(f"  info  thumb home key: {home_name}")

    ok = True
    for n, (x, y, _) in sorted(thumbs.items(),
                               key=lambda kv: -math.hypot(kv[1][0] - hx,
                                                          kv[1][1] - hy)):
        d = math.hypot(x - hx, y - hy)
        if d > 48:
            ok = False
            print(f"  FAIL  reach: {n} is {d:.1f} mm from thumb home (max 48)")
        else:
            print(f"  ok    reach: {n} {d:.1f} mm from thumb home")
    return ok


def main():
    if not POINTS.exists():
        print(f"error: {POINTS} not found - run the ergogen build first")
        return 1

    pts = load_points()
    print(f"Checking {len(pts)} keys "
          f"({sum(1 for n in pts if not n.startswith('mirror_'))} per half)\n")

    results = [
        check_overlaps(pts, CAP_W, CAP_H, "keycap clearance"),
        check_overlaps(pts, BODY_W, BODY_H, "switch body clearance"),
        check_half_gap(pts),
        check_reach(pts),
    ]

    print()
    if all(results):
        print("LAYOUT OK - safe to fabricate")
        return 0
    print("LAYOUT HAS PROBLEMS - do not order boards yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
