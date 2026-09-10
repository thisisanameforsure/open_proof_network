"""F00-R12 (step 3) in the fast tier: the container is assembled with no network, no secrets,
a non-root user and the spec's caps, and docker's own failures surface as errors — over a
scripted `docker` binary, never the real one (the docker tier drives that)."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import pytest
import samples
from fakes import FAKE_RESOLVED

from opn_gate import sandbox
from opn_gate.sandbox import Caps, SandboxToolchain
from opn_gate.toolchain import ToolchainMissingError

CAPS = Caps(cpu=1.5, memory_mib=1024, wallclock_s=30)


def fake_docker(tmp_path: Path, *, inspect_exit: int = 0, fail_on: str = "") -> Path:
    """A `docker` that logs every invocation and answers `inspect` with a chosen exit code."""
    script = tmp_path / "docker"
    log = tmp_path / "docker.log"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        f'if [ -n "{fail_on}" ] && [ "$1" = "{fail_on}" ]; then\n'
        '  echo "simulated failure" >&2; exit 1\n'
        "fi\n"
        'case "$1" in\n'
        f"  inspect) echo {inspect_exit} ;;\n"
        '  cp) [ "$2" = "-" ] && cat > /dev/null ;;\n'
        "esac\n"
        "exit 0\n"
    )
    script.chmod(0o755)
    return script


def log_of(tmp_path: Path) -> list[str]:
    return (tmp_path / "docker.log").read_text().splitlines()


def test_caps_and_tag_come_from_the_spec() -> None:
    caps = Caps.from_spec(
        samples.gate_spec(step3_caps={"cpu": "2", "memory_mib": "4096", "wallclock_s": "600"})
    )
    assert caps == Caps(cpu=2.0, memory_mib=4096, wallclock_s=600)
    assert sandbox.image_tag("leanprover/lean4:v4.33.1") == "opn-gate:leanprover-lean4-v4.33.1"


def test_container_is_isolated_and_carries_no_host_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R12, C8: no network, non-root, capabilities dropped, the spec's caps, and only the two
    environment variables the image needs plus what the call passes — a secret in the host
    environment never reaches the container."""
    monkeypatch.setenv("OPN_GATE_SIGNING_KEY", "SUPERSECRET")
    tc = SandboxToolchain("opn-gate:test", CAPS)
    args = tc.create_args("c1", cwd=Path("/work"), extra_env={"LEAN_PATH": "/a:/b"}, wall=12.0)
    joined = " ".join(args)
    for flag in (
        "--network none",
        f"--user {sandbox.CONTAINER_UID}:{sandbox.CONTAINER_UID}",
        "--cap-drop ALL",
        "--security-opt no-new-privileges",
        "--cpus 1.5",
        "--memory 1024m",
        "--memory-swap 1024m",
        "--workdir /work",
        "opn-gate:test timeout -s KILL 12",
    ):
        assert flag in joined, flag
    envs = [args[i + 1] for i, a in enumerate(args) if a == "--env"]
    assert envs == ["ELAN_HOME=/opt/elan", "HOME=/tmp", "LEAN_PATH=/a:/b"]
    assert "SUPERSECRET" not in joined
    assert os.environ["OPN_GATE_SIGNING_KEY"] == "SUPERSECRET"  # it was there to leak


def test_exec_runs_in_a_fresh_container_and_removes_it(tmp_path: Path) -> None:
    docker = fake_docker(tmp_path, inspect_exit=3)
    tc = SandboxToolchain("opn-gate:test", CAPS, docker=str(docker))
    proc = tc._exec(["lean", "--version"], cwd=tmp_path)
    assert proc.returncode == 3  # the process's exit code, read back from the container
    log = log_of(tmp_path)
    assert log[0].startswith("create --name opn-gate-") and "--network none" in log[0]
    assert log[0].endswith(f"timeout -s KILL {CAPS.wallclock_s} lean --version")
    assert [line.split()[0] for line in log] == ["create", "cp", "start", "inspect", "rm"]
    assert log[-1].startswith("rm -f opn-gate-")


def test_killed_by_the_cap_is_a_timeout(tmp_path: Path) -> None:
    """R12: `timeout -s KILL` inside the container (124/137) becomes the TimeoutExpired every
    step turns into its `timeout` diagnostic; the container is still removed."""
    for code in sandbox._KILLED_BY_TIMEOUT:
        docker = fake_docker(tmp_path, inspect_exit=code)
        tc = SandboxToolchain("opn-gate:test", CAPS, docker=str(docker))
        with pytest.raises(subprocess.TimeoutExpired) as info:
            tc._exec(["lean", "Loop.lean"], timeout_s=7)
        assert info.value.timeout == 7
        assert log_of(tmp_path)[-1].startswith("rm -f")
        (tmp_path / "docker.log").unlink()


def test_docker_failure_is_a_sandbox_error_not_a_verdict(tmp_path: Path) -> None:
    docker = fake_docker(tmp_path, fail_on="create")
    tc = SandboxToolchain("opn-gate:test", CAPS, docker=str(docker))
    with pytest.raises(sandbox.SandboxError, match="docker create failed: simulated failure"):
        tc._exec(["lean", "--version"])
    with pytest.raises(sandbox.SandboxError, match="docker build failed"):
        sandbox.build_image(
            tmp_path, "leanprover/lean4:v4.33.1", docker=str(fake_docker(tmp_path, fail_on="build"))
        )
    assert (
        sandbox.image_exists("opn-gate:nope", docker=str(fake_docker(tmp_path, fail_on="image")))
        is False
    )
    assert sandbox.image_exists("opn-gate:yes", docker=str(fake_docker(tmp_path))) is True


def test_sandbox_never_installs_a_toolchain(tmp_path: Path) -> None:
    """The image holds the pin (D-4 step 1): `install=True` is ignored and an absent toolchain
    is reported, never fetched — there is no network to fetch it over anyway."""

    class Recording(SandboxToolchain):
        calls: ClassVar[list[list[str]]] = []

        def _exec(
            self,
            cmd: Sequence[str],
            *,
            cwd: Path | None = None,
            extra_env: dict[str, str] | None = None,
            timeout_s: float | None = None,
        ) -> subprocess.CompletedProcess[str]:
            self.calls.append(list(cmd))
            return subprocess.CompletedProcess(list(cmd), 0, "leanprover/lean4:v4.0.0\n", "")

    tc = Recording("opn-gate:test", CAPS)
    with pytest.raises(ToolchainMissingError, match="not installed"):
        tc.resolve("leanprover/lean4:v4.33.1", install=True)
    assert tc.calls == [[str(sandbox.CONTAINER_ELAN), "toolchain", "list"]]
    assert tc.metaprogram("opn-hazards") == sandbox.CONTAINER_LEAN_PKG_BIN / "opn-hazards"
    tc.ensure_metaprograms(FAKE_RESOLVED)  # a no-op: nothing is built on the host side
    assert tc.calls == [[str(sandbox.CONTAINER_ELAN), "toolchain", "list"]]
