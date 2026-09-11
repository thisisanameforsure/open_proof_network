"""F10-T3 / AC10, R6, R10: the post-create command runs inside the gate image and pregate.sh
then passes on the tutorial node without building anything. Docker tier.

The image is the one gate/Dockerfile builds (the published digest is the same bytes built at
a tag; until Mike pushes the first tag no digest exists, F10-Q11). No bind mounts, as in the
sandbox: the fixture graph is copied in, the container runs as uid 1000 with no network — the
devcontainer's own conditions minus the editor.
"""

from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path

import pytest
from harness import GRAPH, TUTORIAL

pytestmark = pytest.mark.docker

GRAPH_IN_CONTAINER = "/home/opn/graph"
SCRIPT = (
    "set -euo pipefail\n"
    f"export GRAPH={GRAPH_IN_CONTAINER} NETWORK=/opt/opn/network\n"
    'echo "== post-create"; time bash "$NETWORK/gate/devcontainer/post-create.sh"\n'
    'echo "== pregate"; time "$NETWORK/gate/pregate.sh" --graph "$GRAPH" '
    f"--node {TUTORIAL} --no-diff --out /tmp/pregate\n"
)


def docker(*args: str, input: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["docker", *args], capture_output=True, check=False, input=input)


def test_postcreate_then_pregate(sandbox_image: str, tmp_path: Path) -> None:
    """AC10: post-create proves the toolchain, metaprograms and gate are present; pregate.sh
    passes the committed tutorial proof; neither builds the toolchain. The wall time from
    container start to the pass is recorded for R10's cold series."""
    name = f"opn-devcontainer-{uuid.uuid4().hex[:12]}"
    created = docker(
        "create",
        "--name",
        name,
        "--network",
        "none",
        "--user",
        "1000:1000",
        "--env",
        "HOME=/home/opn",
        sandbox_image,
        "bash",
        "-c",
        SCRIPT,
    )
    assert created.returncode == 0, created.stderr.decode()
    try:
        # The graph, copied in as a tar so the files are owned by the container's user.
        import io  # noqa: PLC0415
        import tarfile  # noqa: PLC0415

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:

            def owned(info: tarfile.TarInfo) -> tarfile.TarInfo:
                info.uid = info.gid = 1000
                info.uname = info.gname = "opn"
                return info

            tar.add(str(GRAPH), arcname="graph", filter=owned)
        copied = docker("cp", "-", f"{name}:/home/opn", input=buf.getvalue())
        assert copied.returncode == 0, copied.stderr.decode()
        started = time.monotonic()
        run = docker("start", "--attach", name)
        elapsed = time.monotonic() - started
        out, err = run.stdout.decode(errors="replace"), run.stderr.decode(errors="replace")
        (tmp_path / "devcontainer.log").write_text(out + "\n--- stderr ---\n" + err)
        print(out)
        print(err)
        assert run.returncode == 0, (out[-3000:], err[-3000:])
    finally:
        docker("rm", "-f", name)
    assert "post-create: metaprograms present" in out
    assert "post-create: opn-gate runs (Python 3.13" in out
    assert "names no olean cache (olean_cache_url null); nothing to fetch" in out
    assert "post-create: done" in out
    assert '"verdict": "pass"' in out
    assert "elan toolchain install" not in out + err and "lake build" not in out + err
    print(f"R10 cold: container start to pregate pass in {elapsed:.1f}s (image {sandbox_image})")
    assert elapsed < 180  # §6: under three minutes cold, on the tutorial graph
