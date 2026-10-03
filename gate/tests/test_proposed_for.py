"""F18-T6: proposed for (F18-R8, AC9; D-14 v3.26, D-3).

A crux statement may say which node of its target it was proposed for, in an append-only
``proposed-for/`` record on the crux, written by its proposer or a listed curator. What is under
test is the gate's half: the path has a role of its own, a pull request that adds one record and
nothing else is a mode of its own, the author and the named node are held to R8's rule, each
refusal by its own code, a proposal may carry its first record, and the products' accessor
reads the latest record through revisions.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml

from opn_gate import cli, ledger, modes, paths, proposed_for, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import Change

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
PROPOSALS = FIXTURES / "proposals"
T = "targets/propositional"
CRUX = "and-reassoc"  # the node that carries the record; its proposer is rewritten to PROPOSER
FOR = "and-swap-reassoc"  # a live node of the same target: the root
OLD = "tutorial-and-swap"  # superseded by FOR in the tests that need a superseded node
PROPOSER = "alice"
SERVICE = "open-proof-network[bot]"  # who opens a pull request the service writes
CURATOR = "thisisanameforsure"
STRANGER = "mallory"


def rel(node: str, name: str = "20261003T120000Z-alice.yaml") -> str:
    return f"{T}/nodes/{node}/{proposed_for.DIR}/{name}"


def record(**over: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": proposed_for.SCHEMA,
        "for": FOR,
        "author": PROPOSER,
        "date": "2026-10-03",
        "note": "the crux the root's outline needs",
    }
    doc.update(over)
    return {k: v for k, v in doc.items() if v is not _DROP}


_DROP = object()


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    """The propositional fixture with ``and-reassoc`` proposed by ``alice`` and one curator."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    meta = root / T / "nodes" / CRUX / "META.yaml"
    meta.write_text(meta.read_text().replace("author: thisisanameforsure", f"author: {PROPOSER}"))
    (root / modes.CURATORS_FILE).write_text(
        json.dumps({"identities": [{"pseudonym": f"{CURATOR}-pseudonym", "github_login": CURATOR}]})
    )
    return root


def put(graph: Path, path: str, content: dict[str, Any] | str) -> Change:
    dest = graph / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = content if isinstance(content, str) else yaml.safe_dump(content, sort_keys=False)
    dest.write_text(text, encoding="utf-8")
    return Change("A", path)


def supersede(graph: Path, old: str = OLD, new: str = FOR) -> None:
    """Mark ``old`` superseded by ``new`` the way ``opn-gate revise`` records it (D-8)."""
    put(
        graph,
        f"{T}/nodes/{old}/status/20261001T000000Z-curator.yaml",
        samples.node_status(status="superseded", cause=f"revised as {new}", reference=new),
    )


def judged(graph: Path, *changes: Change, author: str | None = SERVICE) -> list[str]:
    """Every code the gate gives the diff: classification's, then the checks'."""
    curators = modes.load_curators(graph)
    classification = modes.classify(changes, author=author, curators=curators)
    found = [d.code for d in classification.problems]
    if classification.ok:
        found += [d.code for d in modes.check(graph, classification)]
    return found


# --- the path and the mode ----------------------------------------------------------------------


def test_a_record_has_a_role_of_its_own() -> None:
    located = paths.locate(rel(CRUX))
    assert located is not None
    assert located.role == "proposed-for"
    assert (located.target_id, located.node_id) == ("propositional", CRUX)
    assert paths.SCHEMAS_FOR_ROLE["proposed-for"] == (proposed_for.SCHEMA,)
    # An explicit role: never an append that rides with a proof (the 2026-09-17 fallthrough).
    assert "proposed-for" not in paths.APPEND_ROLES
    for path in (
        f"{T}/nodes/{CRUX}/proposed-for/nested/x.yaml",
        f"{T}/nodes/{CRUX}/proposed-for/x.md",
        f"{T}/proposed-for/x.yaml",
    ):
        assert paths.locate(path) is None, path


def test_one_record_alone_is_the_proposed_for_mode(graph: Path) -> None:
    change = put(graph, rel(CRUX), record())
    classification = modes.classify([change], author=SERVICE)
    assert classification.mode == "proposed-for"
    assert classification.node_id == CRUX
    assert not classification.needs_gate
    assert not classification.needs_admission
    assert not classification.needs_review
    # Earns no ledger line: a pointer is not an artifact (D-19).
    assert ledger.MERGE_LINES["proposed-for"] is None


def test_a_record_is_append_only(graph: Path) -> None:
    put(graph, rel(CRUX), record())
    for status in ("M", "D"):
        codes = [d.code for d in modes.classify([Change(status, rel(CRUX))]).problems]
        assert codes == ["path-forbidden"], status


# --- AC9: who may write it ----------------------------------------------------------------------


def test_the_proposer_passes(graph: Path) -> None:
    """The record's author is the crux's ``provenance.author``; the service opened the PR."""
    assert judged(graph, put(graph, rel(CRUX), record())) == []


def test_a_listed_curator_passes(graph: Path) -> None:
    doc = record(author=f"{CURATOR}-pseudonym")
    change = put(graph, rel(CRUX, f"20261003T120000Z-{CURATOR}-pseudonym.yaml"), doc)
    assert judged(graph, change, author=CURATOR) == []


def test_a_third_party_is_refused(graph: Path) -> None:
    change = put(graph, rel(CRUX, f"20261003T120000Z-{STRANGER}.yaml"), record(author=STRANGER))
    assert judged(graph, change, author=STRANGER) == ["proposed-for-author"]
    # Nor does opening the pull request through the service make a stranger the proposer.
    assert judged(graph, change, author=SERVICE) == ["proposed-for-author"]


def test_the_author_refusal_names_who_may(graph: Path) -> None:
    change = put(graph, rel(CRUX), record(author=STRANGER))
    classification = modes.classify([change], author=STRANGER)
    (problem,) = modes.check(graph, classification)
    assert problem.code == "proposed-for-author"
    assert problem.details["author"] == STRANGER
    assert problem.details["proposer"] == PROPOSER


# --- AC9: what it may name ----------------------------------------------------------------------


def test_an_unknown_node_is_refused(graph: Path) -> None:
    assert judged(graph, put(graph, rel(CRUX), record(**{"for": "ghost"}))) == [
        "proposed-for-unknown-node"
    ]


def test_the_crux_itself_is_refused(graph: Path) -> None:
    assert judged(graph, put(graph, rel(CRUX), record(**{"for": CRUX}))) == ["proposed-for-self"]


def test_a_superseded_node_is_refused_naming_its_successor(graph: Path) -> None:
    supersede(graph)
    change = put(graph, rel(CRUX), record(**{"for": OLD}))
    classification = modes.classify([change], author=SERVICE)
    (problem,) = modes.check(graph, classification)
    assert problem.code == "proposed-for-superseded"
    assert problem.details["successor"] == FOR
    assert FOR in problem.message


@pytest.mark.parametrize(
    "content",
    [
        record(**{"for": _DROP}),
        record(extra=1),
        record(**{"for": "Not An Id"}),
        record(author=""),
        record(author="x" * 101),
        record(date="3 October"),
        record(note="x" * 501),
        record(schema="node-status/v1"),
        "for: [unclosed\n",
        "- a list, not a record\n",
    ],
)
def test_a_malformed_record_is_refused(graph: Path, content: dict[str, Any] | str) -> None:
    assert judged(graph, put(graph, rel(CRUX), content)) == ["proposed-for-malformed"]


def test_the_schema_accepts_a_record_without_a_note() -> None:
    assert schemas.violations(record(note=None)) == []
    assert schemas.violations(record(note=_DROP)) == []


# --- AC9: nothing else in the same pull request -------------------------------------------------


@pytest.mark.parametrize(
    "other",
    [
        f"{T}/nodes/{CRUX}/attempts/20261003T120000Z-alice.yaml",
        f"{T}/nodes/{CRUX}/Proof.lean",
        f"{T}/nodes/{CRUX}/annex/{'a' * 64}.md",
        f"{T}/nodes/{CRUX}/explainer/{'b' * 64}.md",
        f"{T}/nodes/{CRUX}/status/20261003T120000Z-c.yaml",
        f"{T}/approaches/20261003T120000Z-alice.yaml",
    ],
)
def test_a_record_with_any_other_file_is_refused(graph: Path, other: str) -> None:
    changes = [put(graph, rel(CRUX), record()), Change("A", other)]
    classification = modes.classify(changes, author=CURATOR, curators=modes.load_curators(graph))
    assert classification.mode is None
    assert [d.code for d in classification.problems] == ["mode-mixed"]


def test_two_records_in_one_pull_request_are_refused(graph: Path) -> None:
    changes = [
        put(graph, rel(CRUX), record()),
        put(graph, rel(CRUX, "20261003T120001Z-alice.yaml"), record()),
    ]
    assert judged(graph, *changes) == ["proposed-for-multiple"]


def test_records_on_two_nodes_are_refused(graph: Path) -> None:
    changes = [put(graph, rel(CRUX), record()), put(graph, rel(OLD), record())]
    assert judged(graph, *changes) == ["mode-multi-node"]


def test_any_node_may_carry_one(graph: Path) -> None:
    """Not only a ``spec-*`` crux: the rule is the proposer's, whatever the node's origin."""
    change = put(graph, rel(OLD, f"20261003T120000Z-{CURATOR}.yaml"), record(author=CURATOR))
    assert judged(graph, change) == []  # OLD's provenance.author is the fixture's curator


# --- a proposal carries its first record --------------------------------------------------------


def place_proposal(graph: Path, node_id: str = "good") -> list[Change]:
    dest = graph / T / "nodes" / node_id
    shutil.copytree(PROPOSALS / "good", dest)
    return [
        Change("A", p.relative_to(graph).as_posix()) for p in sorted(dest.rglob("*")) if p.is_file()
    ]


def test_a_proposal_may_carry_its_first_record(graph: Path) -> None:
    changes = place_proposal(graph)
    # The fixture proposal is the curator's; the service writes the proposer's pseudonym.
    changes.append(
        put(graph, rel("good", f"20261003T120000Z-{CURATOR}.yaml"), record(author=CURATOR))
    )
    classification = modes.classify(changes, author=SERVICE)
    assert classification.mode == "proposal"
    assert classification.admit == "good"
    assert modes.check(graph, classification) == []


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"for": "ghost"}, "proposed-for-unknown-node"),
        ({"for": "good"}, "proposed-for-self"),
        ({"author": STRANGER}, "proposed-for-author"),
        ({"date": "soon"}, "proposed-for-malformed"),
    ],
)
def test_a_proposal_s_record_is_held_to_the_same_rules(
    graph: Path, over: dict[str, Any], code: str
) -> None:
    changes = place_proposal(graph)
    changes.append(put(graph, rel("good"), record(**{"author": CURATOR, **over})))
    assert judged(graph, *changes) == [code]


def test_a_proposal_s_record_may_not_name_a_superseded_node(graph: Path) -> None:
    supersede(graph)
    changes = place_proposal(graph)
    changes.append(put(graph, rel("good"), record(author=CURATOR, **{"for": OLD})))
    assert judged(graph, *changes) == ["proposed-for-superseded"]


def test_a_proposal_carries_one_record_at_most(graph: Path) -> None:
    changes = place_proposal(graph)
    changes.append(put(graph, rel("good"), record(author=CURATOR)))
    changes.append(put(graph, rel("good", "20261003T120001Z-x.yaml"), record(author=CURATOR)))
    assert judged(graph, *changes) == ["proposed-for-multiple"]


# --- through the entry point gate.yml calls -----------------------------------------------------


def test_the_classify_command(graph: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(graph.parent),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(graph), *args], check=True, env=env, capture_output=True)

    def classify(author: str) -> dict[str, Any]:
        code = cli.main(["classify", "--graph", str(graph), "--base", "HEAD~1", "--author", author])
        out: dict[str, Any] = json.loads(capsys.readouterr().out)
        assert (code == 0) is out["ok"]
        return out

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    put(graph, rel(CRUX), record())
    git("add", "-A")
    git("commit", "-q", "-m", "proposed for")
    out = classify(SERVICE)
    assert out["mode"] == "proposed-for"
    assert out["node"] == CRUX
    assert out["needs_gate"] is False and out["needs_admission"] is False
    assert out["problems"] == []

    put(graph, rel(CRUX, "20261003T130000Z-mallory.yaml"), record(author=STRANGER))
    git("add", "-A")
    git("commit", "-q", "-m", "a stranger's pointer")
    out = classify(STRANGER)
    assert [p["code"] for p in out["problems"]] == ["proposed-for-author"]


# --- the products' accessor ---------------------------------------------------------------------


def facts(graph: Path) -> dict[str, graphmod.NodeFacts]:
    return graphmod.load_nodes(graph, "propositional", [])


def test_no_record_is_none(graph: Path) -> None:
    assert all(node.proposed_for is None for node in facts(graph).values())


def test_the_latest_record_is_published(graph: Path) -> None:
    put(graph, rel(CRUX, "20261001T000000Z-alice.yaml"), record(**{"for": OLD}))
    put(graph, rel(CRUX, "20261002T000000Z-alice.yaml"), record(**{"for": FOR}))
    loaded = proposed_for.latest(graph / T / "nodes" / CRUX)
    assert loaded is not None and loaded["for"] == FOR
    assert facts(graph)[CRUX].proposed_for == FOR


def test_an_invalid_file_is_passed_over(graph: Path) -> None:
    """Appends anyone may file must never decide whether the graph has products (2026-09-17)."""
    put(graph, rel(CRUX, "20261001T000000Z-alice.yaml"), record(**{"for": FOR}))
    put(graph, rel(CRUX, "20261009T000000Z-alice.yaml"), "for: [unclosed\n")
    put(graph, rel(CRUX, "20261008T000000Z-alice.yaml"), record(extra=1))
    assert facts(graph)[CRUX].proposed_for == FOR


def test_a_pointer_follows_a_revision(graph: Path) -> None:
    """A pointer written before its node was revised points at the revision, as a dep does
    (D-8 v3.18: read through, never rewritten)."""
    put(graph, rel(CRUX), record(**{"for": OLD}))
    supersede(graph)
    assert facts(graph)[CRUX].proposed_for == FOR


def test_the_pointer_changes_no_derivation(graph: Path) -> None:
    """A hint, not a dependency: statuses and deps are what they were without it."""
    before = facts(graph)
    put(graph, rel(CRUX), record())
    after = facts(graph)
    assert after[CRUX].deps == before[CRUX].deps
    statuses_before = graphmod.derive_statuses(before)
    statuses_after = graphmod.derive_statuses(after)
    assert statuses_after == statuses_before
