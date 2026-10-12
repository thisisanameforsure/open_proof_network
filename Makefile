# Open Proof Network — verification entrypoints (conventions §2, §6).
#
#   make verify       fast tier: ruff, mypy --strict, pytest without lean/docker/network tests.
#                     Pre-commit hook; must stay under a minute with no Lean toolchain installed.
#   make verify-lean  real tier: the same gate code against the pinned Lean toolchain and the
#                     step-3 container on the fixture graphs (pytest -m "lean or docker").
#   make verify-harness  the connectors' real-client tier (F16-R8): each pinned harness binary
#                     against the local api (pytest -m harness), in the harness image.
#
# Individual tasks still run their own named verification command for evidence capture.

UV ?= uv
FAST_MARKERS := not lean and not docker and not network and not harness
LEAN_MARKERS := lean or docker
HARNESS_MARKERS := harness

.PHONY: verify verify-lean verify-harness lint types test-fast test-lean sync

sync:
	@$(UV) sync --frozen --quiet

lint: sync
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .

types: sync
	$(UV) run --frozen mypy gate
	$(UV) run --frozen mypy api
	$(UV) run --frozen mypy site

test-fast: sync
	$(UV) run --frozen pytest -m "$(FAST_MARKERS)"

test-lean: sync
	@PYTHONPATH=gate $(UV) run --frozen python -m opn_gate.toolchain --require
	$(UV) run --frozen pytest -m "$(LEAN_MARKERS)"

verify: lint types test-fast

verify-lean: test-lean

verify-harness: sync
	$(UV) run --frozen pytest -m "$(HARNESS_MARKERS)"
