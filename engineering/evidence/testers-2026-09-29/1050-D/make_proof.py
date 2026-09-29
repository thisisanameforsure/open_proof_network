"""Build Proof.lean for erdos-1050--h1-v2--h4, a D-8 revision of it, or spec-180d8b72
from the node's committed Statement.lean and the proof body in Proof_h4_full_v6.lean.

usage: python3 make_proof.py <Statement.lean> > Proof.lean

The body is the one checked by POST /check (verify mode, okay true, lint []).
If the statement still carries the hden hypothesis (`∃ (d : ℕ)`), the body intros and clears it;
otherwise that intro and the clear are dropped.
"""
import pathlib, sys
here = pathlib.Path(__file__).parent
full = (here / "Proof_h4_full_v6.lean").read_text(encoding="utf-8")
body = full.split(":= by\n", 1)[1]
with_hden = ("  intro Qc hQc Qx hQx Aq hAq hden\n"
             "  -- the remainder bound does not use the denominator bound: cleared before any hole is stated\n"
             "  clear hden\n")
assert body.startswith(with_hden)
st = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
head, tail = st.rsplit(":= by\n  sorry", 1)
assert tail.strip() == "", "statement body is not the expected sorry"
if "∃ (d : ℕ)" not in head:
    body = "  intro Qc hQc Qx hQx Aq hAq\n" + body[len(with_hden):]
sys.stdout.write(head + ":= by\n" + body)
