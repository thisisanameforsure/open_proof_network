"""F17-T2, F17-T4 / AC4: ``opn-prove import`` over a corpus of prover answers, with the gate's
own step-2 rule as the oracle.

Each case in ``fixtures/prover-answers/`` is an answer as a prover returns it. An accepted answer
must come out as text ``paths.check_proof_is_statement`` admits, and for a complete proof it must
be byte-identical to the node's real ``Proof.lean``, however the answer was wrapped: a proof plan
before a fenced block, a bare tactic block, CRLF line ends, echoed definitions. A refused answer
must be refused with its named code and write nothing. The rescue count at the end is the point
of the client: the answers the gate would refuse if pasted verbatim, and ``import`` makes
admissible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_prove_export import GRAPHS, prove

from opn_gate import layout, paths

CORPUS = Path(__file__).parent / "fixtures" / "prover-answers"
INDEX: dict[str, dict[str, str]] = json.loads((CORPUS / "index.json").read_text())
NODES = {
    "tutorial": ("propositional", "propositional", "tutorial-and-swap"),
    "fact-pos": ("onramp", "euclid-primes", "fact-pos"),
}
KINDS = ("proof", "partial")


def node_of(case: str) -> tuple[object, layout.Statement, Path]:
    graph, target, node = NODES[INDEX[case]["node"]]
    found = prove.find_node(GRAPHS / graph, node, target)
    statement = layout.parse_statement(found.read("Statement.lean"))
    assert isinstance(statement, layout.Statement)
    return found, statement, GRAPHS / graph / "targets" / target / "nodes" / node


def answer(case: str) -> str:
    return (CORPUS / f"{case}.txt").read_bytes().decode("utf-8")


@pytest.mark.parametrize("case", sorted(INDEX))
def test_corpus(case: str) -> None:
    expected = INDEX[case]["expect"]
    found, statement, node_dir = node_of(case)
    if expected in KINDS:
        imported = prove.import_answer(found, answer(case))
        assert imported.kind == expected, imported.notes
        node_id = node_dir.name
        assert paths.check_proof_is_statement(statement, imported.text, node_id=node_id) is None
        if expected == "proof":
            assert imported.text == (node_dir / "Proof.lean").read_text(encoding="utf-8")
    else:
        with pytest.raises(prove.Refused) as refused:
            prove.import_answer(found, answer(case))
        assert refused.value.code == expected, refused.value.message


def test_corpus_has_every_shape() -> None:
    """The shapes F17-AC4 names are all in the corpus, so a deleted case fails here."""
    wanted = {
        "whole-file", "plan-then-fence", "bare-tactics", "set-option-in", "helper-lemma",
        "signature-changed", "sorry-left", "have-holes", "renamed-theorem", "crlf",
        "trailing-prose", "echoes-inlined-defs", "plan-then-fence-deepseek-header",
    }  # fmt: skip
    assert wanted <= set(INDEX), wanted - set(INDEX)
    assert "\r\n" in answer("crlf")


def test_rescues() -> None:
    """Of the answers ``import`` accepts as complete proofs, how many the gate would refuse if a
    contributor pasted the prover's text verbatim as ``Proof.lean``. Printed for the evidence;
    the bar is that the client earns its keep on the shapes provers actually send."""
    rescued = []
    for case, row in sorted(INDEX.items()):
        if row["expect"] != "proof":
            continue
        _, statement, node_dir = node_of(case)
        verbatim = prove.lean_block(answer(case))
        if paths.check_proof_is_statement(statement, verbatim, node_id=node_dir.name) is not None:
            rescued.append(case)
    print(f"rescued {len(rescued)} of {sum(r['expect'] == 'proof' for r in INDEX.values())}: "
          f"{rescued}")  # fmt: skip
    # The tutorial's statement has no definitions to inline, so its extracted block is already
    # admissible; the rescues are the shapes that are not: tactics without the theorem, the
    # theorem under another name, and a file carrying the inlined definitions.
    assert {"bare-tactics", "by-block", "renamed-theorem", "echoes-inlined-defs"} <= set(rescued)


def test_cli_writes_only_on_success(tmp_path: Path) -> None:
    graph, target, node = NODES["tutorial"]
    out = tmp_path / "Proof.lean"
    argv = ["import", "--graph", str(GRAPHS / graph), "--node", node, "--target", target]
    assert prove.main([*argv, str(CORPUS / "plan-then-fence.txt"), "--out", str(out)]) == 0
    assert out.is_file()
    refused = tmp_path / "refused.lean"
    code = prove.main([*argv, str(CORPUS / "helper-lemma.txt"), "--out", str(refused)])
    assert code == 1 and not refused.exists()
