#!/usr/bin/env python3
"""
Verify the generated board outline is a single, closed, connected boundary.

Why this matters: the board silhouette is built by unioning a grown rectangle
around every key. If two groups of keys sit further apart than those rectangles
span, the union quietly produces TWO separate shapes. Ergogen will not warn
you; a board house will either reject the file or ship you two fragments of a
keyboard. This catches that before money is spent.

Parses the DXF with a real group-code reader (DXF is a flat stream of
code/value line pairs) and walks the segment graph.
"""

import sys
import math
from collections import defaultdict
from pathlib import Path

import yaml

BUILD = Path(__file__).resolve().parent.parent / "build"
DXF = BUILD / "outlines" / "board_left.dxf"
POINTS = BUILD / "points" / "points.yaml"

ARC_STEPS = 8          # arcs are sampled, so fillets join their neighbours
WELD = 0.02            # mm; endpoints closer than this are the same vertex
MIN_NECK = 8.0         # mm; thinner than this and the board is snappable
CLOSE = 18.0          # must match `close` in config.yaml
MAX_POCKET = 100.0     # mm^2; concave pockets bigger than this are notches


def read_entities(path):
    """Yield (entity_type, {group_code: value}) for each DXF entity."""
    lines = path.read_text().splitlines()
    pairs = []
    for i in range(0, len(lines) - 1, 2):
        try:
            pairs.append((int(lines[i].strip()), lines[i + 1].strip()))
        except ValueError:
            continue

    ent, data = None, {}
    for code, value in pairs:
        if code == 0:
            if ent:
                yield ent, data
            ent, data = value, {}
        elif ent:
            data.setdefault(code, value)
    if ent:
        yield ent, data


def segments():
    """Flatten every LINE and ARC in the outline into straight segments."""
    segs = []
    for ent, d in read_entities(DXF):
        def num(code):
            v = d.get(code)
            return float(v) if v is not None else None

        if ent == "LINE":
            x1, y1, x2, y2 = num(10), num(20), num(11), num(21)
            if None not in (x1, y1, x2, y2):
                segs.append(((x1, y1), (x2, y2)))

        elif ent == "ARC":
            cx, cy, r, a0, a1 = num(10), num(20), num(40), num(50), num(51)
            if None in (cx, cy, r, a0, a1):
                continue
            if a1 < a0:
                a1 += 360.0
            prev = None
            for i in range(ARC_STEPS + 1):
                a = math.radians(a0 + (a1 - a0) * i / ARC_STEPS)
                p = (cx + r * math.cos(a), cy + r * math.sin(a))
                if prev is not None:
                    segs.append((prev, p))
                prev = p

        elif ent == "CIRCLE":
            # Mounting holes are emitted as whole circles, not arc pairs.
            cx, cy, r = num(10), num(20), num(40)
            if None in (cx, cy, r):
                continue
            steps = ARC_STEPS * 2
            pts = [(cx + r * math.cos(2 * math.pi * i / steps),
                    cy + r * math.sin(2 * math.pi * i / steps))
                   for i in range(steps)]
            segs.extend(zip(pts, pts[1:] + pts[:1]))

    # Arc sampling can emit zero-length segments (an arc with no sweep).
    # They carry no boundary information and only confuse the degree count.
    return [(a, b) for a, b in segs
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9]


def weld(points):
    """
    Assign a canonical id to each point, merging any pair within WELD.

    Rounding coordinates into fixed buckets is not enough: two vertices a
    nanometre apart can straddle a bucket boundary and land in different
    buckets, which shows up later as a phantom "dangling endpoint" on a
    perfectly closed outline. Each point therefore also searches the
    neighbouring buckets before it claims a new id.
    """
    q = max(WELD, 1e-9)
    buckets = defaultdict(list)
    ids = []
    for p in points:
        bx, by = int(math.floor(p[0] / q)), int(math.floor(p[1] / q))
        found = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for rid, rp in buckets.get((bx + dx, by + dy), ()):
                    if math.hypot(rp[0] - p[0], rp[1] - p[1]) <= WELD:
                        found = rid
                        break
                if found is not None:
                    break
            if found is not None:
                break
        if found is None:
            found = len(buckets) * 0 + sum(len(v) for v in buckets.values())
            buckets[(bx, by)].append((found, p))
        ids.append(found)
    return ids


def mount_points():
    """Declared mounting-hole positions, left half only."""
    if not POINTS.exists():
        return []
    raw = yaml.safe_load(POINTS.read_text())
    return [(p["x"], p["y"]) for n, p in raw.items() if n.startswith("mounts_")]


def check_structure():
    """
    Report how thin the board gets, and whether any concave pockets remain.

    A narrow neck is where a PCB snaps, and a sharp concave corner is a crack
    initiation point in both FR4 and the printed plate. The neck width is
    found by eroding the outline until it splits: the radius at which that
    happens is half the narrowest neck.

    board_polygon lives in check_fit, which imports this module - so the
    import is deferred into the function to keep the two from importing each
    other at load time.
    """
    from check_fit import board_polygon          # noqa: E402  (deferred)

    board = board_polygon()
    ok = True

    def pieces(p):
        if p.is_empty:
            return 0
        return 1 if p.geom_type == "Polygon" else len(p.geoms)

    neck, prev = None, 1
    for i in range(1, 400):
        r = i / 10.0
        eroded = board.buffer(-r)
        n = pieces(eroded)
        if n == 0:
            neck = 2 * (r - 0.1)
            print(f"  ok    neck width: > {neck:.1f} mm (never splits)")
            break
        if n > prev:
            neck = 2 * r
            if neck < MIN_NECK:
                ok = False
                print(f"  FAIL  neck width: narrowest neck is {neck:.1f} mm "
                      f"(minimum {MIN_NECK})")
            else:
                print(f"  ok    neck width: narrowest neck {neck:.1f} mm")
            break
        prev = n

    # Concave pockets the closing did not reach.
    closed = board.buffer(CLOSE, join_style=1).buffer(-CLOSE, join_style=1)
    fill = closed.difference(board)
    geoms = ([fill] if fill.geom_type == "Polygon"
             else list(getattr(fill, "geoms", [])))
    pockets = [g for g in geoms if g.area > MAX_POCKET]
    if pockets:
        ok = False
        print(f"  FAIL  notches: {len(pockets)} concave pocket(s) larger than "
              f"{MAX_POCKET} mm^2 remain")
        for g in sorted(pockets, key=lambda g: -g.area)[:5]:
            x0, y0, x1, y1 = g.bounds
            print(f"          {x1-x0:.1f} x {y1-y0:.1f} mm at ({x0:.0f}, {y0:.0f})"
                  f" - raise `close` in config.yaml")
    else:
        print(f"  ok    notches: no concave pocket larger than {MAX_POCKET} mm^2")

    return ok


def main():
    if not DXF.exists():
        print(f"error: {DXF} not found - run the ergogen build first")
        return 1

    segs = segments()
    print(f"Outline has {len(segs)} segments\n")
    if not segs:
        print("  FAIL  outline is empty")
        return 1

    # Weld near-coincident endpoints, then union-find into components.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    flat = [p for seg in segs for p in seg]
    ids = weld(flat)
    idmap = {i: ids[2 * i:2 * i + 2] for i in range(len(segs))}

    degree = defaultdict(int)
    for i, (a, b) in enumerate(segs):
        ka, kb = idmap[i]
        union(ka, kb)
        degree[ka] += 1
        degree[kb] += 1

    comps = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        comps[find(idmap[i][0])].append((a, b))

    ok = True

    # Bounding box per closed loop.
    boxes = []
    for _, s in comps.items():
        xs = [p[0] for seg in s for p in seg]
        ys = [p[1] for seg in s for p in seg]
        boxes.append((min(xs), min(ys), max(xs), max(ys), len(s)))
    boxes.sort(key=lambda b: -((b[2] - b[0]) * (b[3] - b[1])))

    def inside(inner, outer):
        return (inner[0] >= outer[0] - WELD and inner[1] >= outer[1] - WELD
                and inner[2] <= outer[2] + WELD and inner[3] <= outer[3] + WELD)

    # A loop nested inside a larger loop is an interior void (a hole in the
    # copper), not a second board. Both are defects here, but they are
    # different defects and deserve different messages.
    pieces, voids = [], []
    for i, b in enumerate(boxes):
        if any(j != i and inside(b, o) for j, o in enumerate(boxes)):
            voids.append(b)
        else:
            pieces.append(b)

    print(f"  {'ok   ' if len(pieces) == 1 else 'FAIL '} connectivity: "
          f"{len(pieces)} separate board piece(s)")
    for i, b in enumerate(pieces):
        print(f"          piece {i}: {b[4]:4d} segs, "
              f"{b[2]-b[0]:6.1f} x {b[3]-b[1]:6.1f} mm at ({b[0]:.0f}, {b[1]:.0f})")
    # Two pieces is correct: the left half and the mirrored right half.
    if len(pieces) != 1:
        ok = False
        print("          expected exactly 1 (only the left half is fabricated)")

    # Screw holes are deliberate voids. Match them against the declared
    # mounting points so that a hole in the wrong place is still caught.
    mounts = mount_points()
    matched, stray = [], []
    for b in voids:
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        w, h = b[2] - b[0], b[3] - b[1]
        near = [m for m in mounts
                if math.hypot(m[0] - cx, m[1] - cy) < 1.0]
        if near and w < 4.0 and h < 4.0:
            matched.append(b)
        else:
            stray.append(b)

    if len(matched) == len(mounts) and mounts:
        print(f"  ok    mounting holes: all {len(mounts)} present and on "
              f"their declared positions")
    elif mounts:
        ok = False
        print(f"  FAIL  mounting holes: {len(matched)} of {len(mounts)} "
              f"found at declared positions")

    if stray:
        ok = False
        print(f"  FAIL  voids: {len(stray)} unintended hole(s) in the board")
        for b in stray:
            print(f"          void: {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} mm "
                  f"at ({b[0]:.0f}, {b[1]:.0f}) - widen the nearest bridge")
    else:
        print("  ok    voids: no unintended holes in the board")

    ok = check_structure() and ok

    # 2. every vertex must have even degree, or the boundary is not closed
    dangling = [v for v, dg in degree.items() if dg % 2 != 0]
    if dangling:
        ok = False
        print(f"  FAIL  closure: {len(dangling)} dangling endpoint(s) - "
              f"outline is not a closed loop")
    else:
        print("  ok    closure: every boundary vertex is closed")

    print()
    if ok:
        print("OUTLINE OK - single closed boundary")
        return 0
    print("OUTLINE HAS PROBLEMS - do not order boards yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
