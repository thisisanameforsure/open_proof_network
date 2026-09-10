"""Round three of failing-case coverage: the branches the fast tier had not reached, grouped by
module — a failure path each, named by what it proves (session note
2026-09-10-test-coverage-review.md for rounds one and two)."""

from __future__ import annotations

import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import samples
from fakes import FAKE_RESOLVED, FakeToolchain, artifact_result, used_constants_result
from harness import GRAPH, TARGET, TUTORIAL, copy_graph, make_context
from scripted import ScriptedToolchain

from opn_gate import cli, curator, layout, postmerge, products, scaffold, schemas
from opn_gate import graph as graphmod
from opn_gate.graph import GraphError, NodeFacts
from opn_gate.steps import artifact as art
from opn_gate.steps.hazards import StatementStep

NODES = f"targets/{TARGET}/nodes"
CONTEXT_MODULE = f"Nodes.«{TUTORIAL}».Context"
TWO_THEOREMS = "theorem a : True := trivial\ntheorem b : True := trivial\n"


# --- products (F03-R6, R11) ---------------------------------------------------------------------


def test_scan_statement_reads_library_tags_through_the_seam(tmp_path: Path) -> None:
    """R6: the statement's constants, by module, become the sorted set of top-level Mathlib
    namespaces; a submission-local constant (module None) and Lean core name nothing."""
    root = copy_graph(tmp_path)
    node = graphmod.load_target(root, TARGET).nodes["and-reassoc"]
    fake = FakeToolchain(
        constants=used_constants_result(
            [
                ("Mathlib.Order.Basic.le_refl", "Mathlib.Order.Basic"),
                ("And", "Init.Prelude"),
                ("Mathlib.Algebra.Group.mul_one", "Mathlib.Algebra.Group.Defs"),
                ("Mathlib.Order.Lattice.inf", "Mathlib.Order.Lattice"),
                ("local_helper", None),
                ("Mathlib", "Mathlib"),  # the bare root names no namespace
            ]
        )
    )
    tags = products.scan_statement(fake, FAKE_RESOLVED, node, tmp_path / "w")
    assert tags == ["Algebra", "Order"]
    assert (tmp_path / "w" / "src" / "Nodes" / "and-reassoc" / "Context.lean").is_file()
    assert fake.calls[-1] == "used_constants:OpnProp.and_reassoc"


def test_scan_statement_refuses_a_node_whose_statement_no_longer_parses(tmp_path: Path) -> None:
    """The Context compiled, but the statement on disk is not one theorem: the scan names the
    node's defect rather than asking the metaprogram about a declaration it cannot name."""
    root = copy_graph(tmp_path)
    node = graphmod.load_target(root, TARGET).nodes["and-reassoc"]
    (node.path / "Statement.lean").write_text(TWO_THEOREMS)
    fake = FakeToolchain()
    with pytest.raises(GraphError, match=r"node and-reassoc: .*exactly one theorem, found 2"):
        products.scan_statement(fake, FAKE_RESOLVED, node, tmp_path / "w")
    assert not any(c.startswith("used_constants") for c in fake.calls)


def test_tag_cache_reads_a_committed_mapping_and_renders_it_canonically(tmp_path: Path) -> None:
    """A committed cache is trusted per statement hash (no rescan), and re-rendered sorted."""
    path = tmp_path / ".tags-cache.json"
    path.write_text('{"b": ["Order"], "a": ["Algebra", 3]}', encoding="utf-8")
    cache = products.TagCache(path)
    assert cache.entries == {"a": ["Algebra", "3"], "b": ["Order"]} and not cache.dirty
    root = copy_graph(tmp_path)
    node = graphmod.load_target(root, TARGET).nodes["and-reassoc"]
    cache.entries[node.statement_hash] = ["Cached"]

    def never(_n: NodeFacts) -> list[str]:
        raise AssertionError("a cached hash is never rescanned")

    assert cache.tags(node, never) == ["Cached"] and not cache.dirty
    assert cache.rendered() == schemas.canonical_json(
        {"a": ["Algebra", "3"], "b": ["Order"], node.statement_hash: ["Cached"]}
    )


def test_target_ids_is_empty_without_a_targets_directory(tmp_path: Path) -> None:
    assert products.target_ids(tmp_path) == []
    (tmp_path / "targets").write_text("a file, not a directory")
    assert products.target_ids(tmp_path) == []


def test_generate_writes_the_tag_cache_only_when_a_scan_changed_it(tmp_path: Path) -> None:
    """R6 on a Mathlib-pinned graph: the first render scans every frontier node and emits
    `.tags-cache.json` as a product; a second render over the written cache scans nothing and
    emits no cache file (R11: byte-identical products need no rewrite)."""
    root = copy_graph(tmp_path)
    spec_path = layout.gate_spec_path(root, TARGET)
    spec = schemas.load_json(spec_path)
    spec["mathlib_sha"] = samples.SHA1
    spec_path.write_bytes(schemas.canonical_json(spec))
    scanned: list[str] = []

    def scanner(node: NodeFacts) -> list[str]:
        scanned.append(node.node_id)
        return ["Order"]

    first = products.generate(
        root, rendered_from="5" * 40, commit_time="2026-09-10T00:00:00Z", scanner=scanner
    )
    cache_rel = Path("targets") / TARGET / products.TAGS_CACHE
    assert cache_rel in first.files and scanned
    written = first.write(root, write_meta=False)
    assert cache_rel in written and (root / cache_rel).read_bytes() == first.files[cache_rel]

    scanned.clear()
    second = products.generate(
        root, rendered_from="5" * 40, commit_time="2026-09-10T00:00:00Z", scanner=scanner
    )
    assert scanned == [] and cache_rel not in second.files
    assert second.files[Path("frontier.json")] == first.files[Path("frontier.json")]


# --- steps/hazards: the standalone statement step (F02-R7) ---------------------------------------


def test_statement_step_needs_step_1_to_have_passed(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    result = StatementStep().run(ctx)
    assert not result.ok and result.diagnostic is not None
    assert result.diagnostic.code == "step-order" and ctx.node is None


def test_statement_step_reports_the_wall_clock_cap(tmp_path: Path) -> None:
    """Compiling the repo Context past the cap is the `timeout` diagnostic naming the module and
    the cap, not a crash and not an elaboration failure."""
    tc = ScriptedToolchain(timeout_modules={CONTEXT_MODULE})
    ctx = make_context(tmp_path, toolchain=tc)
    ctx.data["toolchain"] = FAKE_RESOLVED
    result = StatementStep().run(ctx)
    assert not result.ok and result.diagnostic is not None
    assert result.diagnostic.code == "timeout"
    assert CONTEXT_MODULE in result.diagnostic.message and "300s" in result.diagnostic.message
    assert tc.calls == [f"elaborate:{CONTEXT_MODULE}"]


# --- steps/artifact (F07-R4, R5) ------------------------------------------------------------------


def test_request_derives_the_artifact_declaration_from_the_statement(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    node_dir = layout.graph_nodes_dir(ctx.graph_root, TARGET) / TUTORIAL
    loaded = layout.load_node(node_dir, TARGET)
    assert isinstance(loaded, layout.Node)
    ctx.node = loaded
    req = art.request(
        ctx,
        "counterexample",
        node_dir=node_dir,
        artifact=node_dir / "Proof.lean",
        artifact_module="M.P",
    )
    assert req.statement == node_dir / "Statement.lean" and req.decl == "OpnProp.and_swap"
    assert req.statement_module == f"Nodes.«{TUTORIAL}».Statement"
    assert req.artifact_decl == "OpnProp.and_swap_refuted" and req.kind == "counterexample"
    assert req.artifact_module == "M.P" and req.artifact == node_dir / "Proof.lean"


def test_run_hands_back_a_clean_partial_with_no_failure(tmp_path: Path) -> None:
    """A partial that matches its statement, with named holes under the cap and none restating
    the goal, is (artifact, None) — and the report is left in ctx.data for the record."""
    fake = FakeToolchain(
        artifact=artifact_result(kind="partial", holes=[("h1", "∀ p : Prop, p → p", False)])
    )
    ctx = make_context(tmp_path, toolchain=fake)
    node_dir = layout.graph_nodes_dir(ctx.graph_root, TARGET) / TUTORIAL
    loaded = layout.load_node(node_dir, TARGET)
    assert isinstance(loaded, layout.Node)
    ctx.node = loaded
    req = art.request(
        ctx, "partial", node_dir=node_dir, artifact=node_dir / "Proof.lean", artifact_module="M.P"
    )
    found, failure = art.run(ctx, FAKE_RESOLVED, req, "partial")
    assert failure is None and found is not None
    assert [h.name for h in found.holes] == ["h1"]
    assert (
        ctx.data["artifact"]["kind"] == "partial"
        and ctx.data["artifact"]["holes"][0]["name"] == "h1"
    )


# --- graph (F03-R1, R3; F07-R6, R8) ---------------------------------------------------------------


def test_artifact_of_is_none_when_the_proof_file_declares_two_theorems(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    node_dir = root / NODES / TUTORIAL
    (node_dir / "Proof.lean").write_text(TWO_THEOREMS)
    assert graphmod.artifact_of(node_dir, "OpnProp.and_swap") is None
    (node_dir / "Proof.lean").unlink()
    assert graphmod.artifact_of(node_dir, "OpnProp.and_swap") is None


def test_a_node_without_a_witness_file_reads_as_a_stub(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    node_dir = root / NODES / TUTORIAL
    assert not graphmod.witness_is_stub(node_dir)
    (node_dir / "Witness.lean").unlink()
    assert graphmod.witness_is_stub(node_dir)


def facts(node_id: str, deps: tuple[str, ...]) -> NodeFacts:
    return NodeFacts(
        node_id=node_id, target_id=TARGET, path=Path("/g") / node_id, statement_hash="a" * 64,
        deps=deps, origin="authored", tutorial=False, relation=None, proof=None, override=None,
    )  # fmt: skip


def test_check_dag_names_the_missing_dep_before_looking_for_a_cycle() -> None:
    """R3: the first problem is named — a dep that is not a node, before any cycle."""
    nodes = {"a": facts("a", ("ghost",)), "b": facts("b", ("a",))}
    with pytest.raises(GraphError, match="node 'a' declares dep 'ghost', which is not a node"):
        graphmod.check_dag(nodes)
    cyclic = {"a": facts("a", ("b",)), "b": facts("b", ("a",))}
    with pytest.raises(GraphError, match="dependency cycle: a -> b -> a"):
        graphmod.check_dag(cyclic)
    graphmod.check_dag({"a": facts("a", ()), "b": facts("b", ("a",))})  # a DAG passes silently


# --- curator (F08-R9, R12) ------------------------------------------------------------------------


def test_dependents_of_skips_a_directory_without_meta(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    nodes_dir = root / NODES
    (nodes_dir / "stray").mkdir()
    (nodes_dir / "not-a-dir.txt").write_text("")
    assert curator.dependents_of(nodes_dir, TUTORIAL) == ["and-swap-reassoc"]
    assert curator.dependents_of(nodes_dir, "nobody") == []


def test_relative_keeps_a_path_outside_the_graph_as_it_is(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    outside = tmp_path / "elsewhere" / "request.yaml"
    assert curator._relative(root, outside) == outside.as_posix()
    assert curator._relative(root, root / NODES / "x" / "META.yaml") == f"{NODES}/x/META.yaml"


def test_missing_library_report_skips_a_node_without_attempts(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    shutil.rmtree(root / NODES / TUTORIAL / "attempts")
    (root / NODES / "and-reassoc" / "attempts" / "not-a-record.txt").write_text("")
    assert curator.missing_library_report(root, TARGET, threshold=1) == []


# --- scaffold (F08-R3; F01-R6) --------------------------------------------------------------------


def test_imports_of_keeps_library_and_defs_modules_once_and_drops_node_imports() -> None:
    texts = [
        "import Init.Core\nimport Nodes.«a».Context\nimport Defs.Helper\n\ntheorem a : True\n",
        "import Init.Core\nimport Std.Data.List\nimport Other.Thing\n",
    ]
    assert scaffold.imports_of(texts) == ["Init.Core", "Defs.Helper", "Std.Data.List"]


def test_context_from_puts_the_import_block_before_the_header() -> None:
    text = scaffold.context_from(
        ("a",),
        {"a": "import Defs.Helper\nimport Nodes.«a».Context\n\ntheorem a : True := by\n  sorry\n"},
    )
    assert text.startswith(
        "import Defs.Helper\n\n/-! Declared dependencies (D-4 step 8): `a`. -/\n"
    )
    assert "Nodes.«a».Context" not in text and text.endswith("theorem a : True := by\n  sorry\n")
    assert scaffold.context_from((), {}) == "/-! Declared dependencies (D-4 step 8): none. -/\n"


def test_files_needs_a_checkout_or_the_dep_statements(tmp_path: Path) -> None:
    """The service holds no checkout (D-35) and hands in statements; the CLI has a checkout;
    neither is a scaffold that cannot see its deps. A speculative proposal also carries its
    status record (F08-Q2)."""
    proposal = scaffold.Proposal(
        node_id="spec-one",
        target_id=TARGET,
        statement="theorem OpnProp.spec_one : True := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="alice",
        deps=(TUTORIAL,),
        speculative=True,
        date="2026-09-10T12:13:14Z",
    )
    with pytest.raises(scaffold.ScaffoldError, match="needs either a nodes directory"):
        scaffold.files(None, proposal)
    root = copy_graph(tmp_path)
    out = scaffold.files(root / NODES, proposal)
    tutorial_statement = (GRAPH / NODES / TUTORIAL / "Statement.lean").read_text()
    assert scaffold.strip_imports(tutorial_statement) in out["Context.lean"]
    assert out["status/20260910T121314-alice.yaml"].startswith("schema: node-status/v1")
    assert "speculative" in out["status/20260910T121314-alice.yaml"]


# --- postmerge (F05-R10; F07-R6) ------------------------------------------------------------------


def test_fetch_claims_snapshot_asks_urllib_with_the_gate_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"schema": "claims/v1"}'

    def urlopen(request: urllib.request.Request, timeout: int) -> Response:
        seen["url"] = request.full_url
        seen["agent"] = request.get_header("User-agent")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    body = postmerge.fetch_claims_snapshot("https://api.example/claims.json")
    assert body == b'{"schema": "claims/v1"}'
    assert seen == {"url": "https://api.example/claims.json", "agent": "opn-gate", "timeout": 10}


def test_partial_merge_as_dict_names_what_it_produced() -> None:
    merge = postmerge.PartialMerge(
        ("p--h1", "p--h2"), "attempts/x-partial.lean", "skeleton-hole", "a" * 64
    )
    assert merge.as_dict() == {
        "children": ["p--h1", "p--h2"],
        "attempt": "attempts/x-partial.lean",
        "origin": "skeleton-hole",
        "annex": "a" * 64,
    }


# --- layout (F00-R19; F07-R4) ---------------------------------------------------------------------


def test_parse_declaration_qualifies_by_the_namespaces_still_open() -> None:
    """A namespace closed before the theorem does not qualify it; nested ones close inner-first;
    an `end` that names something else leaves the stack alone."""
    assert layout.parse_declaration("namespace Foo\nend Foo\ntheorem t : True := trivial\n") == "t"
    assert (
        layout.parse_declaration("namespace A\nnamespace B\nend B\ntheorem t : True := trivial\n")
        == "A.t"
    )
    assert layout.parse_declaration("namespace A\nend Z\ntheorem t : True := trivial\n") == "A.t"
    assert layout.parse_declaration("namespace A\ntheorem t : True := trivial\nend A\n") == "A.t"


# --- cli (F08-R11) --------------------------------------------------------------------------------


def test_last_progress_merge_is_none_when_no_commit_touched_the_nodes(tmp_path: Path) -> None:
    """D-33 (a) on a checkout whose history never touched the target's nodes: no last merge,
    rather than the repository's own first commit."""
    root = copy_graph(tmp_path)
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
    }  # fmt: skip

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    git("init", "-q")
    git("add", "--", f"targets/{TARGET}/gate-spec.json")
    git("commit", "-q", "-m", "spec only")
    assert cli.last_progress_merge(root, TARGET) is None
    git("add", "-A")
    git("commit", "-q", "-m", "nodes")
    assert cli.last_progress_merge(root, TARGET) is not None
    assert cli.last_progress_merge(copy_graph(tmp_path / "bare"), TARGET) is None
