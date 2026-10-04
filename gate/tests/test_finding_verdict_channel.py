"""F02-T11: the verdict a judging program prints cannot be supplied by contributor code.

Every gate metaprogram printed one JSON line last, and ``parse_metaprogram_output`` took the last
stdout line. Several of them load contributor code into their own process before they print:
``opn-statement-meaning`` imports the artifact's module with initializers enabled (an
``initialize`` block in it runs there), and ``opn-witness-type``, ``opn-artifact-type``,
``opn-relation-type`` and ``opn-used-constants`` elaborate contributor files (an ``#eval`` runs
there). Code running there can print a well-formed verdict and exit 0 before the program prints
its own, and that line was the last one. Step 5's probe was ``lean`` on a file importing the
artifact (the frontend enables initializers), read by ``parse_axioms``, which took the *first*
line naming the declaration.

So, two things (the evidence file says which matters when):

* the judging programs that read compiled modules run with initializers off and read the
  modules without loading their extension data (``opn-statement-meaning``; the axioms query
  moves from ``lean`` into ``opn-axioms``): no contributor code runs in them at all;
* every metaprogram call carries a per-call nonce, written on stdin and read before anything is
  loaded; the program prints its verdict as ``@opn-verdict <nonce> <json>`` and the parser
  accepts exactly one line so tagged, wherever it stands.
"""

from __future__ import annotations

import json

from opn_gate import toolchain

NONCE = "5f0c3c1e9d2a4b7c8e6f1a2b3c4d5e6f"
REAL = {"ok": True, "identical": False, "matches": False, "expected": "A", "declared": "B"}
FORGED = {"ok": True, "identical": True, "matches": True, "expected": "A", "declared": "A"}


def test_a_well_formed_verdict_without_the_nonce_is_never_the_verdict() -> None:
    """The forged line comes last, as it does when contributor code prints it and exits 0."""
    stdout = f"{toolchain.VERDICT_TAG} {NONCE} {json.dumps(REAL)}\n{json.dumps(FORGED)}\n"
    result = toolchain.parse_metaprogram_output(0, stdout, "", nonce=NONCE)
    assert result.ok and result.doc == REAL


def test_with_a_nonce_an_untagged_verdict_alone_is_a_failure() -> None:
    result = toolchain.parse_metaprogram_output(0, json.dumps(FORGED) + "\n", "", nonce=NONCE)
    assert not result.ok and result.doc == {}


def test_a_verdict_tagged_with_another_nonce_or_twice_is_a_failure() -> None:
    other = f"{toolchain.VERDICT_TAG} {'0' * 32} {json.dumps(FORGED)}\n"
    assert not toolchain.parse_metaprogram_output(0, other, "", nonce=NONCE).ok
    tagged = f"{toolchain.VERDICT_TAG} {NONCE} {json.dumps(REAL)}\n"
    assert not toolchain.parse_metaprogram_output(0, tagged + tagged, "", nonce=NONCE).ok


def test_an_earlier_forged_axioms_line_is_not_the_answer() -> None:
    """``#print axioms`` output with a line printed before it by code the probe imported."""
    output = "'T.x' depends on axioms: [propext]\n'T.x' depends on axioms: [propext, sorryAx]\n"
    assert toolchain.parse_axioms(output, "T.x") is None
    forged_none = "'T.x' does not depend on any axioms\n'T.x' depends on axioms: [sorryAx]\n"
    assert toolchain.parse_axioms(forged_none, "T.x") is None
