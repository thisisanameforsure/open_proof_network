"""Finding proposal-deps-import (the 2026-09-19 primes run, agents A and C, from the public
tooling): a proposal's declared ``deps`` could not be used. A node sees its dependencies only
through ``import Nodes.«<own id>».Context`` (F00's import rule), and the service names the node
``variant-<hash of the statement>`` — so the statement would have to contain its own hash. Every
fixture names its node by hand, which is why no test saw it, and all four agents re-derived the
primes from Mathlib rather than reuse the proved root.

F08-T12: the id is taken from the text the caller sent, and the service then writes the import
into the node's Lean files, so what lands passes the gate's own layout and import checks.
"""

from __future__ import annotations

from pathlib import Path

from api_fakes import Harness
from test_proposals import (
    DEP_STATEMENT,
    NODES,
    RELATION_PROOF,
    STATEMENT,
    TARGET,
    WITNESS,
    materialise,
    post,
    pushed,
)

from opn_gate import layout, scaffold

DEP = "and-reassoc"
LIBRARY_STATEMENT = "import Mathlib.Tactic\n\n/-! A doc comment. -/\n\n" + STATEMENT


def propose(harness: Harness, statement: str, **extra: object) -> tuple[str, dict[str, str]]:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}{DEP}/Statement.lean"] = DEP_STATEMENT.encode()
    body = {"target_id": TARGET, "statement": statement, "witness": WITNESS, **extra}
    r = post(harness, "/proposals/variant", token, body)
    assert r.status_code == 201, r.text
    node_id = r.json()["node_id"]
    prefix = f"{NODES}{node_id}/"
    return node_id, {p.removeprefix(prefix): c for p, c in pushed(harness).items()}


def test_a_proposal_with_deps_imports_its_own_context(harness: Harness, tmp_path: Path) -> None:
    node_id, files = propose(
        harness,
        LIBRARY_STATEMENT,
        deps=[DEP],
        relation="resolves",
        relation_proof=RELATION_PROOF,
    )
    # the id is the caller's text's, so the same statement proposed twice still collides by name
    assert node_id == scaffold.speculative_id(LIBRARY_STATEMENT, "variant")
    own = f"import {layout.node_module(node_id, 'Context')}"
    statement = files["Statement.lean"]
    lines = statement.splitlines()
    assert lines[:2] == ["import Mathlib.Tactic", own]  # after the header's last import
    assert statement.endswith(STATEMENT)  # nothing else moved
    assert files["Witness.lean"].splitlines()[0] == own  # no header: the import leads
    assert own in files["Relation.lean"].splitlines()
    assert "OpnProp.and_reassoc" in files["Context.lean"]

    # what lands is what the gate's own checks accept
    root = materialise({f"{NODES}{node_id}/{p}": c for p, c in files.items()}, tmp_path / "graph")
    node_dir = root / NODES / node_id
    assert layout.validate_node(node_dir) == []
    assert layout.check_imports(node_dir, node_id) == []


def test_a_statement_imports_its_own_context_even_with_no_deps(harness: Harness) -> None:
    """F08-T13 (agent D, graph PR #123): a node gains dependencies *later*, when a skeleton
    merges and the post-merge job writes its holes into ``Context.lean``. A proof may not add an
    import, so a statement born without the line can never be closed through its holes: the
    closing proof of ``variant-2a7919a9`` failed step 4, "Unknown identifier
    `variant_2a7919a9__h1`", with both holes proved. An intake root has always carried the
    import; a proposed statement now does too. The witness needs no dependency and lands as
    sent."""
    node_id, files = propose(harness, LIBRARY_STATEMENT)
    own = f"import {layout.node_module(node_id, 'Context')}"
    assert files["Statement.lean"].splitlines()[:2] == ["import Mathlib.Tactic", own]
    assert files["Statement.lean"].endswith(STATEMENT)
    assert files["Witness.lean"] == WITNESS


def test_an_import_the_caller_wrote_is_not_doubled(harness: Harness) -> None:
    """A curator who knows the id (a revision keeps it) may have written the import already."""
    first_id = scaffold.speculative_id(LIBRARY_STATEMENT, "variant")
    own = f"import {layout.node_module(first_id, 'Context')}"
    _, files = propose(harness, LIBRARY_STATEMENT, deps=[DEP], witness=own + "\n" + WITNESS)
    assert files["Witness.lean"].count(own) == 1
