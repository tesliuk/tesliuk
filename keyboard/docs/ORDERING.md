# Ordering guide — how to get this built with (almost) no soldering

## The short answer

**Order the PCB from JLCPCB with their PCBA (assembly) service.** They place
every surface-mount part for you — all 24 hotswap sockets, all 24 diodes, the
reset switch. Assembly is roughly $10–20 setup plus a few dollars per board at
these quantities, which is far cheaper than the hours it saves.

That leaves **28 solder joints per half** — 24 header pins for the controller
socket and 4 pins for the TRRS jack. Both are big, well-spaced through-hole
pads on a flat board; this is the easiest soldering that exists, and it is a
genuinely reasonable first-ever soldering job.

If you want **literally zero soldering**, JLCPCB will also assemble
through-hole parts on request ("PTH assembly"). It costs more and adds lead
time, but it removes those last 28 joints. Ask for it in the order notes and
supply the header + jack as consigned parts if their library lacks them.

---

## Before you can order: the board still needs routing

This is the one thing you must not skip, and it is worth being blunt about it.

Ergogen produces a board with **correct component placement and a complete
netlist, but no copper traces.** Open `build/pcbs/pinkyless48.kicad_pcb` in
KiCad and you will see every footprint in the right place with a ratsnest of
thin lines showing what must connect to what — and nothing routed.

So the sequence is:

1. **Open** `build/pcbs/pinkyless48.kicad_pcb` in KiCad 7, 8 or 9. It is saved
   in the KiCad 5 file format; KiCad will offer to convert it. Let it.
2. **Route** the matrix. Rows and columns on a keyboard are simple, mostly
   straight runs — an evening's work by hand, or use the built-in interactive
   router. Free routing with an autorouter also works fine for a board this
   simple.
3. **Add copper pours** for GND on both layers (Add Filled Zone → GND).
4. **Run DRC** and fix anything it reports.
5. **Plot gerbers** (File → Plot, all copper + mask + silk + Edge.Cuts) and
   **generate drill files**. Zip them.

The checks in this repo verify placement, nets, clearances and the outline —
everything that comes *before* routing. They cannot verify traces that do not
exist yet. Run KiCad's DRC after routing; that is what checks your routing.

---

## Why only one PCB design for both halves

The board is **reversible**. Every footprint is generated with `reverse: true`,
which puts its pads on *both* faces of the board. The right half is the same
board flipped over. One design, one set of gerbers, half the PCB cost, and no
chance of the two halves drifting out of sync.

The catch is that assembly is per-side, so you place **two assembly orders**
from the same gerbers:

| Order | Assembly side | Becomes |
|-------|---------------|---------|
| A     | Top           | Left half |
| B     | Bottom        | Right half |

JLCPCB's minimum assembly quantity is typically 2 boards, so ordering 2 of
each gives you a spare of each hand. Bare PCBs are cheap — get 5 or 10.

---

## Bill of materials (per half)

| Qty | Part | Package | Notes |
|----:|------|---------|-------|
| 24 | Kailh Choc v1 hotswap socket, **CPG135001S30** | SMD | JLC assembles. **Verify stock first — see below.** |
| 24 | **1N4148W** diode | SOD-123 | JLC assembles. Extremely common, always in stock. |
| 1 | SMD tactile switch (Alps SKQG / TL3342 series, 4.7 × 3.5 mm) | SMD | Reset button. JLC assembles. |
| 1 | **PJ-320A** TRRS jack | THT | You solder (4 joints). |
| 2 | 12-pin female header, 2.54 mm | THT | You solder (24 joints). Mill-Max 315 sockets if you want the controller to sit low. |
| 1 | RP2040 controller, Pro Micro footprint | — | Sea-Picro, Elite-Pi, 0xCB Helios. Plugs into the headers. |
| 24 | Kailh Choc v1 switch | — | Your choice of weight. |
| 24 | Choc keycap (18 × 17 mm) | — | MBK, Chicago Steno, etc. |
| 6 | M2 × 6 mm self-tapping screw | — | Into the printed bosses. |
| 1 | TRRS cable | — | Connects the halves. |

### The one thing to check before ordering

**Kailh Choc hotswap socket availability at JLCPCB varies.** It is sometimes an
"extended part" (small extra fee), and has occasionally been out of stock
entirely. Search their parts library for `CPG135001S30` *before* you finalise
the order. If it is unavailable you have three options, in order of preference:

1. Consign your own sockets (buy from AliExpress/Typeractive, ship to JLC).
2. Order the boards bare and hand-solder the sockets — they are 2 pads each,
   48 joints per half, tedious but not difficult.
3. Switch to MX and use `CPG151101S11`, which is more reliably stocked. You
   would set `kx: 19.05` and `ky: 19.05` in `src/config.yaml` and change the
   switch footprint from `choc` to `mx`, then rebuild and re-run `make check`.

---

## A warning about the TRRS jack

TRRS carries VCC between the halves. **Never plug or unplug the TRRS cable
while USB is connected.** The plug shorts adjacent contacts as it slides in,
and with power applied that can kill a controller. Unplug USB first, every
time. This is a known hazard of every TRRS split keyboard, not something
specific to this design.

---

## Cost estimate

Rough, for a pair of halves, excluding switches and keycaps:

| Item | Approx. |
|------|---------|
| 5 bare PCBs | $5–10 |
| PCBA, two orders (setup + parts) | $40–70 |
| 2 × RP2040 controller | $15–25 |
| Screws, jack, headers, cable | $10 |
| 3D printing (or ~200 g filament) | $10–25 |
| **Total** | **≈ $80–140** |

Switches and keycaps add roughly $40–80 depending on taste.
