"""F28-T7, T9: closing by construction, the Python half (fast tier).

The join itself is the lean tier's (``test_close_compose.py``); here the fake toolchain stands in
for it, and the staging (``outline_graph.build``, the outline job's, tested there) is replaced by
a recorder, so these tests are about what ``close`` decides, sends and records, and that one sweep
climbs a whole chain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fakes import FAKE_RESOLVED, FakeToolchain
from harness import GRAPH, TARGET, TUTORIAL

from opn_gate import (
    close,
    closing,
    closure,
    graph,
    layout,
    outline,
    outline_graph,
    paths,
    products,
    schemas,
)
from opn_gate.toolchain import MetaprogramResult

TC = FAKE_RESOLVED
PARTIAL = "attempts/20261014T181000Z-a-partial.lean"
FACTS = close.Facts(
    graph_commit="c" * 40,
    network_commit="d" * 40,
    lean_toolchain="leanprover/lean4:v4.33.1",
    mathlib_sha=None,
    timestamp="2026-10-15T12:00:00Z",
)
JOINED = MetaprogramResult(
    ok=True, doc={"ok": True, "holes": [{"hole": "h1", "child": "x"}], "axioms": ["propext"]}
)


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
                "partial": PARTIAL,
                "annex": None,
                "holes": [{"name": f"h{i + 1}", "node": h} for i, h in enumerate(holes)],
            }
            for holes in (routes or [])
        ],
        "circular": [],
    }


def tree_of(tmp_path: Path, *nodes: str) -> Path:
    """A scratch tree with a Statement.lean and an assembly for each node."""
    tree = tmp_path / "tree"
    for n in nodes:
        d = tree / "targets" / "t" / "nodes" / n
        (d / "attempts").mkdir(parents=True)
        (d / "Statement.lean").write_text(f"theorem {n} : True := by\n  sorry\n")
        (d / PARTIAL).write_text(f"theorem {n} : True := by\n  have h : True := sorry\n  exact h\n")
    return tree


@pytest.fixture
def staged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[outline_graph.Found]:
    """Replace the staging with a recorder that answers a Job, and the children's statements with
    a fixed reading, so a test sees exactly what reaches the join."""
    seen: list[outline_graph.Found] = []

    def build(*args: Any, **kw: Any) -> outline.Job:
        found: outline_graph.Found = args[3]
        seen.append(found)
        return outline.Job(
            target=found.target,
            node=found.node,
            artifact=found.artifact,
            file=tmp_path / "Proof.lean",
            module=f"Nodes.«{found.node}».Proof",
            decl=found.node,
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


def ready(node: str, *inputs: str) -> closing.Closable:
    return closing.Closable(node, closing.Link("route", f"{node}@1", inputs), True)


def test_a_route_join_sends_its_assembly_children_and_module_path(
    tmp_path: Path, staged: list[outline_graph.Found]
) -> None:
    tree = tree_of(tmp_path, "p")
    gdoc = {"nodes": [row("p", routes=[["p--h1", "p--h2"]])]}
    fake = FakeToolchain(close_doc=JOINED)
    got = close.join_route(
        fake, TC, tree, "t", ready("p", "p--h1", "p--h2"), tmp_path / "w",
        gdoc=gdoc, facts=FACTS, timeout_s=60,
    )  # fmt: skip
    assert got.ok and got.record is not None
    [req] = fake.close_requests
    assert (req.module, req.decl) == ("Nodes.«p».Proof", "p")
    assert req.out_olean.name == "Proof.olean"
    assert req.out_olean.is_relative_to(tmp_path / "build")
    assert json.loads(req.children.read_text(encoding="utf-8")) == [
        {"node": "p--h1", "decl": "p__h1"},
        {"node": "p--h2", "decl": "p__h2"},
    ]
    assert [f.artifact.path for f in staged] == [PARTIAL]
    record = got.record
    assert schemas.violations(record, closure.SCHEMA) == []
    assert record["link"] == {"kind": "route", "id": "p@1", "inputs": ["p--h1", "p--h2"]}
    assert record["source"]["path"] == PARTIAL and record["source"]["text"] is None
    assert record["axioms"] == ["propext"]
    assert record["signature"]["kind"] == "none"  # signed later, by the post-merge job


def test_a_failed_join_writes_no_record(tmp_path: Path, staged: list[outline_graph.Found]) -> None:
    tree = tree_of(tmp_path, "p")
    gdoc = {"nodes": [row("p", routes=[["p--h1"]])]}
    fake = FakeToolchain(
        close_doc=MetaprogramResult(
            ok=True, doc={"ok": False, "error": "hole h1: no child closes it"}
        )
    )
    got = close.join_route(
        fake, TC, tree, "t", ready("p", "p--h1"), tmp_path / "w",
        gdoc=gdoc, facts=FACTS, timeout_s=60,
    )  # fmt: skip
    assert (got.ok, got.reason, got.detail) == (
        False,
        close.JOIN_FAILED,
        "hole h1: no child closes it",
    )


def test_a_build_failure_is_named(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tree = tree_of(tmp_path, "p")

    def broken(*args: Any, **kw: Any) -> outline.Job:
        raise outline_graph.BuildError("Nodes.«p».Context does not elaborate")

    monkeypatch.setattr(outline_graph, "build", broken)
    got = close.join_route(
        FakeToolchain(), TC, tree, "t", ready("p", "p--h1"), tmp_path / "w",
        gdoc={"nodes": [row("p", routes=[["p--h1"]])]}, facts=FACTS, timeout_s=60,
    )  # fmt: skip
    assert (got.reason, got.detail) == (close.BUILD_FAILED, "Nodes.«p».Context does not elaborate")


def test_one_sweep_climbs_the_chain_and_never_retries_a_failure(
    tmp_path: Path, staged: list[outline_graph.Found], monkeypatch: pytest.MonkeyPatch
) -> None:
    """r <- [a], a <- [b], b proved; and s <- [q], q proved, whose join fails. One sweep joins a,
    then r (once a's record is in the tree), tries s once, and stops."""
    tree = tree_of(tmp_path, "r", "a", "b", "s", "q")
    nodes = layout.graph_nodes_dir(tree, "t")

    def has(n: str) -> bool:
        return closure.path_for(nodes / n).is_file()

    def doc() -> dict[str, Any]:
        st = {"b": "proved", "q": "proved", "a": "proved" if has("a") else "ready"}
        st["r"] = "proved" if has("r") else "ready"
        return {
            "root": "r",
            "nodes": [
                row("r", st["r"], [["a"]]), row("a", st["a"], [["b"]]), row("b", "proved"),
                row("s", "ready", [["q"]]), row("q", "proved"),
            ],
        }  # fmt: skip

    monkeypatch.setattr(graph, "load_target", lambda tree, target: None)
    monkeypatch.setattr(products, "graph_doc", lambda tg, rendered: doc())

    class Fake(FakeToolchain):
        def close(self, tc: Any, req: Any, search_path: Any, *, timeout_s: Any = None) -> Any:
            self.close_requests.append(req)
            if req.decl == "s":
                return MetaprogramResult(ok=True, doc={"ok": False, "error": "no child closes it"})
            return JOINED

    fake = Fake()
    results = close.sweep(fake, TC, tree, "t", tmp_path / "w", facts=FACTS, timeout_s=60)
    assert [(r.node, r.ok) for r in results] == [("a", True), ("s", False), ("r", True)]
    assert [req.decl for req in fake.close_requests] == ["a", "s", "r"]
    assert closure.path_for(nodes / "r").is_file() and not closure.path_for(nodes / "s").is_file()


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
