"""Usage: python3 make_proof.py <hole Statement.lean> <hole>.body > Proof.lean
Replaces the statement's final `  sorry` with the body (which starts with `intro ...`).
Each body was checked by POST /check against the hole's closed_type as printed by precheck
01M3Q9EYS0AMXB2RSA73RPJ74V (skeleton PR #253), with the theorem renamed; not prechecked."""
import sys
st = open(sys.argv[1], encoding="utf-8").read()
body = open(sys.argv[2], encoding="utf-8").read()
assert st.endswith(":= by\n  sorry\n"), "unexpected statement tail"
sys.stdout.write(st[: -len("  sorry\n")] + body)
