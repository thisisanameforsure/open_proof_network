"""F11-T4 / R2: the intake mode — a curated target enters the graph whole, by a listed curator,
and its root is admitted (D-6, D-29).

Before T4 a pull request adding ``targets/<id>/target.yaml``, ``gate-spec.json``, ``defs/`` and
the certificates fitted no mode: each of those paths was "not a path any submission may touch",
so the intake R2 asks for could only have landed as the owner's direct push, the way F00 seeded
the tutorial. Now the classifier names the shape and its refusals, over the exact tree
``intake new`` writes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import TARGET, copy_graph, take_in

from opn_gate import cli, modes, paths
from opn_gate.paths import Change

TARGET_ID = "euclid-primes"
CURATOR = "thisisanameforsure"
OTHER = "second-curator"


def intake_changes(root: Path) -> list[Change]:
    """Every file ``intake new`` wrote, as the additions a pull request would carry."""
    target = root / "targets" / TARGET_ID
    return [
        Change("A", p.relative_to(root).as_posix())
        for p in sorted(target.rglob("*"))
        if p.is_file()
    ]


@pytest.fixture
def taken(tmp_path: Path) -> tuple[Path, list[Change]]:
    root = copy_graph(tmp_path)
    take_in(
        root,
        TARGET_ID,
        defs={"Divides.lean": "def Opn.Divides (a b : Nat) : Prop := ∃ c, b = a * c\n"},
    )
    # take_in reuses a fixture node as the root; a real root enters unproved (D-6, F11-R2).
    (root / "targets" / TARGET_ID / "nodes" / "and-reassoc" / "Proof.lean").unlink()
    return root, intake_changes(root)


def test_an_intake_is_classified_and_its_root_admitted(taken: tuple[Path, list[Change]]) -> None:
    _root, changes = taken
    roles = {paths.locate(c.path).role for c in changes if paths.locate(c.path)}  # type: ignore[union-attr]
    assert {
        "target-record",
        "gate-spec",
        "definition",
        "fidelity",
        "target-status",
        "node",
    } <= roles
    curators = modes.Curators(identities=((CURATOR, CURATOR),))
    c = modes.classify(changes, author=CURATOR, curators=curators)
    assert c.mode == "intake" and c.problems == (), c.as_dict()
    assert c.target_id == TARGET_ID and c.node_id == "and-reassoc"  # take_in's root
    assert c.admit == "and-reassoc" and c.needs_admission and not c.needs_gate
    # The founder is the only curator: step 9 is waived on the record (D-22, F08-Q9).
    assert c.reviewers == () and not c.needs_review and c.review_waived == "single-curator"
    both = modes.Curators(identities=((CURATOR, CURATOR), (OTHER, OTHER)))
    c = modes.classify(changes, author=CURATOR, curators=both)
    assert c.mode == "intake" and c.reviewers == (OTHER,) and c.needs_review


def test_an_intake_is_a_listed_curators_act(taken: tuple[Path, list[Change]]) -> None:
    _root, changes = taken
    curators = modes.Curators(identities=((CURATOR, CURATOR),))
    for author in (None, "stranger"):
        c = modes.classify(changes, author=author, curators=curators)
        assert c.mode is None
        assert [d.code for d in c.problems] == ["curator-unlisted"]
        assert c.problems[0].details["listed"] == [CURATOR]


def test_the_refusals_are_named(taken: tuple[Path, list[Change]]) -> None:
    _root, changes = taken
    curators = modes.Curators(identities=((CURATOR, CURATOR),))

    def codes(cs: list[Change]) -> list[str]:
        return [d.code for d in modes.classify(cs, author=CURATOR, curators=curators).problems]

    # Whole or nothing: no target record, no gate-spec.
    assert codes([c for c in changes if not c.path.endswith("target.yaml")]) == [
        "intake-incomplete"
    ]
    assert codes([c for c in changes if not c.path.endswith("gate-spec.json")]) == [
        "intake-incomplete"
    ]
    # Exactly one node, the root.
    assert codes([c for c in changes if "/nodes/" not in c.path]) == ["intake-root"]
    second = Change("A", f"targets/{TARGET_ID}/nodes/other/Statement.lean")
    assert codes([*changes, second]) == ["intake-root"]
    # Nothing is modified: the target did not exist — and a modified gate-spec is refused before
    # any mode is asked, since the gate's pins are the owner's re-pin, never a submission (D-4).
    modified = [Change("M" if c.path.endswith("gate-spec.json") else "A", c.path) for c in changes]
    assert codes(modified) == ["path-forbidden"]
    # No proof, no append rides along.
    proof = Change("A", f"targets/{TARGET_ID}/nodes/and-reassoc/Proof.lean")
    assert codes([*changes, proof]) == ["mode-mixed"]
    # And a target's file on its own is an incomplete intake, never a submission (R2).
    assert codes([Change("A", f"targets/{TARGET}/fidelity/root-2.yaml")]) == ["intake-incomplete"]


def test_classify_command_names_an_intake(
    taken: tuple[Path, list[Change]],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The workflow's view: ``classify`` over the intake commit says mode intake, admit the root,
    and needs no gate run — with the author it was handed (F08-Q8's OPN_PR_AUTHOR)."""
    root, _changes = taken
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(root.parent),
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    target = root / "targets" / TARGET_ID
    kept = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
    import shutil  # noqa: PLC0415

    shutil.rmtree(target)
    (root / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    git("add", "-A")
    git("commit", "-q", "-m", "before the intake")
    for p, data in kept.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    git("add", "-A")
    git("commit", "-q", "-m", f"intake: {TARGET_ID}")
    monkeypatch.setenv("OPN_PR_AUTHOR", CURATOR)
    code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0, out
    assert out["mode"] == "intake" and out["target"] == TARGET_ID
    assert out["admit"] == "and-reassoc" and out["needs_admission"] is True
    assert out["needs_gate"] is False and out["review_waived"] == "single-curator"
