# pinkyless46 - build and verification
#
# `make` regenerates everything and refuses to succeed if any check fails.
# Never order boards from a tree where `make check` is red.

ERGOGEN ?= npx ergogen
PY      ?= python3

.PHONY: all build check case firmware render clean deps mounts

all: build check case firmware render

deps:
	npm install
	$(PY) -m pip install --quiet numpy trimesh manifold3d shapely pyyaml cairosvg

build:
	$(ERGOGEN) src/config.yaml -o build --svg --debug --clean

# Every check exits non-zero on failure, so make stops at the first problem.
check:
	@echo "== layout  (keycap + switch collisions, thumb reach)"
	@$(PY) src/check_layout.py
	@echo "== outline (single closed board, no stray voids, screw holes)"
	@$(PY) src/check_outline.py
	@echo "== matrix  (switch/diode wiring, duplicate matrix cells)"
	@$(PY) src/check_matrix.py
	@echo "== fit     (components and screws inside the board)"
	@$(PY) src/check_fit.py
	@echo "== shorts  (different-net pad overlaps, copper clearance)"
	@$(PY) src/check_shorts.py
	@echo "ALL CHECKS PASSED"

case:
	$(PY) case/gen_case.py

firmware:
	$(PY) firmware/gen_qmk.py

render:
	$(PY) src/render.py

# Re-derive screw positions after a layout change, then paste into config.yaml
mounts:
	$(PY) src/find_mounts.py

clean:
	rm -rf build
