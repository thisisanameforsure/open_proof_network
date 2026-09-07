# Open Proof Network — single verification entrypoint (conventions §6).
# `make verify` is the regression gate: the full test suite, fail-loud.
# Individual tasks still run their own named verification command for evidence capture.
#
# The stack is not locked yet (conventions §1 TODO). Until F00-T1 wires up the real suite,
# verify passes vacuously so the pre-commit hook doesn't block spec/docs commits.

.PHONY: verify

verify:
	@echo "verify: stack not locked (conventions §1 TODO; F00-T1 wires the suite) — passing vacuously"
