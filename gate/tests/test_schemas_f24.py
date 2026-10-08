"""F24-T1 / AC1: the panel's record schemas accept their own examples and refuse their own
counter-examples (the 2026-10-05 lesson: test a schema's examples against its own patterns before
anyone builds on it)."""

from __future__ import annotations

from typing import Any

import pytest

from opn_gate import schemas

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA"
SIG = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"
SIGNED = {
    "target": "erdos-1",
    "date": "2026-10-08",
    "via": "approval-key",
    "key": KEY,
    "signature": SIG,
}


def ok(doc: dict[str, Any], schema: str) -> bool:
    try:
        schemas.validate(doc, schema)
    except schemas.SchemaError:
        return False
    return True


MOTION = {"schema": "motion/v1", **SIGNED, "opened_by": "alice"}


@pytest.mark.parametrize(
    ("kind", "subject", "valid"),
    [
        ("invite", {"login": "bob"}, True),
        ("invite", {"login": "bob", "note": "the sieve step"}, True),
        ("invite", {"writeup": 1}, False),
        ("invite", {"login": "bob", "threshold": 1}, False),
        ("verify-writeup", {"writeup": 2}, True),
        ("verify-writeup", {"writeup": 2, "login": "bob"}, False),
        ("verify-writeup", {"writeup": 0}, False),
        ("authorship-threshold", {"threshold": 0.05}, True),
        ("authorship-threshold", {"threshold": -1}, False),
        ("authorship-threshold", {}, False),
        ("expel", {"login": "bob"}, False),
    ],
)
def test_motion_examples(kind: str, subject: dict[str, Any], valid: bool) -> None:
    assert ok({**MOTION, "kind": kind, "subject": subject}, "motion/v1") is valid


@pytest.mark.parametrize(
    ("extra", "valid"),
    [
        ({"motion": 1, "login": "bob", "vote": "yes"}, True),
        ({"motion": 1, "login": "bob", "vote": "no"}, True),
        ({"motion": 1, "login": "bob", "vote": "abstain"}, False),
        ({"motion": 0, "login": "bob", "vote": "yes"}, False),
        ({"motion": 1, "login": "-bob", "vote": "yes"}, False),
        ({"motion": 1, "vote": "yes"}, False),
    ],
)
def test_vote_examples(extra: dict[str, Any], valid: bool) -> None:
    assert ok({"schema": "vote/v1", **SIGNED, **extra}, "vote/v1") is valid


WU = {"schema": "writeup/v2", **SIGNED, "signer": "alice"}
RECORD = {"action": "record", "kind": "paper", "title": "On it", "url": "https://arxiv.org/abs/2610.01234",
          "authors": ["alice", "bob"]}  # fmt: skip


@pytest.mark.parametrize(
    ("doc", "valid"),
    [
        (RECORD, True),
        ({**RECORD, "model": "claude-opus-5-5"}, True),
        ({**RECORD, "authors": []}, False),
        ({**RECORD, "authors": ["alice", "alice"]}, False),
        ({**RECORD, "writeup": 1}, False),
        ({**RECORD, "url": "http://x"}, False),
        ({"action": "author-sign", "writeup": 1}, True),
        ({"action": "author-sign"}, False),
        ({"action": "author-sign", "writeup": 1, "title": "x"}, False),
        ({"action": "author-sign", "writeup": 1, "model": "m"}, False),
        ({"action": "arxiv", "writeup": 1, "arxiv": "2610.01234v2"}, True),
        ({"action": "arxiv", "writeup": 1, "arxiv": "math/0601001"}, False),
        ({"action": "arxiv", "writeup": 1}, False),
        ({"action": "submitted", "writeup": 1, "journal": "Annals"}, True),
        ({"action": "submitted", "writeup": 1}, False),
        ({"action": "submitted", "writeup": 1, "journal": "Annals", "doi": "10.1000/x"}, False),
        (
            {
                "action": "accepted",
                "writeup": 1,
                "journal": "Annals",
                "doi": "10.4007/annals.2027.1",
            },
            True,
        ),
        ({"action": "accepted", "writeup": 1, "journal": "Annals"}, True),
        ({"action": "rejected", "writeup": 1, "journal": "Annals"}, True),
        ({"action": "withdrawn", "writeup": 1}, True),
        ({"action": "withdrawn", "writeup": 1, "journal": "Annals"}, False),
    ],
)
def test_writeup_v2_examples(doc: dict[str, Any], valid: bool) -> None:
    assert ok({**WU, **doc}, "writeup/v2") is valid


STEWARD = {"schema": "steward/v3", **SIGNED, "action": "commit", "login": "bob", "name": "Bob",
           "link": None, "commitment": "x"}  # fmt: skip


@pytest.mark.parametrize(
    ("admitted_by", "valid"),
    [("self", True), ("carol", True), ("motion:3", True), ("motion:0", False), ("motion:", False)],
)
def test_steward_v3_admitted_by(admitted_by: str, valid: bool) -> None:
    assert ok({**STEWARD, "admitted_by": admitted_by}, "steward/v3") is valid


def setting(value: Any) -> dict[str, Any]:
    return {"value": value, "since": "2026-10-08", "reason": "The owner's ruling of 2026-10-08."}


PANEL = {
    "vote_threshold": setting({"numerator": 1, "denominator": 2}),
    "vote_window_days": setting(14),
    "vote_minimum": setting(2),
    "vote_minimum_from": setting(3),
    "steward_cap": setting(5),
    "steward_lapse_days": setting(183),
}
POLICY = {
    "schema": "policy/v3",
    "steward_rule": {"enforced": False, "since": None, "evidence": None},
    "steward_admission": "open",
    "panel": PANEL,
}


def test_policy_v3_accepts_the_defaults() -> None:
    assert ok(POLICY, "policy/v3")


@pytest.mark.parametrize(
    ("name", "value"),
    [("vote_window_days", 0), ("vote_minimum", 0), ("steward_cap", 0), ("steward_lapse_days", 0),
     ("vote_threshold", {"numerator": 0, "denominator": 2}), ("vote_window_days", "14")],
)  # fmt: skip
def test_policy_v3_refuses_a_bad_value(name: str, value: Any) -> None:
    assert not ok({**POLICY, "panel": {**PANEL, name: setting(value)}}, "policy/v3")


def test_policy_v3_needs_a_reason_for_every_setting() -> None:
    panel = {**PANEL, "steward_cap": {"value": 5, "since": "2026-10-08"}}
    assert not ok({**POLICY, "panel": panel}, "policy/v3")
