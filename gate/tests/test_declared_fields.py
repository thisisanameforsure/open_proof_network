"""The two helpers F07-T14 adds for the declared fields of an attestation (F07-R13; D-23, D-34).

``bounce.consumed`` names the precheck block a merge consumed without re-applying the bounce rule;
``submission.tooling`` reads the attestation's ``tooling`` object out of the submission block;
``cli.with_declared`` and ``cli.declare_submitter`` carry them through a reproduction and a
hand-opened pull request. The command-level behaviour is
``test_finding_attestation_drops_submission.py``; these are the edges it does not reach.
"""

from __future__ import annotations

from typing import Any

import pytest
import samples

from opn_gate import attestation, bounce, cli, schemas, submission


def precheck_block(**overrides: Any) -> str:
    return bounce.render_block(samples.attestation(**overrides))


# --- bounce.consumed ---------------------------------------------------------------------------


def test_consumed_names_the_hash_and_kind_of_the_attached_block() -> None:
    body = "Submitted.\n\n" + precheck_block() + "\n"
    raw = bounce.extract_block(body)
    assert raw is not None
    assert bounce.consumed(body) == {
        "hash": schemas.content_hash(raw.encode("utf-8")),
        "signature_kind": "none",
    }


def test_consumed_agrees_with_the_digest_the_bounce_rule_takes() -> None:
    body = precheck_block()
    decision = bounce.evaluate(
        bounce.PrecheckPolicy(
            pr_body=body,
            accepted_signatures=("none",),
            max_age_s=10**9,
            now=attestation.utc_now(),
            node_id="someone-else",  # bounced on the node, but the digest is taken first
            statement_hash="",
        )
    )
    assert decision.bounced
    assert bounce.consumed(body)["hash"] == decision.attestation_hash


def test_consumed_is_two_nones_without_a_block() -> None:
    assert bounce.consumed("") == {"hash": None, "signature_kind": None}
    assert bounce.consumed("no fenced block here") == {"hash": None, "signature_kind": None}


def test_consumed_applies_no_rule_to_an_old_or_failing_precheck() -> None:
    stale = precheck_block(
        verdict="fail",
        signature={
            "kind": "service",
            "key_id": "k",
            "value": "v",
            "timestamp": "2020-01-01T00:00:00Z",
        },
    )
    doc = bounce.consumed(stale)
    assert doc["signature_kind"] == "service"
    assert doc["hash"] is not None and len(doc["hash"]) == 64


@pytest.mark.parametrize(
    "inner",
    ["{not json", "[1, 2, 3]", '{"signature": "a string"}', '{"signature": {"kind": null}}'],
)
def test_a_block_that_is_not_an_attestation_still_names_its_hash_and_no_kind(inner: str) -> None:
    body = f"```json\n{bounce.MARKER}\n{inner}\n```"
    doc = bounce.consumed(body)
    assert doc == {"hash": schemas.content_hash(inner.encode("utf-8")), "signature_kind": None}


# --- submission.tooling ------------------------------------------------------------------------


def test_tooling_reads_model_and_harness_and_drops_the_version() -> None:
    block = samples.submission_meta(tooling={"model": "m", "version": "v", "harness": "h"})
    assert submission.tooling(block) == {"model": "m", "harness": "h"}


def test_tooling_is_all_none_without_a_block_or_with_nothing_declared() -> None:
    assert submission.tooling(None) == {"model": None, "harness": None}
    assert submission.tooling({}) == {"model": None, "harness": None}
    assert submission.tooling({"tooling": {"model": "", "harness": None}}) == {
        "model": None,
        "harness": None,
    }


def test_tooling_keeps_one_field_when_only_one_is_declared() -> None:
    assert submission.tooling({"tooling": {"model": "m"}}) == {"model": "m", "harness": None}


# --- cli.with_declared and cli.declare_submitter -----------------------------------------------


def test_with_declared_copies_exactly_the_four_declared_fields() -> None:
    reproduction = samples.attestation()
    committed = dict(reproduction)
    committed.update(
        submitter="alice",
        model_and_tooling="m v h",
        tooling={"model": "m", "harness": "h"},
        precheck_attestation={"hash": "a" * 64, "signature_kind": "service"},
        verdict="fail",  # not declared: a real difference must survive the copy
    )
    out = cli.with_declared(reproduction, committed)
    for key in cli.DECLARED_FIELDS:
        assert out[key] == committed[key]
    assert out["verdict"] == reproduction["verdict"]
    assert attestation.compare(committed, out) == ["verdict"]
    assert reproduction["submitter"] is None  # the input is not mutated


def test_with_declared_leaves_a_field_the_committed_record_lacks() -> None:
    reproduction = samples.attestation(submitter="bob")
    committed = {k: v for k, v in reproduction.items() if k != "submitter"}
    assert cli.with_declared(reproduction, committed)["submitter"] == "bob"


def test_declare_submitter_fills_only_an_empty_submitter() -> None:
    doc = samples.attestation()
    assert doc["submitter"] is None
    filled = cli.declare_submitter(doc, "octocat")
    assert filled["submitter"] == "octocat"
    assert doc["submitter"] is None
    assert cli.declare_submitter(filled, "someone-else")["submitter"] == "octocat"
    assert cli.declare_submitter(doc, None)["submitter"] is None
    assert cli.declare_submitter(doc, "")["submitter"] is None


def test_declare_submitter_refuses_a_login_the_schema_rejects() -> None:
    with pytest.raises(schemas.SchemaError):
        cli.declare_submitter(samples.attestation(), "x" * 500)
