"""F11-T13: a listed curator adds a definition to a target that already exists (F11-R15, Q35).

Until this task a ``defs/`` file could enter the graph only inside its target's intake: any diff
carrying one was routed to the intake rules, which demand the target's record and gate-spec, so
the first target to need a definition after it was listed (erdos-69) had no route at all. The
owner's ruling of 2026-10-01 opens one, and these tests hold its edges: who may use it, that it
only ever *adds*, that it carries nothing else, and that the new file is elaborated in the
sandbox on the merged tree before it can merge.

Covers F11-AC28 to AC34.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import pytest
from harness import copy_graph, take_in

from opn_gate import cli, fidelity, modes
from opn_gate.paths import Change

GRAPH = Path(__file__).resolve().parent / "fixtures" / "graphs" / "onramp"
TARGET_ID = "euclid-primes"
T = f"targets/{TARGET_ID}"
ROOT = "infinitude-of-primes"
CURATOR = "thisisanameforsure"
OTHER = "second-curator"
STRANGER = "some-prover"
NEW = f"{T}/defs/Coprime.lean"
NEW_TEXT = (
    "import Defs.Divides\n\n"
    "def Opn.Coprime (a b : Nat) : Prop := ∀ d : Nat, Opn.Divides d a → Opn.Divides d b → d = 1\n"
)
ONE = modes.Curators(identities=((CURATOR, CURATOR),))
TWO = modes.Curators(identities=((CURATOR, CURATOR), (OTHER, OTHER)))

Git = Callable[..., str]


def classify(changes: list[Change], author: str | None = CURATOR) -> modes.Classification:
    return modes.classify(changes, author=author, curators=ONE)


def codes(changes: list[Change], author: str | None = CURATOR) -> list[str]:
    return [d.code for d in classify(changes, author).problems]


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Git]:
    """The on-ramp fixture as a repository with one listed curator: the merged target."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    doc = {"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]}
    (root / modes.CURATORS_FILE).write_text(json.dumps(doc, indent=2) + "\n")
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "the merged target")
    return root, git


def commit(root: Path, git: Git, files: dict[str, str | None], message: str = "change") -> None:
    """One commit that writes each path, or deletes it when its text is ``None``."""
    for rel, text in files.items():
        path = root / rel
        if text is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", message)


def run_classify(
    root: Path, capsys: pytest.CaptureFixture[str], author: str = CURATOR
) -> tuple[int, dict[str, Any]]:
    code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1", "--author", author])
    return code, json.loads(capsys.readouterr().out)


# --- AC28: the route exists, and it is a curator's -----------------------------------------------


def test_a_listed_curator_adds_a_definition_to_an_existing_target() -> None:
    """R15: one new ``defs/`` file, alone, by a listed curator, is the curator mode. It admits
    no node and runs no proof pipeline; the second listed curator reviews it when there is one,
    and the founding waiver is on the record when there is not (D-22, F08-Q9)."""
    c = classify([Change("A", NEW)])
    assert c.mode == "curator" and c.problems == (), c.as_dict()
    assert c.target_id == TARGET_ID and c.node_id is None
    assert not c.needs_gate and not c.needs_admission
    assert c.reviewers == () and not c.needs_review and c.review_waived == "single-curator"
    reviewed = modes.classify([Change("A", NEW)], author=CURATOR, curators=TWO)
    assert reviewed.mode == "curator" and reviewed.reviewers == (OTHER,) and reviewed.needs_review


def test_several_definitions_may_arrive_together() -> None:
    """A definition may import another (F01-Q2), so two that need each other are one act."""
    c = classify([Change("A", NEW), Change("A", f"{T}/defs/Squarefree.lean")])
    assert c.mode == "curator" and c.problems == ()


# --- AC29: nobody else may use it ----------------------------------------------------------------


@pytest.mark.parametrize("author", [STRANGER, None])
def test_a_definition_from_anyone_else_is_refused_by_name(author: str | None) -> None:
    """D-3: no prover creates a shared definition. The refusal names the rule that applies,
    the author, instead of calling the diff an intake that forgot its record."""
    c = classify([Change("A", NEW)], author)
    assert c.mode is None
    assert [d.code for d in c.problems] == ["curator-unlisted"]
    assert c.problems[0].details["author"] == author
    assert "definition" in c.problems[0].message


def test_the_command_refuses_an_unlisted_author(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str]
) -> None:
    root, git = repo
    commit(root, git, {NEW: NEW_TEXT})
    code, out = run_classify(root, capsys, author=STRANGER)
    assert code == 1 and out["mode"] is None and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["curator-unlisted"]


# --- AC30: it only ever adds (D-3: a definition is immutable) -------------------------------------


@pytest.mark.parametrize("status", ["M", "D"])
def test_an_existing_definition_is_never_modified_or_deleted(status: Literal["M", "D"]) -> None:
    """Guard, green before and after: the new route must not become a way to edit one. The
    refusal is at the path, before any mode or author is asked."""
    for changes in (
        [Change(status, f"{T}/defs/Divides.lean")],
        [Change(status, f"{T}/defs/Divides.lean"), Change("A", NEW)],
    ):
        c = classify(changes)
        assert c.mode is None
        assert [d.code for d in c.problems] == ["path-forbidden"]


def test_a_rename_of_a_definition_is_refused() -> None:
    c = classify([Change("R", NEW, old_path=f"{T}/defs/Divides.lean")])
    assert c.mode is None and c.problems


# --- AC31: it carries nothing else ----------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        f"{T}/nodes/{ROOT}/Proof.lean",  # a proof over the new definition
        f"{T}/nodes/new-lemma/Statement.lean",  # a new node stated over it
        f"{T}/nodes/{ROOT}/attempts/2026-10-01-alice.yaml",  # an append
        f"{T}/status/2026-10-01-note.yaml",  # another curator record
        f"{T}/fidelity/Coprime-1.yaml",  # its certificate: the signer's own pull request (R3)
        f"{T}/gate-spec.json",  # the owner's re-pin
    ],
)
def test_a_definition_mixed_with_anything_else_is_refused(extra: str) -> None:
    """Guard, green before and after: the definition is published alone, so what is reviewed
    is the definition and nothing is stated over it until it is on the record."""
    c = classify([Change("A", NEW), Change("A", extra)])
    assert c.mode is None, extra
    assert {d.code for d in c.problems} <= {"intake-incomplete", "mode-mixed"}, extra


def test_definitions_for_two_targets_are_refused() -> None:
    c = classify([Change("A", NEW), Change("A", "targets/other/defs/Coprime.lean")])
    assert c.mode is None and [d.code for d in c.problems] == ["mode-multi-target"]


# --- AC32: an intake is what it was ---------------------------------------------------------------


def test_an_intake_with_definitions_is_still_an_intake(tmp_path: Path) -> None:
    """Guard: the whole target arriving at once, definitions included, stays the intake mode
    with its root admitted, and an intake short of its record is still named incomplete."""
    root = copy_graph(tmp_path)
    take_in(root, TARGET_ID, defs={"Divides.lean": "def Opn.Divides : Nat := 0\n"})
    (root / T / "nodes" / "and-reassoc" / "Proof.lean").unlink()
    changes = [
        Change("A", p.relative_to(root).as_posix())
        for p in sorted((root / T).rglob("*"))
        if p.is_file()
    ]
    paths_added = {c.path for c in changes}
    for name in ("defs/Divides.lean", "target.yaml", "gate-spec.json"):
        assert f"{T}/{name}" in paths_added
    c = classify(changes)
    assert c.mode == "intake" and c.admit == "and-reassoc" and c.needs_admission, c.as_dict()
    assert codes([x for x in changes if not x.path.endswith("target.yaml")]) == [
        "intake-incomplete"
    ]
    # A lone gate-spec is still an intake that forgot everything else, whoever sends it.
    assert codes([Change("A", f"{T}/gate-spec.json")]) == ["intake-incomplete"]


# --- AC33: checked before the sandbox, and scheduled for it ---------------------------------------


def test_the_command_admits_it_and_schedules_the_sandbox(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str]
) -> None:
    """The workflow reads ``needs_exhibits`` to start the one sandbox step a mode that builds no
    proof may ask for; a new definition asks for it, so it cannot merge unelaborated (C7, C9)."""
    root, git = repo
    commit(root, git, {NEW: NEW_TEXT})
    code, out = run_classify(root, capsys)
    assert code == 0 and out["ok"] is True and out["problems"] == []
    assert out["mode"] == "curator" and out["target"] == TARGET_ID
    assert out["needs_gate"] is False and out["needs_admission"] is False
    assert out["definitions"] == [NEW]
    assert out["needs_exhibits"] is True and out["exhibits"] == []


def test_a_definition_for_a_target_that_does_not_exist_is_an_incomplete_intake(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str]
) -> None:
    """Guard: the route is for a target on the record. Definitions under a new target id are
    what they always were, an intake without its record and gate-spec (R2)."""
    root, git = repo
    commit(root, git, {"targets/brand-new/defs/Thing.lean": "def Opn.thing : Nat := 0\n"})
    code, out = run_classify(root, capsys)
    assert code == 1 and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["intake-incomplete"]


@pytest.mark.parametrize(
    ("name", "text", "code"),
    [
        ("not-a-module.lean", "def Opn.x : Nat := 0\n", "defs-name"),
        ("Coprime.lean", "import Defs.Missing\n\ndef Opn.x : Nat := 0\n", "defs-import"),
        (
            "Coprime.lean",
            f"import Nodes.«{ROOT}».Statement\n\ndef Opn.x : Nat := 0\n",
            "defs-import",
        ),
    ],
)
def test_a_definition_that_cannot_be_a_module_is_refused_before_the_sandbox(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str], name: str, text: str, code: str
) -> None:
    """The existing ``defs-*`` diagnostics, on the merged tree, without starting a toolchain."""
    root, git = repo
    commit(root, git, {f"{T}/defs/{name}": text})
    exit_code, out = run_classify(root, capsys)
    assert exit_code == 1 and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == [code]


def test_an_import_cycle_among_new_definitions_is_refused(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str]
) -> None:
    root, git = repo
    commit(
        root,
        git,
        {
            f"{T}/defs/A.lean": "import Defs.B\n\ndef Opn.a : Nat := 0\n",
            f"{T}/defs/B.lean": "import Defs.A\n\ndef Opn.b : Nat := 0\n",
        },
    )
    exit_code, out = run_classify(root, capsys)
    assert exit_code == 1 and [p["code"] for p in out["problems"]] == ["defs-cycle"]


# --- AC34: a name already taken -------------------------------------------------------------------


def test_a_name_that_differs_only_in_case_from_an_existing_definition_is_refused(
    repo: tuple[Path, Git], capsys: pytest.CaptureFixture[str]
) -> None:
    """``Defs.divides`` beside ``Defs.Divides`` is one file on a case-insensitive checkout (the
    founder's laptop) and two modules in the sandbox: refused, naming both."""
    root, git = repo
    clash = root / T / "defs" / "divides.lean"
    if clash.exists():
        pytest.skip("this filesystem folds case; the two files cannot coexist here")
    clash.write_text("def Opn.divides' : Nat := 0\n")
    git("add", "-A")
    git("commit", "-q", "-m", "clash")
    exit_code, out = run_classify(root, capsys)
    assert exit_code == 1 and [p["code"] for p in out["problems"]] == ["defs-clash"]
    assert out["problems"][0]["details"] == {"file": "divides.lean", "existing": "Divides.lean"}


def test_an_existing_definitions_own_name_cannot_be_added_again() -> None:
    """Guard: the same path is a modification to git, and a modification is forbidden (AC30);
    there is no second way to spell ``Defs.Divides``."""
    assert codes([Change("M", f"{T}/defs/Divides.lean")]) == ["path-forbidden"]


# --- consumers ------------------------------------------------------------------------------------


def test_the_new_definition_is_a_fidelity_subject_at_the_lowest_rung(
    repo: tuple[Path, Git],
) -> None:
    """Guard (F11-R3, Q33): the grade is the minimum over the root and the definitions that
    exist now, so a definition added later is a row with no certificate until someone signs it —
    the target's published grade can fall when one is added, and that is the rule working."""
    root, git = repo
    before = fidelity.definitions(root / T)
    commit(root, git, {NEW: NEW_TEXT})
    assert fidelity.definitions(root / T) == tuple(sorted((*before, "Coprime")))


def test_a_certificate_for_the_new_definition_is_its_signers_own_pull_request() -> None:
    """Guard (F11-R3): the certificate follows in a pull request of its own, as for any subject."""
    c = classify([Change("A", f"{T}/fidelity/Coprime-1.yaml")], author=OTHER)
    assert c.mode == "fidelity" and c.problems == ()


def test_a_postmortem_is_still_an_append() -> None:
    """Guard on the classifier's fallthrough: the new branch takes definitions alone."""
    append = classify([Change("A", f"{T}/nodes/{ROOT}/attempts/2026-10-01-alice.yaml")])
    assert append.mode == "append"
