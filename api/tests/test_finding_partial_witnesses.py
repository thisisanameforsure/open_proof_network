"""F07-T51 (R23, AC46, Q57; D-29 v3.24): the service takes a partial's carried witnesses in the
bundle, and opens nothing the pinned gate did not check.

The gate half is F07-T50: a partial may add ``attempts/<assembly>.<n>.witness`` files, each the
``Witness.lean`` one hole's node is to be born with, and step 7 holds each to the node witness's
own check. The service already takes a ``bundle`` of paths on ``POST /precheck`` and
``POST /submissions``, so a witness is one more path and neither route gains a field.

What the service owes, asserted here:

* a witness file step 2 would refuse (no ``-- hole:`` line, a hole named twice, a ``sorry``, a
  name not attached to the assembly, or no partial beside it) is a 400 with the gate's own code,
  before any job exists or anything is pushed;
* a submission whose bundle carries witnesses binds only to a precheck whose result lists each
  as checked. A gate pinned before T50 ignores a ``.witness`` file at step 2, so its precheck
  passes without looking at it, and the same gate's classifier then refuses the pull request
  (``path-forbidden``); the service refuses first, by name (``hole-witness-unchecked``).

The un-marked pins are what the service accepts today and must keep accepting.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
    result_zip,
)

from opn_gate import schemas

NODE = f"{PROOF_PREFIX}{TUTORIAL_NODE}/"
STEM = "20261001T160800Z-alice-partial"
PARTIAL_PATH = f"{NODE}attempts/{STEM}.lean"
W1 = f"{NODE}attempts/{STEM}.1.witness"
W2 = f"{NODE}attempts/{STEM}.2.witness"
PROOF_PATH = f"{NODE}Proof.lean"


def witness(hole: str, body: str = "trivial") -> str:
    return f"-- hole: {hole}\n\ntheorem witness : True := {body}\n"


CARRYING = {PARTIAL_PATH: TUTORIAL_PROOF, W1: witness("left"), W2: witness("right")}


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def hole(name: str, path: str | None = None, text: str = "") -> dict[str, Any]:
    doc: dict[str, Any] = {
        "name": name,
        "closed_type": "True",
        "expected_witness": "True",
        "restates": None,
        "proved_binders": [],
    }
    if path is not None:
        doc["witness"] = {
            "path": path[len(NODE) :],
            "sha256": schemas.content_hash(text.encode("utf-8")),
            "checked": True,
        }
    return doc


def with_holes(artifact: bytes, holes: list[dict[str, Any]]) -> bytes:
    """The workflow's artifact with ``holes`` in its result, as ``precheck.job`` writes them:
    beside ``steps`` and outside the signed attestation."""
    with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
        result = json.loads(archive.read("result.json"))
    result["holes"] = holes
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json", schemas.canonical_json(result))
    return buffer.getvalue()


def passing_job(
    h: Harness,
    key: PrecheckKey,
    token: str,
    bundle: dict[str, str],
    holes: list[dict[str, Any]] | None,
) -> str:
    """A done, passing precheck of ``bundle`` whose result carries ``holes`` (``None``: a result
    with no ``holes`` key at all, as a gate pinned before F06-T9 writes it)."""
    h.commit_precheck_key(key.public)
    created = h.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": bundle, "artifact_type": "partial"},
        headers=h.auth(token),
    )
    assert created.status_code == 202, created.text
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=TUTORIAL_NODE,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
    )
    if holes is not None:
        artifact = with_holes(artifact, holes)
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    polled = h.client.get(f"/precheck/{doc['id']}").json()
    assert polled["state"] == "done" and polled["result"]["verdict"] == "pass", polled
    return str(doc["id"])


def submit(h: Harness, token: str, bundle: dict[str, str], job: str, kind: str = "partial") -> Any:
    body = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": kind,
        "bundle": bundle,
        "precheck_job_id": job,
    }
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def precheck(h: Harness, token: str, bundle: dict[str, str], kind: str | None = "partial") -> Any:
    body: dict[str, Any] = {"node_id": TUTORIAL_NODE, "bundle": bundle}
    if kind is not None:
        body["artifact_type"] = kind
    return h.client.post("/precheck", json=body, headers=h.auth(token))


# --- what is accepted -----------------------------------------------------------------------------


def test_a_partial_with_checked_witnesses_opens_one_pull_request_with_every_file(
    harness: Harness, key: PrecheckKey
) -> None:
    """AC46: the precheck took the bundle and its result names each carried witness on its
    hole; the submission opens, and the diff is the assembly and both witness files."""
    token = harness.token_for("code_alice", "alice")
    holes = [hole("left", W1, CARRYING[W1]), hole("right", W2, CARRYING[W2]), hole("third")]
    job = passing_job(harness, key, token, CARRYING, holes)
    served = harness.client.get(f"/precheck/{job}").json()["result"]["holes"]
    assert [h.get("witness", {}).get("path") for h in served] == [
        W1[len(NODE) :],
        W2[len(NODE) :],
        None,
    ]
    r = submit(harness, token, CARRYING, job)
    assert r.status_code == 201, r.text
    push = harness.githost.pushes[-1]
    assert push.repo == harness.settings.graph_repo and push.files == CARRYING
    assert len(harness.githost.pulls) == 1


def test_pin_a_partial_without_witnesses_needs_no_holes_in_its_result(
    harness: Harness, key: PrecheckKey
) -> None:
    """**PIN.** A bundle that carries nothing binds to any passing precheck of it, whatever its
    result says of holes: the new refusal reads carried witnesses and nothing else."""
    token = harness.token_for("code_alice", "alice")
    bundle = {PARTIAL_PATH: TUTORIAL_PROOF}
    job = passing_job(harness, key, token, bundle, None)
    assert submit(harness, token, bundle, job).status_code == 201


# --- what the pinned gate did not check -----------------------------------------------------------


@pytest.mark.parametrize(
    "holes",
    [
        None,  # a gate that predates the result's `holes`
        [hole("left"), hole("right")],  # one that predates R23: it ignored the files
        [hole("left", W1, CARRYING[W1]), hole("right")],  # one of the two was not checked
        [hole("left", W1, CARRYING[W1]), hole("right", W2, "another text")],  # another file
    ],
)
def test_a_carried_witness_the_precheck_did_not_check_opens_nothing(
    harness: Harness, key: PrecheckKey, holes: list[dict[str, Any]] | None
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, CARRYING, holes)
    pushed = len(harness.githost.pushes)
    r = submit(harness, token, CARRYING, job)
    assert r.status_code == 400, f"opened on an unchecked witness: {r.status_code} {r.text}"
    body = r.json()
    assert body["error"] == "hole-witness-unchecked", body
    assert W2[len(NODE) :] in body["message"] or W1[len(NODE) :] in body["message"]
    assert "POST /proposals/witness" in body["message"]
    assert len(harness.githost.pushes) == pushed and harness.githost.pulls == []


# --- what step 2 would refuse, refused before a job -----------------------------------------------


@pytest.mark.parametrize(
    ("bundle", "kind", "code"),
    [
        ({PARTIAL_PATH: TUTORIAL_PROOF, W1: "theorem witness : True := trivial\n"}, "partial",
         "hole-witness-unnamed"),
        ({PARTIAL_PATH: TUTORIAL_PROOF, W1: witness("left"), W2: witness("left")}, "partial",
         "hole-witness-duplicate"),
        ({PARTIAL_PATH: TUTORIAL_PROOF, W1: witness("left", "by sorry")}, "partial",
         "hole-witness-sorry"),
        ({PARTIAL_PATH: TUTORIAL_PROOF, f"{NODE}attempts/other.1.witness": witness("left")},
         "partial", "hole-witness-unattached"),
        ({PARTIAL_PATH: TUTORIAL_PROOF, W1: witness("left")}, None, None),
        ({PROOF_PATH: TUTORIAL_PROOF, W1: witness("left")}, "proof",
         "hole-witness-without-partial"),
        ({PROOF_PATH: TUTORIAL_PROOF, W1: witness("left")}, None, "hole-witness-without-partial"),
        ({W1: witness("left")}, None, "hole-witness-without-partial"),
    ],
)  # fmt: skip
def test_a_malformed_carried_witness_costs_no_precheck_job(
    harness: Harness, bundle: dict[str, str], kind: str | None, code: str | None
) -> None:
    """AC46: the gate's own grammar (``opn_gate.carried``), asked before a job is dispatched;
    the row with no code is a well-formed bundle sent without ``artifact_type``, which runs."""
    token = harness.token_for("code_alice", "alice")
    pushed = len(harness.githost.pushes)
    r = precheck(harness, token, bundle, kind)
    if code is None:
        assert r.status_code == 202, r.text
        return
    assert r.status_code == 400, f"a job was spent on it: {r.status_code} {r.text}"
    assert r.json()["error"] == code, r.text
    assert len(harness.githost.pushes) == pushed


def test_a_malformed_carried_witness_is_refused_at_submission_too(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    bad = {PARTIAL_PATH: TUTORIAL_PROOF, W1: "theorem witness : True := trivial\n"}
    r = submit(harness, token, bad, "01JXYZABCDEFGHJKMNPQRSTVWX")
    assert r.status_code == 400 and r.json()["error"] == "hole-witness-unnamed", r.text
    assert harness.githost.pulls == []


# --- the MCP mirror: the same two tools, the same bundle ------------------------------------------


def test_the_two_tools_say_how_a_bundle_carries_witnesses() -> None:
    """The bijection rule holds without a new tool: ``precheck_submission`` and ``submit_proof``
    take the bundle the routes take. Their descriptions say what a witness file is called and
    what names its hole, so an MCP-only client can carry one."""
    from opn_api.mcp import writes  # noqa: PLC0415

    by_name = {tool.name: tool for tool in writes.TOOLS}
    for name in ("precheck_submission", "submit_proof"):
        text = by_name[name].description
        assert ".witness" in text and "-- hole:" in text, name
        assert set(by_name[name].input_schema["properties"]) >= {"node_id", "bundle"}
        assert "witnesses" not in by_name[name].input_schema["properties"]


# --- F07-T53: what the gate gives no role is refused before a job; an old pin's precheck says so --

NEAR_MISSES = (
    f"{NODE}attempts/{STEM}.1.witness.bak",  # an editor's copy
    f"{NODE}attempts/.witness",  # the suffix alone
    f"{NODE}attempts/{STEM}.1.Witness",  # the wrong case
    f"{NODE}attempts/notes.txt",  # nothing the gate knows
)


@pytest.mark.parametrize("extra", NEAR_MISSES)
def test_a_bundle_path_the_gate_gives_no_role_costs_no_job_and_opens_nothing(
    harness: Harness, extra: str
) -> None:
    """The classifier refuses a pull request that adds a file no role covers (``path-forbidden``:
    "not a path any submission may touch"), and step 2 does not look at it, so its precheck
    passes: the service used to spend a job on such a bundle and then open a pull request that
    could only go red. A carried witness with its name slightly wrong is exactly that file."""
    token = harness.token_for("code_alice", "alice")
    bundle = {PARTIAL_PATH: TUTORIAL_PROOF, extra: witness("left")}
    pushed = len(harness.githost.pushes)
    r = precheck(harness, token, bundle)
    assert r.status_code == 400, f"a job was spent on it: {r.status_code} {r.text}"
    body = r.json()
    assert body["error"] == "path-forbidden", body
    assert extra in body["message"] and "not a path any submission may touch" in body["message"]
    r = submit(harness, token, bundle, "01JXYZABCDEFGHJKMNPQRSTVWX")
    assert r.status_code == 400 and r.json()["error"] == "path-forbidden", r.text
    assert len(harness.githost.pushes) == pushed and harness.githost.pulls == []


def test_a_precheck_whose_gate_did_not_check_the_carried_witnesses_says_so(
    harness: Harness, key: PrecheckKey
) -> None:
    """Between the api deploy and a target's re-pin, the pinned gate passes a carrying bundle
    without reading its witness files. The submission is refused (above); the precheck that
    passed now says which files went unchecked, so the contributor is not told ``pass`` about a
    witness nothing looked at and learns it before submitting."""
    token = harness.token_for("code_alice", "alice")
    job = passing_job(
        harness, key, token, CARRYING, [hole("left", W1, CARRYING[W1]), hole("right")]
    )
    served = harness.client.get(f"/precheck/{job}").json()
    assert served["result"]["verdict"] == "pass"
    note = served.get("carried_witnesses")
    assert note is not None, "a pass with an unchecked carried witness and no word about it"
    assert note["unchecked"] == [W2[len(NODE) :]] and note["checked"] == [W1[len(NODE) :]]
    assert "hole-witness-unchecked" in note["message"] and "re-pin" in note["message"]


def test_pin_a_precheck_that_checked_every_carried_witness_adds_nothing(
    harness: Harness, key: PrecheckKey
) -> None:
    """**PIN.** A job whose gate checked every carried file, and a job that carried none, are
    served as they were: the note is for the unchecked case alone."""
    token = harness.token_for("code_alice", "alice")
    holes = [hole("left", W1, CARRYING[W1]), hole("right", W2, CARRYING[W2])]
    job = passing_job(harness, key, token, CARRYING, holes)
    assert "carried_witnesses" not in harness.client.get(f"/precheck/{job}").json()
    plain = passing_job(harness, key, token, {PARTIAL_PATH: TUTORIAL_PROOF}, None)
    assert "carried_witnesses" not in harness.client.get(f"/precheck/{plain}").json()


def test_the_precheck_tool_says_what_the_note_means() -> None:
    from opn_api.mcp import reads  # noqa: PLC0415

    text = next(tool.description for tool in reads.TOOLS if tool.name == "get_precheck")
    assert "carried_witnesses" in text and "unchecked" in text
