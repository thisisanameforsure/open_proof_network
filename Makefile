# Open Proof Network — single verification entrypoint (conventions §6).
# `make verify` is the regression gate: the full test suite, fail-loud.
# Individual tasks still run their own named verification command for evidence capture.
#
# The stack is locked (conventions §1) but F00-T1 has not wired up the real suite yet. Until
# it does, verify passes vacuously so the pre-commit hook doesn't block spec/docs commits.

.PHONY: verify

verify:
	@echo "verify: suite not wired yet (F00-T1) — passing vacuously"
