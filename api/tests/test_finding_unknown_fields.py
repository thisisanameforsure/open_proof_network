"""Finding 5 (2026-09-13, the live MCP contribution): a write route accepts and ignores a key it
does not define.

The tester sent ``artifact_type: partial`` to ``POST /precheck``; the job ran to the same digest
and the same verdict, 2.5 minutes for nothing (job ``01M2DR4M70JSXZT8FJTAEA4HRH``). Every write
handler reads its fields with ``fields.get`` (``identity.body_fields``) and never looks at what
else the body carries, so a misspelled or misplaced key is silent. The MCP adapter's input
schemas say ``additionalProperties: false``; the plain path should say the same.

Asserted here (plan Phase 0, F05-T8): a top-level key outside the route's allowlist is a 400
``unknown-field`` whose message names the key — on ``POST /precheck`` with the tester's exact
key, and on every POST route that takes a JSON body. A known-field body is unchanged, which the
one un-marked test proves today. Held as strict xfails until F05-T8 landed (2026-09-14), when
the marks came off.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
import samples
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)
from mcp_client import NODE, NODE_DIR, TARGET

from opn_api import identity
from opn_api.routes import ROUTES

BUNDLE = {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF}
TUTORIAL_DIR = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/"
STATEMENT = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → p ∨ q := by\n  sorry\n"  # noqa: RUF001
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
EXHIBIT = "import Nodes.«tutorial-and-swap».Context\n\nexample : True := trivial\n"
HOLE = "and-reassoc--h1"
#: A key no write route defines (the tester's own, ``artifact_type``, is a field of
#: ``POST /submissions``, so it is the precheck test's key alone).
STRAY = "stray_key"
FINDING_5 = "finding 5 (F05-R1, F06-R1, F09-R2): {}; fix: F05-T8 (Mike, 2026-09-13)"

#: (body, headers) for a request the route accepts today: the refusal under test is then about
#: the stray key and nothing else.
Prepared = tuple[dict[str, Any], dict[str, str]]
Prepare = Callable[[Harness, PrecheckKey], Prepared]


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def postmortem() -> dict[str, Any]:
    doc = samples.postmortem()
    del doc["schema"], doc["node"]
    return doc


def add_hole(h: Harness) -> None:
    """A hole blocked ``witness-missing`` in graph.json, as ``test_proposals.py`` seeds one."""
    path = f"targets/{TARGET}/graph.json"
    doc = json.loads(h.githost.files[path])
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "blocked",
            "cause": "witness-missing",
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    h.githost.files[path] = json.dumps(doc).encode()
    h.context.files.pop(path, None)


def claims(h: Harness, key: PrecheckKey) -> Prepared:
    return {"node_id": NODE}, h.auth(h.token_for("code_alice", "alice"))


def precheck(h: Harness, key: PrecheckKey) -> Prepared:
    return {"node_id": TUTORIAL_NODE, "bundle": BUNDLE}, {}  # F06-R2: anonymous on the tutorial


def submissions(h: Harness, key: PrecheckKey) -> Prepared:
    token = h.token_for("code_alice", "alice")
    job = h.tutorial_job(key, token=token)
    body = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": BUNDLE,
        "precheck_job_id": job["id"],
    }
    return body, h.auth(token)


def postmortems(h: Harness, key: PrecheckKey) -> Prepared:
    body = {"node_id": TUTORIAL_NODE, "yaml": postmortem()}
    return body, h.auth(h.token_for("code_alice", "alice"))


def annexes(h: Harness, key: PrecheckKey) -> Prepared:
    body = {"node_id": TUTORIAL_NODE, "text": "an informal argument", "licence": "Apache-2.0"}
    return body, h.auth(h.token_for("code_alice", "alice"))


def approach_records(h: Harness, key: PrecheckKey) -> Prepared:
    body = {"target_id": TARGET, "record": {"route": "normalise", "outcome": "exhausted"}}
    return body, h.auth(h.token_for("code_alice", "alice"))


def defect_claims(h: Harness, key: PrecheckKey) -> Prepared:
    h.githost.files[TUTORIAL_DIR + "Statement.lean"] = b"theorem x : True := trivial\n"
    h.context.files.clear()
    body = {"stmt_ref": TUTORIAL_NODE, "class": "junk-value", "line": 1, "exhibit": EXHIBIT}
    return body, h.auth(h.token_for("code_alice", "alice"))


def revision_requests(h: Harness, key: PrecheckKey) -> Prepared:
    body = {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": {"text": "both"}}
    return body, h.auth(h.token_for("code_alice", "alice"))


def speculative(h: Harness, key: PrecheckKey) -> Prepared:
    h.githost.files[NODE_DIR + "Statement.lean"] = (
        b"theorem OpnProp.and_reassoc : True := by\n  sorry\n"
    )
    h.context.files.clear()
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "deps": [NODE]}
    return body, h.auth(h.token_for("code_alice", "alice"))


def variant(h: Harness, key: PrecheckKey) -> Prepared:
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "relation": "related"}
    return body, h.auth(h.token_for("code_alice", "alice"))


def witness(h: Harness, key: PrecheckKey) -> Prepared:
    add_hole(h)
    return {"node_id": HOLE, "witness": WITNESS}, h.auth(h.token_for("code_alice", "alice"))


def tokens(h: Harness, key: PrecheckKey) -> Prepared:
    """The GitHub proof, two steps in (``Harness.token_for``'s first half)."""
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = h.client.get(
        "/auth/github/callback",
        params={"code": "code_alice", "state": state},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 200, cb.text
    body = {
        "proof": cb.json()["proof"],
        "pseudonym": "alice",
        "dco": {"version": identity.DCO_VERSION, "accepted": True},
    }
    return body, {}


def check(h: Harness, key: PrecheckKey) -> Prepared:
    """F13-T3: anonymous; body_fields refuses before any graph read, so no pin need be seeded."""
    return {"target_id": TARGET, "content": "theorem x : True := trivial\n"}, {}


#: Every POST route of ``routes.ROUTES`` that reads a JSON body (``DELETE /claims/<id>`` has none).
WRITE_ROUTES: dict[str, Prepare] = {
    "/tokens": tokens,
    "/claims": claims,
    "/precheck": precheck,
    "/submissions": submissions,
    "/postmortems": postmortems,
    "/annexes": annexes,
    "/approach-records": approach_records,
    "/defect-claims": defect_claims,
    "/revision-requests": revision_requests,
    "/proposals/speculative": speculative,
    "/proposals/variant": variant,
    "/proposals/witness": witness,
    "/check": check,
}


def test_the_table_covers_every_body_taking_write_route() -> None:
    """Setup guard: a route added to ``routes.ROUTES`` without a row here is a test failure,
    not a silently untested route."""
    with_body = {r.path for r in ROUTES if r.method in ("POST", "PUT")}
    assert with_body == set(WRITE_ROUTES)


def test_precheck_refuses_the_testers_stray_key(harness: Harness) -> None:
    """The exact request the tester made: the tutorial precheck plus ``artifact_type``. A 400
    naming the key, and no job is created or dispatched."""
    r = harness.client.post(
        "/precheck", json={"node_id": TUTORIAL_NODE, "bundle": BUNDLE, "artifact_type": "partial"}
    )
    assert r.status_code == 400, f"the stray key was accepted: {r.status_code} {r.text}"
    assert r.json()["error"] == "unknown-field", r.text
    assert "artifact_type" in r.json()["message"], r.text
    assert harness.githost.dispatches == []


@pytest.mark.parametrize("route", sorted(WRITE_ROUTES))
def test_every_write_route_refuses_one_unknown_key(
    harness: Harness, key: PrecheckKey, route: str
) -> None:
    """One stray top-level key on an otherwise acceptable body: 400 ``unknown-field`` naming
    it, and nothing pushed, claimed or minted."""
    body, headers = WRITE_ROUTES[route](harness, key)
    pushes, claims_before = len(harness.githost.pushes), len(harness.store.list_claims())
    r = harness.client.post(route, json={**body, STRAY: "stray"}, headers=headers)
    assert r.status_code == 400, f"{route} accepted the stray key: {r.status_code} {r.text}"
    assert r.json()["error"] == "unknown-field", r.text
    assert STRAY in r.json()["message"], r.text
    assert len(harness.githost.pushes) == pushes
    assert len(harness.store.list_claims()) == claims_before


def test_a_known_field_body_still_works(harness: Harness, key: PrecheckKey) -> None:
    """The allowlist must not break the happy path: the same body without the stray key is
    accepted today, and the refusal above is about the key alone."""
    body, headers = claims(harness, key)
    r = harness.client.post("/claims", json=body, headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["node_id"] == NODE


# --- edges (F05-T8, 2026-09-14) -------------------------------------------------------------------


def test_the_refusal_names_every_stray_key_and_lists_the_accepted_ones(
    harness: Harness, key: PrecheckKey
) -> None:
    """Two stray keys are both named, sorted, and the message lists what the route accepts, so
    a caller fixes the request in one round; ``details`` carries the same two lists as data."""
    body, headers = claims(harness, key)
    r = harness.client.post("/claims", json={**body, "zeta": 1, STRAY: "stray"}, headers=headers)
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == "unknown-field", doc
    assert f"{STRAY}, zeta" in doc["message"], doc["message"]
    assert "node_id, target_id, ttl_hours" in doc["message"], doc["message"]
    assert doc["details"] == {
        "unknown": [STRAY, "zeta"],
        "accepted": ["node_id", "target_id", "ttl_hours"],
    }


def test_only_top_level_keys_are_refused(harness: Harness, key: PrecheckKey) -> None:
    """The allowlist is the route's own field names. A key *inside* a field's object is that
    field's business (``tooling`` keeps three names and ignores the rest, a record is validated
    by its schema), so a stray key nested in ``tooling`` still opens the pull request."""
    body, headers = submissions(harness, key)
    nested = {**body, "tooling": {"model": "m", STRAY: "stray"}}
    r = harness.client.post("/submissions", json=nested, headers=headers)
    assert r.status_code == 201, r.text


def test_an_empty_body_is_not_an_unknown_field(harness: Harness) -> None:
    """No keys, no stray key: an empty body is refused for the field it lacks, as before."""
    token = harness.token_for("code_alice", "alice")
    for raw in (b"", b"{}"):
        r = harness.client.post(
            "/claims",
            content=raw,
            headers={**harness.auth(token), "Content-Type": "application/json"},
        )
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "node-id-invalid", r.text


def test_a_form_body_with_an_unknown_field_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """The browser path (``POST /tokens`` as a urlencoded form) gets the same rule, applied to
    the top-level names after ``proof.id`` and ``dco.accepted`` are nested: the form's own
    fields pass, and one more field is refused by name."""
    body, _ = tokens(harness, key)
    form = {
        "proof.kind": body["proof"]["kind"],
        "proof.id": body["proof"]["id"],
        "dco.version": body["dco"]["version"],
        "dco.accepted": "true",
        "pseudonym": "alice",
    }
    r = harness.client.post("/tokens", data={**form, STRAY: "stray"})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "unknown-field", r.text
    assert STRAY in r.json()["message"], r.text
    ok = harness.client.post("/tokens", data=form, headers={"Accept": "application/json"})
    assert ok.status_code == 201, ok.text  # the proof survived the refusal: nothing was spent
