"""Build Proof.lean for a gate-written hole from its Statement.lean and B's proof body.
usage: python3 proof_from_stmt.py Statement.lean body.lean > Proof.lean
The body file holds the lines after `:= by` (indented two spaces)."""
import sys, pathlib
stmt = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
body = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
tail = ":= by\n  sorry\n"
assert stmt.endswith(tail), repr(stmt[-80:])
sys.stdout.write(stmt[: -len(tail)] + ":= by\n" + body)
