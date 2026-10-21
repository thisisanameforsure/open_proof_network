"""F28-T10 (decisions v3.46; D-12, D-30): a proved ``refutes`` variant refutes the root by
derivation, through the closure the gate already writes for a ``resolves`` one.

A ``refutes`` variant's ``Relation.lean`` proves ``variant → ¬root``. Once the variant is proved,
the post-merge job composes ``relation (variant's theorem)`` as a theorem of type ``¬ <root>``,
the kernel accepts it, and the closure record says ``verdict: refuted``. The root then *derives*
refuted while the variant is proved and its statement is vouched (the same guards as a proving
closure), its target resolves, its dependents read ``dep-refuted``, and a proof of the refuting
variant is asked step 9 like a proof of a resolving one. Nothing is written but the record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FAKE_RESOLVED, FakeToolchain
from harness import TARGET, copy_graph
from test_close import FACTS, staged  # noqa: F401 — the staging recorder, a fixture
from test_closing import doc, found, node
from test_finding_closed_root import frontier, generate, index_row
from test_finding_step9_certified import ROOT, classify, curated, step9
from test_finding_step9_root_only import ASKED, NOT_ASKED_INTERMEDIATE, RELATION, add_node, prove
from test_node_proofs import proof_hash
from test_products import ROOT_NODE, attest, nodes_dir

from opn_gate import close, closing, closure, graph, layout, modes, products, scaffold, schemas

REFUTED = closure.VERDICT_REFUTED
PROVED = closure.VERDICT_PROVED
VARIANT = "variant-refutes"

# --- 1. closing.links: a refutes variant at the root is a variant link with its verdict ---------


def test_a_refutes_variant_at_the_root_is_a_variant_link_with_verdict_refuted() -> None:
    g = doc(node("t"), node("v", "proved", relation="refutes"))
    assert found(g) == {"t": ("variant", "v", ("v",), True)}
    [c] = closing.closable(g)
    assert c.link.verdict == REFUTED
    # the published shape (the MCP's closable list, a closed schema) is unchanged
    assert c.as_dict()["link"] == {"kind": "variant", "id": "v", "inputs": ["v"]}


def test_a_resolves_link_yields_proved_and_a_weaker_variant_no_link() -> None:
    [c] = closing.closable(doc(node("t"), node("v", "proved", relation="resolves")))
    assert c.link.verdict == PROVED
    assert found(doc(node("t"), node("v", "proved", relation="partial"))) == {}


# --- 2. the composed refutation: ``¬ <root statement>`` from the relation and the variant -------

STATEMENT = (
    "import Nodes.«a».Context\n\n"
    "/-- The ancestor. -/\ntheorem a_thm : ∃ K : Nat, K + 0 = K := by\n  sorry\n"
)
REFUTATION = (
    "-- relation: refutes\n\n"
    "theorem relation : (∃ K : Nat, K ≠ K) → ¬ ∃ K : Nat, K + 0 = K :=\n"
    "  fun ⟨_, h⟩ _ => absurd rfl h\n"
)


def statement(text: str) -> layout.Statement:
    st = layout.parse_statement(text)
    assert isinstance(st, layout.Statement), st
    return st


def test_the_refuting_proof_declares_the_negation_under_its_own_name() -> None:
    st = statement(STATEMENT)
    helper = close.as_helper(REFUTATION, "variant", st.prefix)
    text = close.link_text(st, helper, "v_thm", "Nodes.«v».Proof", verdict=REFUTED)
    assert text.splitlines()[:2] == ["import Nodes.«a».Context", "import Nodes.«v».Proof"]
    assert text.index("private theorem opn_closing_link") < text.index("/-- The ancestor. -/")
    assert (
        "theorem a_thm_refuted : ¬ (∃ K : Nat, K + 0 = K) := (opn_closing_link @_root_.v_thm)"
        in text
    )
    assert "theorem a_thm :" not in text  # the root's own declaration is not restated
    assert "sorry" not in text


def test_binders_before_the_colon_are_bound_under_the_negation() -> None:
    """``theorem t (n : Nat) (h : 0 < n) : n < 3`` is the proposition ``∀ n h, n < 3``, and its
    negation is of the whole, never ``∀ n h, ¬ n < 3``."""
    st = statement("theorem t (n : Nat) (h : 0 < n) : n < 3 := by\n  sorry\n")
    text = close.link_text(st, "", "v", None, verdict=REFUTED)
    assert text.strip() == (
        "theorem t_refuted : ¬ (∀ (n : Nat) (h : 0 < n), n < 3) := (opn_closing_link @_root_.v)"
    )


def test_the_proving_text_is_unchanged() -> None:
    st = statement(STATEMENT)
    helper = close.as_helper(REFUTATION, "variant", st.prefix)
    assert close.link_text(st, helper, "v", None) == close.link_text(
        st, helper, "v", None, verdict=PROVED
    )
    assert "theorem a_thm : ∃ K : Nat, K + 0 = K := (opn_closing_link @_root_.v)" in (
        close.link_text(st, helper, "v", None)
    )


# --- 3. join_link and the sweep write the verdict (fake toolchain) ----------------------------


def refutes_variant(
    root: Path, node_id: str, n: int, submitter: str, *, proved: bool = True
) -> None:
    """A ``refutes`` variant of the fixture root with no dependencies, proved and attested as
    merge ``n`` (as ``test_target_proofs.resolves_variant`` does for a resolving one)."""
    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=TARGET,
        statement=f"theorem OpnProp.{node_id.replace('-', '_')} : True := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="refutes",
        relation_proof="theorem relation : True → ¬ False := fun _ h => h\n",
        date="2026-09-12T00:00:00Z",
    )
    scaffold.validate(proposal)
    written = scaffold.write(nodes_dir(root), proposal)
    if not proved:
        return
    text = (written / "Statement.lean").read_text(encoding="utf-8")
    (written / "Proof.lean").write_text(text.replace("sorry", "trivial"), encoding="utf-8")
    attest(
        root,
        node_id,
        n=n,
        artifact_hash=proof_hash(root, node_id),
        submitter=submitter,
        footprint={"nodes": []},
    )
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-09-12-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )


def refuting_link() -> closing.Closable:
    return closing.Closable(
        ROOT_NODE, closing.Link("variant", VARIANT, (VARIANT,), verdict=REFUTED), True
    )


def test_the_join_through_a_refutes_variant_records_verdict_refuted(
    tmp_path: Path,
    staged: list[Any],  # noqa: F811 — the imported fixture
) -> None:
    root = copy_graph(tmp_path)
    refutes_variant(root, VARIANT, 5, "eve")
    got = close.join_link(
        FakeToolchain(), FAKE_RESOLVED, root, TARGET, refuting_link(), tmp_path / "w",
        facts=FACTS, timeout_s=60,
    )  # fmt: skip
    assert got.ok, (got.reason, got.detail)
    assert got.record is not None
    assert got.record["verdict"] == REFUTED
    assert got.record["link"] == {"kind": "variant", "id": VARIANT, "inputs": [VARIANT]}
    text = str(got.record["source"]["text"])
    # the recorder stands in for ``close.children`` with ``<id with underscores>`` as the decl
    assert "theorem OpnProp.and_swap_reassoc_refuted : ¬ (∀ p q r : Prop," in text
    assert text.rstrip().endswith(":= (opn_closing_link @_root_.variant_refutes)")
    assert [f.artifact.path for f in staged] == [close.LINK_FILE]


def test_the_sweep_closes_the_root_as_refuted(
    tmp_path: Path,
    staged: list[Any],  # noqa: F811 — the imported fixture
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The post-merge job's loop (``opn-gate close``): a refutes link goes through it like a
    resolves one and leaves ``closure.json`` with ``verdict: refuted`` beside the root."""
    root = copy_graph(tmp_path)
    refutes_variant(root, VARIANT, 5, "eve")
    g = doc(node(ROOT_NODE), node(VARIANT, "proved", relation="refutes"), root=ROOT_NODE)
    monkeypatch.setattr(graph, "load_target", lambda tree, target: None)
    monkeypatch.setattr(products, "graph_doc", lambda tg, rendered: g)
    results = close.sweep(
        FakeToolchain(), FAKE_RESOLVED, root, TARGET, tmp_path / "w", facts=FACTS, timeout_s=60
    )
    assert [(r.node, r.ok) for r in results] == [(ROOT_NODE, True)]
    record = closure.load(nodes_dir(root) / ROOT_NODE)
    assert record is not None and record["verdict"] == REFUTED


# --- 4. derive_statuses: the root reads refuted while the variant is proved and it is vouched --

HASH = "a" * 64
PROOF = graph.Proof(merge_commit="0" * 40, trust_base=graph.TRUST_KERNEL, attestation="")


def facts(
    node_id: str,
    *,
    proved: bool = False,
    relation: str | None = None,
    deps: tuple[str, ...] = (),
    closure_record: dict[str, Any] | None = None,
) -> graph.NodeFacts:
    return graph.NodeFacts(
        node_id=node_id,
        target_id="t",
        path=Path(node_id),
        statement_hash=HASH,
        deps=deps,
        origin="variant" if relation else "authored",
        tutorial=False,
        relation=relation,
        proof=PROOF if proved else None,
        override=None,
        artifact="proof" if proved else None,
        closure=closure_record,
    )


def record(verdict: str | None, *, statement_hash: str = HASH) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "statement_hash": statement_hash,
        "link": {"kind": "variant", "id": "v", "inputs": ["v"]},
    }
    if verdict is not None:
        rec["verdict"] = verdict
    return rec


def refuted_root(*, variant_proved: bool = True, verdict: str | None = REFUTED) -> dict[str, Any]:
    return {
        "r": facts("r", closure_record=record(verdict)),
        "v": facts("v", proved=variant_proved, relation="refutes"),
        "d": facts("d", deps=("r",)),
    }


def test_a_refuted_verdict_derives_refuted_and_its_dependents_dep_refuted() -> None:
    got = graph.derive_statuses(refuted_root(), root="r", root_vouched=True)
    assert got == {"d": "blocked", "r": "refuted", "v": "proved"}
    nodes = refuted_root()
    assert graph.blocked_because(nodes["d"], got.__getitem__) == (True, graph.CAUSE_DEP_REFUTED)


def test_an_unvouched_root_is_not_refuted() -> None:
    got = graph.derive_statuses(refuted_root(), root="r", root_vouched=False)
    assert got["r"] == "ready" and got["v"] == "proved"


def test_a_variant_no_longer_proved_reopens_the_root() -> None:
    """D-18: no record moves; the derivation falls back the moment its input does."""
    nodes = refuted_root(variant_proved=False)
    got = graph.derive_statuses(nodes, root="r", root_vouched=True)
    assert got == {"d": "blocked", "r": "ready", "v": "ready"}  # d waits on an open r, no cause
    assert graph.blocked_because(nodes["d"], got.__getitem__) == (True, None)


def test_a_record_for_another_statement_refutes_nothing() -> None:
    nodes = refuted_root()
    nodes["r"] = facts("r", closure_record=record(REFUTED, statement_hash="f" * 64))
    assert graph.derive_statuses(nodes, root="r", root_vouched=True)["r"] == "ready"


def test_a_v1_record_without_a_verdict_still_proves() -> None:
    got = graph.derive_statuses(refuted_root(verdict=None), root="r", root_vouched=True)
    assert got["r"] == "proved"


# --- 5. products: resolved target, the refutation listed, nothing on the frontier --------------


def write_refuting_closure(root: Path) -> None:
    node_dir = nodes_dir(root) / ROOT_NODE
    text = "theorem x_refuted : ¬ True := (opn_closing_link @_root_.OpnProp.variant_refutes)\n"
    rec = closure.build(
        target_id=TARGET,
        node_id=ROOT_NODE,
        statement_hash=schemas.content_hash((node_dir / "Statement.lean").read_bytes()),
        link=closure.Link("variant", VARIANT, (VARIANT,)),
        source_path=None,
        source_text=text,
        source_hash=schemas.content_hash(text.encode()),
        axioms=[],
        verdict=REFUTED,
        graph_commit="c" * 40,
        network_commit=None,
        lean_toolchain="leanprover/lean4:v4.33.1",
        mathlib_sha=None,
        timestamp="2026-10-21T12:00:00Z",
    )
    closure.write(node_dir, rec)


@pytest.fixture
def refuted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = copy_graph(tmp_path, publish=True)
    refutes_variant(root, VARIANT, 5, "eve")
    write_refuting_closure(root)
    monkeypatch.setattr(modes, "root_vouched", lambda target_dir, **kw: "certificate")
    return root


def test_the_target_resolves_and_the_root_leaves_the_frontier(refuted: Path) -> None:
    tg = graph.load_target(refuted, TARGET)
    assert tg.statuses[ROOT_NODE] == "refuted"
    assert products.closing_node(tg) == ROOT_NODE
    prod = generate(refuted)
    assert index_row(prod)["status"] == "resolved"
    assert ROOT_NODE not in frontier(prod) and VARIANT not in frontier(prod)


def test_target_proofs_lists_the_refutation_with_its_relation(refuted: Path) -> None:
    tg = graph.load_target(refuted, TARGET)
    gdoc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    [entry] = gdoc["target_proofs"]
    assert (entry["node_id"], entry["relation"], entry["submitter"]) == (VARIANT, "refutes", "eve")
    assert entry["closure"] == [VARIANT]
    [row] = [n for n in gdoc["nodes"] if n["node_id"] == ROOT_NODE]
    assert row["status"] == "refuted"
    assert row["closure"] == {
        "kind": "variant",
        "id": VARIANT,
        "inputs": [VARIANT],
        "record": f"{ROOT_NODE}/closure.json",
    }


def test_unvouched_the_refuting_variant_is_the_closing_node(
    refuted: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modes, "root_vouched", lambda target_dir, **kw: None)
    tg = graph.load_target(refuted, TARGET)
    assert tg.statuses[ROOT_NODE] == "blocked"  # open: the fixture root's own deps are unproved
    assert products.closing_node(tg) == VARIANT
    assert index_row(generate(refuted))["status"] != "resolved"


# --- 6. step 9: a proof of a refuting variant settles the root while it is open ----------------


@pytest.mark.parametrize(
    ("root_proved", "expected"), [(False, ASKED), (True, NOT_ASKED_INTERMEDIATE)]
)
def test_a_refutes_variant_is_asked_step9_only_while_the_root_is_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], root_proved: bool, expected: tuple[Any, ...]
) -> None:
    """Beside ``test_a_resolves_variant_is_a_root_proof_only_while_the_root_is_open``: proving a
    ``refutes`` variant settles the target by refutation (D-30 v3.46), so the one review that
    means something is asked of it; under a closed root it settles nothing."""
    repo, _ = curated(tmp_path, keep_proof=root_proved)
    if root_proved:
        att = samples.attestation(
            node_id=ROOT,
            statement_hash=schemas.content_hash((repo.node / "Statement.lean").read_bytes()),
            merge_commit="2" * 40,
            graph_commit="1" * 40,
            runner="hosted",
        )
        (repo.root / "attestations").mkdir(exist_ok=True)
        (repo.root / "attestations" / "000001.json").write_bytes(schemas.canonical_json(att))
    variant = add_node(
        repo, "variant-0d0d0d0d", origin="variant", relation="refutes", relation_proof=RELATION
    )
    repo.commit("base")
    prove(repo, variant)
    _, out = classify(repo, capsys)
    assert out["mode"] == "proof", out
    assert step9(out) == expected, out
