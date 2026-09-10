"""F07-T1: PR modes, append-mode checks, the annex hash rule, explainers (R3, R9, R10).

Covers AC3 (the classification matrix), AC11 (append mode runs schema checks and nothing else),
AC12 (an annex is named for its content) and AC13 (an explainer needs a merged proof).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import samples
import yaml

from opn_gate import cli, modes, paths, schemas
from opn_gate.paths import Change

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
T = "targets/propositional"
N = f"{T}/nodes/tutorial-and-swap"
UNPROVED = "and-swap-reassoc"  # the root: blocked in the pristine fixture, so it has no Proof.lean


def added(*p: str) -> list[Change]:
    return [Change("A", path) for path in p]


def mode_of(*p: str) -> str | None:
    return modes.classify(added(*p)).mode


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    """A writable copy of the propositional fixture; tests add the files a PR would."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    return root


def write(graph: Path, path: str, data: bytes | str) -> Change:
    dest = graph / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data.encode() if isinstance(data, str) else data)
    return Change("A", path)


def problems(graph: Path, *changes: Change) -> list[str]:
    classification = modes.classify(changes)
    found = [d.code for d in classification.problems]
    if classification.ok:
        found += [d.code for d in modes.check(graph, classification)]
    return found


# --- AC3: the classification matrix ------------------------------------------------------------


@pytest.mark.parametrize(
    ("paths_touched", "mode"),
    [
        ((f"{N}/Proof.lean",), "proof"),
        ((f"{N}/Proof.lean", f"{N}/attempts/2026-09-10-alice.yaml"), "proof"),
        ((f"{N}/Proof.lean", f"{N}/waivers/native_decide.yaml"), "proof"),
        ((f"{N}/Proof.lean", f"{N}/annex/{'a' * 64}.md"), "proof"),
        ((f"{N}/attempts/2026-09-10-alice-partial.lean",), "partial"),
        (
            (f"{N}/attempts/2026-09-10-alice-partial.lean", f"{N}/attempts/2026-09-10-alice.yaml"),
            "partial",
        ),
        ((f"{N}/attempts/2026-09-10-alice.yaml",), "append"),
        ((f"{N}/attempts/precheck/01m23sfd.json",), "append"),
        ((f"{N}/annex/{'a' * 64}.md",), "append"),
        ((f"{T}/approaches/2026-09-10-alice.yaml",), "append"),
        (
            (f"{N}/attempts/2026-09-10-alice.yaml", f"{T}/approaches/2026-09-10-alice.yaml"),
            "append",
        ),
        ((f"{N}/explainer/{'b' * 64}.md",), "explainer"),
    ],
)
def test_classification_matrix(paths_touched: tuple[str, ...], mode: str) -> None:
    """AC3: each path pattern lands in its mode, and appends ride with a proof or a partial."""
    assert mode_of(*paths_touched) == mode


def test_classification_rejects_mixtures_and_forbidden_paths() -> None:
    """AC3: a PR mixing Proof.lean with an explainer is rejected; so is anything with no mode."""
    mixed = modes.classify(added(f"{N}/Proof.lean", f"{N}/explainer/{'b' * 64}.md"))
    assert mixed.mode is None
    assert [d.code for d in mixed.problems] == ["mode-mixed"]
    assert "explainer" in mixed.problems[0].message

    both_artifacts = modes.classify(
        added(f"{N}/Proof.lean", f"{N}/attempts/2026-09-10-alice-partial.lean")
    )
    assert both_artifacts.mode is None

    for path in (
        f"{N}/Statement.lean",
        f"{N}/META.yaml",
        f"{T}/defs/Helper.lean",
        f"{T}/gate-spec.json",
        ".github/workflows/evil.yml",
        f"{N}/status/2026-09-10-curator.yaml",  # a curator record is F08's mode, not F07's
        f"{N}/attempts/precheck/nested/deep.json",
        f"{N}/annex/notes.txt",
        f"{N}/explainer/why.rst",
    ):
        rejected = modes.classify(added(path))
        assert rejected.mode is None, path
        assert [d.code for d in rejected.problems] == ["path-forbidden"], path


def test_classification_scoping_and_change_status() -> None:
    """One target, one node, and nothing modified or deleted but Proof.lean and its waiver."""
    other = f"{T}/nodes/and-reassoc/attempts/2026-09-10-alice.yaml"
    two_nodes = modes.classify(added(f"{N}/attempts/2026-09-10-alice.yaml", other))
    assert [d.code for d in two_nodes.problems] == ["mode-multi-node"]

    two_targets = modes.classify(added(f"{N}/Proof.lean", "targets/other/nodes/n/Proof.lean"))
    assert [d.code for d in two_targets.problems] == ["mode-multi-target"]

    assert modes.classify([Change("M", f"{N}/Proof.lean")]).mode == "proof"
    for change in (
        Change("D", f"{N}/Proof.lean"),
        Change("M", f"{N}/attempts/2026-09-10-alice.yaml"),
        Change("D", f"{N}/annex/{'a' * 64}.md"),
        Change("R", f"{N}/Proof.lean", f"{N}/Old.lean"),
    ):
        assert modes.classify([change]).mode is None, change

    assert modes.classify([]).problems[0].code == "mode-empty"


def test_only_proof_and_partial_build() -> None:
    """R9, R10: an append or an explainer never starts a sandbox and never waits for a review."""
    for mode_paths, builds in (
        ((f"{N}/Proof.lean",), True),
        ((f"{N}/attempts/2026-09-10-alice-partial.lean",), True),
        ((f"{N}/attempts/2026-09-10-alice.yaml",), False),
        ((f"{N}/explainer/{'b' * 64}.md",), False),
    ):
        classification = modes.classify(added(*mode_paths))
        assert classification.needs_gate is builds
        assert classification.needs_review is builds


# --- AC11: append mode is path and schema checks, and nothing else ------------------------------


def test_append_mode_schema_only(graph: Path) -> None:
    """AC11: a valid postmortem passes on schema alone; a bad enum fails naming the field."""
    good = write(
        graph,
        f"{N}/attempts/2026-09-10-alice.yaml",
        yaml.safe_dump(samples.postmortem(), sort_keys=True),
    )
    classification = modes.classify([good])
    assert classification.mode == "append"
    assert modes.check(graph, classification) == []

    bad = write(
        graph,
        f"{N}/attempts/2026-09-10-bob.yaml",
        yaml.safe_dump(samples.postmortem(outcome="gave-up"), sort_keys=True),
    )
    found = modes.check(graph, modes.classify([bad]))
    assert [d.code for d in found] == ["append-invalid"]
    assert "outcome" in found[0].message


def test_append_mode_checks_every_record_kind(graph: Path) -> None:
    """R9: each append validates against its own schema — approach records and precheck records
    included, since they are the two the service does not write for a node."""
    ok = [
        write(
            graph,
            f"{T}/approaches/2026-09-10-alice.yaml",
            yaml.safe_dump(samples.approach_record(), sort_keys=True),
        ),
        write(
            graph,
            f"{N}/attempts/precheck/01m23sfd.json",
            schemas.canonical_json(samples.precheck_record()),
        ),
    ]
    assert problems(graph, *ok) == []

    bad_approach = write(
        graph,
        f"{T}/approaches/2026-09-10-bob.yaml",
        yaml.safe_dump(samples.approach_record(outcome="ran-out"), sort_keys=True),
    )
    assert problems(graph, bad_approach) == ["append-invalid"]

    long_route = write(
        graph,
        f"{T}/approaches/2026-09-10-carol.yaml",
        yaml.safe_dump(samples.approach_record(route="x" * 501), sort_keys=True),
    )
    assert problems(graph, long_route) == ["append-invalid"]

    passing_precheck = write(
        graph,
        f"{N}/attempts/precheck/01m23sfe.json",
        schemas.canonical_json(samples.precheck_record(verdict="pass")),
    )
    assert problems(graph, passing_precheck) == ["append-invalid"]

    unparseable = write(graph, f"{N}/attempts/2026-09-10-dan.yaml", "route: [unclosed\n")
    assert problems(graph, unparseable) == ["append-invalid"]


# --- AC12: an annex is named for its content ----------------------------------------------------


def test_annex_name_is_hash(graph: Path) -> None:
    """AC12: the file name is the SHA-256 of the file, so a citation is mechanical (D-31)."""
    data = samples.annex_file()
    digest = schemas.content_hash(data)
    assert problems(graph, write(graph, f"{N}/annex/{digest}.md", data)) == []

    misnamed = write(graph, f"{N}/annex/{'0' * 64}.md", data)
    found = modes.check(graph, modes.classify([misnamed]))
    assert [d.code for d in found] == ["content-hash-name"]
    assert found[0].details["expected"] == f"{digest}.md"

    edited = samples.annex_file(body="a different argument\n")
    assert problems(graph, write(graph, f"{N}/annex/{digest}.md", edited)) == ["content-hash-name"]


def test_annex_front_matter_and_cap(graph: Path) -> None:
    """R9, D-23: an annex declares its node, contributor and licence, and stays under the cap."""
    no_licence = samples.annex_front_matter()
    del no_licence["licence"]
    head = yaml.safe_dump(no_licence, sort_keys=True)
    unlicensed = f"---\n{head}---\nprose\n".encode()
    assert problems(
        graph, write(graph, f"{N}/annex/{schemas.content_hash(unlicensed)}.md", unlicensed)
    ) == ["append-invalid"]

    bare = b"just prose, no front matter\n"
    assert problems(graph, write(graph, f"{N}/annex/{schemas.content_hash(bare)}.md", bare)) == [
        "append-invalid"
    ]

    body = "x" * (paths.ANNEX_MAX_BYTES + 1)
    huge = samples.annex_file(body=body)
    assert problems(graph, write(graph, f"{N}/annex/{schemas.content_hash(huge)}.md", huge)) == [
        "annex-too-large"
    ]


# --- AC13: explainers ---------------------------------------------------------------------------


def test_explainer_mode(graph: Path) -> None:
    """AC13: an explainer on an unproved node is a misfiled annex; on a proved one it passes
    with no Lean build."""
    data = b"# Why the swap works\n\nBoth conjuncts are already in hand.\n"
    digest = schemas.content_hash(data)

    proved = write(graph, f"{N}/explainer/{digest}.md", data)
    classification = modes.classify([proved])
    assert classification.mode == "explainer"
    assert classification.needs_gate is False
    assert modes.check(graph, classification) == []

    # The fixture ships every node with a proof, so take one away: an unproved node is exactly a
    # node directory with no Proof.lean, which is the only file a proof ever merges (D-3).
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    unproved_path = f"{T}/nodes/{UNPROVED}/explainer/{digest}.md"
    found = modes.check(graph, modes.classify([write(graph, unproved_path, data)]))
    assert [d.code for d in found] == ["explainer-unproved"]
    assert "annex" in found[0].message

    misnamed = write(graph, f"{N}/explainer/{'c' * 64}.md", data)
    assert [d.code for d in modes.check(graph, modes.classify([misnamed]))] == ["content-hash-name"]


# --- the schemas T1 adds ------------------------------------------------------------------------


def test_new_schemas_accept_their_samples() -> None:
    for doc in (
        samples.annex_front_matter(),
        samples.approach_record(),
        samples.precheck_record(),
        samples.submission_meta(),
    ):
        schemas.validate(doc)


@pytest.mark.parametrize(
    ("sample", "bad"),
    [
        ("annex_front_matter", {"licence": "MIT"}),
        ("annex_front_matter", {"node": "Bad Id"}),
        ("annex_front_matter", {"extra": 1}),
        ("approach_record", {"outcome": "vibes"}),
        ("approach_record", {"route": ""}),
        ("approach_record", {"pinned_mathlib_sha": "short"}),
        ("approach_record", {"detail": "no such field"}),
        ("precheck_record", {"verdict": "fail"}),
        ("precheck_record", {"first_failing_step": 0}),
        ("precheck_record", {"transcript": "never"}),
        ("submission_meta", {"artifact_type": "sketch"}),
        ("submission_meta", {"identity": {"pseudonym": "a", "proof_kind": "vibes"}}),
        ("submission_meta", {"tooling": {"model": None, "harness": None}}),
        ("submission_meta", {"submission_id": "lowercase"}),
    ],
)
def test_new_schemas_reject(sample: str, bad: dict[str, object]) -> None:
    doc = getattr(samples, sample)(**bad)
    assert schemas.violations(doc)


# --- the command the workflow runs --------------------------------------------------------------


def test_classify_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The entry point gate.yml calls: a mode, whether it needs the sandbox, and every problem.

    Proved against a real diff, because the workflow hands it two commits and not a change list.
    """
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")

    record = yaml.safe_dump(samples.postmortem(), sort_keys=True)
    (root / N / "attempts" / "2026-09-10-alice.yaml").write_text(record)
    git("add", "-A")
    git("commit", "-q", "-m", "postmortem")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "mode": "append",
        "target": "propositional",
        "node": "tutorial-and-swap",
        "needs_gate": False,
        "needs_review": False,
        "problems": [],
        "ok": True,
    }

    (root / N / "attempts" / "2026-09-10-bob.yaml").write_text(
        yaml.safe_dump(samples.postmortem(route_class="vibes"), sort_keys=True)
    )
    git("add", "-A")
    git("commit", "-q", "-m", "bad postmortem")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["append-invalid"]

    (root / T / "defs" / "Sneak.lean").write_text("-- not a submission path\n")
    git("add", "-A")
    git("commit", "-q", "-m", "sneak")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] is None
    assert [p["code"] for p in out["problems"]] == ["path-forbidden"]


def test_locate_is_the_whole_grammar() -> None:
    """Every role in the mode table comes from one path, and nothing else has a role."""
    roles = {
        f"{N}/Proof.lean": "proof",
        f"{N}/waivers/native_decide.yaml": "waiver",
        f"{N}/attempts/x-partial.lean": "partial",
        f"{N}/attempts/x.yaml": "postmortem",
        f"{N}/attempts/x.yml": "postmortem",
        f"{N}/attempts/precheck/x.json": "precheck-record",
        f"{N}/annex/{'a' * 64}.md": "annex",
        f"{N}/explainer/{'a' * 64}.md": "explainer",
        f"{T}/approaches/x.yaml": "approach-record",
    }
    for path, role in roles.items():
        located = paths.locate(path)
        assert located is not None and located.role == role, path
        assert located.target_id == "propositional"
        assert located.node_id == (None if role == "approach-record" else "tutorial-and-swap")
    for path in (
        "README.md",
        "targets/Bad Target/nodes/n/Proof.lean",
        f"{T}/approaches/nested/x.yaml",
        f"{N}/attempts/",
        f"{N}/Witness.lean",
    ):
        assert paths.locate(path) is None, path
