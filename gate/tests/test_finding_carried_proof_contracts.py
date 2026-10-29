"""F32-T0 (R4, R5, R9; Q7, Q15; D-5, D-34 v3.49): the contracts a carried proof is built on.

A partial may carry the proofs of its holes (D-29 v3.49), and a hole whose proof was carried is
born proved with an attestation of its own beside the partial's (D-5 v3.49). Before anything is
checked or written, the record's shape has to exist and every writer has to emit it:

* ``attestation/v8`` is ``v7`` plus ``carried_by``, required and nullable as ``v7``'s
  ``automation`` is, so every record says whether it is a born-proved hole's; the back-pointer
  is facts of the tree (the parent, the assembly's path and hash, the carried file's path and
  hash), never anything of the run, so D-5's comparison masks nothing new (Q7);
* every reader keeps a *set* of the versions it accepts, and every writer emits ``v8`` with
  ``carried_by: null``;
* the path ``attempts/<assembly>.<n>.proof`` has a role of its own, ``hole-proof``, so the
  classifier sees it, and until the step-2 reader exists (T1) no mode takes it (Q15: an older
  pin gives it no role, so nothing reads it as something else);
* ``PROTOCOL_VERSION`` follows the decisions document to 3.49.
"""

from __future__ import annotations

from pathlib import Path

import samples
from harness import TARGET, make_context

from opn_gate import attestation, bounce, modes, paths, pipeline, products, schemas
from opn_gate.paths import Change

PREFIX = f"targets/{TARGET}/nodes/and-swap-reassoc/attempts/"
STEM = "20260912T120000Z-someone-partial"

CARRIED_BY = {
    "node_id": "and-swap-reassoc",
    "assembly": {"path": f"attempts/{STEM}.lean", "artifact_hash": "e" * 64},
    "carried": {"path": f"attempts/{STEM}.1.proof", "sha256": "f" * 64},
}


def test_attestation_v8_is_published_and_pinned() -> None:
    assert "attestation/v8" in schemas.known_schemas()
    hashes = (Path(schemas.__file__).parents[1] / "schemas" / "HASHES").read_text(encoding="utf-8")
    assert "  attestation/v8.json" in hashes
    assert schemas.compute_hashes()["attestation/v8.json"] in hashes


def test_carried_by_is_required_and_nullable() -> None:
    v8 = samples.attestation(schema="attestation/v8", carried_by=None)
    assert schemas.violations(v8, "attestation/v8") == []
    assert schemas.violations({**v8, "carried_by": CARRIED_BY}, "attestation/v8") == []
    missing = {k: v for k, v in v8.items() if k != "carried_by"}
    assert schemas.violations(missing, "attestation/v8"), "carried_by must be required"
    for bad in (
        {**CARRIED_BY, "pr": 12},  # nothing of the run: the record names facts of the tree
        {k: v for k, v in CARRIED_BY.items() if k != "carried"},
        {**CARRIED_BY, "carried": {"path": f"attempts/{STEM}.1.witness", "sha256": "f" * 64}},
        {**CARRIED_BY, "assembly": {"path": f"attempts/{STEM}.lean", "artifact_hash": "x"}},
    ):
        assert schemas.violations({**v8, "carried_by": bad}, "attestation/v8"), bad
    # v7 is unchanged and has no such field (D-34: versioned, never edited).
    assert schemas.violations(samples.attestation(schema="attestation/v7"), "attestation/v7") == []
    assert schemas.violations(
        {**samples.attestation(schema="attestation/v7"), "carried_by": None}, "attestation/v7"
    )


def test_every_reader_accepts_every_version_and_the_writer_emits_v8(tmp_path: Path) -> None:
    """A reader keeps a set (the 2026-10-18 log: a set derived from the current constant drops
    the version before it); the writer emits v8 with ``carried_by: null``."""
    assert attestation.SCHEMA == "attestation/v8"
    assert tuple(f"attestation/v{n}" for n in range(1, 9)) == bounce.ACCEPTED_SCHEMAS
    assert attestation.ACCEPTED_SCHEMAS == bounce.ACCEPTED_SCHEMAS
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=None)
    assert doc["schema"] == "attestation/v8" and doc["carried_by"] is None
    assert schemas.violations(doc, "attestation/v8") == []
    # carried_by is a fact of the tree, so D-5's comparison does not mask it.
    assert "carried_by" not in attestation.MASKED_FIELDS
    assert attestation.compare(doc, {**doc, "carried_by": CARRIED_BY}) == ["carried_by"]


def test_a_carried_proof_has_a_role_and_no_mode_takes_it_yet() -> None:
    """Q15: the role is reserved now, so the classifier says what the file is; T1 gives partial
    mode the reader. Until then a ``.proof`` file beside an assembly fits no mode."""
    where = paths.locate(PREFIX + f"{STEM}.1.proof")
    assert where is not None and where.role == "hole-proof"
    assert where.node_id == "and-swap-reassoc"
    assert "hole-proof" not in paths.MODIFIABLE_ROLES and "hole-proof" not in paths.APPEND_ROLES
    for name in (".proof", f"{STEM}.1.proof/x", f"{STEM}.1.proof.lean"):
        located = paths.locate(PREFIX + name)
        assert located is None or located.role != "hole-proof", name
    # A carried witness is still what it was.
    witness = paths.locate(PREFIX + f"{STEM}.1.witness")
    assert witness is not None and witness.role == "hole-witness"


def test_protocol_version_is_3_49() -> None:
    assert products.PROTOCOL_VERSION == "3.49"


def test_the_precheck_result_documents_holes_proof() -> None:
    """R9: the result's ``holes[].proof`` (path, sha256, checked) is part of the result's
    documented contract before any code fills it (T2)."""
    from precheck import job  # noqa: PLC0415 — gate/precheck is a sibling package

    doc = job.result_document.__doc__ or ""
    assert "``proof``" in doc and "holes[].proof" in doc


def test_a_partial_with_a_proof_file_is_not_classified_as_a_partial_yet() -> None:
    both = [Change("A", PREFIX + f"{STEM}.lean"), Change("A", PREFIX + f"{STEM}.1.proof")]
    assert modes.classify(both).mode is None
