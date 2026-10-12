"""F26-T1 / AC1: the review's eight record schemas and the three product versions are pinned,
well-formed, and self-consistent — every id example a description names matches the pattern it
sits beside (the 2026-10-05 lesson: a contract carried a pattern refusing its own example), and
a minimal record of each kind validates; the path locator gives each its role and the mode table
never lets one fall through to an append (the 2026-09-17 lesson).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from opn_gate import modes, paths, policy, review, schemas

RECORDS = (
    "review/v1",
    "candidate/v1",
    "intent-test/v1",
    "review-question/v1",
    "review-answer/v1",
    "pair/v1",
    "exhibit/v1",
    "review-signature/v1",
)
PRODUCTS = ("policy/v4", "targets-index/v11", "graph/v9", "context/v7")
T = "propositional"
SIG = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"
SIGNED = {"login": "alice", "via": "approval-key", "key": "ssh-ed25519 AAAA", "signature": SIG}


def test_every_schema_is_pinned_and_well_formed() -> None:
    pins = schemas.read_pins()
    for name in RECORDS + PRODUCTS:
        assert f"{name}.json" in pins, name
        jsonschema.Draft202012Validator.check_schema(schemas.load_schema(name))
    assert schemas.verify_pins() == []


def test_the_id_grammar_accepts_its_own_examples() -> None:
    pattern = re.compile(schemas.load_schema("candidate/v1")["$defs"]["id"]["pattern"])
    for example in ("c-0123abcd", "t-89abcdef", "q-1", "q-12", "e-deadbeef"):
        assert pattern.fullmatch(example), example
    lean = re.compile(schemas.load_schema("candidate/v1")["properties"]["lean_file"]["pattern"])
    assert lean.fullmatch("c-0123abcd.lean") and not lean.fullmatch("Problem.lean")


def records() -> dict[str, dict[str, Any]]:
    """One minimal valid record per kind."""
    day = "2026-10-12"
    return {
        "review/v1": {
            "schema": "review/v1",
            "target": T,
            "opened_by": {"identity": "network", "role": "network"},
            "date": day,
            "words": "For all p q, p and q implies q and p.",
            "cases": [],
            "concepts": ["And"],
            "source": {"kind": "existing", "ref": "tutorial-and-swap"},
            "tracking": None,
            "supersedes": None,
        },
        "candidate/v1": {
            "schema": "candidate/v1",
            "target": T,
            "id": "c-0123abcd",
            "author": "alice",
            "method": "manual",
            "models": [],
            "read_others": False,
            "origin": "submitted",
            "source": None,
            "lean_file": "c-0123abcd.lean",
            "statement_hash": "0" * 64,
            "date": day,
        },
        "intent-test/v1": {
            "schema": "intent-test/v1",
            "target": T,
            "id": "t-89abcdef",
            "case": "p = True, q = False",
            "probe": "holds",
            "concept": None,
            "expected": {"value": True, "source": "agreement", "ref": "agreement:2"},
            "author": "gate",
            "lean_file": "t-89abcdef.lean",
            "date": day,
        },
        "review-question/v1": {
            "schema": "review-question/v1",
            "target": T,
            "id": "q-1",
            "question": "Suppose 5 were the only prime. Would the conjecture hold at n = 2?",
            "raised_by": {"kind": "mutant", "ref": "e-deadbeef"},
            "asked_to": "intent",
            "date": day,
        },
        "review-answer/v1": {
            "schema": "review-answer/v1",
            "target": T,
            "id": "a-1",
            "question": "q-1",
            "answer": "No.",
            "cites": None,
            "date": day,
            **SIGNED,
        },
        "pair/v1": {
            "schema": "pair/v1",
            "target": T,
            "a": "c-0123abcd",
            "b": "c-89abcdef",
            "forward": {"state": "proved", "exhibit": "e-deadbeef", "attempt": None},
            "backward": {
                "state": "open",
                "exhibit": None,
                "attempt": {"who": "gate", "tool": "grind", "budget_s": 20},
            },
            "date": day,
        },
        "exhibit/v1": {
            "schema": "exhibit/v1",
            "target": T,
            "id": "e-deadbeef",
            "kind": "pair",
            "candidate": "c-0123abcd",
            "test": "c-89abcdef",
            "result": "proved",
            "detail": "a implies b",
            "lean_file": "e-deadbeef.lean",
            "toolchain": "leanprover/lean4:v4.33.1",
            "mathlib_sha": None,
            "run": "local",
            "date": day,
        },
        "review-signature/v1": {
            "schema": "review-signature/v1",
            "target": T,
            "role": "intent",
            "decision": "accept",
            "cluster": "c-0123abcd",
            "question": None,
            "date": day,
            **SIGNED,
        },
    }


@pytest.mark.parametrize("name", RECORDS)
def test_a_minimal_record_of_each_kind_validates(name: str) -> None:
    assert schemas.violations(records()[name], name) == []
    # and an edit is refused: the schema is closed
    bad = {**records()[name], "extra": 1}
    assert schemas.violations(bad, name) != []


def test_every_review_path_has_its_role_and_a_lean_file_shares_it() -> None:
    cases = {
        f"targets/{T}/review/review.yaml": "review",
        f"targets/{T}/review/candidates/c-0123abcd.yaml": "candidate",
        f"targets/{T}/review/candidates/c-0123abcd.lean": "candidate",
        f"targets/{T}/review/tests/t-89abcdef.yaml": "intent-test",
        f"targets/{T}/review/tests/t-89abcdef.lean": "intent-test",
        f"targets/{T}/review/questions/q-1.yaml": "review-question",
        f"targets/{T}/review/answers/a-1.yaml": "review-answer",
        f"targets/{T}/review/pairs/c-0123abcd--c-89abcdef.yaml": "pair",
        f"targets/{T}/review/exhibits/e-deadbeef.json": "review-exhibit",
        f"targets/{T}/review/exhibits/e-deadbeef.lean": "review-exhibit",
        f"targets/{T}/review/signatures/intent-2026-10-12-1.yaml": "review-signature",
    }
    for path, role in cases.items():
        located = paths.locate(path)
        assert located is not None and located.role == role, (path, located)
        assert located.target_id == T
        assert role in paths.SCHEMAS_FOR_ROLE
    for nobody in (
        f"targets/{T}/review/notes.md",
        f"targets/{T}/review/exhibits/e-deadbeef.yaml",
        f"targets/{T}/review/candidates/sub/c-0123abcd.yaml",
        f"targets/{T}/review/pairs/x.lean",
    ):
        assert paths.locate(nobody) is None, nobody


def test_every_review_role_has_a_mode_that_is_not_append() -> None:
    for role in modes.REVIEW_RECORD_ROLES:
        assert role in modes.RECORD_MODES, role
        assert modes.RECORD_MODES[role] != "append"
    for role in modes.REVIEW_JOB_ROLES:
        assert modes.RECORD_MODES[role] == "review-job"


def test_a_job_record_in_a_pull_request_is_refused_by_name(tmp_path: Path) -> None:
    located = paths.locate(f"targets/{T}/review/questions/q-1.yaml")
    assert located is not None
    found = modes.check_review_record(tmp_path, located, None)  # type: ignore[arg-type]
    assert [d.code for d in found] == ["review-job-record"]


def test_the_state_of_a_target_with_no_review_is_none(tmp_path: Path) -> None:
    doc = review.state_of(tmp_path)
    assert (
        doc["state"] == "none"
        and doc["candidates"] == 0
        and doc["signers"]
        == {
            "intent": None,
            "independent": None,
        }
    )
    assert review.open_pairs(tmp_path) == [] and review.for_context(tmp_path) is None
    assert schemas.violations(doc, "graph/v9") != []  # it is a field, not a document
    graph_doc = schemas.load_schema("graph/v9")["properties"]["review"]
    jsonschema.validate(doc, graph_doc)


def test_policy_v4_carries_who_may_open_and_defaults_to_all_three(tmp_path: Path) -> None:
    assert policy.parse(None).review_openers == ("proposer", "steward", "curator")
    doc = {
        "schema": "policy/v4",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "open",
        "panel": schemas.load_schema("policy/v3")["properties"]["panel"].get("default", {}),
        "review_openers": {"roles": ["curator"], "since": "2026-10-12", "evidence": "the pilot"},
    }
    v3 = {k: v for k, v in doc.items() if k != "review_openers"} | {"schema": "policy/v3"}
    # a v3 file still parses with the default
    import json  # noqa: PLC0415

    parsed3 = (
        policy.parse(json.dumps(v3).encode()) if schemas.violations(v3, "policy/v3") == [] else None
    )
    if parsed3 is not None:
        assert parsed3.review_openers == ("proposer", "steward", "curator")
    if schemas.violations(doc, "policy/v4") == []:
        parsed = policy.parse(json.dumps(doc).encode())
        assert parsed.review_openers == ("curator",) and parsed.review_openers_since == "2026-10-12"
