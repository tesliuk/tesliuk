#!/usr/bin/env python3
"""
Verify every component actually fits on the board.

A footprint whose pads hang over the board edge is a dead board: the pads are
milled away during depanelisation and the part has nothing to solder to. This
is easy to do accidentally, because the controller and the jack are placed by
hand-tuned offsets rather than by the key grid.

Coordinate note: ergogen writes outlines in its own frame but emits KiCad
footprints with Y NEGATED (`(at x -y r)`). Comparing the two without undoing
that flip makes every part look off-board, so the KiCad Y is negated back
here before testing.
"""

import sys
import math
from collections import defaultdict
from pathlib import Path

import yaml
from shapely.geometry import Polygon, MultiPoint, Point as SPt
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_matrix import parse, modules          # noqa: E402
from check_outline import segments, WELD         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "build" / "pcbs" / "pinkyless46.kicad_pcb"

# Copper must stay this far inside the board edge (JLCPCB minimum is 0.2 mm;
# 0.3 gives room for milling tolerance).
EDGE_CLEARANCE = 0.3
EDGE_MARGIN_MOUNT = 3.5   # a screw boss needs more room than a pad


def board_polygon():
    """
    Trace the outline segments into a single ordered ring.

    polygonize() chokes on the arc-sampled fillet vertices because they are
    not bit-identical, so the ring is walked explicitly using the same weld
    tolerance the closure check uses.
    """
    segs = segments()
    q = max(WELD, 1e-9)
    key = lambda p: (round(p[0] / q), round(p[1] / q))

    coord = {}
    adj = defaultdict(list)
    for a, b in segs:
        ka, kb = key(a), key(b)
        coord.setdefault(ka, a)
        coord.setdefault(kb, b)
        if ka != kb:
            adj[ka].append(kb)
            adj[kb].append(ka)

    # Trace EVERY ring and keep the largest. The outline also contains the
    # mounting holes as separate closed circles, so starting from an
    # arbitrary vertex can easily walk a 2 mm screw hole and return that as
    # "the board".
    rings, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        ring, prev, cur = [coord[start]], None, start
        seen.add(start)
        while True:
            nxts = [n for n in adj[cur] if n != prev]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                break
            seen.add(nxt)
            ring.append(coord[nxt])
            prev, cur = cur, nxt
            if len(ring) > len(segs) + 4:
                break
        if len(ring) >= 3:
            poly = Polygon(ring)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty:
                rings.append(poly)

    if not rings:
        raise RuntimeError("could not trace any closed ring from the outline")
    return max(rings, key=lambda p: p.area)


def at(mod):
    for n in mod:
        if isinstance(n, list) and n and n[0] == "at":
            return float(n[1]), float(n[2]), (float(n[3]) if len(n) > 3 else 0.0)
    return None


def pad_points(mod):
    """Corners of every pad, in ERGOGEN coordinates (KiCad Y flipped back)."""
    pos = at(mod)
    if pos is None:
        return []
    mx, my, mr = pos
    a = math.radians(mr)
    ca, sa = math.cos(a), math.sin(a)

    pts = []
    for n in mod:
        if not (isinstance(n, list) and n and n[0] == "pad"):
            continue
        pa = next((s for s in n if isinstance(s, list) and s and s[0] == "at"), None)
        sz = next((s for s in n if isinstance(s, list) and s and s[0] == "size"), None)
        if pa is None:
            continue
        px, py = float(pa[1]), float(pa[2])
        w, h = (float(sz[1]), float(sz[2])) if sz else (0.0, 0.0)
        for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            lx, ly = px + dx, py + dy
            gx = mx + lx * ca - ly * sa
            gy = my + lx * sa + ly * ca
            pts.append((gx, -gy))          # undo ergogen's Y negation
    return pts


def main():
    if not PCB.exists():
        print(f"error: {PCB} not found - run the ergogen build first")
        return 1

    board = board_polygon()
    print(f"Board outline: {board.area/100:.1f} cm^2, "
          f"{board.bounds[2]-board.bounds[0]:.1f} x "
          f"{board.bounds[3]-board.bounds[1]:.1f} mm\n")

    safe = board.buffer(-EDGE_CLEARANCE)
    tree = parse(PCB.read_text())

    groups = defaultdict(list)
    for m in modules(tree):
        groups[m[1]].append(m)

    ok = True
    for name in sorted(groups):
        offenders = []
        checked = 0
        for m in groups[name]:
            pts = pad_points(m)
            if not pts:
                continue
            checked += 1
            hull = MultiPoint([SPt(*p) for p in pts]).convex_hull
            if not safe.contains(hull):
                over = hull.difference(safe).area
                offenders.append((at(m), over))

        label = name.split(":")[-1]
        if not checked:
            print(f"  WARN  {label}: no pads found to check")
            continue
        if offenders:
            ok = False
            print(f"  FAIL  {label}: {len(offenders)}/{checked} overhang the "
                  f"board edge")
            for pos, over in offenders[:5]:
                print(f"          at {tuple(round(v,1) for v in pos)} - "
                      f"{over:.1f} mm^2 outside")
        else:
            print(f"  ok    {label}: all {checked} fit with "
                  f"{EDGE_CLEARANCE} mm edge clearance")

    # Mounting holes: a screw that clips a pad is as dead as a part hanging
    # off the edge, and the positions were chosen before the last few
    # outline edits - so re-verify them against the board as built.
    pts_file = ROOT / "build" / "points" / "points.yaml"
    if pts_file.exists():
        raw = yaml.safe_load(pts_file.read_text())
        mounts = [(p["x"], p["y"]) for n, p in raw.items()
                  if n.startswith("mounts_")]
        pads = unary_union([MultiPoint([SPt(*q) for q in pad_points(m)]).convex_hull
                            for m in modules(parse(PCB.read_text()))
                            if pad_points(m)])
        MIN_PAD = 3.0
        bad = []
        for mx, my in mounts:
            c = SPt(mx, my)
            d = c.distance(pads)
            if d < MIN_PAD or not board.buffer(-EDGE_MARGIN_MOUNT).contains(c):
                bad.append((mx, my, d))
        if bad:
            ok = False
            print(f"  FAIL  mounting holes: {len(bad)}/{len(mounts)} too close "
                  f"to a pad or the edge")
            for mx, my, d in bad:
                print(f"          ({mx:.0f}, {my:.0f}) - {d:.1f} mm to nearest pad")
        else:
            print(f"  ok    mounting holes: all {len(mounts)} clear of pads "
                  f"(>= {MIN_PAD} mm) and inside the edge")

    print()
    if ok:
        print("FIT OK - every component is inside the board")
        return 0
    print("FIT HAS PROBLEMS - do not order boards yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
