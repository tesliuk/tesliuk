#!/usr/bin/env python3
"""Rasterise the generated SVGs to PNG so the previews survive a clean build."""

import sys
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
JOBS = [
    (ROOT / "build" / "outlines" / "preview.svg", ROOT / "build" / "preview.png", 1500),
    (ROOT / "build" / "case" / "plate_left.svg", ROOT / "build" / "case" / "plate_left.png", 900),
]


def main():
    made = 0
    for src, dst, width in JOBS:
        if not src.exists():
            print(f"  skip {src.name} (not built yet)")
            continue
        cairosvg.svg2png(url=str(src), write_to=str(dst),
                         output_width=width, background_color="white")
        print(f"  wrote {dst.relative_to(ROOT)}")
        made += 1
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
