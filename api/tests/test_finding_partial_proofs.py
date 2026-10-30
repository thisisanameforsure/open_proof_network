"""F32-T8 (R9, AC12, Q15; D-29 v3.49): the service takes a partial's carried proofs in the
bundle, and opens nothing the pinned gate did not check.

The gate half is F32-T1 and T2: a partial may add ``attempts/<assembly>.<n>.proof`` files, each
naming one hole on a ``-- hole:`` line and holding the body of that hole's proof after a
``-- proof:`` line; step 2 reads their grammar, and steps 4 to 8 check each against the node its
hole becomes, which the precheck result reports on the hole (``holes[].proof``). The service
already takes a ``bundle`` of paths on ``POST /precheck`` and ``POST /submissions``, so a proof
is one more path and neither route gains a field.

What the service owes, asserted here:

* a proof file step 2 would refuse is a 400 with the gate's own code, before any job exists or
  anything is pushed, on both routes;
* a target whose pinned gate predates F32 gives ``.proof`` no role, so its classifier would
  refuse the pull request: the service refuses the bundle by name (``hole-proof-unchecked``)
  before a job is spent, asking the pin itself (``uses.pinned_has``, the postmortem/v2
  precedent);
* a submission whose bundle carries proofs binds only to a precheck whose result lists each as
  checked, byte for byte; a passing job that did not check one says so (``carried_proofs``).

The un-marked pins are what the service accepts today and must keep accepting.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import pytest
import samples
from api_fakes import (
    AUTOMATION,
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PARTIAL,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
    result_zip,
)

from opn_gate import schemas

TARGET = "propositional"
NODE = f"{PROOF_PREFIX}{TUTORIAL_NODE}/"
STEM = "20261030T090000Z-alice-partial"
PARTIAL_PATH = f"{NODE}attempts/{STEM}.lean"
W1 = f"{NODE}attempts/{STEM}.1.witness"
W2 = f"{NODE}attempts/{STEM}.2.witness"
P1 = f"{NODE}attempts/{STEM}.1.proof"
P2 = f"{NODE}attempts/{STEM}.2.proof"
PROOF_PATH = f"{NODE}Proof.lean"
PIN = samples.SHA1
#: the file whose presence at a pin means its gate checks a carried proof (F32-T2)
MARKER = "gate/opn_gate/steps/hole_proofs.py"


def witness(hole: str) -> str:
    return f"-- hole: {hole}\n\ntheorem witness : True := trivial\n"


def proof(hole: str, body: str = "by\n  trivial", helpers: str = "") -> str:
    return f"-- hole: {hole}\n{helpers}-- proof:\n{body}\n"


CARRYING = {
    PARTIAL_PATH: TUTORIAL_PARTIAL,
    W1: witness("left"),
    W2: witness("right"),
    P1: proof("left"),
}


def pinned(h: Harness, *, reads_proofs: bool) -> None:
    """The target's gate-spec.json pins ``PIN``; the network tree at ``PIN`` carries the gate's
    carried-proof check exactly when ``reads_proofs``."""
    h.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(network_commit=PIN)
    )
    if reads_proofs:
        h.githost.files_at.setdefault(PIN, {})[MARKER] = b"# the check\n"
    h.context.files.clear()


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def sha(text: str) -> str:
    return schemas.content_hash(text.encode("utf-8"))


def hole(
    name: str,
    *,
    witnessed: str | None = None,
    proved: str | None = None,
    text: str | None = None,
    checked: bool = True,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "name": name,
        "closed_type": "True",
        "expected_witness": "True",
        "restates": None,
        "proved_binders": [],
    }
    if witnessed is not None:
        doc["witness"] = {
            "path": witnessed[len(NODE) :],
            "sha256": sha(CARRYING[witnessed]),
            "checked": True,
        }
    if proved is not None:
        doc["proof"] = {
            "path": proved[len(NODE) :],
            "sha256": sha(text if text is not None else CARRYING[proved]),
            "checked": checked,
        }
    return doc


CHECKED = [hole("left", witnessed=W1, proved=P1), hole("right", witnessed=W2)]


def with_holes(artifact: bytes, holes: list[dict[str, Any]]) -> bytes:
    with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
        result = json.loads(archive.read("result.json"))
    result["holes"] = holes
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json", schemas.canonical_json(result))
    return buffer.getvalue()


def precheck(h: Harness, token: str, bundle: dict[str, str], kind: str | None = "partial") -> Any:
    body: dict[str, Any] = {"node_id": TUTORIAL_NODE, "bundle": bundle}
    if kind is not None:
        body["artifact_type"] = kind
    return h.client.post("/precheck", json=body, headers=h.auth(token))


def passing_job(
    h: Harness,
    key: PrecheckKey,
    token: str,
    bundle: dict[str, str],
    holes: list[dict[str, Any]] | None,
) -> str:
    h.commit_precheck_key(key.public)
    created = precheck(h, token, bundle)
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
        "automation": AUTOMATION,
    }
    return h.client.post("/submissions", json=body, headers=h.auth(token))


# --- what is accepted -----------------------------------------------------------------------------


def test_a_partial_with_a_checked_proof_opens_one_pull_request_with_every_file(
    harness: Harness, key: PrecheckKey
) -> None:
    """AC12: the precheck took the bundle and its result names the carried proof as checked on
    its hole; the submission opens, and the diff is the assembly, both witnesses and the proof."""
    pinned(harness, reads_proofs=True)
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, CARRYING, CHECKED)
    served = harness.client.get(f"/precheck/{job}").json()
    assert [h.get("proof", {}).get("path") for h in served["result"]["holes"]] == [
        P1[len(NODE) :],
        None,
    ]
    assert "carried_proofs" not in served
    r = submit(harness, token, CARRYING, job)
    assert r.status_code == 201, r.text
    push = harness.githost.pushes[-1]
    assert push.repo == harness.settings.graph_repo and push.files == CARRYING
    assert len(harness.githost.pulls) == 1


def test_a_proof_with_helpers_and_crlf_line_ends_is_taken_as_its_bytes(
    harness: Harness, key: PrecheckKey
) -> None:
    """R1 (F07-Q58 (3)): the file is read as bytes, so the hash the gate reports for it is the
    hash of what was sent, and the bound precheck matches it."""
    pinned(harness, reads_proofs=True)
    text = (
        "-- hole: left\r\nprivate theorem t : True := trivial\r\n-- proof:\r\nby\r\n  exact t\r\n"
    )
    bundle = {**CARRYING, P1: text}
    token = harness.token_for("code_alice", "alice")
    holes = [hole("left", witnessed=W1, proved=P1, text=text), hole("right", witnessed=W2)]
    job = passing_job(harness, key, token, bundle, holes)
    assert submit(harness, token, bundle, job).status_code == 201


def test_pin_a_bundle_with_no_proof_is_not_asked_about_the_pin(
    harness: Harness, key: PrecheckKey
) -> None:
    """**PIN.** A partial carrying witnesses and no proof is prechecked and submitted on a target
    whose pin predates F32, as before: the pin is asked only when a proof is carried."""
    pinned(harness, reads_proofs=False)
    token = harness.token_for("code_alice", "alice")
    bundle = {PARTIAL_PATH: TUTORIAL_PARTIAL, W1: witness("left")}
    job = passing_job(harness, key, token, bundle, [hole("left", witnessed=W1)])
    served = harness.client.get(f"/precheck/{job}").json()
    assert "carried_proofs" not in served
    assert submit(harness, token, bundle, job).status_code == 201
    assert not any(path == MARKER for path, _ in harness.githost.fetches)


# --- the target's pin predates F32 ----------------------------------------------------------------


def test_an_older_pin_refuses_a_carried_proof_before_any_job(harness: Harness) -> None:
    """Q15: the pinned gate gives ``.proof`` no role, so its step 2 would pass the file unread and
    its classifier would refuse the pull request. Refused here, by name, before a job is spent;
    the remedy is the way that works on every pin."""
    pinned(harness, reads_proofs=False)
    token = harness.token_for("code_alice", "alice")
    pushed = len(harness.githost.pushes)
    r = precheck(harness, token, CARRYING)
    assert r.status_code == 400, f"a job was spent on it: {r.status_code} {r.text}"
    body = r.json()
    assert body["error"] == "hole-proof-unchecked", body
    assert P1[len(NODE) :] in body["message"] and "re-pin" in body["message"]
    assert len(harness.githost.pushes) == pushed
    r = submit(harness, token, CARRYING, "01JXYZABCDEFGHJKMNPQRSTVWX")
    assert r.status_code == 400 and r.json()["error"] == "hole-proof-unchecked", r.text
    assert len(harness.githost.pushes) == pushed and harness.githost.pulls == []


def test_an_unreadable_pin_opens_nothing(harness: Harness) -> None:
    """C7: a target with no readable gate-spec.json cannot say its gate checks a proof, so the
    answer is the one that opens nothing."""
    token = harness.token_for("code_alice", "alice")  # no gate-spec.json in the fixture graph
    r = precheck(harness, token, CARRYING)
    assert r.status_code == 400 and r.json()["error"] == "hole-proof-unchecked", r.text


# --- what the bound precheck did not check --------------------------------------------------------


@pytest.mark.parametrize(
    "holes",
    [
        None,  # a gate that predates the result's `holes`
        [hole("left", witnessed=W1), hole("right", witnessed=W2)],  # it ignored the proof
        [hole("left", witnessed=W1, proved=P1, text="another text"), hole("right", witnessed=W2)],
        [hole("left", witnessed=W1, proved=P1, checked=False), hole("right", witnessed=W2)],
    ],
)
def test_a_carried_proof_the_precheck_did_not_check_opens_nothing(
    harness: Harness, key: PrecheckKey, holes: list[dict[str, Any]] | None
) -> None:
    """AC12: whatever the pin says, the submission binds only to a result naming the proof as
    checked, byte for byte, on a hole; the served job says which went unchecked."""
    pinned(harness, reads_proofs=True)
    token = harness.token_for("code_alice", "alice")
    if holes is None:
        bundle = {PARTIAL_PATH: TUTORIAL_PARTIAL, W1: witness("left"), P1: proof("left")}
    else:
        bundle = CARRYING
    job = passing_job(harness, key, token, bundle, holes)
    served = harness.client.get(f"/precheck/{job}").json()
    note = served.get("carried_proofs")
    assert note is not None, "a pass with an unchecked carried proof and no word about it"
    assert note["unchecked"] == [P1[len(NODE) :]] and note["checked"] == []
    assert "hole-proof-unchecked" in note["message"]
    pushed = len(harness.githost.pushes)
    r = submit(harness, token, bundle, job)
    assert r.status_code == 400, f"opened on an unchecked proof: {r.status_code} {r.text}"
    body = r.json()
    # with no `holes` at all the witness is unchecked too, and its refusal is asked first
    assert body["error"] == ("hole-witness-unchecked" if holes is None else "hole-proof-unchecked")
    if holes is not None:
        assert P1[len(NODE) :] in body["message"] and "re-pin" in body["message"]
    assert len(harness.githost.pushes) == pushed and harness.githost.pulls == []


# --- what step 2 would refuse, refused before a job -----------------------------------------------

BASE = {PARTIAL_PATH: TUTORIAL_PARTIAL, W1: witness("left"), W2: witness("right")}


@pytest.mark.parametrize(
    ("extra", "kind", "code"),
    [
        ({P1: "-- proof:\nby\n  trivial\n"}, "partial", "hole-proof-unnamed"),
        ({P1: proof("left"), P2: proof("left")}, "partial", "hole-proof-duplicate"),
        ({P1: "-- hole: left\nby\n  trivial\n"}, "partial", "hole-proof-malformed"),
        ({P1: "-- hole: left\n-- proof:\n\n"}, "partial", "hole-proof-malformed"),
        ({P1: proof("left", "by\n  sorry")}, "partial", "hole-proof-sorry"),
        ({P1: proof("left", "by\n  admit")}, "partial", "hole-proof-sorry"),
        ({P1: proof("left", helpers="import Defs.Fact\n")}, "partial", "hole-proof-uses"),
        ({P1: proof("left", helpers="import Nodes.«tutorial-and-swap».Proof\n")}, "partial",
         "hole-proof-uses"),
        ({P1: proof("left", helpers="theorem t : True := trivial\n")}, "partial",
         "helper-forbidden"),
        ({P1: proof("third")}, "partial", "hole-proof-without-witness"),
        ({f"{NODE}attempts/other.1.proof": proof("left")}, "partial", "hole-proof-unattached"),
        ({P1: proof("left")}, None, None),
    ],
)  # fmt: skip
def test_a_malformed_carried_proof_costs_no_precheck_job(
    harness: Harness, extra: dict[str, str], kind: str | None, code: str | None
) -> None:
    """AC12: the gate's own grammar (``opn_gate.carried.read_proofs``), asked before a job is
    dispatched; the row with no code is a well-formed bundle sent without ``artifact_type``,
    which runs."""
    pinned(harness, reads_proofs=True)
    token = harness.token_for("code_alice", "alice")
    pushed = len(harness.githost.pushes)
    r = precheck(harness, token, {**BASE, **extra}, kind)
    if code is None:
        assert r.status_code == 202, r.text
        return
    assert r.status_code == 400, f"a job was spent on it: {r.status_code} {r.text}"
    assert r.json()["error"] == code, r.text
    assert len(harness.githost.pushes) == pushed


@pytest.mark.parametrize(
    ("bundle", "kind"),
    [
        ({PROOF_PATH: TUTORIAL_PROOF, P1: proof("left")}, "proof"),
        ({PROOF_PATH: TUTORIAL_PROOF, P1: proof("left")}, None),
        ({P1: proof("left")}, None),
    ],
)
def test_a_proof_file_without_a_partial_is_refused(
    harness: Harness, bundle: dict[str, str], kind: str | None
) -> None:
    pinned(harness, reads_proofs=True)
    token = harness.token_for("code_alice", "alice")
    r = precheck(harness, token, bundle, kind)
    assert r.status_code == 400 and r.json()["error"] == "hole-proof-without-partial", r.text


def test_a_malformed_carried_proof_is_refused_at_submission_too(harness: Harness) -> None:
    pinned(harness, reads_proofs=True)
    token = harness.token_for("code_alice", "alice")
    bad = {**BASE, P1: "-- hole: left\nby\n  trivial\n"}
    r = submit(harness, token, bad, "01JXYZABCDEFGHJKMNPQRSTVWX")
    assert r.status_code == 400 and r.json()["error"] == "hole-proof-malformed", r.text
    assert harness.githost.pulls == []


# --- the MCP mirror: the same two tools, the same bundle ------------------------------------------


def test_the_two_tools_say_how_a_bundle_carries_a_proof() -> None:
    """R9: no tool and no parameter is added; ``precheck_submission`` and ``submit_proof`` say
    what a proof file is called and how it is laid out, so an MCP-only client can carry one."""
    from opn_api.mcp import writes  # noqa: PLC0415

    by_name = {tool.name: tool for tool in writes.TOOLS}
    for name in ("precheck_submission", "submit_proof"):
        text = by_name[name].description
        assert ".proof" in text and "-- proof:" in text, name
        assert "proofs" not in by_name[name].input_schema["properties"]
    assert "hole-proof-unchecked" in by_name["submit_proof"].description
    assert "holes[].proof" in by_name["precheck_submission"].description


def test_the_precheck_tool_says_what_the_proof_note_means() -> None:
    from opn_api.mcp import reads  # noqa: PLC0415

    text = next(tool.description for tool in reads.TOOLS if tool.name == "get_precheck")
    assert "carried_proofs" in text
