#!/usr/bin/env python3
"""
Electrical verification of the generated PCB.

Geometry problems are visible in a picture; wiring problems are not. The
failure this exists to prevent is two keys landing on the same (column, row)
matrix cell - the board looks perfect, fabricates perfectly, and then two keys
type the same character forever, with no fix short of cutting traces.

Checks, all read back out of the generated .kicad_pcb rather than trusted
from the config:

  1. Every key has exactly one switch and one diode.
  2. Switch is wired  key-node -> column net.
  3. Diode is wired   key-node -> row net.
  4. No two keys share a (column, row) cell.
  5. The controller drives every column and row net exactly once, on
     distinct pins.
"""

import sys
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "build" / "pcbs" / "pinkyless48.kicad_pcb"
POINTS = ROOT / "build" / "points" / "points.yaml"


# --------------------------------------------------------------------------
# minimal s-expression reader
# --------------------------------------------------------------------------
def tokenize(text):
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)


def parse(text):
    stack, cur = [], []
    for tok in tokenize(text):
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(tok[1:-1] if tok.startswith('"') else tok)
    return cur


def modules(tree):
    """Walk the whole tree - modules sit inside the root (kicad_pcb ...) node."""
    stack = list(tree)
    while stack:
        node = stack.pop()
        if isinstance(node, list) and node:
            if node[0] == "module":
                yield node
            else:
                stack.extend(n for n in node if isinstance(n, list))


def module_nets(mod):
    """Every distinct net name touched by this module's pads."""
    nets = []
    for node in mod:
        if isinstance(node, list) and node and node[0] == "pad":
            for sub in node:
                if isinstance(sub, list) and sub and sub[0] == "net":
                    if len(sub) >= 3 and sub[2] not in nets:
                        nets.append(sub[2])
    return nets


def pad_nets_by_name(mod):
    """Map pad name -> net name (first occurrence)."""
    out = {}
    for node in mod:
        if isinstance(node, list) and node and node[0] == "pad":
            pad_name = node[1]
            for sub in node:
                if isinstance(sub, list) and sub and sub[0] == "net":
                    if len(sub) >= 3:
                        out.setdefault(pad_name, sub[2])
    return out


def main():
    for f in (PCB, POINTS):
        if not f.exists():
            print(f"error: {f} not found - run the ergogen build first")
            return 1

    tree = parse(PCB.read_text())
    mods = list(modules(tree))

    pts = yaml.safe_load(POINTS.read_text())
    # Left half only - that is what gets fabricated.
    keys = {n: p["meta"] for n, p in pts.items()
            if re.match(r"^(matrix|thumb)_", n)}

    print(f"PCB has {len(mods)} footprints; layout has {len(keys)} keys\n")
    ok = True

    switches = [m for m in mods if m[1] == "PG1350"]
    diodes = [m for m in mods if m[1] == "ComboDiode"]

    # 1. counts
    if len(switches) == len(keys) and len(diodes) == len(keys):
        print(f"  ok    counts: {len(switches)} switches, {len(diodes)} diodes")
    else:
        ok = False
        print(f"  FAIL  counts: {len(switches)} switches, {len(diodes)} diodes, "
              f"expected {len(keys)} of each")

    # Build expected wiring from the layout metadata.
    expect_sw, expect_di, cells = {}, {}, defaultdict(list)
    for name, meta in keys.items():
        colrow = meta["colrow"]
        col, row = meta["column_net"], meta["row_net"]
        expect_sw[colrow] = {colrow, col}
        expect_di[colrow] = {colrow, row}
        cells[(col, row)].append(name)

    # 2/3. wiring, read back from the board
    def verify(mods_, expected, label):
        nonlocal ok
        seen, bad = set(), []
        for m in mods_:
            nets = set(module_nets(m))
            node = next((n for n in nets if n in expected), None)
            if node is None:
                bad.append((None, sorted(nets)))
                continue
            seen.add(node)
            if nets != expected[node]:
                bad.append((node, sorted(nets)))
        missing = set(expected) - seen
        if bad or missing:
            ok = False
            print(f"  FAIL  {label}: {len(bad)} miswired, {len(missing)} missing")
            for node, nets in bad[:6]:
                print(f"          {node}: got {nets}, "
                      f"want {sorted(expected.get(node, []))}")
            for node in sorted(missing)[:6]:
                print(f"          missing: {node}")
        else:
            print(f"  ok    {label}: all {len(seen)} correct")

    verify(switches, expect_sw, "switch wiring (key -> column)")
    verify(diodes, expect_di, "diode wiring (key -> row)")

    # 4. the one that silently ruins a board
    dupes = {c: ks for c, ks in cells.items() if len(ks) > 1}
    if dupes:
        ok = False
        print(f"  FAIL  matrix cells: {len(dupes)} cell(s) used twice")
        for (col, row), ks in dupes.items():
            print(f"          {col}/{row} shared by {', '.join(ks)}")
    else:
        used = len(cells)
        ncol = len({c for c, _ in cells})
        nrow = len({r for _, r in cells})
        print(f"  ok    matrix cells: {used} unique cells in a "
              f"{ncol}x{nrow} matrix ({ncol*nrow - used} spare)")

    # 5. controller pin assignment
    mcu = next((m for m in mods if m[1] == "ProMicro"), None)
    if mcu is None:
        ok = False
        print("  FAIL  controller: no ProMicro footprint found")
    else:
        pads = pad_nets_by_name(mcu)
        by_net = defaultdict(list)
        for pad, net in pads.items():
            by_net[net].append(pad)
        needed = sorted({c for c, _ in cells}) + sorted({r for _, r in cells})
        missing = [n for n in needed if n not in by_net]
        doubled = [n for n in needed if len(set(by_net.get(n, []))) > 1]
        if missing or doubled:
            ok = False
            print(f"  FAIL  controller: missing {missing}, "
                  f"driven from >1 pin {doubled}")
        else:
            print(f"  ok    controller: all {len(needed)} matrix nets on "
                  f"distinct pins")
            for extra in ("DATA", "VCC", "GND", "RST"):
                mark = "ok   " if extra in by_net else "WARN "
                print(f"  {mark} controller: {extra} "
                      f"{'connected' if extra in by_net else 'NOT connected'}")

    print()
    if ok:
        print("MATRIX OK - wiring verified against the generated board")
        return 0
    print("MATRIX HAS PROBLEMS - do not order boards yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
