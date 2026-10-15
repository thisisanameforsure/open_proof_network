"""F28-T2: composing a node's closing proof, the Python half (fast tier).

The composer itself is the lean tier's (``test_close_compose.py``); here the fake toolchain stands
in for it, and the staging (``outline_graph.build``, the outline job's, already tested there) is
replaced by a recorder, so these tests are about what ``close.compose`` decides and sends.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fakes import FAKE_RESOLVED, FakeToolchain
from harness import GRAPH, TARGET, TUTORIAL

from opn_gate import close, layout, outline, outline_graph, paths
from opn_gate.toolchain import MetaprogramResult

TC = FAKE_RESOLVED
PARTIAL = "attempts/20261014T181000Z-a-partial.lean"


def row(
    node_id: str, status: str = "ready", routes: list[list[str]] | None = None
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "status": status,
        "deps": [],
        "origin": "skeleton-hole",
        "relation": None,
        "decompositions": [
            {
                "partial": PARTIAL if k == 0 else f"attempts/2026101{k}T000000Z-b-partial.lean",
                "annex": None,
                "holes": [{"name": f"h{i + 1}", "node": h} for i, h in enumerate(holes)],
            }
            for k, holes in enumerate(routes or [])
        ],
        "circular": [],
    }


def tree_with(tmp_path: Path, *rows: dict[str, Any], root: str = "p") -> Path:
    tree = tmp_path / "tree"
    target = tree / "targets" / "t"
    (target / "nodes" / "p" / "attempts").mkdir(parents=True)
    (target / "nodes" / "p" / PARTIAL).write_text("theorem p : True := by\n  sorry\n")
    doc = {"schema": "graph/v9", "target_id": "t", "root": root, "nodes": list(rows)}
    (target / "graph.json").write_text(json.dumps(doc), encoding="utf-8")
    return tree


@pytest.fixture
def staged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[outline_graph.Found]:
    """Replace the staging with a recorder that answers a Job, and the children's statements with
    a fixed reading, so a test sees exactly what reaches the composer."""
    seen: list[outline_graph.Found] = []

    def build(*args: Any, **kw: Any) -> outline.Job:
        found: outline_graph.Found = args[3]
        seen.append(found)
        return outline.Job(
            target=found.target,
            node=found.node,
            artifact=found.artifact,
            file=tmp_path / "Proof.lean",
            module="Nodes.«p».Proof",
            decl="p",
            holes={},
            search_path=(tmp_path / "build",),
        )

    monkeypatch.setattr(outline_graph, "build", build)
    monkeypatch.setattr(
        close,
        "children",
        lambda tree, target, inputs: [{"node": n, "decl": n.replace("-", "_")} for n in inputs],
    )
    return seen


def test_a_node_that_is_not_closable_is_refused_before_anything_runs(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    tree = tree_with(tmp_path, row("p", routes=[["p--h1"]]), row("p--h1"))
    fake = FakeToolchain()
    got = close.compose(fake, TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert (got.ok, got.reason, got.link) == (False, close.NOT_CLOSABLE, None)
    assert staged == [] and fake.close_requests == []


def test_a_node_waiting_on_a_closable_child_is_not_ready(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    """A10's middle level: closable, but its closing proof waits on the child's."""
    tree = tree_with(
        tmp_path,
        row("p", routes=[["p--h1"]]),
        row("p--h1", routes=[["p--h1--h1"]]),
        row("p--h1--h1", "proved"),
    )
    got = close.compose(FakeToolchain(), TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert (got.reason, got.detail) == (close.NOT_READY, "waits on p--h1")
    assert staged == []


def test_a_claim_link_on_a_node_that_does_not_load_is_named(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    """A claim link goes to ``compose_link`` (T3); a node the gate cannot load is a build
    failure before anything is staged."""
    hole = row("p--h1", "proved")
    hole["circular"] = [{"ancestor": "p", "claim": "p--h1/defects/x.yaml"}]
    tree = tree_with(tmp_path, row("p"), hole)
    got = close.compose(FakeToolchain(), TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert got.reason == close.BUILD_FAILED
    assert got.link is not None and got.link.kind == "claim"
    assert staged == []


def test_a_ready_route_stages_its_own_assembly_and_sends_its_children(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    """The route chosen (the second here, the first being open) names the assembly staged, and
    the children file lists that route's holes in its order."""
    tree = tree_with(
        tmp_path,
        row("p", routes=[["p--h1"], ["p--h2", "p--h3"]]),
        row("p--h1"),
        row("p--h2", "proved"),
        row("p--h3", "proved"),
    )
    fake = FakeToolchain(
        close_doc=MetaprogramResult(
            ok=True,
            doc={"ok": True, "sites": [{"child": "p--h2"}], "composed": "theorem p : True := x"},
        )
    )
    got = close.compose(fake, TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert got.ok and got.proof == "theorem p : True := x"
    assert got.link is not None and got.link.id == "p@2"
    assert [f.artifact.path for f in staged] == ["attempts/20261011T000000Z-b-partial.lean"]
    [req] = fake.close_requests
    assert (req.module, req.decl) == ("Nodes.«p».Proof", "p")
    assert json.loads(req.children.read_text(encoding="utf-8")) == [
        {"node": "p--h2", "decl": "p__h2"},
        {"node": "p--h3", "decl": "p__h3"},
    ]


def test_a_composer_failure_is_reported_with_its_sites(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    """F28-R10's first half: a hole no child closes is a named failure, the sites kept."""
    tree = tree_with(tmp_path, row("p", routes=[["p--h1"]]), row("p--h1", "proved"))
    site = {"line": 5, "problem": "no child's statement closes this hole", "tried": ["x"]}
    fake = FakeToolchain(
        close_doc=MetaprogramResult(
            ok=True, doc={"ok": False, "error": "a hole could not be closed", "sites": [site]}
        )
    )
    got = close.compose(fake, TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert (got.ok, got.reason, got.detail) == (
        False,
        close.COMPOSE_FAILED,
        "a hole could not be closed",
    )
    assert got.sites == (site,)
    assert json.loads(json.dumps(got.as_dict()))["sites"] == [site]


def test_a_build_failure_is_named(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tree = tree_with(tmp_path, row("p", routes=[["p--h1"]]), row("p--h1", "proved"))

    def broken(*args: Any, **kw: Any) -> outline.Job:
        raise outline_graph.BuildError("Nodes.«p».Context does not elaborate")

    monkeypatch.setattr(outline_graph, "build", broken)
    got = close.compose(FakeToolchain(), TC, tree, "t", "p", tmp_path / "w", timeout_s=60)
    assert (got.reason, got.detail) == (close.BUILD_FAILED, "Nodes.«p».Context does not elaborate")


def test_children_read_each_statement_s_theorem() -> None:
    """The decl comes from the node's own statement, as the gate loads it."""
    assert close.children(GRAPH, TARGET, (TUTORIAL,)) == [
        {"node": TUTORIAL, "decl": "OpnProp.and_swap"}
    ]


# --- claims and variants (F28-T3) ---------------------------------------------------------------

EXHIBIT = (
    "import Mathlib\n\nopen scoped Nat\n\n"
    "theorem circular : (∃ K : Nat, K = K) → (∃ K : Nat, K + 0 = K) := by\n"
    "  rintro ⟨K, _⟩\n  exact ⟨K, rfl⟩\n"
)
STATEMENT = (
    "import Mathlib\nimport Nodes.«a».Context\n\nopen scoped Nat\n\n"
    "/-- The ancestor. -/\ntheorem a_thm : ∃ K : Nat, K + 0 = K := by\n  sorry\n"
)


def test_an_exhibit_becomes_a_private_helper() -> None:
    got = close.as_helper(EXHIBIT, "claim", STATEMENT)
    assert got.startswith("private theorem opn_closing_link : (∃ K")
    assert "import" not in got and "open" not in got
    assert "circular" not in got


def test_every_declaration_of_the_implication_is_made_private() -> None:
    src = (
        "import Mathlib\n\nlemma aux : True := trivial\n\n"
        "theorem circular : True → True := fun _ => aux\n"
    )
    got = close.as_helper(src, "claim", STATEMENT)
    assert "private lemma aux" in got and "private theorem opn_closing_link" in got


def test_an_open_the_statement_lacks_is_refused() -> None:
    src = "import Mathlib\n\nopen Real\n\ntheorem circular : True → True := id\n"
    with pytest.raises(close.LinkError, match="open Real"):
        close.as_helper(src, "claim", STATEMENT)


def test_an_implication_under_another_name_is_refused() -> None:
    with pytest.raises(close.LinkError, match="no `relation`"):
        close.as_helper(EXHIBIT, "variant", STATEMENT)


def test_the_link_proof_is_the_statement_with_helper_and_use() -> None:
    st = layout.parse_statement(STATEMENT)
    assert isinstance(st, layout.Statement)
    helper = close.as_helper(EXHIBIT, "claim", STATEMENT)
    text = close.link_text(st, helper, "h_thm", "Nodes.«a--h1--h1».Proof")
    lines = text.splitlines()
    assert lines[:3] == [
        "import Mathlib",
        "import Nodes.«a».Context",
        "import Nodes.«a--h1--h1».Proof",
    ]
    assert text.index("private theorem opn_closing_link") < text.index("/-- The ancestor. -/")
    assert text.rstrip().endswith(":= (opn_closing_link @_root_.h_thm)")
    # step 2's own readings: the use line is a use, the rest the statement with a helper block
    assert layout.split_uses(st.prefix, text, "a")[1] == ("Nodes.«a--h1--h1».Proof",)
    assert paths.check_proof_is_statement(st, text, node_id="a") is None
    assert paths.helper_problem(helper, first_line=1) is None


def test_a_dependency_needs_no_use_line() -> None:
    st = layout.parse_statement(STATEMENT)
    assert isinstance(st, layout.Statement)
    text = close.link_text(st, close.as_helper(EXHIBIT, "claim", STATEMENT), "h_thm", None)
    assert "Proof" not in text.splitlines()[2]
