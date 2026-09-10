"""F00-T6, F02-R7: the gate's own commands in the fast tier — every refusal before a verdict
exists (exit 2), every verdict's exit code, and what is written — over the fake seam."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
from fakes import FakeToolchain, hazards_result
from harness import GRAPH, TARGET, TUTORIAL, copy_graph

from opn_gate import attestation, cli, config, pipeline, schemas, signer, toolchain
from opn_gate.diagnostic import Diagnostic
from opn_gate.toolchain import AxiomResult, ElabResult, ToolchainMissingError

NODES = f"targets/{TARGET}/nodes"
NAT_SUB = {"checker": "nat-sub", "location": "n - 1", "message": "subtraction on Nat truncates"}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeToolchain:
    """The CLI builds its toolchain from settings; here that is the fake, whatever the host has."""
    tc = FakeToolchain()
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: tc))
    return tc


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return code, out, captured.err


def git_repo(tmp_path: Path) -> tuple[Path, Any]:
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

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    return root, git


# --- refusals before any verdict exists: exit 2, a line on stderr, nothing written --------------


def test_pregate_refuses_a_missing_graph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run(capsys, "pregate", "--graph", str(tmp_path / "nope"), "--node", TUTORIAL)
    assert code == cli.EXIT_ERROR and out == {}
    assert "graph checkout not found" in err


def test_pregate_refuses_an_invalid_gate_spec(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """F00-R9: gate-spec.json is validated before anything runs; a bad one is a usage error."""
    graph = copy_graph(tmp_path)
    spec = graph / "targets" / TARGET / "gate-spec.json"
    spec.write_text('{"schema": "gate-spec/v1", "graph_id": "propositional"}')
    code, out, err = run(capsys, "pregate", "--graph", str(graph), "--node", TUTORIAL)
    assert code == cli.EXIT_ERROR and out == {}
    assert "cannot load" in err and "gate-spec.json" in err
    spec.write_text("{not json")
    code, _out, err = run(capsys, "pregate", "--graph", str(graph), "--node", TUTORIAL)
    assert code == cli.EXIT_ERROR and "cannot read JSON" in err
    assert fake.calls == []


def test_pregate_needs_a_target_when_the_graph_has_several(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    (graph / "targets" / "other").mkdir()
    code, _out, err = run(capsys, "pregate", "--graph", str(graph), "--node", TUTORIAL)
    assert code == cli.EXIT_ERROR and "--target is required" in err and "other" in err
    with pytest.raises(cli.CliError):
        cli.infer_target(graph)
    (graph / "targets" / "other").rmdir()
    assert cli.infer_target(graph) == TARGET


def test_pregate_without_a_toolchain_names_the_install_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R16: no elan means no verdict, and the message says how to get one."""

    def missing(_cls: object, _settings: object) -> FakeToolchain:
        raise ToolchainMissingError(f"elan not found; run {toolchain.INSTALL_SCRIPT}")

    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(missing))
    graph = copy_graph(tmp_path)
    code, out, err = run(
        capsys, "pregate", "--graph", str(graph), "--node", TUTORIAL, "--out", str(tmp_path / "o")
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert toolchain.INSTALL_SCRIPT in err
    assert not (tmp_path / "o" / "verdict.json").exists()


# --- verdicts: exit codes and the files every run writes -----------------------------------------


def test_pregate_passes_and_writes_verdict_and_attestation(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)  # not a git checkout: step 2 runs without a diff, with a warning
    out_dir = tmp_path / "out"
    code, out, _err = run(
        capsys,
        "pregate",
        "--graph",
        str(graph),
        "--node",
        TUTORIAL,
        "--out",
        str(out_dir),
        "--model",
        "claude-fable-5-1",
        "--harness",
        "claude-code",
    )
    assert code == cli.EXIT_PASS
    assert out["verdict"] == "pass" and out["first_failing_step"] is None
    verdict = json.loads((out_dir / "verdict.json").read_text())
    assert [s["step"] for s in verdict["steps"]] == [1, 2, 4, 5, 6, 7, 8]
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["schema"].startswith("attestation/") and doc["runner"] == "local"
    assert doc["graph_commit"] is None and doc["signature"]["kind"] == "none"
    assert doc["tooling"] == {"model": "claude-fable-5-1", "harness": "claude-code"}
    assert out["attestation"] == str(out_dir / "attestation.json")
    assert fake.calls[0] == "resolve:leanprover/lean4:v4.33.1:install=False"


def test_pregate_failure_exits_1_and_still_writes_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC14 (the exit half): a failed verdict is exit 1 with the attestation on disk."""
    failing = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    monkeypatch.setattr(
        toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: failing)
    )
    graph = copy_graph(tmp_path)
    out_dir = tmp_path / "out"
    code, out, _err = run(
        capsys, "pregate", "--graph", str(graph), "--node", TUTORIAL, "--out", str(out_dir)
    )
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 5 and out["diagnostic"]["code"] == "axiom-not-allowed"
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["verdict"] == "fail" and doc["first_failing_step"] == 5


def test_pregate_diffs_the_worktree_and_records_a_clean_head(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """R11: on a git checkout the diff against --base is what step 2 checks; a dirty tree has no
    graph_commit, a clean one records HEAD; --install reaches the seam; --no-diff skips git."""
    root, git = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    (root / NODES / TUTORIAL / "Statement.lean").write_text("theorem OpnProp.x : True := sorry\n")
    code, out, _err = run(
        capsys,
        "pregate",
        "--graph",
        str(root),
        "--node",
        TUTORIAL,
        "--install",
        "--out",
        str(tmp_path / "o1"),
    )
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 2 and out["diagnostic"]["code"] == "path-forbidden"
    assert out["diagnostic"]["details"]["paths"] == [f"{NODES}/{TUTORIAL}/Statement.lean"]
    assert fake.calls[0].endswith("install=True")
    assert schemas.load_json(Path(out["attestation"]))["graph_commit"] is None

    git("checkout", "--", ".")
    code, out, _err = run(
        capsys,
        "pregate",
        "--graph",
        str(root),
        "--node",
        TUTORIAL,
        "--base",
        "HEAD",
        "--out",
        str(tmp_path / "o2"),
    )
    assert code == cli.EXIT_PASS
    assert schemas.load_json(Path(out["attestation"]))["graph_commit"] == head

    code, _out, err = run(
        capsys,
        "pregate",
        "--graph",
        str(root),
        "--node",
        TUTORIAL,
        "--base",
        "no-such-ref",
        "--out",
        str(tmp_path / "o3"),
    )
    assert code == cli.EXIT_ERROR and "git diff against 'no-such-ref' failed" in err

    (root / NODES / TUTORIAL / "Statement.lean").write_text("theorem OpnProp.x : True := sorry\n")
    code, out, _err = run(
        capsys,
        "pregate",
        "--graph",
        str(root),
        "--node",
        TUTORIAL,
        "--no-diff",
        "--out",
        str(tmp_path / "o4"),
    )
    assert code == cli.EXIT_FAIL and out["diagnostic"]["code"] == "statement-hash"


def test_worktree_helpers_on_non_git_and_dirty_trees(tmp_path: Path) -> None:
    graph = copy_graph(tmp_path)
    assert cli.worktree_changes(graph, None) is None
    assert cli.clean_head(graph) is None
    root, git = git_repo(tmp_path / "r")
    assert cli.clean_head(root) == git("rev-parse", "HEAD")
    (root / "untracked.txt").write_text("x")
    assert cli.clean_head(root) is None
    changes = cli.worktree_changes(root, None)
    assert changes is not None and [c.path for c in changes] == ["untracked.txt"]


def test_pregate_sign_produces_a_verifiable_contributor_signature(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """R11 (AC24's fast half): --sign yields a `contributor` signature over the signed bytes
    that verifies against the key's public half, and the record still validates."""
    key = tmp_path / "id_test"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    graph = copy_graph(tmp_path)
    out_dir = tmp_path / "out"
    code, _out, _err = run(
        capsys,
        "pregate",
        "--graph",
        str(graph),
        "--node",
        TUTORIAL,
        "--out",
        str(out_dir),
        "--sign",
        str(key),
    )
    assert code == cli.EXIT_PASS
    doc = schemas.load_json(out_dir / "attestation.json")
    sig = doc["signature"]
    assert sig["kind"] == "contributor" and sig["key_id"].startswith("SHA256:")
    s = signer.SshKeygenSigner()
    assert s.verify(
        attestation.signed_bytes(doc), sig["value"], (tmp_path / "id_test.pub").read_text()
    )
    doc["verdict"] = "fail"  # any change to the signed fields breaks it
    assert not s.verify(
        attestation.signed_bytes(doc), sig["value"], (tmp_path / "id_test.pub").read_text()
    )


@pytest.mark.xfail(
    strict=True,
    reason="a --sign key that ssh-keygen cannot use raises SignerError out of cli.main after the "
    "verdict was computed: no verdict.json is written and the process dies with a traceback "
    "instead of exit 2 (conventions §5: exceptions are caught at boundaries; C7)",
)
def test_pregate_sign_with_an_unusable_key_is_a_usage_error(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    bad_key = tmp_path / "not-a-key"
    bad_key.write_text("garbage\n")
    code = cli.main(
        [
            "pregate",
            "--graph",
            str(graph),
            "--node",
            TUTORIAL,
            "--sign",
            str(bad_key),
            "--out",
            str(tmp_path / "o"),
        ]
    )
    assert code == cli.EXIT_ERROR


def test_emit_maps_every_verdict_kind_to_its_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = config.load({})
    doc = {"schema": "attestation/v4"}
    for kind, code in (
        ("pass", cli.EXIT_PASS),
        ("fail", cli.EXIT_FAIL),
        ("bounced", cli.EXIT_BOUNCED),
    ):
        verdict = pipeline.Verdict(verdict=kind, steps=(), diagnostic=Diagnostic("d", "m"))  # type: ignore[arg-type]
        out_dir = tmp_path / kind
        out_dir.mkdir()
        assert cli.emit(verdict, doc, out_dir, settings) == code
        summary = json.loads(capsys.readouterr().out)
        assert summary["verdict"] == kind and summary["verdict_file"] == str(
            out_dir / "verdict.json"
        )
        assert json.loads((out_dir / "verdict.json").read_text())["verdict"] == kind
        assert (out_dir / "attestation.json").read_bytes() == schemas.canonical_json(doc)


# --- opn-gate hazards: step 6 alone (F02-R7) ---------------------------------------------------


def test_hazards_command_refuses_a_non_node_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    for bad in (
        graph / "targets" / TARGET,
        graph / "targets" / TARGET / "nodes",
        tmp_path / "nope",
    ):
        code, out, err = run(capsys, "hazards", str(bad))
        assert code == cli.EXIT_ERROR and out == {}, bad
        assert "is not a node directory" in err


def test_hazards_command_reports_findings_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R7: the same JSON as the pipeline step, plus the `hazards` block, exit 1 on a finding."""
    graph = copy_graph(tmp_path)
    spec_path = graph / "targets" / TARGET / "gate-spec.json"
    spec = schemas.load_json(spec_path)
    spec["hazard_checkers"] = ["nat-sub"]
    spec_path.write_bytes(schemas.canonical_json(spec))
    tc = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: tc))
    node_dir = graph / NODES / TUTORIAL
    code, out, _err = run(capsys, "hazards", str(node_dir), "--out", str(tmp_path / "o"))
    assert code == cli.EXIT_FAIL
    assert [s["step"] for s in out["steps"]] == [1, 2, 6]
    assert out["first_failing_step"] == 6 and out["diagnostic"]["code"] == "hazard-unacknowledged"
    assert out["hazards"]["findings"] == [NAT_SUB] and out["hazards"]["acknowledged"] == []
    # The statement step compiled the repo's own Context (sorry-bodied deps), not a generated one.
    assert "elaborate:Nodes.«tutorial-and-swap».Context" in tc.calls
    assert not any(c.startswith("kernel_replay") or c.startswith("axioms") for c in tc.calls)
    assert not (tmp_path / "o" / "attestation.json").exists()  # not a submission: no record


def test_hazards_command_passes_with_no_checkers(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    code, out, _err = run(
        capsys, "hazards", str(graph / NODES / TUTORIAL), "--out", str(tmp_path / "o")
    )
    assert code == cli.EXIT_PASS
    assert out["verdict"] == "pass" and out["hazards"] == {
        "checkers": [],
        "findings": [],
        "acknowledged": [],
    }


def test_hazards_command_fails_when_the_statement_does_not_elaborate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The standalone step 2 (StatementStep) fails closed on an elaboration error or a broken
    node layout, naming the step, before any checker runs."""
    tc = FakeToolchain(
        elab=ElabResult(
            ok=False,
            messages=(toolchain.Message("Context.lean", 2, 1, "error", "unknown identifier"),),
        )
    )
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: tc))
    graph = copy_graph(tmp_path)
    node_dir = graph / NODES / TUTORIAL
    code, out, _err = run(capsys, "hazards", str(node_dir), "--out", str(tmp_path / "o1"))
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 2 and out["diagnostic"]["code"] == "elaboration-failed"
    assert out["diagnostic"]["details"]["messages"][0]["text"] == "unknown identifier"
    assert out["hazards"] is None

    (node_dir / "stray.txt").write_text("")
    code, out, _err = run(capsys, "hazards", str(node_dir), "--out", str(tmp_path / "o2"))
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 2 and out["diagnostic"]["code"] == "layout-extra"


def test_hazards_command_refuses_a_bad_checker_list_before_step_1(
    tmp_path: Path, fake: FakeToolchain, capsys: pytest.CaptureFixture[str]
) -> None:
    """F02-AC1 through the command: the config guard runs here too."""
    graph = copy_graph(tmp_path)
    spec_path = graph / "targets" / TARGET / "gate-spec.json"
    spec = schemas.load_json(spec_path)
    spec["hazard_checkers"] = ["bogus"]
    spec_path.write_bytes(schemas.canonical_json(spec))
    code, out, _err = run(
        capsys, "hazards", str(graph / NODES / TUTORIAL), "--out", str(tmp_path / "o")
    )
    assert code == cli.EXIT_FAIL
    assert out["diagnostic"]["code"] == "config-unknown-checker"
    assert all(s["result"] == "skipped" for s in out["steps"]) and fake.calls == []


# --- the git-facing commands refuse what is not a checkout ---------------------------------------


def test_git_commands_refuse_a_non_checkout_and_an_unknown_ref(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    code, out, err = run(capsys, "classify", "--graph", str(graph), "--base", "HEAD~1")
    assert code == cli.EXIT_ERROR and out == {} and "is not a git checkout" in err

    root, _git = git_repo(tmp_path / "r")
    code, _out, err = run(capsys, "classify", "--graph", str(root), "--base", "no-such-ref")
    assert code == cli.EXIT_ERROR and "unknown base 'no-such-ref'" in err
    code, _out, err = run(
        capsys, "classify", "--graph", str(root), "--base", "HEAD", "--head", "nope"
    )
    assert code == cli.EXIT_ERROR and "unknown commit 'nope'" in err
    assert cli.commit_changes(root, "HEAD") == []  # the root commit has no parent: nothing changed


def test_sign_command_refuses_without_a_key_or_with_the_wrong_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """C8: the gate key comes from config alone; a foreign public key is refused before writing."""
    att = tmp_path / "att.json"
    att.write_bytes(schemas.canonical_json(samples.attestation()))
    out = tmp_path / "signed.json"
    pub = tmp_path / "gate.pub"
    monkeypatch.delenv("OPN_GATE_SIGNING_KEY", raising=False)
    code, _o, err = run(
        capsys, "sign", "--attestation", str(att), "--public-key", str(pub), "--out", str(out)
    )
    assert code == cli.EXIT_ERROR and "OPN_GATE_SIGNING_KEY is not set" in err

    key = tmp_path / "gate"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    other = tmp_path / "other"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
    monkeypatch.setenv("OPN_GATE_SIGNING_KEY", key.read_text())
    code, _o, err = run(
        capsys,
        "sign",
        "--attestation",
        str(att),
        "--public-key",
        str(tmp_path / "other.pub"),
        "--out",
        str(out),
    )
    assert code == cli.EXIT_ERROR and "does not verify" in err and not out.exists()

    not_att = tmp_path / "meta.json"
    not_att.write_bytes(schemas.canonical_json(samples.meta()))
    code, _o, err = run(
        capsys,
        "sign",
        "--attestation",
        str(not_att),
        "--public-key",
        str(tmp_path / "gate.pub"),
        "--out",
        str(out),
    )
    assert code == cli.EXIT_ERROR and "not an attestation" in err and not out.exists()

    code, o, _err = run(
        capsys,
        "sign",
        "--attestation",
        str(att),
        "--public-key",
        str(tmp_path / "gate.pub"),
        "--out",
        str(out),
    )
    assert code == cli.EXIT_PASS and o["signed"] == str(out)
    assert schemas.load_json(out)["signature"]["kind"] == "gate"
