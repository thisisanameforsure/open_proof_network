"""F05-T29: ``POST /literature`` (D-3, D-25, D-32 v3.35; the amendment of 2026-10-08 §2).

Any contributor proposes what the literature says of a statement: the service writes an
unsigned ``literature/v1`` record as the token's identity, dated now, and opens it on the node's
``literature/<ts>-<contributor>.yaml`` through the append machinery (one target, same-second
rule, duplicate rule). The pull request names the target's current stewards as the people whose
confirmation it awaits, and says a curator may confirm too: that is the notification the
amendment names.
"""

from __future__ import annotations

from typing import Any

import yaml
from api_fakes import TUTORIAL_NODE, Harness

from opn_gate import schemas, steward

TARGET = "propositional"
NODE = TUTORIAL_NODE
NODE_DIR = f"targets/{TARGET}/nodes/{NODE}/"
ROUTE = "/literature"


def steward_record(login: str, n: int, action: str = steward.COMMIT) -> dict[str, Any]:
    return {
        "schema": "steward/v2",
        "target": TARGET,
        "action": action,
        "login": login,
        "name": login.title(),
        "link": None,
        "commitment": steward.SENTENCE_FOR[action],
        "date": "2026-10-04",
        "via": "approval-key",
        "admitted_by": "self",
        "key": "ssh-ed25519 AAAA",
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n",
    }


def seed_stewards(h: Harness, *records: tuple[str, str]) -> None:
    """``(login, action)`` records under the target's ``stewards/``, in order."""
    for n, (login, action) in enumerate(records, start=1):
        h.githost.files[f"targets/{TARGET}/{steward.DIR}/{n}.yaml"] = yaml.safe_dump(
            steward_record(login, n, action), sort_keys=False
        ).encode()
    h.context.files.clear()
    h.context.listings.clear()


def proposal(**over: Any) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "status": "known",
        "references": [
            {
                "title": "Granville and Ramaré, Explicit bounds on exponential sums (1996)",
                "url": "https://doi.org/10.1112/S0025579300011608",
                "note": "Theorem 1 proves the statement for all n.",
            }
        ],
        "summary": "A proof is published; nothing in Mathlib formalises it.",
        "model_and_tooling": None,
    } | over


def post(h: Harness, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(ROUTE, json=body, headers=h.auth(token))


def only_file(h: Harness) -> tuple[str, str]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    return next(iter(push.files.items()))


# --- the record ----------------------------------------------------------------------------------


def test_a_proposal_lands_as_an_unsigned_literature_record_by_the_caller(harness: Harness) -> None:
    """The record is literature/v1, attributed to the token's identity, dated now, with every
    signature field null; it sits at the node's literature/<ts>-<contributor>.yaml."""
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, proposal())
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path == NODE_DIR + "literature/20260909T120000Z-alice.yaml"
    doc = yaml.safe_load(content)
    assert schemas.violations(doc, "literature/v1") == []
    assert doc["schema"] == "literature/v1"
    assert (doc["node"], doc["contributor"], doc["date"]) == (NODE, "alice", "2026-09-09T12:00:00Z")
    assert doc["status"] == "known"
    assert doc["references"] == proposal()["references"]
    assert doc["summary"] == proposal()["summary"]
    assert (doc["confirms"], doc["via"], doc["key"], doc["signature"]) == (None, None, None, None)
    out = r.json()
    assert set(out) == {"id", "path", "pr_url", "pr_number"}
    assert out["path"] == path
    push = harness.githost.pushes[-1]
    assert push.author is not None and push.author.name == "alice"


def test_the_pull_request_names_the_stewards_awaiting_confirmation(harness: Harness) -> None:
    """The notification (v3.35): the body names every active steward of the target by login,
    omits one who stepped down, and says a curator may confirm too."""
    seed_stewards(
        harness, ("alice", steward.COMMIT), ("bob", steward.COMMIT), ("bob", steward.STEP_DOWN)
    )
    token = harness.token_for("code_bob", "bobby")
    r = post(harness, token, proposal())
    assert r.status_code == 201, r.text
    (pr,) = harness.githost.pulls
    assert pr.title == f"literature: {NODE}"
    assert "awaiting confirmation by `alice`" in pr.body
    assert "`bob`" not in pr.body
    assert "curator may confirm" in pr.body
    assert "literature record" in pr.body and "`bobby`" in pr.body


def test_without_a_steward_the_pull_request_says_so(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    assert post(harness, token, proposal()).status_code == 201
    (pr,) = harness.githost.pulls
    assert "no steward" in pr.body and "curator" in pr.body


def test_the_contributor_and_date_are_the_services_not_the_callers(harness: Harness) -> None:
    """Unknown top-level keys are refused (F05-T8): a caller cannot send contributor or date."""
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, proposal(contributor="somebody-else"))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "unknown-field"
    assert harness.githost.pushes == []


def test_model_and_tooling_may_be_omitted_and_is_written_null(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    body = proposal()
    del body["model_and_tooling"]
    assert post(harness, token, body).status_code == 201
    doc = yaml.safe_load(only_file(harness)[1])
    assert doc["model_and_tooling"] is None


def test_model_and_tooling_is_recorded_as_declared(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    assert post(harness, token, proposal(model_and_tooling="claude, by hand")).status_code == 201
    assert yaml.safe_load(only_file(harness)[1])["model_and_tooling"] == "claude, by hand"


# --- refusals ------------------------------------------------------------------------------------


def test_a_missing_bearer_is_401(harness: Harness) -> None:
    r = harness.client.post(ROUTE, json=proposal())
    assert r.status_code == 401 and r.json()["error"] == "unauthenticated"


def test_an_unknown_node_is_404(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, proposal(node_id="no-such-node"))
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "node-unknown"
    assert harness.githost.pushes == []


def test_a_bad_status_is_400_naming_the_field(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, proposal(status="hard"))
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"] == "arguments-invalid"
    assert body["details"]["field"] == "status"
    assert "open" in body["message"] and "known" in body["message"]
    assert harness.githost.pushes == []


def test_a_reference_without_https_is_400_naming_the_field(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    refs = [{"title": "A page", "url": "http://example.org/x", "note": None}]
    r = post(harness, token, proposal(references=refs))
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"] == "arguments-invalid"
    assert body["details"]["field"] == "references[0].url"
    assert harness.githost.pushes == []


def test_references_are_required_and_shaped(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for bad in ([], "a paper", [{"url": "https://x.org"}], [{"title": "", "url": None}]):
        r = post(harness, token, proposal(references=bad))
        assert r.status_code == 400, (bad, r.text)
        assert r.json()["error"] == "arguments-invalid"
        assert r.json()["details"]["field"].startswith("references"), (bad, r.json())
    assert harness.githost.pushes == []


def test_a_reference_may_carry_null_url_and_note(harness: Harness) -> None:
    """An offline reference (a book) has no URL; the schema allows null for both."""
    token = harness.token_for("code_alice", "alice")
    refs = [{"title": "Hardy and Wright, ch. 22", "url": None, "note": None}]
    r = post(harness, token, proposal(references=refs))
    assert r.status_code == 201, r.text
    assert yaml.safe_load(only_file(harness)[1])["references"] == refs


def test_an_over_long_summary_is_refused_by_the_schemas_own_cap(harness: Harness) -> None:
    """R14: the cap is the schema's, named with its number, the text never echoed."""
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, proposal(summary="x" * 2001))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "field-too-long"
    assert "2000" in r.json()["message"] and "xxxx" not in r.json()["message"]


def test_a_missing_summary_is_400(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    body = proposal()
    del body["summary"]
    r = post(harness, token, body)
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == "summary"


def test_a_second_record_in_the_same_second_is_409_and_opens_nothing(harness: Harness) -> None:
    """F13-T23: the file name is to the second, so a different record now would share it."""
    token = harness.token_for("code_alice", "alice")
    assert post(harness, token, proposal()).status_code == 201
    r = post(harness, token, proposal(status="elementary"))
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "record-name-taken"
    assert r.headers["Retry-After"] == "1"
    assert len(harness.githost.pushes) == 1
    harness.clock.advance(seconds=1)
    assert post(harness, token, proposal(status="elementary")).status_code == 201


def test_an_identical_open_proposal_is_a_duplicate(harness: Harness) -> None:
    """F07-T35: the same record from another identity, open on the node, is refused."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    assert post(harness, alice, proposal()).status_code == 201
    harness.clock.advance(seconds=1)
    r = post(harness, bob, proposal())
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "duplicate-submission"
    assert len(harness.githost.pushes) == 1


def test_the_submission_is_watchable_under_its_own_kind(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    out = post(harness, token, proposal()).json()
    r = harness.client.get(f"/submissions/{out['id']}")
    assert r.status_code == 200, r.text
    record = r.json()["submission"]
    assert record["kind"] == "literature"
    assert record["node_id"] == NODE and record["artifact_type"] is None
