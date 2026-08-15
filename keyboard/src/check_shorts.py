#!/usr/bin/env python3
"""
Short-circuit check: no two pads on DIFFERENT nets may overlap.

Ergogen places footprints from a config; it does not run a design-rule check,
so nothing stops the controller, the jack and the reset button - all positioned
by hand-tuned offsets - from landing on top of each other. Overlapping pads on
different nets is a dead short that fabricates perfectly and fails instantly.

Pads that overlap on the SAME net are fine and expected: the switch pad and its
diode pad deliberately share the key's node.

Also reports the smallest gap between pads of different nets, which is the
number JLCPCB cares about (their minimum is 0.127 mm for standard process).
"""

import sys
import math
from itertools import combinations
from pathlib import Path

from shapely.geometry import Polygon, Point as SPt
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_matrix import parse, modules      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "build" / "pcbs" / "pinkyless48.kicad_pcb"

MIN_GAP = 0.127     # JLCPCB standard minimum copper-to-copper spacing


def at(node):
    for n in node:
        if isinstance(n, list) and n and n[0] == "at":
            return (float(n[1]), float(n[2]),
                    float(n[3]) if len(n) > 3 else 0.0)
    return None


def pads(mod):
    """Yield (net_name, polygon) for every pad, in ergogen coordinates."""
    pos = at(mod)
    if pos is None:
        return
    mx, my, mr = pos
    a = math.radians(mr)
    ca, sa = math.cos(a), math.sin(a)

    for n in mod:
        if not (isinstance(n, list) and n and n[0] == "pad"):
            continue
        shape = n[3] if len(n) > 3 else "rect"
        pa = next((s for s in n if isinstance(s, list) and s and s[0] == "at"), None)
        sz = next((s for s in n if isinstance(s, list) and s and s[0] == "size"), None)
        net = next((s for s in n if isinstance(s, list) and s and s[0] == "net"), None)
        if pa is None or sz is None:
            continue

        net_name = net[2] if net and len(net) > 2 else None
        px, py = float(pa[1]), float(pa[2])
        pr = math.radians(float(pa[3])) if len(pa) > 3 else 0.0
        w, h = float(sz[1]), float(sz[2])

        if shape in ("circle", "oval") and abs(w - h) < 1e-6:
            local = [(px + w / 2 * math.cos(t), py + w / 2 * math.sin(t))
                     for t in [i * math.pi / 8 for i in range(16)]]
        else:
            cb, sb = math.cos(pr), math.sin(pr)
            local = [(px + dx * cb - dy * sb, py + dx * sb + dy * cb)
                     for dx, dy in ((-w/2, -h/2), (w/2, -h/2),
                                    (w/2, h/2), (-w/2, h/2))]

        world = [(mx + lx * ca - ly * sa, -(my + lx * sa + ly * ca))
                 for lx, ly in local]
        yield net_name, Polygon(world)


def main():
    if not PCB.exists():
        print(f"error: {PCB} not found - run the ergogen build first")
        return 1

    tree = parse(PCB.read_text())
    items = []
    for m in modules(tree):
        for net, poly in pads(m):
            if poly.is_valid and poly.area > 0:
                items.append((net, poly, m[1]))

    print(f"Checking {len(items)} pads\n")
    ok = True

    geoms = [p for _, p, _ in items]
    index = STRtree(geoms)

    shorts = []
    for i, (net_a, poly_a, ref_a) in enumerate(items):
        for j in index.query(poly_a):
            if j <= i:
                continue
            net_b, poly_b, ref_b = items[j]
            # Unnetted pads are mechanical (mounting slots, switch posts).
            if net_a is None or net_b is None or net_a == net_b:
                continue
            if poly_a.intersects(poly_b):
                area = poly_a.intersection(poly_b).area
                if area > 1e-6:
                    shorts.append((net_a, net_b, ref_a, ref_b, area,
                                   poly_a.centroid))

    if shorts:
        ok = False
        print(f"  FAIL  shorts: {len(shorts)} pad pair(s) on different nets "
              f"overlap")
        for na, nb, ra, rb, area, c in sorted(shorts, key=lambda s: -s[4])[:10]:
            print(f"          {na} <-> {nb}  ({ra} / {rb})  "
                  f"{area:.2f} mm^2 at ({c.x:.0f}, {c.y:.0f})")
    else:
        print("  ok    shorts: no pads on different nets overlap")

    # Tightest clearance between different nets.
    worst = None
    for i, (net_a, poly_a, ref_a) in enumerate(items):
        near = index.query(poly_a.buffer(1.0))
        for j in near:
            if j <= i:
                continue
            net_b, poly_b, ref_b = items[j]
            if net_a is None or net_b is None or net_a == net_b:
                continue
            d = poly_a.distance(poly_b)
            if worst is None or d < worst[0]:
                worst = (d, net_a, net_b, ref_a, ref_b)

    if worst is not None:
        d, na, nb, ra, rb = worst
        if d < MIN_GAP:
            ok = False
            print(f"  FAIL  clearance: {na}-{nb} only {d:.3f} mm apart "
                  f"(minimum {MIN_GAP})")
        else:
            print(f"  ok    clearance: tightest different-net gap is "
                  f"{d:.3f} mm ({na}-{nb}), minimum {MIN_GAP}")

    print()
    if ok:
        print("SHORTS OK - no different-net pad overlaps")
        return 0
    print("SHORTS FOUND - do not order boards yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
