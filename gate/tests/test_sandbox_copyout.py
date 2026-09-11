"""F00-R12 (step 3), the copy seams in the fast tier: what goes into the container (owners and
modes per mount kind, parents first), what comes back out of `docker cp` as a tar stream — a
member that escapes the destination, an absolute name, a symlink pointing outside, a truncated
or empty stream — and the host-side wall-clock guard that kills a container `docker start`
never returned from. No container runs: `_docker` is overridden, or docker is a script."""

from __future__ import annotations

import io
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import pytest
from test_sandbox import fake_docker, log_of

from opn_gate import sandbox
from opn_gate.sandbox import CONTAINER_UID, Caps, SandboxToolchain

CAPS = Caps(cpu=1.0, memory_mib=512, wallclock_s=20)


class Recording(SandboxToolchain):
    """`_docker` replaced: every call is recorded, `cp -` in captures the stream, `cp ... -`
    out answers with `stream`. Nothing is executed."""

    def __init__(self, *args: Any, stream: bytes = b"", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stream = stream
        self.calls: list[list[str]] = []
        self.copied_in: bytes | None = None

    def _docker(self, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append(list(args))
        if args[0] == "cp" and args[1] == "-":
            self.copied_in = kwargs["input"]
        if args[0] == "cp" and args[-1] == "-":
            return subprocess.CompletedProcess(list(args), 0, self.stream, b"")
        return subprocess.CompletedProcess(list(args), 0, b"", b"")


def stream(*members: tuple[str, bytes | None, dict[str, Any]]) -> bytes:
    """A tar stream as `docker cp <name>:<dir> -` would emit: (name, data-or-None, extra)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data, extra in members:
            info = tarfile.TarInfo(name)
            for key, value in extra.items():
                setattr(info, key, value)
            if data is None:
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


# --- copy in ------------------------------------------------------------------------------------


def test_copy_in_ships_read_only_trees_as_root_and_writable_ones_as_the_sandbox_user(
    tmp_path: Path,
) -> None:
    """R12: the node goes in owned by root (0644/0755, so the sandbox user cannot alter it), the
    work directory owned by the sandbox user, both at their host paths with the parents first
    so `docker cp` can create them; a writable directory that does not exist yet is created."""
    node = tmp_path / "graph" / "nodes" / "n"
    (node / "annex").mkdir(parents=True)
    (node / "Statement.lean").write_text("theorem t : True := sorry\n")
    (node / "Statement.lean").chmod(0o600)
    work = tmp_path / "out" / "work"
    tc = Recording("opn-gate:test", CAPS, read_only=[node], read_write=[work])
    tc._copy_in("c1")
    assert tc.calls == [["cp", "-", "c1:/"]] and work.is_dir()
    assert tc.copied_in is not None
    with tarfile.open(fileobj=io.BytesIO(tc.copied_in)) as tar:
        members = tar.getmembers()
    names = [m.name for m in members]
    assert not any(n.startswith("/") for n in names)
    node_arc = str(node.resolve()).lstrip("/")
    work_arc = str(work.resolve()).lstrip("/")
    # Parents precede the tree they hold, and none of them is the root itself.
    assert names.index(node_arc.rsplit("/", 1)[0]) < names.index(node_arc)
    assert names.index(work_arc.rsplit("/", 1)[0]) < names.index(work_arc)
    assert "" not in names
    by_name = {m.name: m for m in members}
    statement = by_name[f"{node_arc}/Statement.lean"]
    assert (statement.uid, statement.gid, statement.mode) == (0, 0, 0o644)
    assert (by_name[node_arc].mode, by_name[f"{node_arc}/annex"].uid) == (0o755, 0)
    assert (by_name[work_arc].uid, by_name[work_arc].gid) == (CONTAINER_UID, CONTAINER_UID)
    assert statement.uname == "" and statement.gname == ""  # no host account name leaks in


# --- copy out -----------------------------------------------------------------------------------


def test_copy_out_lands_the_container_tree_under_the_host_parent(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "stale.txt").write_text("before")
    tar_bytes = stream(
        ("work", None, {"type": tarfile.DIRTYPE, "mode": 0o755}),
        ("work/stale.txt", b"after", {"mode": 0o644}),
        ("work/build/Proof.olean", b"olean", {"mode": 0o644}),
    )
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=tar_bytes)
    tc._copy_out("c1")
    assert tc.calls == [["cp", f"c1:{work.resolve()}", "-"]]
    assert (work / "stale.txt").read_text() == "after"
    assert (work / "build" / "Proof.olean").read_bytes() == b"olean"


def test_copy_out_drops_members_with_absolute_names(tmp_path: Path) -> None:
    """A member named from `/` is never extracted, wherever it would land."""
    work = tmp_path / "work"
    tar_bytes = stream(
        ("/etc/evil", b"x", {"mode": 0o644}),
        (
            f"{work.resolve()}/evil".lstrip("/"),
            b"y",
            {"mode": 0o644},
        ),  # relative form of the same dir
        ("work/ok.txt", b"ok", {"mode": 0o644}),
    )
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=tar_bytes)
    tc._copy_out("c1")
    assert (work / "ok.txt").read_text() == "ok"
    assert not (tmp_path / "etc").exists() and not (work / "evil").exists()
    assert not (tmp_path / "work" / "evil").exists()


def test_copy_out_refuses_a_member_escaping_the_destination(tmp_path: Path) -> None:
    """`..` in a member name is refused by the data filter before anything is written; the
    file it aimed at does not appear."""
    work = tmp_path / "work"
    tar_bytes = stream(("../escape.txt", b"x", {"mode": 0o644}))
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=tar_bytes)
    with pytest.raises(tarfile.OutsideDestinationError):
        tc._copy_out("c1")
    assert not (tmp_path.parent / "escape.txt").exists()
    assert not (tmp_path / "escape.txt").exists()


def test_copy_out_refuses_symlinks_that_point_outside(tmp_path: Path) -> None:
    work = tmp_path / "work"
    absolute = stream(("work/passwd", None, {"type": tarfile.SYMTYPE, "linkname": "/etc/passwd"}))
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=absolute)
    with pytest.raises(tarfile.AbsoluteLinkError):
        tc._copy_out("c1")
    assert not (work / "passwd").exists()

    relative = stream(("work/up", None, {"type": tarfile.SYMTYPE, "linkname": "../../../outside"}))
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=relative)
    with pytest.raises(tarfile.LinkOutsideDestinationError):
        tc._copy_out("c1")
    assert not (work / "up").is_symlink()


def test_copy_out_strips_setuid_and_world_writable_bits(tmp_path: Path) -> None:
    work = tmp_path / "work"
    tar_bytes = stream(("work/tool", b"#!/bin/sh\n", {"mode": 0o4777}))
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=tar_bytes)
    tc._copy_out("c1")
    mode = (work / "tool").stat().st_mode & 0o7777
    assert not mode & 0o4000 and not mode & 0o002


@pytest.mark.parametrize("cut", [0, 300, 700])
def test_a_truncated_or_empty_copy_out_stream_is_a_sandbox_error(tmp_path: Path, cut: int) -> None:
    """F08-Q18: a `docker cp` stream that is empty or cut short is docker failing, and it is
    reported as a SandboxError naming the directory, not as a tar parser's ReadError."""
    work = tmp_path / "work"
    whole = stream(("work/out.txt", b"x" * 400, {"mode": 0o644}))
    tc = Recording("opn-gate:test", CAPS, read_write=[work], stream=whole[:cut])
    with pytest.raises(sandbox.SandboxError, match=r"docker cp of .*work"):
        tc._copy_out("c1")
    assert not (work / "out.txt").exists()


# --- the host-side guard and the build --------------------------------------------------------


def test_a_container_that_never_returns_is_killed_and_the_timeout_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R12: `docker start --attach` is bounded by the cap plus the grace; past it the container
    is killed, removed, and the TimeoutExpired reaches the step like an in-container kill."""
    docker = fake_docker(tmp_path)
    real_run = subprocess.run

    def hanging(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        if cmd[:2] == [str(docker), "start"]:
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout") or 0)
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", hanging)
    tc = SandboxToolchain("opn-gate:test", CAPS, docker=str(docker))
    with pytest.raises(subprocess.TimeoutExpired) as info:
        tc._exec(["lean", "Loop.lean"], timeout_s=3)
    assert info.value.timeout == 3 + sandbox.GRACE_S
    verbs = [line.split()[0] for line in log_of(tmp_path)]
    assert verbs == ["create", "cp", "kill", "rm"]  # no inspect, no copy out
    name = log_of(tmp_path)[0].split()[2]
    assert log_of(tmp_path)[-2] == f"kill {name}" and log_of(tmp_path)[-1] == f"rm -f {name}"


def test_build_image_returns_the_tag_for_the_pin(tmp_path: Path) -> None:
    docker = fake_docker(tmp_path)
    tag = sandbox.build_image(tmp_path / "gate", "leanprover/lean4:v4.33.1", docker=str(docker))
    assert tag == "opn-gate:leanprover-lean4-v4.33.1"
    build = log_of(tmp_path)[0]
    assert build.startswith("build --quiet -f") and f"-t {tag} {tmp_path / 'gate'}" in build
    assert "--build-arg LEAN_TOOLCHAIN=leanprover/lean4:v4.33.1" in build
