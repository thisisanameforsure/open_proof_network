"""F25-T3 / AC2: the ``automation`` block end to end in the gate (F25-R1, R3; D-23 v3.37).

A ``submission-meta/v1`` block still parses with ``automation`` read as absent; a v2 block is
held to the trio (method, models, framework) and to integer token counts; ``attestation/v7``
copies the block as declared and ``ledger/v2`` carries it on the line the merge earns, or null;
the free ``model_and_tooling`` string is unchanged, ``undeclared`` included; and a v1 ledger file
is lifted to v2 with null on every entry it already had.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
from test_cli_sandboxed import Seam, git_repo
from test_finding_ledger_credits_merges import PROVED, commit_proof, entries, ledger_run

from opn_gate import attestation as attestationmod
from opn_gate import ledger, schemas, submission

V1 = "submission-meta/v1"
V2 = "submission-meta/v2"


def block(doc: dict[str, Any]) -> dict[str, Any]:
    """The document as the gate reads it back out of a pull-request body."""
    parsed = submission.extract("some words\n\n" + submission.render_block(doc) + "\nmore\n")
    assert parsed is not None, doc
    return parsed


# --- R1: v1 still parses; the trio; integer tokens -----------------------------------------------


def test_a_v1_block_parses_with_automation_absent() -> None:
    doc = block(samples.submission_meta())
    assert doc["schema"] == V1
    assert submission.automation(doc) is None
    assert submission.model_and_tooling(doc) == submission.UNDECLARED
    assert submission.SCHEMA == V2
    assert submission.ACCEPTED_SCHEMAS == (V1, V2)


def test_a_v2_block_parses_and_carries_the_block_as_declared() -> None:
    doc = block(samples.submission_meta_v2())
    assert submission.automation(doc) == samples.automation()
    # a v2 block without the optional field is still a v2 block, and reads as no disclosure
    bare = samples.submission_meta_v2()
    del bare["automation"]
    assert schemas.violations(bare, V2) == []
    assert submission.automation(bare) is None


@pytest.mark.parametrize("field", ["method", "models", "framework"])
def test_the_trio_is_required(field: str) -> None:
    auto = samples.automation()
    del auto[field]
    found = schemas.violations(samples.submission_meta_v2(automation=auto), V2)
    assert found, field
    assert any(field in v.message for v in found), [v.message for v in found]


def test_the_method_is_the_registrys_vocabulary() -> None:
    for method in ("manual", "copilot", "agent", "autonomous", "other"):
        doc = samples.submission_meta_v2(automation=samples.automation(method=method))
        assert schemas.violations(doc, V2) == [], method
    bad = samples.submission_meta_v2(automation=samples.automation(method="llm"))
    assert schemas.violations(bad, V2) != []


def test_models_is_a_non_empty_list_of_names() -> None:
    assert schemas.violations(
        samples.submission_meta_v2(automation=samples.automation(models=[])), V2
    )
    assert schemas.violations(
        samples.submission_meta_v2(automation=samples.automation(models="claude")), V2
    )


@pytest.mark.parametrize("tokens", [{"input": "12", "output": 3}, {"input": 1.5, "output": 2}])
def test_tokens_are_integers(tokens: dict[str, Any]) -> None:
    doc = samples.submission_meta_v2(automation=samples.automation(tokens=tokens))
    found = schemas.violations(doc, V2)
    assert any("tokens" in v.path for v in found), [(v.path, v.message) for v in found]


def test_tokens_and_the_other_cost_fields_are_optional_and_accepted() -> None:
    auto = samples.automation(
        tool_setup="one MCP server, the guide",
        wall_time="about 40 minutes",
        tokens={"input": 120000, "output": 9000},
        hardware="one laptop; hosted models",
        spend="subscription",
    )
    doc = samples.submission_meta_v2(automation=auto)
    assert schemas.violations(doc, V2) == []
    assert submission.automation(block(doc)) == auto


def test_a_field_the_block_does_not_know_is_refused() -> None:
    doc = samples.submission_meta_v2(automation=samples.automation(cost_usd=12.4))
    assert schemas.violations(doc, V2) != []


# --- R3: the attestation and the ledger carry it; the string is unchanged ------------------------


def test_the_attestation_copies_the_block_as_declared() -> None:
    doc = samples.attestation(automation=samples.automation())
    assert attestationmod.SCHEMA == "attestation/v7"
    assert schemas.violations(doc, attestationmod.SCHEMA) == []
    assert schemas.violations(samples.attestation(automation=None), attestationmod.SCHEMA) == []
    # the block's own rule holds inside the attestation too
    broken = samples.attestation(automation={"method": "agent"})
    assert schemas.violations(broken, attestationmod.SCHEMA) != []


def test_model_and_tooling_is_unchanged_beside_the_block() -> None:
    declared = samples.submission_meta_v2(
        tooling={"model": "claude-fable-5-1", "version": "2026-10", "harness": "Claude Code"}
    )
    assert submission.model_and_tooling(declared) == "claude-fable-5-1 2026-10 Claude Code"
    assert submission.model_and_tooling(samples.submission_meta_v2()) == submission.UNDECLARED
    assert submission.UNDECLARED == "undeclared"


def test_a_ledger_entry_carries_the_block_or_null() -> None:
    base = {
        "line": "proof",
        "target": "propositional",
        "node": PROVED,
        "artifact": "Proof.lean",
        "merge_commit": "4" * 40,
        "date": "2026-10-11T12:00:00Z",
    }
    with_block = ledger.Entry(**base, automation=samples.automation())  # type: ignore[arg-type]
    without = ledger.Entry(**base)  # type: ignore[arg-type]
    empty = {"schema": ledger.SCHEMA, "identity": "alice", "entries": []}
    doc = ledger.append(ledger.append(empty, with_block), without)
    assert doc["schema"] == "ledger/v2"
    assert [e["automation"] for e in doc["entries"]] == [samples.automation(), None]
    assert doc["entries"][0]["tooling"] == ledger.UNDECLARED  # the string stays what it was


def test_a_v1_ledger_file_is_lifted_and_rewritten_as_v2_with_null_on_old_entries(
    tmp_path: Path,
) -> None:
    old: dict[str, Any] = {
        "schema": "ledger/v1",
        "identity": "alice",
        "entries": [
            {
                "line": "proof",
                "target": "propositional",
                "node": PROVED,
                "artifact": "Proof.lean",
                "merge_commit": "4" * 40,
                "date": "2026-09-14T12:00:00Z",
                "tooling": "claude-opus-5 2026-09 claude-code",
                "status": "active",
            }
        ],
    }
    assert schemas.violations(old, "ledger/v1") == []
    path = ledger.ledger_path(tmp_path, "alice")
    path.parent.mkdir(parents=True)
    path.write_bytes(schemas.canonical_json(old))
    loaded = ledger.load(tmp_path, "alice")
    assert loaded["schema"] == "ledger/v2"
    (entry,) = ledger.entries_of(loaded)
    assert entry["automation"] is None
    assert entry["tooling"] == "claude-opus-5 2026-09 claude-code"
    ledger.write(tmp_path, loaded)
    rewritten = schemas.load_json(path, "ledger/v2")
    first: dict[str, Any] = old["entries"][0]
    assert ledger.entries_of(rewritten) == [{**first, "automation": None}]


# --- the post-merge job: the entry carries what the attestation attested -------------------------


def attest(root: Path, name: str, merge_commit: str, automation: dict[str, Any] | None) -> None:
    directory = root / "attestations"
    directory.mkdir(exist_ok=True)
    doc = samples.attestation(
        node_id=PROVED,
        merge_commit=merge_commit,
        runner="hosted",
        review={"kind": "pr-approval", "reviewer": "rev", "reference": None},
        model_and_tooling="claude-fable-5-1 Claude Code 2.1",
        submitter="alice",
        automation=automation,
    )
    (directory / name).write_bytes(schemas.canonical_json(schemas.validate(doc)))


def test_a_merged_proof_whose_attestation_declares_automation_earns_an_entry_carrying_it(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_proof(root, git, PROVED, author="alice")
    attest(root, "000006.json", "e" * 40, samples.automation(method="manual"))  # another merge
    attest(root, "000007.json", head, samples.automation())
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    (entry,) = entries(root, "alice")
    assert entry["automation"] == samples.automation()
    assert entry["tooling"] == "claude-fable-5-1 Claude Code 2.1"


def test_a_merged_proof_whose_attestation_declares_none_earns_an_entry_with_null(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_proof(root, git, PROVED, author="alice")
    attest(root, "000007.json", head, None)
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    (entry,) = entries(root, "alice")
    assert entry["automation"] is None
    assert ledger.merge_automation(root, head) is None
    assert ledger.merge_automation(root, "f" * 40) is None  # no record: nothing
