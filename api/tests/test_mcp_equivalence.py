"""F09-T4 / AC3, AC4: every tool equals its plain path — the file or the endpoint response for
the same request, modulo the R6 demarcation; every write reaches exactly one endpoint."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_harness,
    make_precheck_key,
)
from mcp_client import NODE, NODE_DIR, TARGET, McpClient, materialize, plain, seed_node, unwrap

from opn_api.mcp import demarcate
from opn_api.mcp.server import TOOLS
from opn_gate import context, schemas

ULID_RE = re.compile(r"[0-9A-Z]{26}")
STATEMENT = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → p ∨ q := by\n  sorry\n"  # noqa: RUF001
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
EXHIBIT = "import Nodes.«tutorial-and-swap».Context\n\nexample : True := trivial\n"
TUTORIAL_DIR = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def seed_graph(harness: Harness) -> None:
    """Every file the read tools look at, beside the fixture products."""
    seed_node(harness)
    files = harness.githost.files
    files[f"targets/{TARGET}/approaches/20260910T120000Z-alice.yaml"] = (
        b"schema: approach-record/v1\ntarget: propositional\ncontributor: alice\n"
        b"route: try the obvious thing\noutcome: exhausted\npinned_mathlib_sha: null\n"
        b"model_and_tooling: null\ndate: '2026-09-10T12:00:00Z'\n"
    )
    files[f"targets/{TARGET}/defs/Helper.lean"] = b"def helper : Nat := 1\n"
    files[f"targets/{TARGET}/defs/Helper.cert.yaml"] = b"schema: fidelity/v1\nkind: mechanical\n"
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(lean_toolchain="leanprover/lean4:v4.33.1", network_commit="9" * 40)
    )
    files["attestations/000001.json"] = json.dumps(
        samples.attestation(node_id=TUTORIAL_NODE, graph_commit="5" * 40)
    ).encode()
    files["schemas/postmortem/v1.json"] = schemas.schema_path("postmortem/v1").read_bytes()
    files[TUTORIAL_DIR + "Statement.lean"] = b"theorem x : True := trivial\n"
    harness.context.files.clear()


def test_read_tools_equal_plain_path(
    harness: Harness, key: PrecheckKey, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """AC3: each read tool's result is the file's parsed content or the endpoint's body."""
    seed_graph(harness)
    token = harness.token_for("code_alice", "alice-p")
    harness.client.post("/claims", json={"node_id": NODE}, headers=harness.auth(token))
    job = harness.tutorial_job(key)
    client = McpClient(harness)

    assert client.ok("server_info") == harness.client.get("/info.json").json()
    assert client.ok("list_targets") == plain(harness, "targets/index.json")
    assert client.ok("list_frontier") == harness.client.get("/frontier.json").json()
    assert client.ok("get_gate_spec", {"target_id": TARGET}) == plain(
        harness, f"targets/{TARGET}/gate-spec.json"
    )
    assert client.ok("get_submission", {"submission_id": "000001"}) == plain(
        harness, "attestations/000001.json"
    )
    assert client.ok("get_schema", {"name": "postmortem/v1"}) == plain(
        harness, "schemas/postmortem/v1.json"
    )
    assert (
        client.ok("get_precheck", {"job_id": job["id"]})
        == harness.client.get(f"/precheck/{job['id']}").json()
    )

    target = client.ok("get_target", {"target_id": TARGET})
    assert target["graph"] == plain(harness, f"targets/{TARGET}/graph.json")
    approach = f"targets/{TARGET}/approaches/20260910T120000Z-alice.yaml"
    assert unwrap(target["approaches"]) == [{"path": approach, "record": plain(harness, approach)}]

    defs = client.ok("get_defs", {"target_id": TARGET})
    lean = f"targets/{TARGET}/defs/Helper.lean"
    raw = harness.githost.files[lean]
    assert defs["defs"] == [
        {"path": lean, "sha256": hashlib.sha256(raw).hexdigest(), "content": raw.decode()}
    ]
    cert = f"targets/{TARGET}/defs/Helper.cert.yaml"
    assert defs["certificates"] == [{"path": cert, "record": plain(harness, cert)}]

    node = client.ok("get_node", {"node_id": NODE})
    files = harness.githost.files
    assert node["files"] == {
        **{
            name: files[NODE_DIR + name].decode()
            for name in ("Statement.lean", "Context.lean", "Witness.lean")
        },
        "Proof.lean": None,
    }
    assert node["context"] == derived_bundle(harness, tmp_path_factory.mktemp("tree"))
    assert node["context_source"] == "derived"  # the fake graph commits no CONTEXT.json
    [annex] = [p for p in files if p.startswith(NODE_DIR + "annex/") and p.endswith(".md")]
    text = files[annex].decode()
    front, _, body = text.removeprefix("---\n").partition("---\n")
    assert unwrap(node["annexes"]) == [
        {"path": annex, "front": schemas.validate(yaml.safe_load(front), "annex/v1"), "text": body}
    ]
    explainer = NODE_DIR + "explainer/overview.md"
    assert unwrap(node["explainers"]) == [
        {"path": explainer, "front": {}, "text": files[explainer].decode()}
    ]
    overlay = harness.client.get("/frontier.json").json()
    assert node["claims"] == next(e["claims"] for e in overlay["entries"] if e["node_id"] == NODE)
    assert node["claims"]["active"][0]["pseudonym"] == "alice-p"


def derived_bundle(harness: Harness, tree: Path) -> dict[str, Any]:
    """What the post-merge job would write for the fixture node: the gate's generator over the
    same files, with the states graph.json records (F10-R3)."""
    materialize(harness, tree)
    states = context.graph_states(json.loads(harness.githost.files[f"targets/{TARGET}/graph.json"]))
    rendered = json.loads(harness.githost.files["frontier.json"])["rendered_from"]
    return context.build(
        context.DiskReader(tree), TARGET, NODE, states=states, rendered_from=rendered
    )


def test_get_node_uses_context(harness: Harness, tmp_path: Path) -> None:
    """F10-AC4: with CONTEXT.json committed, the tool's bundle is that file plus the raw files,
    demarcation included — and the file is exactly what the tool derived without it."""
    seed_graph(harness)
    client = McpClient(harness)
    before = client.ok("get_node", {"node_id": NODE})
    assert before["context_source"] == "derived"
    committed = schemas.canonical_json(derived_bundle(harness, tmp_path / "tree"))
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = committed
    harness.context.files.clear()
    after = client.ok("get_node", {"node_id": NODE})
    assert after["context_source"] == "file"
    assert after["context"] == json.loads(committed) == before["context"]
    assert {k: v for k, v in after.items() if k != "context_source"} == {
        k: v for k, v in before.items() if k != "context_source"
    }
    assert (
        after["files"]["Statement.lean"]
        == harness.githost.files[NODE_DIR + "Statement.lean"].decode()
    )
    # The bundle carries the injection only wrapped, as the file does (R6; F10-R3).
    assert demarcate.bare_strings(after["context"]) == demarcate.bare_strings(json.loads(committed))
    assert "ignore previous instructions" in json.dumps(after["context"])
    # A committed bundle that does not validate is a named error, not a partial answer (R10).
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = b'{"schema": "context/v1"}'
    harness.context.files.clear()
    failed = client.failed("get_node", {"node_id": NODE})
    assert failed["error"] == "context-invalid" and failed["source"] == "graph"


# --- AC4 ------------------------------------------------------------------------------------------


def masked(value: Any) -> Any:
    """Ids the service mints (ULIDs) differ between two fresh harnesses; nothing else may."""
    return json.loads(ULID_RE.sub("<ulid>", json.dumps(value, sort_keys=True)))


def endpoint_calls(caplog: pytest.LogCaptureFixture) -> list[str]:
    """The routes the access log saw, the MCP transport's own requests excluded (R11)."""
    return [
        r.getMessage().split(" identity=")[0].split(" ", 1)[1]  # "<method> <label> identity=..."
        for r in caplog.records
        if r.name == "opn_api.access" and " /mcp " not in r.getMessage()
    ]


Setup = Callable[[Harness, str], dict[str, Any]]


def no_setup(h: Harness, token: str) -> dict[str, Any]:
    return {}


def with_claim(h: Harness, token: str) -> dict[str, Any]:
    r = h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(token))
    return {"claim_id": r.json()["id"]}


def with_statement(h: Harness, token: str) -> dict[str, Any]:
    h.githost.files[TUTORIAL_DIR + "Statement.lean"] = b"theorem x : True := trivial\n"
    h.context.files.clear()
    return {}


def with_dep(h: Harness, token: str) -> dict[str, Any]:
    h.githost.files[NODE_DIR + "Statement.lean"] = (
        b"theorem OpnProp.and_reassoc : True := by\n  sorry\n"
    )
    h.context.files.clear()
    return {}


def postmortem() -> dict[str, Any]:
    doc = samples.postmortem()
    del doc["schema"], doc["node"]
    return doc


BUNDLE = {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF}
# tool -> (tool arguments, route label, endpoint body, setup)
WRITES: dict[str, tuple[dict[str, Any], str, dict[str, Any], Setup]] = {
    "claim_node": (
        {"node_id": NODE, "ttl": 5},
        "POST /claims",
        {"node_id": NODE, "ttl_hours": 5},
        no_setup,
    ),
    "release_claim": ({}, "DELETE /claims/{claim_id}", {}, with_claim),
    "precheck_submission": (
        {"node_id": TUTORIAL_NODE, "bundle": BUNDLE},
        "POST /precheck",
        {"node_id": TUTORIAL_NODE, "bundle": BUNDLE},
        no_setup,
    ),
    "submit_postmortem": (
        {"node_id": TUTORIAL_NODE, "yaml": postmortem()},
        "POST /postmortems",
        {"node_id": TUTORIAL_NODE, "yaml": postmortem()},
        no_setup,
    ),
    "submit_informal_annex": (
        {"node_id": TUTORIAL_NODE, "text": "an informal argument", "licence": "Apache-2.0"},
        "POST /annexes",
        {"node_id": TUTORIAL_NODE, "text": "an informal argument", "licence": "Apache-2.0"},
        no_setup,
    ),
    "submit_approach_record": (
        {"target_id": TARGET, "record": {"route": "normalise", "outcome": "exhausted"}},
        "POST /approach-records",
        {"target_id": TARGET, "record": {"route": "normalise", "outcome": "exhausted"}},
        no_setup,
    ),
    "file_defect_claim": (
        {"stmt_ref": TUTORIAL_NODE, "class": "junk-value", "line": 1, "exhibit": EXHIBIT},
        "POST /defect-claims",
        {"stmt_ref": TUTORIAL_NODE, "class": "junk-value", "line": 1, "exhibit": EXHIBIT},
        with_statement,
    ),
    "file_revision_request": (
        {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": {"text": "both follow"}},
        "POST /revision-requests",
        {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": {"text": "both follow"}},
        no_setup,
    ),
    "propose_speculative_node": (
        {"target_id": TARGET, "stmt": STATEMENT, "witness": WITNESS, "deps": [NODE]},
        "POST /proposals/speculative",
        {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "deps": [NODE]},
        with_dep,
    ),
    "propose_variant": (
        {"target_id": TARGET, "stmt": STATEMENT, "witness": WITNESS, "relation": "related"},
        "POST /proposals/variant",
        {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "relation": "related"},
        no_setup,
    ),
}


def submit_proof_pair(key: PrecheckKey) -> tuple[Harness, dict[str, Any], Harness, dict[str, Any]]:
    """Two harnesses each with a passing precheck bound to the same bundle and identity."""
    pair = []
    for _ in range(2):
        h = make_harness()
        token = h.token_for("code_alice", "alice")
        job = h.tutorial_job(key, token=token)
        attestation = h.client.get(f"/precheck/{job['id']}").json()
        assert attestation["state"] == "done"
        pair.append((h, token, attestation))
    (a, ta, at_a), (b, tb, at_b) = pair
    args = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": BUNDLE,
        "attestation": at_a,
    }
    body = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": BUNDLE,
        "precheck_job_id": at_b["id"],
    }
    return a, {"token": ta, "args": args}, b, {"token": tb, "body": body}


def test_write_tools_forward_once(
    caplog: pytest.LogCaptureFixture, key: PrecheckKey, tmp_path: Path
) -> None:
    """AC4: each write tool with a token makes exactly one endpoint call, and its result equals
    the endpoint's own response to the same request — on a second, identical harness."""
    caplog.set_level(logging.INFO, logger="opn_api.access")
    covered = set()
    for name, (given, route, body, setup) in WRITES.items():
        a, b = make_harness(), make_harness()
        token_a = a.token_for("code_alice", "alice")
        token_b = b.token_for("code_alice", "alice")
        args = {**given, **setup(a, token_a)}
        ids = setup(b, token_b)
        path = route.split(" ", 1)[1].format(**ids)
        caplog.clear()
        result = McpClient(a).call(name, args, token=token_a)
        assert endpoint_calls(caplog) == [route], (name, endpoint_calls(caplog))
        direct = b.client.request(
            route.split(" ")[0], path, json=body or None, headers=b.auth(token_b)
        )
        assert result.structuredContent is not None
        got = {k: v for k, v in result.structuredContent.items() if k in ("status", "body")}
        assert masked(got) == masked({"status": direct.status_code, "body": direct.json()}), name
        assert result.isError is (direct.status_code >= 400), name
        assert direct.status_code < 400, (name, direct.json())  # every row drives the happy path
        assert masked([p.files for p in a.githost.pushes]) == masked(
            [p.files for p in b.githost.pushes]
        ), name
        assert masked([c.__dict__ for c in a.store.list_claims()]) == masked(
            [c.__dict__ for c in b.store.list_claims()]
        ), name
        covered.add(name)

    a, tool_side, b, plain_side = submit_proof_pair(key)
    caplog.clear()
    result = McpClient(a).call("submit_proof", tool_side["args"], token=tool_side["token"])
    assert endpoint_calls(caplog) == ["POST /submissions"]
    direct = b.client.post(
        "/submissions", json=plain_side["body"], headers=b.auth(plain_side["token"])
    )
    assert direct.status_code == 201, direct.text
    assert result.structuredContent is not None
    got = {k: v for k, v in result.structuredContent.items() if k in ("status", "body")}
    assert masked(got) == masked({"status": 201, "body": direct.json()})
    assert masked([p.files for p in a.githost.pushes]) == masked(
        [p.files for p in b.githost.pushes]
    )
    covered.add("submit_proof")
    assert covered == {t.name for t in TOOLS if t.write}
