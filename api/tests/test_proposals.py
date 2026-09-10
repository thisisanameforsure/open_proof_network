"""F08-T3: the proposal routes (R3, R4, R5; AC8, AC9).

The service scaffolds a node with the gate's own builder and opens the pull request; whether the
node may enter the graph is admission's answer, on the runner. So what is under test is the
shape of what lands — a D-3 directory whose bytes the classifier calls a proposal — and the
refusals that need no Lean to decide.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from api_fakes import TUTORIAL_NODE, Harness, make_harness

from opn_api import proposals
from opn_gate import graph as graphmod
from opn_gate import layout, modes, records, scaffold, schemas
from opn_gate.paths import Change

TARGET = "propositional"
NODES = f"targets/{TARGET}/nodes/"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
STATEMENT = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → p ∨ q := by\n  sorry\n"  # noqa: RUF001
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
DEP_STATEMENT = "theorem OpnProp.and_reassoc : True := by\n  sorry\n"
RELATION_PROOF = "theorem relation : True := trivial\n"


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def pushed(h: Harness) -> dict[str, str]:
    return dict(h.githost.pushes[-1].files)


def materialise(files: dict[str, str], root: Path) -> Path:
    """Write what the service pushed as a tree, the way the merge commit would hold it."""
    for path, content in files.items():
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return root


# --- AC8: POST /proposals/speculative ------------------------------------------------------------


def test_speculative_scaffold(harness: Harness, tmp_path: Path) -> None:
    """AC8: the directory validates against D-3, the node is marked speculative (by a status
    record, F08-Q2), Context.lean carries the deps' signatures, and a proposal PR is opened."""
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    r = post(
        harness,
        "/proposals/speculative",
        token,
        {
            "target_id": TARGET,
            "statement": STATEMENT,
            "witness": WITNESS,
            "deps": ["and-reassoc"],
            "model": "claude-opus-5",
        },
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    node_id = doc["node_id"]
    assert node_id == scaffold.speculative_id(STATEMENT)
    assert node_id.startswith("spec-") and len(node_id) == len("spec-") + 8
    assert doc["target_id"] == TARGET
    assert doc["pr_url"].endswith("/pull/1")

    files = pushed(harness)
    prefix = f"{NODES}{node_id}/"
    assert all(p.startswith(prefix) for p in files), files
    root = materialise(files, tmp_path / "graph")
    node_dir = root / NODES / node_id
    assert layout.validate_node(node_dir) == []  # D-3, as the layout check will see it
    meta = yaml.safe_load((node_dir / "META.yaml").read_text())
    parsed = layout.parse_statement((node_dir / "Statement.lean").read_text())
    assert isinstance(parsed, layout.Statement)
    assert meta["statement-hash"] == parsed.statement_hash
    assert meta["id"] == node_id
    assert meta["origin"] == "authored"
    assert meta["deps"] == ["and-reassoc"]
    assert meta["provenance"] == {
        "author": "alice",
        "model": "claude-opus-5",
        "source": None,
        "date": "2026-09-09",
    }
    assert schemas.violations(meta) == []
    # F08-Q2: `speculative` is a status record inside the directory, and F03 derives it.
    record = records.load_node_status(node_dir)
    assert record is not None and record.status == "speculative"
    assert record.author == "alice"
    # F01-R6: the dep's signature, verbatim.
    assert DEP_STATEMENT.strip() in (node_dir / "Context.lean").read_text()
    assert (node_dir / "Statement.lean").read_text() == STATEMENT
    assert (node_dir / "Witness.lean").read_text() == WITNESS
    assert not (node_dir / "Relation.lean").exists()

    # What the service pushed is what the gate classifies as a proposal, and nothing else.
    classification = modes.classify([Change("A", p) for p in files])
    assert classification.mode == "proposal"
    assert classification.admit == node_id
    assert modes.check(root, classification) == []

    push = harness.githost.pushes[-1]
    assert push.branch.startswith("propose/")
    assert push.author is not None and push.author.name == "alice"
    assert push.committer is not None and push.committer.name != "alice"
    assert push.message.startswith(f"proposal: {node_id}\n")
    pr = harness.githost.pulls[-1]
    assert pr.head == push.branch and pr.title == f"proposal: {node_id}"
    assert "D-29" in pr.body


def test_speculative_refusals(harness: Harness) -> None:
    """R3: an unknown target or dep, a missing file, a bad statement shape — each a named 400 or
    404 before anything is pushed."""
    token = harness.token_for("code_alice", "alice")
    ok = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    cases: list[tuple[dict[str, Any], int, str]] = [
        ({**ok, "target_id": "nowhere"}, 404, "target-unknown"),
        ({**ok, "deps": ["ghost"]}, 404, "dep-unknown"),
        ({**ok, "deps": "and-reassoc"}, 400, "deps-invalid"),
        ({**ok, "statement": ""}, 400, "statement-missing"),
        ({"target_id": TARGET, "statement": STATEMENT}, 400, "witness-missing"),
        ({**ok, "statement": "theorem a : True := trivial\n"}, 400, "proposal-invalid"),
        ({**ok, "statement": "x" * (proposals.MAX_LEAN_BYTES + 1)}, 400, "field-too-long"),
        ({**ok, "model": 7}, 400, "tooling-invalid"),
    ]
    for body, status, code in cases:
        r = post(harness, "/proposals/speculative", token, body)
        assert r.status_code == status, (code, r.text)
        assert r.json()["error"] == code, r.text
    assert harness.githost.pushes == []


# --- AC9: POST /proposals/variant -----------------------------------------------------------------


def test_variant_requires_proof_for_label(harness: Harness, tmp_path: Path) -> None:
    """AC9: `resolves` with no proof is a 400 naming the relation proof; `related` needs none;
    with a proof the label rides inside Relation.lean, where F03 and admission read it."""
    token = harness.token_for("code_alice", "alice")
    base = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    r = post(harness, "/proposals/variant", token, {**base, "relation": "resolves"})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "relation-proof-required"
    assert "relation_proof" in r.json()["message"]
    assert "variant → root" in r.json()["message"]
    assert harness.githost.pushes == []

    r = post(harness, "/proposals/variant", token, {**base, "relation": "sideways"})
    assert r.status_code == 400 and r.json()["error"] == "relation-invalid"

    related = post(harness, "/proposals/variant", token, base)
    assert related.status_code == 201, related.text
    node_id = related.json()["node_id"]
    assert node_id.startswith("variant-")
    files = pushed(harness)
    assert f"{NODES}{node_id}/Relation.lean" not in files
    root = materialise(files, tmp_path / "related")
    node_dir = root / NODES / node_id
    assert layout.validate_node(node_dir) == []
    assert yaml.safe_load((node_dir / "META.yaml").read_text())["origin"] == "variant"
    assert graphmod.relation_of(node_dir, "variant") == "related"
    assert not (node_dir / "status").exists()  # a variant is not speculative

    # A `related` variant with a proof claims nothing the proof could prove (F08-Q6).
    r = post(harness, "/proposals/variant", token, {**base, "relation_proof": RELATION_PROOF})
    assert r.status_code == 400 and r.json()["error"] == "proposal-invalid"

    partial = post(
        harness,
        "/proposals/variant",
        token,
        {**base, "relation": "partial", "relation_proof": RELATION_PROOF},
    )
    assert partial.status_code == 201, partial.text
    files = pushed(harness)
    root = materialise(files, tmp_path / "partial")
    node_dir = root / NODES / partial.json()["node_id"]
    relation = (node_dir / "Relation.lean").read_text()
    assert relation == f"-- relation: partial\n{RELATION_PROOF}"
    assert graphmod.relation_of(node_dir, "variant") == "partial"
    classification = modes.classify([Change("A", p) for p in files])
    assert classification.mode == "proposal"
    assert modes.check(root, classification) == []

    # A proof that already names a different label is refused rather than relabelled.
    r = post(
        harness,
        "/proposals/variant",
        token,
        {
            **base,
            "relation": "partial",
            "relation_proof": "-- relation: resolves\n" + RELATION_PROOF,
        },
    )
    assert r.status_code == 400 and r.json()["error"] == "proposal-invalid"
    assert "resolves" in r.json()["message"]


# --- POST /proposals/witness (F07-Q3, F08-R5) -----------------------------------------------------


HOLE = "and-reassoc--h1"


def add_hole(harness: Harness, *, cause: str | None = "witness-missing") -> None:
    """Put a compiler-derived hole into the committed graph.json, blocked as the post-merge job
    leaves one (F07-R6), and drop the service's cached copy."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != HOLE]
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "blocked" if cause else "ready",
            "cause": cause,
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)


def test_witness_completion_route(harness: Harness) -> None:
    """R5: a witness for a hole blocked `witness-missing` opens a PR adding only Witness.lean;
    a ready node, an unknown node, or a witness that is itself a sorry is refused."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    r = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert r.status_code == 201, r.text
    assert r.json()["node_id"] == HOLE
    files = pushed(harness)
    assert files == {f"{NODES}{HOLE}/Witness.lean": WITNESS}
    assert modes.classify([Change("M", p) for p in files]).mode == "proposal"

    stub = post(
        harness,
        "/proposals/witness",
        token,
        {"node_id": HOLE, "witness": "theorem witness : True := by\n  sorry\n"},
    )
    assert stub.status_code == 400 and stub.json()["error"] == "witness-invalid"
    ready = post(
        harness, "/proposals/witness", token, {"node_id": TUTORIAL_NODE, "witness": WITNESS}
    )
    assert ready.status_code == 400 and ready.json()["error"] == "witness-not-missing"
    unknown = post(harness, "/proposals/witness", token, {"node_id": "ghost", "witness": WITNESS})
    assert unknown.status_code == 404
    assert len(harness.githost.pushes) == 1

    add_hole(harness, cause=None)  # a filled hole is ready: its slot is closed
    r = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert r.status_code == 400 and r.json()["error"] == "witness-not-missing"


# --- limits and auth ------------------------------------------------------------------------------


def test_proposals_are_rate_limited_per_identity_per_day(harness: Harness) -> None:
    """F08 §6, D-29: 40 proposals per identity per day, published in the policy; the 41st is a
    429 with Retry-After, and the write-per-hour limit still applies underneath."""
    assert harness.settings.rate_limit_policy()["proposals_per_day"] == 40
    h = make_harness({"OPN_API_PROPOSALS_PER_DAY": "2", "OPN_API_WRITES_PER_HOUR": "100"})
    token = h.token_for("code_alice", "alice")
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    for i in range(2):
        r = post(h, "/proposals/speculative", token, {**body, "statement": STATEMENT + f"-- {i}\n"})
        assert r.status_code == 201, r.text
    r = post(h, "/proposals/speculative", token, {**body, "statement": STATEMENT + "-- 3\n"})
    assert r.status_code == 429
    assert r.json()["error"] == "rate-limited"
    assert int(r.headers["Retry-After"]) > 0
    assert len(h.githost.pushes) == 2
    assert h.client.get("/info.json").json()["rate_limit_policy"]["proposals_per_day"] == 2


def test_proposals_need_a_token(harness: Harness) -> None:
    for route, body in (
        (
            "/proposals/speculative",
            {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS},
        ),
        ("/proposals/variant", {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}),
        ("/proposals/witness", {"node_id": HOLE, "witness": WITNESS}),
    ):
        assert harness.client.post(route, json=body).status_code == 401
    assert harness.githost.pushes == []


def test_scaffold_from_texts_matches_scaffold_from_tree(tmp_path: Path) -> None:
    """The service's builder and the gate's are one function: the same proposal from fetched
    statements and from a checkout produces the same bytes."""
    fixtures = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "graphs"
    root = tmp_path / "graph"
    shutil.copytree(fixtures / "propositional", root)
    nodes_dir = root / NODES
    dep_text = (nodes_dir / "and-reassoc" / "Statement.lean").read_text()
    proposal = scaffold.Proposal(
        node_id="spec-abcdef01",
        target_id=TARGET,
        statement=STATEMENT,
        witness=WITNESS,
        author="alice",
        deps=("and-reassoc",),
        date="2026-09-10T00:00:00Z",
    )
    from_tree = scaffold.files(nodes_dir, proposal)
    from_texts = scaffold.files(None, proposal, dep_statements={"and-reassoc": dep_text})
    assert from_tree == from_texts
