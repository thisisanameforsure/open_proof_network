"""F08-R9 to R12 through the entry point: the curator's four commands driven by ``cli.main``,
their happy paths, every refusal's exit code, and every malformed input the coverage sweep
found escaping ``main`` as a traceback (F08-Q18; conventions §5: exceptions are caught at
boundaries; the CLI's contract is ``{"ok": false, "refused": ...}`` and exit 1 for a refusal,
exit 2 for a usage error, never a stack trace)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FakeToolchain
from harness import TARGET, copy_graph

from opn_gate import cli, curator, layout, schemas, toolchain
from opn_gate import graph as graphmod

ROOT = "and-swap-reassoc"
INTERIOR = "and-reassoc"
AUTHOR = "thisisanameforsure"
DATE = "2026-09-10T12:13:14Z"
STAMP = "20260910T121314Z"
NEW_STATEMENT = (
    "import Nodes.«and-reassoc-v2».Context\n\n"
    "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
)


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return code, out, captured.err


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def write_request(root: Path, node_id: str, **overrides: Any) -> Path:
    path = nodes_dir(root) / node_id / "revisions" / "20260910T000000-alice.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = samples.revision_request(node=node_id, contributor="alice", **overrides)
    path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    return path


def common(root: Path, *rest: str) -> list[str]:
    return ["--graph", str(root), "--author", AUTHOR, "--date", DATE, *rest]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeToolchain:
    tc = FakeToolchain()
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: tc))
    return tc


def git_init(root: Path, home: Path) -> Any:
    env = {
        "GIT_AUTHOR_NAME": "curator",
        "GIT_AUTHOR_EMAIL": "c@x",
        "GIT_COMMITTER_NAME": "curator",
        "GIT_COMMITTER_EMAIL": "c@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
    }

    def git(*args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        )
        return proc.stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    return git


# --- happy paths through the entry point ---------------------------------------------------------


def test_status_command_writes_an_abandonment_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R11: ``status <node> abandoned --cause`` writes one node-status/v1 record, prints its
    path, and the derived status follows it."""
    root = copy_graph(tmp_path)
    code, out, err = run(
        capsys, "status", *common(root, INTERIOR, "abandoned", "--cause", "dead branch (D-14)")
    )
    assert code == cli.EXIT_PASS and err == ""
    written = f"targets/{TARGET}/nodes/{INTERIOR}/status/{STAMP}-{AUTHOR}.yaml"
    assert out == {"ok": True, "ref": INTERIOR, "status": "abandoned", "written": [written]}
    doc = yaml.safe_load((root / written).read_text())
    assert doc["status"] == "abandoned" and doc["author"] == AUTHOR and doc["date"] == "2026-09-10"
    assert schemas.violations(doc, "node-status/v1") == []
    assert graphmod.load_target(root, TARGET).statuses[INTERIOR] == "abandoned"


def test_status_command_declares_a_target_active_and_branches_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R11, Q17: an ``active`` declaration needs no evidence; ``--branch`` commits the one record
    on a new branch and prints the push the curator runs next."""
    root = copy_graph(tmp_path)
    git = git_init(root, tmp_path)
    code, out, _err = run(
        capsys,
        "status",
        *common(root, "--branch", "curator/active", TARGET, "active", "--cause", "a merge landed"),
    )
    assert code == cli.EXIT_PASS and out["ok"] is True
    written = f"targets/{TARGET}/status/{STAMP}-{AUTHOR}.yaml"
    assert out["written"] == [written] and out["branch"] == "curator/active"
    assert out["next"] == "git push -u origin curator/active && gh pr create --fill"
    assert git("rev-parse", "--abbrev-ref", "HEAD") == "curator/active"
    assert git("show", "--name-only", "--format=", "HEAD").split() == [written]
    assert git("status", "--porcelain") == ""


def test_consolidate_command_asks_the_local_toolchain_and_writes_the_record(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """R10 through the command, without ``--no-toolchain``: the gate-spec is loaded, the probe
    is elaborated by the toolchain settings name, and on 'defeq' the superseded record lands."""
    root = copy_graph(tmp_path)
    code, out, err = run(
        capsys, "consolidate", *common(root, "--out", str(tmp_path / "o"), ROOT, INTERIOR)
    )
    assert code == cli.EXIT_PASS and err == ""
    written = f"targets/{TARGET}/nodes/{INTERIOR}/status/{STAMP}-{AUTHOR}.yaml"
    assert out == {"ok": True, "keep": ROOT, "drop": INTERIOR, "written": [written]}
    doc = yaml.safe_load((root / written).read_text())
    assert doc["status"] == "superseded" and doc["reference"] == ROOT
    assert any(c.startswith("elaborate:") and "Consolidate" in c for c in fake.calls)
    assert (tmp_path / "o" / "work").is_dir()


def test_missing_library_command_lists_lemmas_at_the_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R12 through the command: three postmortems naming one lemma reach the default threshold
    of 3, a lemma named once does not, ``--target`` is honoured, and nothing is created."""
    root = copy_graph(tmp_path)
    att = nodes_dir(root) / INTERIOR / "attempts"
    for i in range(3):
        (att / f"2026-09-0{i + 1}-x.yaml").write_text(
            yaml.safe_dump(
                samples.postmortem(
                    node=INTERIOR,
                    failure_class="missing-library",
                    artifacts={"missing_lemmas": ["Uniform bound", *(["rare"] if i == 0 else [])]},
                )
            ),
            encoding="utf-8",
        )
    before = tree(root)
    code, out, err = run(capsys, "missing-library", "--graph", str(root), "--target", TARGET)
    assert code == cli.EXIT_PASS and err == ""
    assert out["target"] == TARGET and out["threshold"] == curator.DEFAULT_THRESHOLD == 3
    assert out["lemmas"] == [
        {"lemma": "uniform bound", "count": 3, "as_written": ["Uniform bound"], "nodes": [INTERIOR]}
    ]
    assert out["created"] == []
    assert tree(root) == before

    code, out, _err = run(capsys, "missing-library", "--graph", str(root), "--threshold", "1")
    assert code == cli.EXIT_PASS and [m["lemma"] for m in out["lemmas"]] == [
        "uniform bound",
        "rare",
    ]


# --- refusals the entry point already turns into an answer ---------------------------------------


def test_curator_commands_refuse_a_missing_graph_before_reading_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nowhere = tmp_path / "nope"
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT)
    for argv in (
        [
            "revise",
            *common(nowhere, INTERIOR, "--statement", str(statement), "--request", "r.yaml"),
        ],
        ["consolidate", *common(nowhere, ROOT, INTERIOR)],
        ["status", *common(nowhere, INTERIOR, "abandoned", "--cause", "x")],
    ):
        code, out, err = run(capsys, *argv)
        assert code == cli.EXIT_ERROR and out == {}, argv[0]
        assert "graph checkout not found" in err, argv[0]


def test_curator_refusals_are_answers_with_exit_1_and_write_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every CuratorError is an answer: ``{"ok": false, "refused": <reason>}``, exit 1, the same
    reason on stderr, and the tree as it was (C7)."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT)
    before = tree(root)
    for argv, reason in (
        (
            ["consolidate", *common(root, "--no-toolchain", "ghost", INTERIOR)],
            "ghost is not a node",
        ),
        (["consolidate", *common(root, "--no-toolchain", ROOT, ROOT)], "two different nodes"),
        (["status", *common(root, "ghost", "abandoned", "--cause", "x")], "ghost is not a node"),
        (["status", *common(root, INTERIOR, "dormant", "--cause", "x")], "is a target status"),
        (["status", *common(root, TARGET, "abandoned", "--cause", "x")], "is a node status"),
        (["status", *common(root, TARGET, "active", "--cause", "   ")], "--cause is required"),
        (
            [
                "revise",
                *common(root, ROOT, "--statement", str(statement), "--request", str(request)),
            ],
            f"not {ROOT!r}",
        ),
        (
            [
                "revise",
                *common(root, "ghost", "--statement", str(statement), "--request", str(request)),
            ],
            "ghost is not a node",
        ),
    ):
        code, out, err = run(capsys, *argv)
        assert code == cli.EXIT_FAIL, argv
        assert out["ok"] is False and reason in out["refused"], argv
        assert f"refused: {out['refused']}" in err
    assert tree(root) == before


def test_status_refuses_an_unknown_status_at_the_parser(tmp_path: Path) -> None:
    """argparse's choices are the union of D-14's and D-33's statuses; anything else never
    reaches the command."""
    root = copy_graph(tmp_path)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["status", *common(root, INTERIOR, "resurrected", "--cause", "x")])
    assert exit_.value.code == 2
    assert not (nodes_dir(root) / INTERIOR / "status").exists()


def test_branch_refusals_are_usage_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Q17: ``--branch`` on a tree that is not a checkout, or naming a branch that exists, is a
    usage error (exit 2) naming the git step; the record itself is already on disk by then."""
    root = copy_graph(tmp_path)
    code, out, err = run(
        capsys, "status", *common(root, "--branch", "b", TARGET, "active", "--cause", "x")
    )
    assert code == cli.EXIT_ERROR and out == {} and "--branch needs a git checkout" in err

    root = copy_graph(tmp_path / "git")
    git = git_init(root, tmp_path)
    git("branch", "taken")
    head = git("rev-parse", "--abbrev-ref", "HEAD")
    code, out, err = run(
        capsys, "status", *common(root, "--branch", "taken", TARGET, "active", "--cause", "x")
    )
    assert code == cli.EXIT_ERROR and out == {} and "git checkout failed" in err
    # HEAD did not move, nothing was committed, and the record sits untracked for the curator.
    assert git("rev-parse", "--abbrev-ref", "HEAD") == head
    assert git("status", "--porcelain").split() == ["??", f"targets/{TARGET}/status/"]


# --- malformed inputs, each once a traceback out of main (coverage sweep; F08-Q18) ---------------


def test_revise_with_a_schema_invalid_request_is_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A request that does not satisfy revision-request/v1 is a refusal, and nothing is written."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR, defect_class="weaker")
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT)
    before = tree(root)
    code, out, _err = run(
        capsys,
        "revise",
        *common(root, INTERIOR, "--statement", str(statement), "--request", str(request)),
    )
    assert code == cli.EXIT_FAIL and out["ok"] is False and "revision-request/v1" in out["refused"]
    assert tree(root) == before


def test_revise_with_a_missing_request_file_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--request` naming no file is refused by name before anything else is read."""
    root = copy_graph(tmp_path)
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT)
    code, out, err = run(
        capsys,
        "revise",
        *common(
            root, INTERIOR, "--statement", str(statement), "--request", str(tmp_path / "no.yaml")
        ),
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert "no.yaml" in err


def test_revise_with_a_missing_statement_file_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--statement` naming no file is exit 2 naming the path, not a FileNotFoundError."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    code, out, err = run(
        capsys,
        "revise",
        *common(
            root, INTERIOR, "--statement", str(tmp_path / "no.lean"), "--request", str(request)
        ),
    )
    assert code == cli.EXIT_ERROR and out == {} and "no.lean" in err


def test_revise_with_a_statement_that_is_not_one_is_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A statement that is a proof (no sorry body) is a refusal naming the shape."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT.replace("by\n  sorry", "fun p q r h => ⟨h.1.1, h.1.2, h.2⟩"))
    before = tree(root)
    code, out, _err = run(
        capsys,
        "revise",
        *common(root, INTERIOR, "--statement", str(statement), "--request", str(request)),
    )
    assert code == cli.EXIT_FAIL and out["ok"] is False and "sorry" in out["refused"]
    assert tree(root) == before


def test_status_with_a_malformed_date_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--date yesterday` is a malformed flag: exit 2 before any record is built or written."""
    root = copy_graph(tmp_path)
    code, out, err = run(
        capsys,
        "status",
        "--graph",
        str(root),
        "--author",
        AUTHOR,
        "--date",
        "yesterday",
        INTERIOR,
        "abandoned",
        "--cause",
        "x",
    )
    assert code == cli.EXIT_ERROR and out == {} and "yesterday" in err
    assert not (nodes_dir(root) / INTERIOR / "status").exists()


def test_status_dormant_on_a_defective_graph_is_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dormancy declaration on a graph with a dependency cycle is a refusal naming the cycle,
    as the products command answers the same GraphError."""
    root = copy_graph(tmp_path)
    meta_path = nodes_dir(root) / INTERIOR / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [ROOT]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
    code, out, _err = run(capsys, "status", *common(root, TARGET, "dormant", "--cause", "quiet"))
    assert code == cli.EXIT_FAIL and out["ok"] is False and "cycle" in out["refused"]
    assert not (root / "targets" / TARGET / "status").exists()


def test_consolidate_with_a_broken_gate_spec_is_a_usage_error(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken gate-spec.json is the `cannot load ...` usage error every other command gives,
    and the toolchain is never asked."""
    root = copy_graph(tmp_path)
    (root / "targets" / TARGET / "gate-spec.json").write_text("{not json")
    code, out, err = run(capsys, "consolidate", *common(root, ROOT, INTERIOR))
    assert code == cli.EXIT_ERROR and out == {} and "gate-spec.json" in err
    assert fake.calls == []


def test_missing_library_refuses_a_missing_graph_or_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`missing-library` checks the checkout and the target like the other curator commands."""
    code, out, err = run(capsys, "missing-library", "--graph", str(tmp_path / "nope"))
    assert code == cli.EXIT_ERROR and out == {} and "graph checkout not found" in err
    root = copy_graph(tmp_path)
    code, out, err = run(capsys, "missing-library", "--graph", str(root), "--target", "ghost")
    assert code == cli.EXIT_ERROR and out == {} and "ghost" in err
    # The same target check guards the commands that write (they would otherwise hit the OS).
    code, out, err = run(
        capsys, "status", *common(root, "--target", "ghost", TARGET, "active", "--cause", "x")
    )
    assert code == cli.EXIT_ERROR and out == {} and "ghost" in err


def test_status_rejects_k_below_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """R11, D-33, Q18: K is the attempt threshold a dormancy declaration is measured against;
    `--k 0` would make it vacuous, so the flag has a lower bound of one — a usage error (exit 2)
    from the parser, before any record is considered."""
    root = copy_graph(tmp_path)
    for bad in ("0", "-1", "one"):
        with pytest.raises(SystemExit) as info:
            cli.main(["status", *common(root, TARGET, "dormant", "--cause", "quiet", "--k", bad)])
        assert info.value.code == cli.EXIT_ERROR, bad
        err = capsys.readouterr().err
        assert "--k" in err and ("at least 1" in err or "not an integer" in err), bad
    assert not (root / "targets" / TARGET / "status").exists()
    assert cli.positive_int("1") == 1 and cli.positive_int("42") == 42


def test_branch_acts_on_the_graph_even_under_a_git_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Q18's last find: git exports GIT_DIR, GIT_INDEX_FILE, GIT_WORK_TREE and GIT_PREFIX to a
    hook, so a pre-commit hook running the suite from a worktree handed them to every `git -C
    <graph>` call and `--branch` checked out and staged in the *calling* repository. With them
    set here to a scratch repository, the branch and the commit land on the graph and the
    scratch repository's HEAD, index and tree are untouched."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "README").write_text("the repository that ran the hook\n")
    scratch_git = git_init(scratch, tmp_path)
    scratch_head = scratch_git("symbolic-ref", "HEAD")
    scratch_commit = scratch_git("rev-parse", "HEAD")
    monkeypatch.setenv("GIT_DIR", str(scratch / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(scratch))
    monkeypatch.setenv("GIT_INDEX_FILE", str(scratch / ".git" / "index"))
    monkeypatch.setenv("GIT_PREFIX", "")

    root = copy_graph(tmp_path)
    git = git_init(root, tmp_path)
    code, out, _err = run(
        capsys,
        "status",
        *common(root, TARGET, "active", "--cause", "work resumes", "--branch", "curator/active"),
    )
    assert code == cli.EXIT_PASS and out["branch"] == "curator/active"
    assert git("branch", "--show-current") == "curator/active"
    assert git("status", "--porcelain") == ""
    assert git("log", "-1", "--format=%s") == f"status: {TARGET} active"

    assert scratch_git("symbolic-ref", "HEAD") == scratch_head
    assert scratch_git("rev-parse", "HEAD") == scratch_commit
    assert scratch_git("status", "--porcelain") == ""
    assert not scratch_git("branch", "--list", "curator/active")
