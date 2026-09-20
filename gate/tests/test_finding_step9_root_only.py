"""F07-T24 (decisions v3.20): step 9 is asked of an artifact that settles the root, and of nothing
else; a calibration target asks it of nothing.

The owner's ruling on the 2026-09-19 primes run. Four outside agents proved versions of the
infinitude of primes beneath an already-proved root, and every one of their proofs, skeletons and
hole proofs stopped at a red step 9 until a person approved it: the review had been asked of every
node under an uncertified root (v3.11). What the review is *for* is a mathematician confirming
that the Lean statement says what the conjecture says, at the moment the conjecture would be
called settled. A hole, a crux, a skeleton or a variant makes no such claim.

Same harness as ``test_finding_step9_certified.py``: ``opn-gate classify`` over a checkout's last
commit, as the graph's workflow runs it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from test_finding_step9_certified import (
    ROOT,
    TARGET_ID,
    Repo,
    classify,
    curated,
    step9,
    submit_partial,
    submit_proof,
)

from opn_gate import bounce, postmerge, products, scaffold, schemas
from opn_gate import graph as graphmod

NOT_ASKED_INTERMEDIATE = (False, "intermediate", None)
NOT_ASKED_CALIBRATION = (False, "calibration", None)
ASKED = (True, "pr-approval", None)

CHILD_STATEMENT = "theorem OpnProp.child_lemma : ∀ p : Prop, p → p := by\n  sorry\n"
CHILD_PROOF = CHILD_STATEMENT.replace("  sorry\n", "  intro p h\n  exact h\n")
WITNESS = "theorem witness : ∃ p : Prop, p := ⟨True, trivial⟩\n"
RELATION = "theorem relation : True := trivial\n"


def add_node(repo: Repo, node_id: str, **proposal: Any) -> Path:
    """A second node of the target, as a merged proposal leaves it."""
    return scaffold.write(
        repo.target / "nodes",
        scaffold.Proposal(
            node_id=node_id,
            target_id=TARGET_ID,
            statement=CHILD_STATEMENT,
            witness=WITNESS,
            author="someone",
            **proposal,
        ),
    )


def prove(repo: Repo, node_dir: Path) -> None:
    (node_dir / "Proof.lean").write_text(CHILD_PROOF, encoding="utf-8")
    repo.commit(f"a proof of {node_dir.name}")


def test_a_proof_of_a_node_that_is_not_the_root_asks_no_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, _ = curated(tmp_path)
    crux = add_node(repo, "spec-0a0a0a0a", deps=())
    repo.commit("base: the root, uncertified, and a crux beneath it")
    prove(repo, crux)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof" and out["needs_gate"] is True, out
    assert step9(out) == NOT_ASKED_INTERMEDIATE, out


def test_a_proof_of_the_uncertified_root_still_asks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The one place the review means something, unchanged."""
    repo, proof = curated(tmp_path)
    add_node(repo, "spec-0a0a0a0a")
    repo.commit("base")
    submit_proof(repo, proof)
    _, out = classify(repo, capsys)
    assert step9(out) == ASKED, out


def test_a_skeleton_settles_nothing_even_on_the_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A partial leaves the root open (D-12 v3.19): whoever closes it later is the one asked."""
    repo, _ = curated(tmp_path)
    repo.commit("base")
    submit_partial(repo)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "partial", out
    assert step9(out) == NOT_ASKED_INTERMEDIATE, out


@pytest.mark.parametrize(
    ("root_proved", "expected"), [(False, ASKED), (True, NOT_ASKED_INTERMEDIATE)]
)
def test_a_resolves_variant_is_a_root_proof_only_while_the_root_is_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], root_proved: bool, expected: tuple[Any, ...]
) -> None:
    """A variant labelled ``resolves`` implies the root (D-30), so proving it settles the target
    by another road — unless the root is already closed, when it settles nothing."""
    repo, _ = curated(tmp_path, keep_proof=root_proved)
    if root_proved:
        # Proved means a proof in the tree *and* its merged attestation (F03-Q7).
        doc = samples.attestation(
            node_id=ROOT,
            statement_hash=schemas.content_hash((repo.node / "Statement.lean").read_bytes()),
            merge_commit="2" * 40,
            graph_commit="1" * 40,
            runner="hosted",
        )
        (repo.root / "attestations").mkdir(exist_ok=True)
        (repo.root / "attestations" / "000001.json").write_bytes(schemas.canonical_json(doc))
    variant = add_node(
        repo, "variant-0b0b0b0b", origin="variant", relation="resolves", relation_proof=RELATION
    )
    repo.commit("base")
    prove(repo, variant)
    _, out = classify(repo, capsys)
    assert out["mode"] == "proof", out
    assert step9(out) == expected, out


@pytest.mark.parametrize("relation", ["partial", "related"])
def test_a_weaker_variant_never_asks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], relation: str
) -> None:
    repo, _ = curated(tmp_path)
    variant = add_node(
        repo,
        "variant-0c0c0c0c",
        origin="variant",
        relation=relation,
        relation_proof=RELATION if relation == "partial" else None,
    )
    repo.commit("base")
    prove(repo, variant)
    _, out = classify(repo, capsys)
    assert step9(out) == NOT_ASKED_INTERMEDIATE, out


def test_a_calibration_target_asks_nothing_even_of_its_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A result already in the literature settles no open conjecture (D-6 on-ramp, D-27)."""
    repo, proof = curated(tmp_path)
    record = repo.target / "target.yaml"
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    doc["calibration"] = True
    record.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    repo.commit("base: a calibration target")
    submit_proof(repo, proof)
    _, out = classify(repo, capsys)
    assert step9(out) == NOT_ASKED_CALIBRATION, out


def test_a_proof_cannot_declare_its_own_target_calibration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flag is read from the base: a diff that touches target.yaml is not a proof at all."""
    repo, proof = curated(tmp_path)
    repo.commit("base")
    record = repo.target / "target.yaml"
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    doc["calibration"] = True
    record.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    (repo.node / "Proof.lean").write_text(proof, encoding="utf-8")
    repo.commit("a proof that brings its own exemption")
    _, out = classify(repo, capsys)
    assert out["mode"] != "proof" or step9(out) == ASKED, out


def test_a_graph_that_cannot_be_read_keeps_asking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """C7: nothing stands in for a person on a guess."""
    repo, _ = curated(tmp_path)
    crux = add_node(repo, "spec-0a0a0a0a")
    (repo.node / "META.yaml").write_text("not: [valid", encoding="utf-8")
    repo.commit("base: the root's META does not parse")
    prove(repo, crux)
    _, out = classify(repo, capsys)
    assert out.get("needs_review") is True, out


def test_the_root_is_the_declared_one(tmp_path: Path) -> None:
    assert ROOT == "and-reassoc"  # the fixtures above rely on take_in's root


# --- the record: an attestation never reads as if a review had happened -------------------------


@pytest.mark.parametrize("kind", ["intermediate", "calibration"])
def test_the_attestation_records_why_nobody_was_asked(kind: str) -> None:
    review = postmerge.review_block(kind)  # type: ignore[arg-type]
    assert review == {"kind": kind, "reviewer": None, "reference": None}
    doc = postmerge.record_step9(samples.attestation(), merge_commit="3" * 40, review=review)
    assert doc["schema"] == "attestation/v5" and doc["review"]["kind"] == kind
    for extra in ({"reviewer": "someone"}, {"reference": "fidelity/root-1.yaml"}):
        with pytest.raises(ValueError, match="not asked"):
            postmerge.review_block(kind, **extra)  # type: ignore[arg-type]


def test_v4_records_are_still_read() -> None:
    """D-34: versioned, never edited — every attestation merged before v3.20 stays valid."""
    assert (
        "attestation/v4" in bounce.ACCEPTED_SCHEMAS and "attestation/v5" in bounce.ACCEPTED_SCHEMAS
    )
    old = {**samples.attestation(), "schema": "attestation/v4"}
    assert schemas.violations(old, "attestation/v4") == []
    assert schemas.violations(
        {**old, "review": postmerge.review_block("intermediate")}, "attestation/v4"
    )


def test_the_index_says_a_calibration_target_asks_nothing(tmp_path: Path) -> None:
    repo, _ = curated(tmp_path)
    assert products.step9_basis(graphmod.load_target(repo.root, TARGET_ID)) == "review"
    record = repo.target / "target.yaml"
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    doc["calibration"] = True
    record.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert products.step9_basis(graphmod.load_target(repo.root, TARGET_ID)) == "calibration"
