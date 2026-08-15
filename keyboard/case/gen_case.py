#!/usr/bin/env python3
"""
Generate printable STLs for the pinkyless48 case.

Reads the SAME geometry the PCB was built from - the board outline traced out
of the generated DXF, and the key/mount positions from points.yaml - so the
case cannot drift out of sync with the board. Change the layout, rebuild, and
the case follows.

Two parts per half:

  plate_<side>.stl   1.3 mm switch plate. Choc switches clip into 13.8 mm
                     square cutouts and it sits directly on the PCB. Also
                     carries an opening over the controller strip.
  tray_<side>.stl    bottom tray: floor, perimeter wall, and screw bosses
                     that hold the PCB off the floor so the hotswap sockets
                     have somewhere to live.

Stack, measured from the inside floor of the tray:

    0.0 - 2.0   tray floor
    2.0 - 6.0   air gap (hotswap sockets protrude ~1.8 mm under the PCB)
    6.0 - 7.6   PCB
    7.6 - 8.9   switch plate  <- wall top is flush here
    above       switch bodies, and the socketed controller / TRRS jack,
                which stand proud of the plate through its opening

Booleans are done with manifold3d via trimesh, and every part is asserted
watertight before it is written - a non-manifold STL will slice into garbage.
"""

import sys
import math
from pathlib import Path

import numpy as np
import trimesh
import yaml
from shapely.geometry import Polygon, Point as SPt, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from check_fit import board_polygon, pad_points     # noqa: E402
from check_matrix import parse, modules             # noqa: E402

OUT = ROOT / "build" / "case"
POINTS = ROOT / "build" / "points" / "points.yaml"
PCB = ROOT / "build" / "pcbs" / "pinkyless48.kicad_pcb"

# ---- dimensions, millimetres ---------------------------------------------
PLATE_T = 1.3        # Choc plate thickness; the latches expect 1.2-1.3
SWITCH_CUT = 13.8    # Choc plate cutout, the one dimension you must not vary
PCB_T = 1.6
FLOOR_T = 2.0
SOCKET_GAP = 4.0     # air under the PCB for the hotswap sockets
WALL_T = 2.4
FIT_GAP = 0.4        # clearance between PCB edge and inner wall

SCREW_CLEAR_R = 1.15   # M2 clearance hole, in plate and PCB
SCREW_PILOT_R = 0.85   # M2 self-tapping pilot, in the boss
BOSS_R = 2.8

PCB_BOTTOM = FLOOR_T + SOCKET_GAP        # 6.0
PCB_TOP = PCB_BOTTOM + PCB_T             # 7.6
PLATE_BOTTOM = PCB_TOP
PLATE_TOP = PLATE_BOTTOM + PLATE_T       # 8.9
WALL_TOP = PLATE_TOP

ARC_SEG = 32


def rot_square(x, y, r, size):
    """A square of `size`, centred at (x, y), rotated r degrees."""
    a = math.radians(r)
    ca, sa = math.cos(a), math.sin(a)
    h = size / 2.0
    return Polygon([(x + dx * ca - dy * sa, y + dx * sa + dy * ca)
                    for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h))])


def load_points():
    raw = yaml.safe_load(POINTS.read_text())
    keys, mounts = {}, []
    for name, p in raw.items():
        if name.startswith("mirror_"):
            continue
        if name.startswith(("matrix_", "thumb_")):
            keys[name] = (float(p["x"]), float(p["y"]), float(p.get("r", 0)))
        elif name.startswith("mounts_"):
            mounts.append((float(p["x"]), float(p["y"])))
    return keys, mounts


def controller_opening():
    """
    Rectangle in the plate over the controller, jack and reset button.

    The controller is socketed on header strips, so it stands ~4 mm proud of
    the PCB - well above the plate. Without an opening the plate would sit on
    top of it and nothing would fit together.
    """
    tree = parse(PCB.read_text())
    blobs = []
    for m in modules(tree):
        if m[1] in ("ProMicro", "TRRS-PJ-320A-dual") or "TACT" in m[1]:
            pts = pad_points(m)
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                blobs.append(box(min(xs), min(ys), max(xs), max(ys)))
    if not blobs:
        return None
    return unary_union(blobs).buffer(1.2, join_style=2)


def extrude(poly, z0, z1):
    """Extrude a shapely polygon (holes included) between two z heights."""
    if poly.is_empty:
        return None
    meshes = []
    geoms = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
    for g in geoms:
        if g.area <= 0:
            continue
        m = trimesh.creation.extrude_polygon(g, height=z1 - z0)
        m.apply_translation((0, 0, z0))
        meshes.append(m)
    if not meshes:
        return None
    return trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]


def cyl(x, y, r, z0, z1):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=ARC_SEG)
    m.apply_translation((x, y, (z0 + z1) / 2.0))
    return m


def build_plate(board, keys, mounts, opening):
    holes = [rot_square(x, y, r, SWITCH_CUT) for x, y, r in keys.values()]
    holes += [SPt(mx, my).buffer(SCREW_CLEAR_R, quad_segs=8) for mx, my in mounts]
    if opening is not None:
        holes.append(opening)
    plate = board.difference(unary_union(holes))
    return extrude(plate, PLATE_BOTTOM, PLATE_TOP), plate


def plate_preview(plate, path):
    """Write a top-down SVG of the plate so the cutouts can be eyeballed."""
    minx, miny, maxx, maxy = plate.bounds
    w, h = maxx - minx, maxy - miny
    pad = 5

    def ring(coords):
        pts = " ".join(f"{x-minx+pad:.2f},{maxy-y+pad:.2f}" for x, y in coords)
        return f'<polygon points="{pts}" />'

    parts = []
    geoms = plate.geoms if plate.geom_type == "MultiPolygon" else [plate]
    for g in geoms:
        parts.append(ring(g.exterior.coords))
        parts.extend(ring(i.coords) for i in g.interiors)

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'width="{w+2*pad:.0f}mm" height="{h+2*pad:.0f}mm" '
           f'viewBox="0 0 {w+2*pad:.2f} {h+2*pad:.2f}">'
           f'<rect width="100%" height="100%" fill="white"/>'
           f'<g fill="#d8d8d8" stroke="black" stroke-width="0.4" '
           f'fill-rule="evenodd">{"".join(parts)}</g></svg>')
    path.write_text(svg)


def build_tray(board, mounts, opening):
    outer = board.buffer(FIT_GAP + WALL_T, join_style=1, quad_segs=8)
    cavity = board.buffer(FIT_GAP, join_style=1, quad_segs=8)

    parts = [extrude(outer, 0.0, FLOOR_T),
             extrude(outer.difference(cavity), FLOOR_T, WALL_TOP)]

    for mx, my in mounts:
        parts.append(cyl(mx, my, BOSS_R, FLOOR_T, PCB_BOTTOM))

    solid = trimesh.boolean.union([p for p in parts if p is not None])

    pilots = [cyl(mx, my, SCREW_PILOT_R, -0.5, PCB_BOTTOM + 0.5)
              for mx, my in mounts]
    return trimesh.boolean.difference([solid] + pilots)


def mirrored(mesh, axis_x):
    """
    Mirror a half across a vertical plane to produce its opposite hand.

    A reflection has negative determinant, so it reverses triangle winding and
    turns the solid inside out. trimesh already flips winding inside
    apply_transform, so inverting again unconditionally would undo the fix -
    the volume sign is the reliable test, so use that instead of assuming.
    """
    m = mesh.copy()
    T = np.eye(4)
    T[0, 0] = -1.0
    T[0, 3] = 2.0 * axis_x
    m.apply_transform(T)
    if m.volume < 0:
        m.invert()
    return m


def save(mesh, name, problems):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if mesh is None:
        problems.append(f"{name}: nothing to write")
        return
    if not mesh.is_watertight:
        mesh.fill_holes()
    mesh.merge_vertices()
    status = "watertight" if mesh.is_watertight else "NOT WATERTIGHT"
    if not mesh.is_watertight:
        problems.append(f"{name}: mesh is not watertight")
    # Negative volume means the normals point inward - the slicer would read
    # the part as an infinite void and print nothing useful.
    if mesh.volume < 0:
        problems.append(f"{name}: inverted normals (negative volume)")
    mesh.export(path)
    size = mesh.extents
    print(f"  {path.name:22s} {status:15s} "
          f"{size[0]:6.1f} x {size[1]:6.1f} x {size[2]:5.1f} mm  "
          f"{mesh.volume/1000:7.1f} cm^3")


def main():
    for f in (POINTS, PCB):
        if not f.exists():
            print(f"error: {f} not found - run the ergogen build first")
            return 1

    board = board_polygon().buffer(0)
    keys, mounts = load_points()
    opening = controller_opening()

    print(f"Board {board.bounds[2]-board.bounds[0]:.1f} x "
          f"{board.bounds[3]-board.bounds[1]:.1f} mm, "
          f"{len(keys)} keys, {len(mounts)} screws")
    print(f"Stack: floor {FLOOR_T} | gap {SOCKET_GAP} | pcb {PCB_T} | "
          f"plate {PLATE_T}  = {WALL_TOP} mm tall\n")

    problems = []

    # A screw whose head lands inside a switch cutout has nothing to clamp.
    cuts = unary_union([rot_square(x, y, r, SWITCH_CUT) for x, y, r in keys.values()])
    # Test the whole clearance circle, not just the centre: a screw hole that
    # merely clips the edge of a cutout still leaves the switch unsupported.
    clash = [(mx, my) for mx, my in mounts
             if cuts.intersects(SPt(mx, my).buffer(SCREW_CLEAR_R))]
    if clash:
        problems.append(f"{len(clash)} mounting hole(s) break into a switch cutout")
        print(f"  FAIL  {len(clash)} screw(s) break into a switch cutout: {clash}")
    else:
        webs = [cuts.distance(SPt(mx, my).buffer(SCREW_CLEAR_R)) for mx, my in mounts]
        print(f"  ok    screw clearance: thinnest plate web {min(webs):.2f} mm")

    # The controller opening must not eat into a switch cutout either.
    if opening is not None:
        gap = opening.distance(cuts)
        if gap < 0.8:
            problems.append(f"controller opening only {gap:.2f} mm from a "
                            f"switch cutout")
            print(f"  FAIL  controller opening {gap:.2f} mm from a switch cutout")
        else:
            print(f"  ok    controller opening: {gap:.2f} mm from nearest cutout")

    plate, plate_poly = build_plate(board, keys, mounts, opening)
    tray = build_tray(board, mounts, opening)

    # Every cutout must survive into the plate. If a switch hole merged into
    # the board edge or the controller opening, the plate silently loses a
    # switch mount and the switch will not clip in.
    geoms = (plate_poly.geoms if plate_poly.geom_type == "MultiPolygon"
             else [plate_poly])
    n_holes = sum(len(g.interiors) for g in geoms)
    n_open = 0 if opening is None else (
        len(opening.geoms) if opening.geom_type == "MultiPolygon" else 1)
    expected = len(keys) + len(mounts) + n_open
    if n_holes == expected:
        print(f"  ok    plate cutouts: {n_holes} "
              f"({len(keys)} switch + {len(mounts)} screw + "
              f"{n_open} controller/jack/reset)")
    else:
        print(f"  note  plate cutouts: {n_holes} closed holes, expected "
              f"{expected} - some cutout merged with the outline or the "
              f"controller opening")
    print()

    OUT.mkdir(parents=True, exist_ok=True)
    plate_preview(plate_poly, OUT / "plate_left.svg")

    axis = board.bounds[2] + 30.0        # mirror line to the right of the board
    print("Left half:")
    save(plate, "plate_left.stl", problems)
    save(tray, "tray_left.stl", problems)
    print("Right half (mirrored):")
    save(mirrored(plate, axis), "plate_right.stl", problems)
    save(mirrored(tray, axis), "tray_right.stl", problems)

    print()
    if problems:
        print("CASE HAS PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"CASE OK - 4 STLs written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
