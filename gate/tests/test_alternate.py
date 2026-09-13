"""F07-T9..T11: a theorem keeps every proof (R3, R7, R15; AC9, AC22-AC24; D-25 v3.13, F07-Q20).

A later complete proof of a proved node is its own pull request adding
``attempts/<ts>-<pseudonym>-alternate.lean``. It is classified ``alternate``, checked like a proof,
never asked step 9, and merges with ``Proof.lean`` untouched. The machine never judges two proofs
alike: the only duplicate rule is exact bytes (Mike, 2026-09-13).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from opn_gate import modes, paths
from opn_gate.paths import Change

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
T = "targets/propositional"
PROVED = "tutorial-and-swap"
#: A proved node that is not the tutorial: D-27 keeps the tutorial's proof file open to rehearsal.
OTHER_PROVED = "and-reassoc"
#: The fixture ships this node with a proof too; a test that needs it open removes the file.
UNPROVED = "and-swap-reassoc"


def alternate_path(node: str = PROVED, who: str = "bob", stamp: str = "20260913T120000Z") -> str:
    return f"{T}/nodes/{node}/attempts/{stamp}-{who}-alternate.lean"


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    return root


def proof_of(graph: Path, node: str = PROVED) -> str:
    return (graph / T / "nodes" / node / "Proof.lean").read_text(encoding="utf-8")


def another_route(graph: Path, node: str = PROVED) -> str:
    """The node's proof by a different term: same header and signature (F00-R19), new body."""
    original = proof_of(graph, node)
    changed = original.replace("exact ⟨h.2, h.1⟩", "exact And.intro h.2 h.1")
    assert changed != original  # guard: the fixture's proof still has the body this rewrites
    return changed


def add(graph: Path, path: str, text: str) -> Change:
    dest = graph / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return Change("A", path)


def found(graph: Path, *changes: Change) -> list[str]:
    """Every refusal a pull request gets before a sandbox: classification, then ``check``."""
    classification = modes.classify(changes)
    codes = [d.code for d in classification.problems]
    if classification.ok:
        codes += [d.code for d in modes.check(graph, classification)]
    return codes


# --- F07-T9: classification (R3, R7; AC9) --------------------------------------------------------


def test_an_alternate_path_has_its_own_role() -> None:
    """R3: ``-alternate.lean`` under ``attempts/`` is an alternate; any other flat ``.lean`` there
    stays a partial, and nothing nested is either."""
    located = paths.locate(alternate_path())
    assert located is not None and located.role == "alternate"
    assert located.node_id == PROVED
    partial = paths.locate(f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob-partial.lean")
    assert partial is not None and partial.role == "partial"
    nested = f"{T}/nodes/{PROVED}/attempts/sub/20260913T120000Z-bob-alternate.lean"
    assert paths.locate(nested) is None


def test_alternate_classification_and_refusals(graph: Path) -> None:
    """AC9: one alternate differing from the proof by a byte is mode ``alternate``, built and
    unreviewed, with nothing to refuse; each of the refusals fires on its own case."""
    one_byte = add(graph, alternate_path(), proof_of(graph) + "\n")
    classification = modes.classify([one_byte])
    assert classification.mode == "alternate"
    assert classification.node_id == PROVED
    assert classification.needs_gate is True
    assert classification.needs_review is False  # D-4 v3.13: step 9 is not asked of an alternate
    assert modes.check(graph, classification) == []

    # Byte-identical to the node's proof: the only duplicate rule there is (F07-Q20).
    same = add(graph, alternate_path(who="carol"), proof_of(graph))
    assert found(graph, same) == ["alternate-duplicate"]

    # More than one alternate in one pull request.
    second = add(graph, alternate_path(who="dave"), another_route(graph))
    assert found(graph, one_byte, second) == ["alternate-multiple"]

    # A merged Proof.lean is never modified; the refusal names where the proof belongs instead.
    replaced = modes.classify([Change("M", f"{T}/nodes/{OTHER_PROVED}/Proof.lean")])
    refusals = modes.check(graph, replaced)
    assert [d.code for d in refusals] == ["proof-replaces-merged"]
    assert f"{OTHER_PROVED}/attempts/<ts>-<pseudonym>-alternate.lean" in refusals[0].message


def test_an_alternate_on_an_unproved_node_is_refused(graph: Path) -> None:
    """R7: with no ``Proof.lean`` there is nothing to be an alternate to; it should be a proof."""
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    change = add(graph, alternate_path(node=UNPROVED), "theorem x : True := trivial\n")
    assert found(graph, change) == ["alternate-unproved"]


def test_a_copy_of_an_earlier_alternate_is_a_duplicate_and_a_changed_one_is_not(
    graph: Path,
) -> None:
    """R7: an alternate already recorded counts like the proof; its own new file never does."""
    earlier = another_route(graph)
    attempts = graph / T / "nodes" / PROVED / "attempts"
    (attempts / "20260912T090000Z-alice-alternate.lean").write_text(earlier, encoding="utf-8")
    copy = add(graph, alternate_path(), earlier)
    assert found(graph, copy) == ["alternate-duplicate"]

    (graph / copy.path).unlink()
    changed = add(graph, alternate_path(), earlier.replace("h.2 h.1", "h.right h.left"))
    assert found(graph, changed) == []


def test_an_alternate_rides_with_appends_but_not_with_a_proof_or_a_partial(graph: Path) -> None:
    """R3: appends may accompany an alternate; a Proof.lean or a partial alongside is mixed."""
    alt = alternate_path()
    postmortem = f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob.yaml"
    assert modes.classify([Change("A", alt), Change("A", postmortem)]).mode == "alternate"
    for other in (
        f"{T}/nodes/{PROVED}/Proof.lean",
        f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob-partial.lean",
    ):
        mixed = modes.classify([Change("A", alt), Change("A", other)])
        assert mixed.mode is None, other
        assert [d.code for d in mixed.problems] == ["mode-mixed"], other


def test_a_first_proof_is_still_a_proof(graph: Path) -> None:
    """Regression guard: adding Proof.lean to an unproved node is the ordinary proof mode."""
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    first = modes.classify([Change("A", f"{T}/nodes/{UNPROVED}/Proof.lean")])
    assert first.mode == "proof" and first.needs_review is True


def test_the_tutorial_nodes_proof_stays_open_to_rehearsal(graph: Path) -> None:
    """D-27: every operator proves the tutorial node again, on the git path by replacing its
    Proof.lean, and it earns nothing, so modifying it is still an ordinary proof. Found by the
    guide's own walkthrough, which does exactly that (gate/agents/AGENTS.md)."""
    rehearsal = modes.classify([Change("M", f"{T}/nodes/{PROVED}/Proof.lean")])
    assert rehearsal.mode == "proof"
    assert modes.check(graph, rehearsal) == []


def test_an_unreadable_meta_is_not_taken_for_a_tutorial(graph: Path) -> None:
    """C7: the exemption needs the flag read, so a META that will not parse is refused."""
    (graph / T / "nodes" / PROVED / "META.yaml").write_text("tutorial: [\n", encoding="utf-8")
    rehearsal = modes.classify([Change("M", f"{T}/nodes/{PROVED}/Proof.lean")])
    assert [d.code for d in modes.check(graph, rehearsal)] == ["proof-replaces-merged"]
