"""The sandboxed and git-facing commands through ``cli.main`` in the fast tier: ``reproduce``,
``gate``, ``postmerge``, ``exhibits``, ``admit --sandbox``, ``ledger`` and ``products`` on a
Mathlib pin — every refusal before a verdict exists (exit 2), every verdict's exit code, and what
each writes. Docker is a scripted binary that "builds" and "inspects" instantly and answers
``docker cp`` out with a tar of the host directory; the step-3 seam the CLI constructs is a
``SandboxToolchain`` stand-in whose processes are the fake seam from ``fakes.py``, so the
container assembly (image, caps, mounts) is asserted while nothing runs in a container. The
docker tier drives the real image (``test_reproduce_docker.py``, ``test_admit_docker.py``).

A malformed flag is a usage error before the export, the image build and the run — the coverage
sweep found four escaping ``main`` as tracebacks after that work (F08-Q18; conventions §5).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FakeToolchain, used_constants_result
from harness import FIXTURES, GRAPH, TARGET, TUTORIAL, copy_graph
from scripted import ScriptedToolchain

from opn_gate import attestation, bounce, cli, postmerge, sandbox, scaffold, schemas, toolchain
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.sandbox import Caps, SandboxToolchain
from opn_gate.toolchain import AxiomResult, ElabResult, ToolchainMissingError

NODES = f"targets/{TARGET}/nodes"
PIN = "leanprover/lean4:v4.33.1"
TAG = sandbox.image_tag(PIN)
EXHIBIT0 = f"Nodes.«{TUTORIAL}».Exhibit0"
STATEMENT = "theorem OpnProp.spec_one : ∀ p : Prop, p → p := by\n  sorry\n"
WITNESS = "theorem witness : True := trivial\n"
Git = Callable[..., str]


# --- the scripted docker and the sandbox stand-in ------------------------------------------------


def scripted_docker(directory: Path, *, image_present: bool = True) -> Path:
    """A ``docker`` that logs every invocation, answers ``image inspect`` from ``image.exit`` (so
    a test can flip presence), builds instantly, and answers ``cp <name>:<dir> -`` with a tar of
    the host directory — what the real one would return after a run that wrote nothing new."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "docker"
    log = directory / "docker.log"
    (directory / "image.exit").write_text("0" if image_present else "1")
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'case "$1" in\n'
        f'  image) exit "$(cat "{directory}/image.exit")" ;;\n'
        "  inspect) echo 0 ;;\n"
        '  cp) if [ "$2" = "-" ]; then cat > /dev/null; else\n'
        '        src="${2#*:}"; tar -C "$(dirname "$src")" -c "$(basename "$src")"; fi ;;\n'
        "esac\n"
        "exit 0\n"
    )
    script.chmod(0o755)
    return script


@dataclass
class Seam:
    """What the CLI assembled: the docker log, every sandbox it constructed, and the fake the
    pipeline actually ran on (swap ``fake`` before the call to script the steps)."""

    docker_dir: Path
    fake: FakeToolchain = field(default_factory=FakeToolchain)
    made: list[dict[str, Any]] = field(default_factory=list)

    def set_image_present(self, present: bool) -> None:
        (self.docker_dir / "image.exit").write_text("0" if present else "1")

    def docker_log(self) -> list[str]:
        log = self.docker_dir / "docker.log"
        return log.read_text().splitlines() if log.is_file() else []

    def docker_verbs(self) -> list[str]:
        return [line.split()[0] for line in self.docker_log()]


@pytest.fixture
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Seam:
    """``ensure_image`` runs the real ``image_exists``/``build_image`` over the scripted docker;
    ``SandboxToolchain`` is replaced by a factory that records the mounts and hands back the
    fake seam, so the pipeline's steps run on ``seam.fake``."""
    docker = scripted_docker(tmp_path / "docker-bin")
    s = Seam(docker_dir=docker.parent)
    real_exists, real_build = sandbox.image_exists, sandbox.build_image

    def image_exists(tag: str) -> bool:
        return real_exists(tag, docker=str(docker))

    def build_image(gate_dir: Path, lean_toolchain: str, *, mathlib_sha: str | None = None) -> str:
        return real_build(gate_dir, lean_toolchain, mathlib_sha=mathlib_sha, docker=str(docker))

    def make_sandbox(
        image: str,
        caps: Caps,
        *,
        read_only: Sequence[Path] = (),
        read_write: Sequence[Path] = (),
    ) -> FakeToolchain:
        s.made.append(
            {
                "image": image,
                "caps": caps,
                "read_only": [p.resolve() for p in read_only],
                "read_write": [p.resolve() for p in read_write],
            }
        )
        return s.fake

    monkeypatch.setattr(sandbox, "image_exists", image_exists)
    monkeypatch.setattr(sandbox, "build_image", build_image)
    monkeypatch.setattr(sandbox, "SandboxToolchain", make_sandbox)
    return s


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    """The exit code, the *last* JSON document on stdout, and stderr."""
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    docs = json_documents(captured.out)
    out: dict[str, Any] = docs[-1] if docs else {}
    return code, out, captured.err


def json_documents(text: str) -> list[dict[str, Any]]:
    """Every JSON object on stdout, in order (``reproduce --compare`` prints two)."""
    decoder = json.JSONDecoder()
    docs: list[dict[str, Any]] = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        doc, i = decoder.raw_decode(text, i)
        docs.append(doc)
    return docs


def git_repo(tmp_path: Path, *, author: str = "t") -> tuple[Path, Git, str]:
    """The fixture as a repo: a base commit without the tutorial proof, then one adding it —
    the shape of a merged submission. Returns (root, git, base_sha)."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    proof = root / NODES / TUTORIAL / "Proof.lean"
    proof_text = proof.read_text()
    proof.unlink()
    env = {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "committer",
        "GIT_COMMITTER_EMAIL": "c@x",
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
    base = git("rev-parse", "HEAD")
    proof.write_text(proof_text)
    git("add", "-A")
    git("commit", "-q", "-m", "prove tutorial-and-swap")
    return root, git, base


def precheck_body(root: Path, **overrides: Any) -> str:
    """A pull-request body carrying a passing precheck attestation for the tutorial node."""
    statement = root / NODES / TUTORIAL / "Statement.lean"
    doc = samples.attestation(
        node_id=TUTORIAL,
        statement_hash=schemas.content_hash(statement.read_bytes()),
        signature={
            "kind": "none",
            "key_id": None,
            "value": None,
            "timestamp": attestation.utc_now().strftime(bounce.TIMESTAMP_FORMAT),
        },
    )
    doc.update(overrides)
    return "Proof attached.\n\n" + bounce.render_block(doc) + "\n"


# --- refusals before any verdict exists: exit 2, nothing built, nothing written -----------------


def test_sandboxed_commands_refuse_a_non_checkout_and_an_unknown_commit(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    body = tmp_path / "body.md"
    body.write_text("")
    for argv in (
        ["reproduce", "--graph", str(graph), "--commit", "HEAD", "--node", TUTORIAL],
        [
            "gate",
            "--graph",
            str(graph),
            "--base",
            "HEAD~1",
            "--target",
            TARGET,
            "--node",
            TUTORIAL,
            "--pr-body-file",
            str(body),
        ],
        [
            "postmerge",
            "--graph",
            str(graph),
            "--commit",
            "HEAD",
            "--pr",
            "1",
            "--review-kind",
            "tutorial",
            "--target",
            TARGET,
            "--node",
            TUTORIAL,
        ],
        ["ledger", "--graph", str(graph), "--commit", "HEAD"],
        ["exhibits", "--graph", str(graph), "--base", "HEAD~1"],
    ):
        code, out, err = run(capsys, *argv)
        assert code == cli.EXIT_ERROR and out == {}, argv[0]
        assert "is not a git checkout" in err, argv[0]

    root, _git, _base = git_repo(tmp_path / "r")
    code, _out, err = run(
        capsys, "reproduce", "--graph", str(root), "--commit", "nope", "--node", TUTORIAL
    )
    assert code == cli.EXIT_ERROR and "unknown commit 'nope'" in err
    code, _out, err = run(
        capsys,
        "gate",
        "--graph",
        str(root),
        "--base",
        "nope",
        "--target",
        TARGET,
        "--node",
        TUTORIAL,
        "--pr-body-file",
        str(body),
    )
    assert code == cli.EXIT_ERROR and "unknown base 'nope'" in err
    code, _out, err = run(capsys, "exhibits", "--graph", str(root), "--base", "nope")
    assert code == cli.EXIT_ERROR and "unknown base 'nope'" in err
    assert seam.docker_log() == [] and seam.made == [] and seam.fake.calls == []


def test_sandboxed_commands_refuse_a_broken_gate_spec_in_the_exported_tree(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The spec is read from the tree at the commit, not the worktree: a broken one committed
    there is a usage error before docker is asked for anything."""
    root, git, _base = git_repo(tmp_path)
    spec = root / "targets" / TARGET / "gate-spec.json"
    spec.write_text('{"schema": "gate-spec/v1"}')
    git("commit", "-q", "-am", "break the spec")
    out_dir = tmp_path / "o"
    code, out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--out",
        str(out_dir),
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert "cannot load" in err and "gate-spec.json" in err
    assert (
        out_dir / "tree" / "targets" / TARGET / "gate-spec.json"
    ).read_text() == '{"schema": "gate-spec/v1"}'
    assert not (out_dir / "verdict.json").exists()
    assert seam.docker_log() == [] and seam.made == []

    # The previous commit's spec is intact, and reproducing *that* commit reads it.
    git("checkout", "-q", "HEAD~1", "--", "targets")
    code, _out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD~1",
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o2"),
    )
    assert code == cli.EXIT_PASS


def test_sandboxed_commands_need_a_target_when_the_tree_has_several(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    (root / "targets" / "other").mkdir()
    (root / "targets" / "other" / "README.md").write_text("a second target\n")
    git("add", "-A")
    git("commit", "-q", "-m", "second target")
    code, out, err = run(
        capsys, "reproduce", "--graph", str(root), "--commit", "HEAD", "--node", TUTORIAL
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert "--target is required" in err and "other" in err
    assert seam.made == []
    # Named, the run proceeds — and fails at step 2, because the commit's own diff is what step
    # 2 checks, and this commit added a file outside the node (R11).
    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--target",
        TARGET,
        "--out",
        str(tmp_path / "o"),
    )
    assert code == cli.EXIT_FAIL and out["first_failing_step"] == 2
    assert out["diagnostic"]["details"]["paths"] == ["targets/other/README.md"]


def test_the_image_is_built_when_absent_and_refused_under_no_build(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """``ensure_image``: present -> used; absent + ``--no-build`` -> exit 2 naming the tag;
    absent -> built from gate/Dockerfile for the spec's pin; ``--image`` asks docker nothing."""
    root, _git, _base = git_repo(tmp_path)
    seam.set_image_present(False)
    code, out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--no-build",
        "--out",
        str(tmp_path / "o1"),
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert f"sandbox image {TAG} is not present" in err
    assert seam.docker_verbs() == ["image"] and seam.made == []
    assert not (tmp_path / "o1" / "verdict.json").exists()

    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o2"),
    )
    assert code == cli.EXIT_PASS and out["verdict"] == "pass"
    assert seam.docker_verbs() == ["image", "image", "build"]
    build = seam.docker_log()[-1]
    assert f"-f {cli.GATE_DIR / 'Dockerfile'}" in build
    assert f"--build-arg LEAN_TOOLCHAIN={PIN} -t {TAG} {cli.GATE_DIR.parent}" in build  # F10-T3
    assert seam.made[-1]["image"] == TAG

    code, _out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--image",
        "opn-gate:mine",
        "--out",
        str(tmp_path / "o3"),
    )
    assert code == cli.EXIT_PASS
    assert seam.docker_verbs() == ["image", "image", "build"]  # nothing more was asked
    assert seam.made[-1]["image"] == "opn-gate:mine"


def test_a_failed_image_build_is_a_usage_error(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `docker build` failure is exit 2 naming it, not a SandboxError traceback."""
    root, _git, _base = git_repo(tmp_path)
    seam.set_image_present(False)

    def failing_build(
        gate_dir: Path, lean_toolchain: str, *, mathlib_sha: str | None = None
    ) -> str:
        msg = "docker build failed: no space left on device"
        raise sandbox.SandboxError(msg)

    monkeypatch.setattr(sandbox, "build_image", failing_build)
    code, out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o"),
    )
    assert code == cli.EXIT_ERROR and out == {} and "docker build failed" in err


# --- reproduce (D-5): the mounts, the verdict, and --compare -------------------------------------


def test_reproduce_exports_the_tree_and_mounts_the_node_read_only(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F00-R5, R12: the tree at the commit is exported without .git, the node directory is
    mounted read-only and the work directory read-write, the caps are the spec's, the diff is
    the commit's own, and the attestation names the commit."""
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    (root / NODES / TUTORIAL / "Statement.lean").write_text(
        "theorem OpnProp.x : True := sorry\n"
    )  # dirty worktree: ignored
    out_dir = tmp_path / "o"
    code, out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(out_dir),
    )
    assert code == cli.EXIT_PASS and err == ""
    assert out["verdict"] == "pass" and [s["step"] for s in out["steps"]] == [1, 2, 4, 5, 6, 7, 8]
    tree = out_dir / "tree"
    assert (tree / NODES / TUTORIAL / "Proof.lean").is_file() and not (tree / ".git").exists()
    assert "OpnProp.x" not in (tree / NODES / TUTORIAL / "Statement.lean").read_text()
    made = seam.made[-1]
    assert made["caps"] == Caps(cpu=2.0, memory_mib=2048, wallclock_s=300)
    assert made["read_only"] == [(tree / NODES / TUTORIAL).resolve()]
    assert made["read_write"] == [(out_dir / "work").resolve()]
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["graph_commit"] == head and doc["runner"] == "local" and doc["verdict"] == "pass"
    assert schemas.violations(doc) == []
    assert seam.fake.calls[0] == f"resolve:{PIN}:install=False"
    assert cli.commit_changes(root, head) == [Change("A", f"{NODES}/{TUTORIAL}/Proof.lean")]


def test_reproduce_compare_is_the_d5_verdict(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-5: ``--compare`` re-derives and diffs against the committed record with the run
    environment masked and step 9 copied over; identical is exit 0, a difference is exit 1 with
    the differing fields named — and the reproduction's own verdict does not decide it."""
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    code, first, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o1"),
    )
    assert code == cli.EXIT_PASS
    produced = schemas.load_json(Path(first["attestation"]))
    committed = postmerge.record_step9(
        produced, merge_commit=head, review=postmerge.review_block("tutorial")
    )
    committed_path = tmp_path / "000001.json"
    committed_path.write_bytes(schemas.canonical_json(committed))

    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o2"),
        "--compare",
        str(committed_path),
    )
    assert code == cli.EXIT_PASS and out == {"identical": True, "differing_fields": []}

    tampered = dict(committed, verdict="fail", first_failing_step=4)
    committed_path.write_bytes(schemas.canonical_json(tampered))
    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o3"),
        "--compare",
        str(committed_path),
    )
    assert code == cli.EXIT_FAIL
    assert out == {"identical": False, "differing_fields": ["first_failing_step", "verdict"]}
    assert (tmp_path / "o3" / "verdict.json").is_file()  # the run itself still left its record

    # A reproduction that fails the same way the committed record says it failed *is* reproduced.
    seam.fake = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    code, failed, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o4"),
    )
    assert code == cli.EXIT_FAIL and failed["first_failing_step"] == 5
    committed_path.write_bytes(
        schemas.canonical_json(
            postmerge.record_step9(
                schemas.load_json(Path(failed["attestation"])),
                merge_commit=head,
                review=postmerge.review_block("tutorial"),
            )
        )
    )
    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        head,
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o5"),
        "--compare",
        str(committed_path),
    )
    assert code == cli.EXIT_PASS and out["identical"] is True


def test_reproduce_compare_against_a_missing_or_unreadable_file_is_a_usage_error(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--compare` is read before the run: a missing or non-JSON file is exit 2 with no sandbox
    spent and no verdict written."""
    root, _git, _base = git_repo(tmp_path)
    code, out, err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o"),
        "--compare",
        str(tmp_path / "nope.json"),
    )
    assert code == cli.EXIT_ERROR and out == {} and "nope.json" in err
    assert not (tmp_path / "o" / "verdict.json").exists()
    assert "build" not in seam.docker_verbs() and "create" not in seam.docker_verbs()


def test_reproduce_runs_the_real_sandbox_seam_over_the_scripted_docker(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the real ``SandboxToolchain`` (docker scripted, so every container is empty): step 1
    asks the image for its toolchains, gets none, and the verdict is a step-1 failure naming the
    pin — a failed container is a verdict, never a crash — after create, copy in, start,
    inspect, copy out and remove, in that order."""
    docker = seam.docker_dir / "docker"

    def real_sandbox(
        image: str, caps: Caps, *, read_only: Sequence[Path] = (), read_write: Sequence[Path] = ()
    ) -> (
        SandboxToolchain
    ):  # the module-level import is the real class; the fixture rebinds the name
        return SandboxToolchain(
            image, caps, read_only=read_only, read_write=read_write, docker=str(docker)
        )

    monkeypatch.setattr(sandbox, "SandboxToolchain", real_sandbox)
    root, _git, _base = git_repo(tmp_path)
    code, out, _err = run(
        capsys,
        "reproduce",
        "--graph",
        str(root),
        "--commit",
        "HEAD",
        "--node",
        TUTORIAL,
        "--out",
        str(tmp_path / "o"),
    )
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 1 and out["diagnostic"]["code"] == "toolchain-missing"
    assert PIN in out["diagnostic"]["message"]
    assert seam.docker_verbs() == ["image", "create", "cp", "start", "inspect", "cp", "rm"]
    create = seam.docker_log()[1]
    assert "--network none" in create and create.endswith(
        f"{TAG} timeout -s KILL 300 {sandbox.CONTAINER_ELAN} toolchain list"
    )
    assert (tmp_path / "o" / "attestation.json").is_file()


# --- gate: the bounce rule, then the verdict ---------------------------------------------------


def gate_argv(root: Path, base: str, body: Path, out: Path) -> list[str]:
    return [
        "gate", "--graph", str(root), "--base", base, "--target", TARGET, "--node", TUTORIAL,
        "--pr-body-file", str(body), "--out", str(out),
    ]  # fmt: skip


def test_gate_bounces_a_pull_request_without_a_precheck_and_runs_no_step(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F00-R13: no attached attestation -> bounced, exit 3, no step run, the record written."""
    root, _git, base = git_repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text("no block here\n")
    out_dir = tmp_path / "o"
    code, out, _err = run(capsys, *gate_argv(root, base, body, out_dir))
    assert code == cli.EXIT_BOUNCED
    assert out["verdict"] == "bounced" and out["steps"] == []
    assert out["diagnostic"]["message"] == "no precheck attestation attached to the pull request"
    assert seam.fake.calls == []
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["verdict"] == "bounced"
    assert doc["precheck_attestation"] == {"hash": None, "signature_kind": None}


def test_gate_bounces_a_precheck_for_another_statement(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, base = git_repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text(precheck_body(root, statement_hash="f" * 64))
    code, out, _err = run(capsys, *gate_argv(root, base, body, tmp_path / "o"))
    assert code == cli.EXIT_BOUNCED
    assert "different node or statement" in out["diagnostic"]["message"]
    assert seam.fake.calls == []


def test_gate_passes_with_an_attached_precheck_and_maps_a_failure_to_exit_1(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The authoritative run: the diff is base..head, the precheck's hash and signature kind
    are recorded, the verdict decides the exit code (0 / 1), and the record names HEAD."""
    root, git, base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    body = tmp_path / "body.md"
    body.write_text(precheck_body(root))
    out_dir = tmp_path / "o1"
    code, out, _err = run(capsys, *gate_argv(root, base, body, out_dir))
    assert code == cli.EXIT_PASS and out["verdict"] == "pass"
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["graph_commit"] == head
    assert doc["precheck_attestation"]["signature_kind"] == "none"
    assert len(doc["precheck_attestation"]["hash"]) == 64
    assert seam.made[-1]["read_only"] == [(out_dir / "tree" / NODES / TUTORIAL).resolve()]

    seam.fake = FakeToolchain(elab=ElabResult(ok=False))
    code, out, _err = run(capsys, *gate_argv(root, base, body, tmp_path / "o2"))
    assert code == cli.EXIT_FAIL and out["verdict"] == "fail"
    assert schemas.load_json(tmp_path / "o2" / "attestation.json")["verdict"] == "fail"


def test_gate_with_no_statement_at_the_commit_bounces_on_the_hash(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """A node whose Statement.lean is not in the tree at HEAD has an empty statement hash for
    the bounce rule, so the attached attestation can never match it."""
    root, git, base = git_repo(tmp_path)
    body = tmp_path / "body.md"
    body.write_text(precheck_body(root))
    (root / NODES / TUTORIAL / "Statement.lean").unlink()
    git("commit", "-q", "-am", "drop the statement")
    code, out, _err = run(capsys, *gate_argv(root, base, body, tmp_path / "o"))
    assert code == cli.EXIT_BOUNCED
    assert "different node or statement" in out["diagnostic"]["message"]


def test_gate_with_a_missing_pr_body_file_is_a_usage_error(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--pr-body-file` is read before the export and the image: a missing file is exit 2."""
    root, _git, base = git_repo(tmp_path)
    code, out, err = run(capsys, *gate_argv(root, base, tmp_path / "nope.md", tmp_path / "o"))
    assert code == cli.EXIT_ERROR and out == {} and "nope.md" in err
    assert seam.docker_verbs() == [] and not (tmp_path / "o" / "tree").exists()


# --- postmerge: step 9 on the merge commit ------------------------------------------------------


def postmerge_argv(root: Path, out: Path, *rest: str) -> list[str]:
    return [
        "postmerge", "--graph", str(root), "--commit", "HEAD", "--pr", "7", "--target", TARGET,
        "--node", TUTORIAL, "--out", str(out), *rest,
    ]  # fmt: skip


def test_postmerge_records_step9_and_exits_with_the_verdict(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F00-R14: the record carries runner hosted, the merge commit and the review block, and
    stays unsigned (signing is `sign`); a merged commit that does not pass is exit 1 with the
    record written and a line saying nothing will be attested."""
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    approval = tmp_path / "approval.md"
    approval.write_text("LGTM\n")
    out_dir = tmp_path / "o1"
    code, out, err = run(
        capsys,
        *postmerge_argv(
            root,
            out_dir,
            "--review-kind",
            "pr-approval",
            "--reviewer",
            "rev",
            "--approval-body-file",
            str(approval),
        ),
    )
    assert code == cli.EXIT_PASS and err == "" and out["verdict"] == "pass"
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["runner"] == "hosted" and doc["merge_commit"] == head
    assert doc["review"] == {"kind": "pr-approval", "reviewer": "rev", "reference": None}
    assert doc["signature"]["kind"] == "none" and schemas.violations(doc) == []

    seam.fake = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    code, out, err = run(
        capsys, *postmerge_argv(root, tmp_path / "o2", "--review-kind", "tutorial")
    )
    assert code == cli.EXIT_FAIL and out["first_failing_step"] == 5
    assert "does not pass the gate; not attesting" in err
    assert schemas.load_json(tmp_path / "o2" / "attestation.json")["verdict"] == "fail"


def test_postmerge_refuses_a_review_block_that_names_nobody(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-4 step 9 (v3.11): pr-approval without a reviewer, certificate/provenance without a
    reference — usage errors after the run, with no attestation written."""
    root, _git, _base = git_repo(tmp_path)
    for kind, missing in (
        ("pr-approval", "approving reviewer"),
        ("certificate", "needs a reference"),
        ("provenance", "needs a reference"),
    ):
        out_dir = tmp_path / kind
        code, out, err = run(capsys, *postmerge_argv(root, out_dir, "--review-kind", kind))
        assert code == cli.EXIT_ERROR and out == {} and missing in err, kind
        assert not (out_dir / "attestation.json").exists(), kind


def test_postmerge_refuses_an_unapproved_waiver_and_writes_nothing(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """F02-R9 through the command: a waived proof with no approval naming the waiver is a
    refusal — `{"verdict": "refused"}` with the diagnostic, exit 1, no verdict or attestation
    on disk. (The rule itself is test_postmerge's; here it is the wiring: what the CLI does
    with a refusal.)"""
    root, _git, _base = git_repo(tmp_path)
    seen: list[list[str]] = []

    def refuse(doc: dict[str, Any], bodies: Sequence[str]) -> Diagnostic:
        seen.append(list(bodies))
        return Diagnostic("waiver-unapproved", "no approving review names the waiver", {})

    monkeypatch.setattr(postmerge, "check_waiver", refuse)
    approval = tmp_path / "approval.md"
    approval.write_text("LGTM, nice proof\n")
    out_dir = tmp_path / "o"
    code, out, err = run(
        capsys,
        *postmerge_argv(
            root,
            out_dir,
            "--review-kind",
            "tutorial",
            "--approval-body-file",
            str(approval),
            "--approval-body-file",
            str(approval),
        ),
    )
    assert code == cli.EXIT_FAIL
    assert out["verdict"] == "refused" and out["diagnostic"]["code"] == "waiver-unapproved"
    assert "no approving review names the waiver" in err
    assert seen == [["LGTM, nice proof\n", "LGTM, nice proof\n"]]
    assert not (out_dir / "verdict.json").exists() and not (out_dir / "attestation.json").exists()


def test_postmerge_with_a_missing_approval_body_file_is_a_usage_error(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--approval-body-file` is read before the run: a missing file is exit 2, no sandbox."""
    root, _git, _base = git_repo(tmp_path)
    code, out, err = run(
        capsys,
        *postmerge_argv(
            root,
            tmp_path / "o",
            "--review-kind",
            "tutorial",
            "--approval-body-file",
            str(tmp_path / "nope.md"),
        ),
    )
    assert code == cli.EXIT_ERROR and out == {} and "nope.md" in err
    assert seam.docker_verbs() == []


# --- exhibits: the append mode's one build (F08-R6, R7) -----------------------------------------


def commit_revision_request(root: Path, git: Git, **overrides: Any) -> str:
    rel = f"{NODES}/{TUTORIAL}/revisions/20260910T000000-alice.yaml"
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    doc = samples.revision_request(**overrides)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "revision request")
    return rel


def test_exhibits_refuses_a_diff_that_is_not_an_append(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, base = git_repo(tmp_path)
    code, out, err = run(
        capsys, "exhibits", "--graph", str(root), "--base", base, "--out", str(tmp_path / "o")
    )
    assert code == cli.EXIT_ERROR and out == {}
    assert "exhibits belong to append mode; this diff is 'proof'" in err
    assert seam.made == [] and not (tmp_path / "o").exists()


def test_exhibits_elaborates_in_the_sandbox_and_names_the_one_that_fails(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """C9: ``--sandbox`` mounts only the work directory read-write (an exhibit is staged, never
    read from the tree); every exhibit passing is exit 0 with exhibits.json; one failing is exit
    1 naming its record on stderr."""
    root, git, _base = git_repo(tmp_path)
    base = git("rev-parse", "HEAD")
    rel = commit_revision_request(root, git)
    out_dir = tmp_path / "o1"
    code, out, err = run(
        capsys,
        "exhibits",
        "--graph",
        str(root),
        "--base",
        base,
        "--sandbox",
        "--out",
        str(out_dir),
        "--install",
    )
    assert code == cli.EXIT_PASS and err == ""
    assert out == {"ok": True, "exhibits": [rel], "sandboxed": True, "problems": []}
    assert json.loads((out_dir / "exhibits.json").read_text()) == out
    assert seam.made[-1]["read_only"] == [] and seam.made[-1]["read_write"] == [
        (out_dir / "work").resolve()
    ]
    assert seam.fake.calls[0] == f"resolve:{PIN}:install=False"  # never installs in the sandbox
    assert f"elaborate:{EXHIBIT0}" in seam.fake.calls

    seam.fake = ScriptedToolchain(failing_modules={EXHIBIT0})
    code, out, err = run(
        capsys,
        "exhibits",
        "--graph",
        str(root),
        "--base",
        base,
        "--sandbox",
        "--out",
        str(tmp_path / "o2"),
    )
    assert code == cli.EXIT_FAIL and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["exhibit-elaboration"]
    assert rel in out["problems"][0]["message"] and "exhibit-elaboration" in err


def test_exhibits_without_the_sandbox_uses_the_local_toolchain_or_refuses(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    base = git("rev-parse", "HEAD")
    commit_revision_request(root, git)
    local = FakeToolchain()
    monkeypatch.setattr(
        toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: local)
    )
    code, out, _err = run(
        capsys,
        "exhibits",
        "--graph",
        str(root),
        "--base",
        base,
        "--out",
        str(tmp_path / "o1"),
        "--install",
    )
    assert code == cli.EXIT_PASS and out["sandboxed"] is False
    assert local.calls[0] == f"resolve:{PIN}:install=True" and seam.made == []

    def missing(_cls: object, _settings: object) -> FakeToolchain:
        raise ToolchainMissingError(f"elan not found; run {toolchain.INSTALL_SCRIPT}")

    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(missing))
    code, out, err = run(
        capsys, "exhibits", "--graph", str(root), "--base", base, "--out", str(tmp_path / "o2")
    )
    assert code == cli.EXIT_ERROR and out == {} and toolchain.INSTALL_SCRIPT in err

    (root / "targets" / TARGET / "gate-spec.json").write_text("{not json")
    code, out, err = run(
        capsys, "exhibits", "--graph", str(root), "--base", base, "--out", str(tmp_path / "o3")
    )
    assert code == cli.EXIT_ERROR and out == {} and "cannot load" in err and "gate-spec.json" in err


# --- admit: the mechanical admission check through the command (F08-R1, R2) --------------------


def place_proposal(graph: Path, case: str) -> Path:
    dest = graph / NODES / case
    shutil.copytree(FIXTURES / "proposals" / case, dest)
    return dest


def test_admit_reports_the_first_failing_check_and_carries_the_data_it_gathered(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 names the check on stderr; the summary carries whatever the checks recorded
    (hazards, axioms, witness) so a proposer can read what passed before the failure."""
    graph = copy_graph(tmp_path)
    node_dir = place_proposal(graph, "good")
    out_dir = tmp_path / "o1"
    code, out, err = run(capsys, "admit", str(node_dir), "--sandbox", "--out", str(out_dir))
    assert code == cli.EXIT_PASS and err == ""
    assert out["verdict"] == "pass" and out["sandboxed"] is True and out["node"] == "good"
    assert {"hazards", "statement_axioms", "witness"} <= set(out)
    assert json.loads((out_dir / "admission.json").read_text()) == out
    assert seam.made[-1]["read_only"] == [node_dir.resolve()]

    seam.fake = FakeToolchain(elab=ElabResult(ok=False))
    code, out, err = run(capsys, "admit", str(node_dir), "--sandbox", "--out", str(tmp_path / "o2"))
    assert code == cli.EXIT_FAIL and out["verdict"] == "fail"
    assert out["first_failing_check"] is not None
    assert f"admission failed at {out['first_failing_check']}:" in err
    assert "hazards" not in out  # nothing past the failure was gathered


def test_admit_refuses_before_building_when_the_spec_or_toolchain_is_missing(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    graph = copy_graph(tmp_path)
    node_dir = place_proposal(graph, "good")
    seam.set_image_present(False)
    code, out, err = run(
        capsys, "admit", str(node_dir), "--sandbox", "--no-build", "--out", str(tmp_path / "o1")
    )
    assert code == cli.EXIT_ERROR and out == {} and "is not present" in err
    assert not (tmp_path / "o1" / "admission.json").exists()

    def missing(_cls: object, _settings: object) -> FakeToolchain:
        raise ToolchainMissingError(f"elan not found; run {toolchain.INSTALL_SCRIPT}")

    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(missing))
    code, out, err = run(capsys, "admit", str(node_dir), "--out", str(tmp_path / "o2"))
    assert code == cli.EXIT_ERROR and out == {} and toolchain.INSTALL_SCRIPT in err

    (graph / "targets" / TARGET / "gate-spec.json").write_text('{"schema": "gate-spec/v1"}')
    code, out, err = run(capsys, "admit", str(node_dir), "--out", str(tmp_path / "o3"))
    assert code == cli.EXIT_ERROR and out == {} and "cannot load" in err
    assert seam.made == []


# --- ledger: the statement line after a proposal merges (F08-R13) --------------------------------


def commit_proposal(root: Path, git: Git, node_id: str, **kw: Any) -> str:
    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=TARGET,
        statement=STATEMENT,
        witness=WITNESS,
        author="alice",
        **kw,
    )
    scaffold.write(root / NODES, proposal)
    git(
        "add", "--", f"{NODES}/{node_id}"
    )  # the node alone: a ledger a previous run wrote stays out
    git("commit", "-q", "-m", f"propose {node_id}")
    return git("rev-parse", "HEAD")


def test_ledger_earns_nothing_for_a_proof_or_a_hole_and_says_why(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path, author="alice")
    head = git("rev-parse", "HEAD")
    code, out, _err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == cli.EXIT_PASS
    assert out == {
        "earned": False,
        "commit": head,
        "reason": "not a merged node proposal (mode 'proof')",
    }

    hole = commit_proposal(root, git, "spec-hole", origin="compiler-derived")
    code, out, _err = run(capsys, "ledger", "--graph", str(root), "--commit", hole)
    assert code == cli.EXIT_PASS and out["earned"] is False
    assert out["reason"] == "spec-hole (compiler-derived) earns no statement line (D-19, D-31)"
    assert not (root / "ledger").exists()


def test_ledger_writes_the_proposers_statement_line_from_the_merge(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The identity is the pull request's commit author — the second parent of a merge commit,
    the commit's own author otherwise — and the line names the merge commit."""
    root, git, _base = git_repo(tmp_path, author="alice")
    head = commit_proposal(root, git, "spec-one")
    code, out, _err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == cli.EXIT_PASS
    assert out["earned"] is True and out["identity"] == "alice" and out["node"] == "spec-one"
    assert out["line"] == "statement" and out["written"] == "ledger/alice.json"
    doc = schemas.load_json(root / "ledger" / "alice.json", "ledger/v1")
    assert doc["entries"][0]["merge_commit"] == head
    assert doc["entries"][0]["artifact"] == "Statement.lean"

    # A merge commit: the proposal on a branch by alice, merged by the bot as the first parent.
    git("checkout", "-q", "-b", "proposal")
    tip = commit_proposal(root, git, "spec-two")
    git("checkout", "-q", "-")
    git(
        "-c",
        "user.name=bot",
        "-c",
        "user.email=b@x",
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge #9",
        "proposal",
    )
    merge = git("rev-parse", "HEAD")
    assert git("rev-parse", f"{merge}^2") == tip
    code, out, _err = run(capsys, "ledger", "--graph", str(root), "--commit", merge)
    assert code == cli.EXIT_PASS and out.get("earned") is True, out
    assert out["identity"] == "alice" and out["node"] == "spec-two"
    assert [e["node"] for e in schemas.load_json(root / "ledger" / "alice.json")["entries"]] == [
        "spec-one",
        "spec-two",
    ]


def test_ledger_refuses_an_identity_that_cannot_hold_a_ledger(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """A commit author that is not a pseudonym (ledger/v1's pattern) earns nothing rather than
    a file named after it; the reason names the identity."""
    root, git, _base = git_repo(tmp_path, author="Not A Pseudonym!")
    head = commit_proposal(root, git, "spec-three")
    code, out, _err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == cli.EXIT_PASS and out["earned"] is False
    assert "'Not A Pseudonym!' cannot hold a ledger" in out["reason"]
    assert not (root / "ledger").exists()


# --- products on a Mathlib pin, and the module entry point ----------------------------------------


def test_products_scans_a_mathlib_pinned_graph_inside_the_sandbox(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R6, F03-R6 (C9): on a Mathlib-pinned target the library-tag scan runs inside the
    step-3 image built for that Mathlib — chosen from the spec, with the target directory
    mounted read-only — and nobody has to ask for it; the frontier carries the tags it found."""
    root, git, _base = git_repo(tmp_path)
    spec_path = root / "targets" / TARGET / "gate-spec.json"
    spec = schemas.load_json(spec_path)
    spec["mathlib_sha"] = samples.SHA1
    spec_path.write_bytes(schemas.canonical_json(spec))
    git("commit", "-q", "-am", "pin mathlib")
    seam.fake.constants = used_constants_result(
        [("Nat.Prime", "Mathlib.Data.Nat.Prime.Basic"), ("le_refl", "Mathlib.Order.Basic")]
    )
    code, out, err = run(capsys, "products", "--graph", str(root), "--out", str(tmp_path / "o"))
    assert code == cli.EXIT_PASS, err
    assert out["ok"] is True
    made = seam.made[-1]
    assert made["image"] == sandbox.image_tag(PIN, samples.SHA1)
    assert made["read_only"] == [(root / "targets" / TARGET).resolve()]
    assert f"resolve:{PIN}:install=False:mathlib={samples.SHA1[:12]}" in seam.fake.calls
    assert any(c.startswith("used_constants:") for c in seam.fake.calls)
    frontier = json.loads((tmp_path / "o" / "frontier.json").read_text())
    assert {tuple(e["tags"]["library"]) for e in frontier["entries"]} == {("Data", "Order")}
    # A graph with no Mathlib pin builds no sandbox at all: the tutorial's job is untouched.
    seam.made.clear()
    spec["mathlib_sha"] = None
    spec_path.write_bytes(schemas.canonical_json(spec))
    git("commit", "-q", "-am", "unpin")
    code, out, _err = run(capsys, "products", "--graph", str(root), "--out", str(tmp_path / "p"))
    assert code == cli.EXIT_PASS and seam.made == []


def test_module_entry_point_exits_2_on_usage() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "opn_gate.cli"],
        cwd=cli.GATE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2 and "usage: opn-gate" in proc.stderr
