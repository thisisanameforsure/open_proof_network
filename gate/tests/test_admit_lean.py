"""F08-T1 / AC18: ``opn-gate admit`` against the real toolchain.

The fast tier proves the composition; this proves the files. Every proposal fixture is placed in
a copy of the graph it belongs to and admitted with the pinned Lean, so the statements really
elaborate, the witnesses really have the type F01 derives, the hazard checkers really fire, and
the relation proofs really prove — or fail — the implication their label claims.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from harness import ADVERSARIAL, GRAPH, TARGET, copy_graph

from opn_gate import admit, config, layout, schemas
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

PROPOSALS = Path(__file__).resolve().parent / "fixtures" / "proposals"
ADVERSARIAL_TARGET = "adversarial"

#: fixture -> (the graph it belongs to, the check it must fail at, the diagnostic code).
#: ``None`` means it must be admitted.
CASES: dict[str, tuple[Path, str | None, str | None]] = {
    "good": (GRAPH, None, None),
    "bad-statement": (GRAPH, "statement", "statement-elaboration"),
    "bad-witness": (GRAPH, "witness", "witness-type-mismatch"),
    "hazard": (ADVERSARIAL, "hazards", "hazard-unacknowledged"),
    "variant-resolves": (GRAPH, None, None),
    "variant-backwards": (GRAPH, "relation", "relation-direction"),
    "variant-related": (GRAPH, None, None),
}


def admit_fixture(tmp_path: Path, case: str, graph: Path, tc: LocalToolchain) -> admit.Admission:
    root = copy_graph(tmp_path / case, graph)
    target = ADVERSARIAL_TARGET if graph is ADVERSARIAL else TARGET
    shutil.copytree(PROPOSALS / case, layout.graph_nodes_dir(root, target) / case)
    spec_path = layout.gate_spec_path(root, target)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    ctx = RunContext(
        graph_root=root,
        claim=Claim(target, case),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / case / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return admit.run(ctx)


@pytest.mark.parametrize("case", list(CASES))
def test_admission_matrix(
    case: str,
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> None:
    """AC18: each fixture passes, or fails at the check it is broken at — with the real Lean."""
    graph, expected_check, expected_code = CASES[case]
    result = admit_fixture(tmp_path, case, graph, real_toolchain)
    summary = result.as_dict()
    if expected_check is None:
        assert result.admitted, summary
        return
    assert not result.admitted, summary
    assert result.first_failing_check == expected_check, summary
    assert result.diagnostic is not None
    assert result.diagnostic.code == expected_code, summary
    after = [c for c in result.checks if c.result == "skipped"]
    assert all(c.result != "pass" for c in after)


def test_a_proposal_redeclaring_an_existing_nodes_theorem_is_refused(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """A proposal whose statement declares a theorem name another node of the target already
    declares must be refused by admission, naming the declaration."""
    case = "good"
    root = copy_graph(tmp_path / case, GRAPH)
    node_dir = layout.graph_nodes_dir(root, TARGET) / case
    shutil.copytree(PROPOSALS / case, node_dir)
    tutorial = layout.parse_statement(
        (layout.graph_nodes_dir(root, TARGET) / "tutorial-and-swap" / "Statement.lean").read_text()
    )
    assert isinstance(tutorial, layout.Statement)
    statement = node_dir / "Statement.lean"
    text = statement.read_text().replace("OpnProp.and_weaken", tutorial.decl_name)
    assert tutorial.decl_name in text
    statement.write_text(text)
    meta = node_dir / "META.yaml"
    meta.write_text(
        meta.read_text().replace(
            "statement-hash: 6699224fc51b6d024769f98e6e8dcca2987bae7576a1a27eed059b9a05f8cf29",
            f"statement-hash: {schemas.content_hash(text.encode('utf-8'))}",
        )
    )
    spec_path = layout.gate_spec_path(root, TARGET)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, case),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / case / "work",
        toolchain=real_toolchain,
        settings=config.load({}),
    )
    result = admit.run(ctx)
    assert not result.admitted, result.as_dict()
    assert result.diagnostic is not None
    assert tutorial.decl_name in result.diagnostic.message, result.as_dict()


def test_the_relation_direction_is_the_claim(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """D-30, AC4 against the real elaborator: the same proof passes as ``resolves`` and fails as
    ``partial``, because the only difference is which implication the label claims."""
    passing = admit_fixture(tmp_path, "variant-resolves", GRAPH, real_toolchain)
    assert passing.admitted, passing.as_dict()
    assert passing.data["relation"]["expected"] == passing.data["relation"]["declared"]

    failing = admit_fixture(tmp_path, "variant-backwards", GRAPH, real_toolchain)
    assert failing.diagnostic is not None
    details = failing.diagnostic.details
    assert details["label"] == "partial"
    assert details["expected"] != details["declared"]
    # The two fixtures carry the same implication; only the label differs.
    assert details["declared"] == passing.data["relation"]["declared"]
