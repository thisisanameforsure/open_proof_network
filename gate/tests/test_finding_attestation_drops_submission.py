"""Finding attestation-drops-submission (the Euclid tester, 2026-09-13; F07-R13, D-23, D-34, D-5).

A service-opened pull request carries two blocks: the ``opn-precheck-attestation`` the bounce rule
reads and the ``opn-submission`` block declaring who submitted and with what. ``attestation.build``
can record both — ``submitter``, ``model_and_tooling``, ``tooling`` and ``precheck_attestation`` —
but no command hands it the block: ``gate`` builds without ``submission=``, ``postmerge`` reads the
body only for ``--apply-partial`` and never records the precheck it consumed, and ``reproduce``
copies step 9 from the committed record but not these four declared fields, so a correct record
could never reproduce. Every live attestation so far says ``submitter: null, undeclared``.

The pseudonym and tooling are deliberately not the defaults, so a default cannot pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
from harness import TUTORIAL
from test_cli_sandboxed import (
    NODES,
    Seam,
    gate_argv,
    git_repo,
    postmerge_argv,
    precheck_body,
    run,
)

from opn_gate import attestation, bounce, cli, schemas, submission

PSEUDONYM = "euclid-tester-7c2"
TOOLING = {"model": "claude-opus-5", "version": "2026-09", "harness": "claude-code"}
DECLARED = "claude-opus-5 2026-09 claude-code"
REASON = (
    "finding attestation-drops-submission (F07-R13, D-23, D-34, D-5): {defect}; "
    "fix: F07-T14 (Mike, 2026-09-14)"
)


def submission_block() -> str:
    return submission.render_block(
        samples.submission_meta(
            identity={"pseudonym": PSEUDONYM, "proof_kind": "github"},
            tooling=dict(TOOLING),
        )
    )


def service_body(root: Path, **precheck_overrides: Any) -> str:
    """The body the service writes: the precheck block, then the submission block."""
    return precheck_body(root, **precheck_overrides) + "\n" + submission_block() + "\n"


def raw_precheck_hash(body: str) -> str:
    """The digest the bounce rule takes of the attached block (bounce.evaluate)."""
    raw = bounce.extract_block(body)
    assert raw is not None
    return schemas.content_hash(raw.encode("utf-8"))


def assert_declared(doc: dict[str, Any]) -> None:
    assert doc["submitter"] == PSEUDONYM, doc["submitter"]
    assert doc["model_and_tooling"] == DECLARED, doc["model_and_tooling"]
    assert doc["tooling"] == {"model": TOOLING["model"], "harness": TOOLING["harness"]}


@pytest.mark.xfail(
    strict=True,
    reason=REASON.format(
        defect="cli.run_gate never passes the opn-submission block to attestation.build, so "
        "submitter is null and tooling undeclared"
    ),
)
def test_the_gate_run_records_the_submission_block(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, base = git_repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text(service_body(root))
    out_dir = tmp_path / "o"
    code, out, err = run(capsys, *gate_argv(root, base, body, out_dir))
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", err
    doc = schemas.load_json(out_dir / "attestation.json")
    assert_declared(doc)
    assert doc["precheck_attestation"]["signature_kind"] == "none"
    assert len(doc["precheck_attestation"]["hash"]) == 64
    assert schemas.violations(doc) == []


@pytest.mark.xfail(
    strict=True,
    reason=REASON.format(
        defect="cli.run_postmerge reads the body only for --apply-partial and records neither "
        "the submission block nor the precheck it consumed"
    ),
)
def test_postmerge_records_the_block_and_the_consumed_precheck(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, _base = git_repo(tmp_path)
    body_text = service_body(root)
    body = tmp_path / "body.md"
    body.write_text(body_text)
    out_dir = tmp_path / "o"
    code, out, err = run(
        capsys,
        *postmerge_argv(root, out_dir, "--review-kind", "tutorial", "--pr-body-file", str(body)),
    )
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", err
    doc = schemas.load_json(out_dir / "attestation.json")
    assert_declared(doc)
    assert doc["precheck_attestation"] == {
        "hash": raw_precheck_hash(body_text),
        "signature_kind": "none",
    }
    assert schemas.violations(doc) == []

    # The merge already passed the bounce rule at gate time: a precheck older than the graph's
    # max age is still what was consumed, and the post-merge record says so (no age rule here).
    stale_text = service_body(
        root,
        signature={
            "kind": "none",
            "key_id": None,
            "value": None,
            "timestamp": "2020-01-01T00:00:00Z",
        },
    )
    stale = tmp_path / "stale.md"
    stale.write_text(stale_text)
    code, out, err = run(
        capsys,
        *postmerge_argv(
            root, tmp_path / "o2", "--review-kind", "tutorial", "--pr-body-file", str(stale)
        ),
    )
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", err
    old = schemas.load_json(tmp_path / "o2" / "attestation.json")
    assert old["precheck_attestation"] == {
        "hash": raw_precheck_hash(stale_text),
        "signature_kind": "none",
    }
    assert_declared(old)


@pytest.mark.xfail(
    strict=True,
    reason=REASON.format(
        defect="the gate run records the consumed precheck and the post-merge record does not, "
        "so the two records of one merge disagree"
    ),
)
def test_the_gate_run_and_the_post_merge_record_agree_once_step_9_is_masked(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, base = git_repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text(service_body(root))
    code, _out, err = run(capsys, *gate_argv(root, base, body, tmp_path / "g"))
    assert code == cli.EXIT_PASS, err
    code, _out, err = run(
        capsys,
        *postmerge_argv(
            root, tmp_path / "p", "--review-kind", "tutorial", "--pr-body-file", str(body)
        ),
    )
    assert code == cli.EXIT_PASS, err
    gate_doc = schemas.load_json(tmp_path / "g" / "attestation.json")
    post_doc = schemas.load_json(tmp_path / "p" / "attestation.json")
    assert attestation.compare(gate_doc, attestation.with_step9(post_doc, gate_doc)) == []


@pytest.mark.xfail(
    strict=True,
    reason=REASON.format(
        defect="with no opn-submission block neither postmerge's --author nor the gate's "
        "OPN_PR_AUTHOR reaches the record, so a hand-opened merge names nobody"
    ),
)
def test_a_hand_opened_merge_names_the_login_as_submitter(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, base = git_repo(tmp_path)
    monkeypatch.delenv("OPN_PR_AUTHOR", raising=False)
    code, out, err = run(
        capsys,
        *postmerge_argv(root, tmp_path / "p", "--review-kind", "tutorial", "--author", "octocat"),
    )
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", err
    post = schemas.load_json(tmp_path / "p" / "attestation.json")
    assert post["submitter"] == "octocat", post["submitter"]
    assert post["model_and_tooling"] == "undeclared"
    assert post["precheck_attestation"] == {"hash": None, "signature_kind": None}

    # The gate job: a hand-opened pull request still attaches a precheck, but no submission block;
    # the workflow passes the login as OPN_PR_AUTHOR (a new flag would break the pinned gate).
    monkeypatch.setenv("OPN_PR_AUTHOR", "octocat")
    body = tmp_path / "body.md"
    body.write_text(precheck_body(root))
    code, out, err = run(capsys, *gate_argv(root, base, body, tmp_path / "g"))
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", err
    gated = schemas.load_json(tmp_path / "g" / "attestation.json")
    assert gated["submitter"] == "octocat", gated["submitter"]
    assert gated["model_and_tooling"] == "undeclared"
    assert gated["tooling"] == {"model": None, "harness": None}


@pytest.mark.xfail(
    strict=True,
    reason=REASON.format(
        defect="cli.run_reproduce copies only step 9 from the committed record, so a record "
        "carrying submitter, model_and_tooling, tooling and precheck_attestation never reproduces"
    ),
)
def test_reproduce_compare_copies_the_declared_fields(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    body_text = service_body(root)
    body = tmp_path / "body.md"
    body.write_text(body_text)
    code, _out, err = run(
        capsys,
        *postmerge_argv(
            root, tmp_path / "p", "--review-kind", "tutorial", "--pr-body-file", str(body)
        ),
    )
    assert code == cli.EXIT_PASS, err
    committed = schemas.load_json(tmp_path / "p" / "attestation.json")
    # The committed record as the post-merge job writes it once it records the submission
    # (idempotent after F07-T14; today postmerge leaves these null, which is its own test above).
    committed.update(
        submitter=PSEUDONYM,
        model_and_tooling=DECLARED,
        tooling={"model": TOOLING["model"], "harness": TOOLING["harness"]},
        precheck_attestation={"hash": raw_precheck_hash(body_text), "signature_kind": "none"},
    )
    assert schemas.violations(committed) == []
    committed_path = tmp_path / "000007.json"
    committed_path.write_bytes(schemas.canonical_json(committed))

    code, out, err = run(
        capsys,
        "reproduce", "--graph", str(root), "--commit", head, "--node", TUTORIAL,
        "--out", str(tmp_path / "r"), "--compare", str(committed_path),
    )  # fmt: skip
    assert out == {"identical": True, "differing_fields": []}, out
    assert code == cli.EXIT_PASS, err
    assert (tmp_path / "r" / "tree" / NODES / TUTORIAL / "Proof.lean").is_file()
