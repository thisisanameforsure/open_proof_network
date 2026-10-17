"""F29-T3 (R5, AC7; D-12 v3.44): the service refuses an unlabelled partial before any precheck.

A partial names its approach, a licence and each hole's label and claim in its own comments
(``opn_gate.labels``). The post-merge job files those words as each hole's first gloss, so a
partial without them would reach the record with nameless holes, and the gate refuses it at
step 4 (``partial-unlabelled``, F29-T2). The service asks first: ``POST /precheck`` and
``POST /submissions`` refuse such a bundle by the same name, naming each problem, before any job
is saved or dispatched and before the host is written to, so the omission costs nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import (
    AUTOMATION,
    PROOF_PREFIX,
    TUTORIAL_NODE,
    Harness,
    PrecheckKey,
    make_precheck_key,
    result_zip,
)
from mcp_client import McpClient

from opn_api import appends, submissions
from opn_gate import codes, labels

PARTIAL_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/attempts/20261017T100000Z-alice-partial.lean"
CODE = "partial-unlabelled"

#: Two holes, nothing declared: the shape an agent sends when it has not read the guide.
UNLABELLED = (
    "import Nodes.X.Context\n\n"
    "theorem x : True := by\n"
    "  have h_left : True := sorry\n"
    "  have h_right : True := sorry\n"
    "  exact h_left\n"
)
#: The same partial with every declaration D-12 v3.44 asks for.
LABELLED = (
    "import Nodes.X.Context\n\n"
    "theorem x : True := by\n"
    "  -- approach: split the claim into its two halves and close each directly\n"
    "  -- licence: CC-BY-4.0\n"
    "  -- label: the left half\n"
    "  -- claim: $\\top$\n"
    "  -- The first conjunct, taken on its own.\n"
    "  have h_left : True := sorry\n"
    "  -- label: the right half\n"
    "  -- claim: $\\top$\n"
    "  have h_right : True := sorry\n"
    "  exact h_left\n"
)
#: Declared, but the second hole's label is missing: one named problem.
HALF_LABELLED = LABELLED.replace("  -- label: the right half\n", "")


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def precheck(h: Harness, token: str, text: str) -> Any:
    return h.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {PARTIAL_PATH: text}, "artifact_type": "partial"},
        headers=h.auth(token),
    )


def passing_job(
    h: Harness, key: PrecheckKey, token: str, text: str, monkeypatch: pytest.MonkeyPatch
) -> str:
    """A done, passing precheck job over ``text``. The service's own precheck refuses an
    unlabelled partial, so the job is minted with the check lifted for that one request: the
    shape of a job a service deployed before the rule handed out, which the submission route
    must still refuse on its own."""
    h.commit_precheck_key(key.public)
    with monkeypatch.context() as m:
        m.setattr(submissions, "check_declarations", lambda *a, **k: None)
        created = precheck(h, token, text)
    assert created.status_code == 202, created.text
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=TUTORIAL_NODE,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
    )
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    polled = h.client.get(f"/precheck/{doc['id']}").json()
    assert polled["state"] == "done" and polled["result"]["verdict"] == "pass", polled
    return str(doc["id"])


def submit(h: Harness, token: str, text: str, job: str) -> Any:
    body = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "partial",
        "bundle": {PARTIAL_PATH: text},
        "precheck_job_id": job,
        "automation": AUTOMATION,
    }
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def host_writes(h: Harness) -> tuple[int, int, int]:
    return len(h.githost.pushes), len(h.githost.pulls), len(h.githost.dispatches)


def problems_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = doc["details"]["problems"]
    return found


# --- POST /precheck ---------------------------------------------------------------------------


def test_precheck_refuses_an_unlabelled_partial_before_any_job(harness: Harness) -> None:
    """AC7: 400 partial-unlabelled naming each problem with its hole; no job saved, nothing
    pushed or dispatched, no run started."""
    token = harness.token_for("code_alice", "alice")
    jobs = set(harness.store.jobs)
    writes = host_writes(harness)
    fetched = len(harness.githost.fetches)
    r = precheck(harness, token, UNLABELLED)
    assert r.status_code == 400, f"an unlabelled partial was prechecked: {r.status_code} {r.text}"
    doc = r.json()
    assert doc["error"] == CODE
    assert "approach" in doc["message"] and "licence" in doc["message"], doc["message"]
    codes_found = [p["code"] for p in problems_of(doc)]
    assert codes_found == ["approach", "licence", "label", "claim", "label", "claim"], codes_found
    assert {p["hole"] for p in problems_of(doc) if p["code"] in ("label", "claim")} == {
        "h_left",
        "h_right",
    }
    assert all("h_" in p["message"] for p in problems_of(doc) if p["hole"]), problems_of(doc)
    assert set(harness.store.jobs) == jobs, "a job was saved"
    assert host_writes(harness) == writes, "the host was written to"
    # The reads that precede the bundle's validation (the node's facts, the paths the node already
    # has) are the only host reads: the refusal comes before the annex or the rendering commit is
    # read, and before any branch is pushed.
    during = [p for p, _ in harness.githost.fetches[fetched:]]
    assert not any(p.startswith("job/") for p in during), during
    assert not any("/annex/" in p for p in during), during


def test_precheck_names_the_one_missing_line(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = precheck(harness, token, HALF_LABELLED)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == CODE
    assert problems_of(r.json()) == [
        {
            "code": "label",
            "message": problems_of(r.json())[0]["message"],
            "hole": "h_right",
            "line": 11,
        }
    ]
    assert "h_right" in r.json()["message"]


def test_precheck_takes_a_labelled_partial(harness: Harness) -> None:
    """The declared partial passes this check and reaches the job (202)."""
    token = harness.token_for("code_alice", "alice")
    r = precheck(harness, token, LABELLED)
    assert r.status_code == 202, r.text
    assert harness.githost.pushes[-1].files[f"bundle/{PARTIAL_PATH}"] == LABELLED


def test_precheck_holds_a_partial_by_its_path_when_no_type_is_declared(harness: Harness) -> None:
    """``artifact_type`` is optional on the precheck; a bundle whose one file the gate's roles
    call a partial is a partial, and is held to the rule."""
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {PARTIAL_PATH: UNLABELLED}},
        headers=harness.auth(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == CODE


def test_a_proof_is_not_held_to_a_partials_declarations(harness: Harness) -> None:
    proof = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {proof: "theorem x : True := trivial\n"}},
        headers=harness.auth(token),
    )
    assert r.status_code == 202, r.text


# --- POST /submissions ------------------------------------------------------------------------


def test_submission_refuses_an_unlabelled_partial_and_opens_nothing(
    harness: Harness, key: PrecheckKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, UNLABELLED, monkeypatch)
    writes = host_writes(harness)
    r = submit(harness, token, UNLABELLED, job)
    assert r.status_code == 400, f"an unlabelled partial was submitted: {r.status_code} {r.text}"
    assert r.json()["error"] == CODE
    assert {p["hole"] for p in problems_of(r.json()) if p["hole"]} == {"h_left", "h_right"}
    assert host_writes(harness) == writes
    assert harness.store.list_open_submissions() == []
    # The job was not spent: a corrected bundle is a different digest, so it is prechecked anew;
    # the refusal comes before the job is bound, so nothing about it changed.
    assert harness.client.get(f"/precheck/{job}").json()["state"] == "done"


def test_submission_takes_a_labelled_partial_on_to_the_next_check(
    harness: Harness, key: PrecheckKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PIN: the declared partial passes this check and opens its pull request."""
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, LABELLED, monkeypatch)
    r = submit(harness, token, LABELLED, job)
    assert r.status_code == 201, r.text
    assert harness.githost.pushes[-1].files == {PARTIAL_PATH: LABELLED}


# --- the catalogue, the licence list and the MCP ----------------------------------------------


def test_the_code_is_catalogued_with_a_remedy(harness: Harness) -> None:
    row = codes.CATALOG[CODE]
    assert row.source in ("api", "both")  # ``both`` once the gate's step 4 emits it (F29-T2)
    assert "approach" in row.meaning and row.remedy
    by_code = {c["code"]: c for c in harness.client.get("/errors.json").json()["codes"]}
    assert by_code[CODE]["remedy"] == row.remedy


def test_the_service_reads_the_gates_licence_list() -> None:
    assert appends.LICENCES is labels.LICENCES


def test_the_precheck_tool_answers_the_same_code(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    doc = McpClient(harness).failed(
        "precheck_submission",
        {
            "node_id": TUTORIAL_NODE,
            "bundle": {PARTIAL_PATH: UNLABELLED},
            "artifact_type": "partial",
        },
        token=token,
    )
    assert doc["status"] == 400 and doc["body"]["error"] == CODE, doc
    problems = doc["body"]["details"]["problems"]
    assert {p["hole"] for p in problems if p["hole"]} == {"h_left", "h_right"}
