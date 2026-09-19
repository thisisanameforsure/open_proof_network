"""F03-T11 (R14, AC18, Q14; D-14 v3.19): a proposer's ``speculative`` label yields to a merged
artifact.

The finding (F04-T21, 2026-09-19): ``derive_statuses`` let the latest status record win over the
artifact for every record status, and nothing writes a record when a proof merges, so a crux node
born ``speculative`` (F08-Q2) would still read ``speculative`` after its proof landed — on the
frontier, claimable, with the kernel's verdict in the tree. A label on an open statement says
nothing about a settled one (the shape of ``stale_is_void``, F08-T10). Every other record keeps
its precedence: a person's judgment over the derivation.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET, copy_graph
from test_products import attest, node_status_record

from opn_gate import graph
from opn_gate.records import StatusRecord

NODE = "and-reassoc"  # the fixture's proved interior node; a crux is the same shape with a label

_DECL_RE = re.compile(r"^(theorem|lemma)\s+(\S+)", re.M)


def node_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes" / NODE


def as_counterexample(root: Path) -> None:
    """Rewrite the node's ``Proof.lean`` to declare ``<name>_refuted``: which artifact a proof
    file is, the gate reads off the name it declares (F07-R4, Q11)."""
    proof = node_dir(root) / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    m = _DECL_RE.search(text)
    assert m is not None
    proof.write_text(text.replace(m.group(2), m.group(2) + "_refuted", 1), encoding="utf-8")


def test_a_merged_proof_settles_a_speculative_node(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    node_status_record(root, NODE, "speculative")
    assert graph.load_target(root, TARGET).statuses[NODE] == "speculative"  # the label, unsettled
    attest(root, NODE, n=1)
    assert graph.load_target(root, TARGET).statuses[NODE] == "proved"


def test_a_merged_counterexample_settles_a_speculative_node(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    node_status_record(root, NODE, "speculative")
    as_counterexample(root)
    attest(root, NODE, n=1)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[NODE].artifact == "counterexample"
    assert tg.statuses[NODE] == "refuted"


def test_an_attestation_without_an_artifact_leaves_the_label(tmp_path: Path) -> None:
    """A merged partial earns a passing attestation against the parent's statement and leaves
    no ``Proof.lean`` (F03-Q7): the node is not settled, so the label still decides."""
    root = copy_graph(tmp_path, publish=True)
    node_status_record(root, NODE, "speculative")
    (node_dir(root) / "Proof.lean").unlink()
    attest(root, NODE, n=1)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[NODE].proof is not None and tg.nodes[NODE].artifact is None
    assert tg.statuses[NODE] == "speculative"


def test_every_other_record_keeps_its_precedence(tmp_path: Path) -> None:
    """A curator's ``abandoned`` beside a merged proof still reads abandoned: a judgment, not a
    label. The one status the rule touches is the proposer's own."""
    root = copy_graph(tmp_path, publish=True)
    node_status_record(root, NODE, "abandoned")
    attest(root, NODE, n=1)
    assert graph.load_target(root, TARGET).statuses[NODE] == "abandoned"


def test_the_rule_is_settledness_alone() -> None:
    """``speculative_is_void`` is ``settled``: true with an artifact and its proof, false with
    either missing, and false for any other record status whatever the artifact."""
    proved = graph.Proof(merge_commit="0" * 40, trust_base=graph.TRUST_KERNEL, attestation="")

    def facts(*, proof: graph.Proof | None, artifact: str | None, status: str) -> graph.NodeFacts:
        rec = StatusRecord(status, "alice", "2026-09-19", Path("r.yaml"), {})
        return graph.NodeFacts(
            node_id="n",
            target_id=TARGET,
            path=Path("n"),
            statement_hash="a" * 64,
            deps=(),
            origin="authored",
            tutorial=False,
            relation=None,
            proof=proof,
            override=rec,
            artifact=artifact,
        )

    assert graph.speculative_is_void(facts(proof=proved, artifact="proof", status="speculative"))
    assert graph.speculative_is_void(facts(proof=proved, artifact="vacuity", status="speculative"))
    assert not graph.speculative_is_void(facts(proof=None, artifact="proof", status="speculative"))
    assert not graph.speculative_is_void(facts(proof=proved, artifact=None, status="speculative"))
    assert not graph.speculative_is_void(facts(proof=proved, artifact="proof", status="abandoned"))
    assert not graph.speculative_is_void(facts(proof=proved, artifact="proof", status="stale"))
