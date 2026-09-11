"""The step-3 sandbox (D-4 step 3; F00-R12): the same Toolchain seam, every call in a container.

``SandboxToolchain`` is ``LocalToolchain`` with one difference: each process runs inside the
image built from ``gate/Dockerfile`` with no network, no environment beyond what is set here, a
non-root user, and the cpu / memory / wall-clock caps the graph's ``gate-spec.json`` declares
(C6). No tmpfs is mounted at ``/tmp``: host work directories may live under ``/tmp`` (pytest
on Linux does that) and a mount there would hide the files copied in. Nothing is bind-mounted:
the directories a call needs are copied into a fresh container at their host paths (read-only
ones owned by root, writable ones by the sandbox user), the process runs, the writable ones are
copied back, and the container is removed. That keeps the sandbox independent of host
file-sharing and of uid mismatches on hosted runners.
"""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

CONTAINER_ELAN = Path("/opt/elan/bin/elan")
CONTAINER_LEAN_PKG_BIN = Path("/opt/opn/lean/.lake/build/bin")
CONTAINER_UID = 1000
GRACE_S = 30.0  # host-side slack beyond the in-container `timeout`
_KILLED_BY_TIMEOUT = (124, 137)


class SandboxError(RuntimeError):
    """docker itself failed (not the process inside it)."""


@dataclass(frozen=True)
class Caps:
    cpu: float
    memory_mib: int
    wallclock_s: int

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> Caps:
        caps = spec["step3_caps"]
        return cls(
            cpu=float(caps["cpu"]),
            memory_mib=int(caps["memory_mib"]),
            wallclock_s=int(caps["wallclock_s"]),
        )


def image_tag(lean_toolchain: str) -> str:
    """A docker tag for the toolchain, e.g. ``opn-gate:leanprover-lean4-v4.33.1``."""
    return "opn-gate:" + re.sub(r"[^A-Za-z0-9_.-]+", "-", lean_toolchain)


def build_image(gate_dir: Path, lean_toolchain: str, *, docker: str = "docker") -> str:
    """``docker build`` the sandbox image for ``lean_toolchain``; returns the tag."""
    tag = image_tag(lean_toolchain)
    cmd = [
        docker,
        "build",
        "--quiet",
        "-f",
        str(gate_dir / "Dockerfile"),
        "--build-arg",
        f"LEAN_TOOLCHAIN={lean_toolchain}",
        "-t",
        tag,
        str(gate_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        msg = f"docker build failed: {proc.stderr.strip()[-2000:]}"
        raise SandboxError(msg)
    return tag


def image_exists(tag: str, *, docker: str = "docker") -> bool:
    proc = subprocess.run([docker, "image", "inspect", tag], capture_output=True, check=False)
    return proc.returncode == 0


class SandboxToolchain(LocalToolchain):
    """The seam inside the container. ``resolve`` never installs: the image holds the pin."""

    def __init__(
        self,
        image: str,
        caps: Caps,
        *,
        read_only: Sequence[Path] = (),
        read_write: Sequence[Path] = (),
        docker: str = "docker",
    ) -> None:
        super().__init__(CONTAINER_ELAN, CONTAINER_LEAN_PKG_BIN)
        self.image = image
        self.caps = caps
        self.read_only = [p.resolve() for p in read_only]
        self.read_write = [p.resolve() for p in read_write]
        self.docker = docker

    # -- container assembly -------------------------------------------------------------------

    def create_args(
        self, name: str, *, cwd: Path | None, extra_env: dict[str, str] | None, wall: float
    ) -> list[str]:
        args = [
            self.docker,
            "create",
            "--name",
            name,
            "--network",
            "none",
            "--user",
            f"{CONTAINER_UID}:{CONTAINER_UID}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "512",
            "--cpus",
            f"{self.caps.cpu:g}",
            "--memory",
            f"{self.caps.memory_mib}m",
            "--memory-swap",
            f"{self.caps.memory_mib}m",
            "--env",
            "ELAN_HOME=/opt/elan",
            "--env",
            "HOME=/tmp",
        ]
        for key, value in (extra_env or {}).items():
            args += ["--env", f"{key}={value}"]
        if cwd is not None:
            args += ["--workdir", str(cwd.resolve())]
        args += [self.image, "timeout", "-s", "KILL", f"{int(wall)}"]
        return args

    def _docker(self, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        proc = subprocess.run([self.docker, *args], capture_output=True, check=False, **kwargs)
        if proc.returncode != 0:
            msg = f"docker {args[0]} failed: {proc.stderr.decode(errors='replace').strip()[-2000:]}"
            raise SandboxError(msg)
        return proc

    def _copy_in(self, name: str) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for root in self.read_only:
                _add_tree(tar, root, uid=0)
            for root in self.read_write:
                root.mkdir(parents=True, exist_ok=True)
                _add_tree(tar, root, uid=CONTAINER_UID)
        self._docker("cp", "-", f"{name}:/", input=buf.getvalue())

    def _copy_out(self, name: str) -> None:
        for root in self.read_write:
            proc = self._docker("cp", f"{name}:{root}", "-")
            if not proc.stdout:
                msg = f"docker cp of {root} returned an empty stream"
                raise SandboxError(msg)
            # A stream that does not parse is docker failing, not the container's output; the
            # data filter's own refusals (a member escaping the destination) are not ReadErrors
            # and pass through as themselves.
            try:
                with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r") as tar:
                    members = [m for m in tar.getmembers() if not m.name.startswith("/")]
                    tar.extractall(root.parent, members=members, filter="data")
            except tarfile.ReadError as exc:
                msg = f"docker cp of {root} returned a stream that is not a tar archive: {exc}"
                raise SandboxError(msg) from exc

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        wall = timeout_s if timeout_s is not None else float(self.caps.wallclock_s)
        name = f"opn-gate-{uuid.uuid4().hex[:12]}"
        self._docker(*self.create_args(name, cwd=cwd, extra_env=extra_env, wall=wall)[1:], *cmd)
        try:
            self._copy_in(name)
            try:
                run = subprocess.run(
                    [self.docker, "start", "--attach", name],
                    capture_output=True,
                    text=True,
                    timeout=wall + GRACE_S,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                subprocess.run([self.docker, "kill", name], capture_output=True, check=False)
                raise
            code = self._exit_code(name)
            if code in _KILLED_BY_TIMEOUT:
                raise subprocess.TimeoutExpired(list(cmd), wall, run.stdout, run.stderr)
            self._copy_out(name)
        finally:
            subprocess.run([self.docker, "rm", "-f", name], capture_output=True, check=False)
        return subprocess.CompletedProcess(list(cmd), code, run.stdout, run.stderr)

    def _exit_code(self, name: str) -> int:
        proc = self._docker("inspect", "-f", "{{.State.ExitCode}}", name)
        return int(proc.stdout.decode().strip() or "1")

    def resolve(self, toolchain: str, *, install: bool = False) -> ResolvedToolchain:
        return super().resolve(toolchain, install=False)

    def metaprogram(self, name: str) -> Path:
        """The image carries the built package (F01-R10); nothing is checked on the host side."""
        return self.lean_pkg_bin / name

    def ensure_metaprograms(self, tc: ResolvedToolchain) -> None:
        return None


def _add_tree(tar: tarfile.TarFile, root: Path, *, uid: int) -> None:
    """Add ``root`` and everything under it with absolute names (leading slash stripped)."""

    def owned(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = info.gid = uid
        info.uname = info.gname = ""
        info.mode = 0o755 if info.isdir() else 0o644
        return info

    # Parent directories first so docker cp can create the path.
    for parent in reversed(root.parents):
        if parent == Path("/"):
            continue
        info = tarfile.TarInfo(str(parent).lstrip("/"))
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tar.addfile(info)
    tar.add(str(root), arcname=str(root).lstrip("/"), recursive=True, filter=owned)
