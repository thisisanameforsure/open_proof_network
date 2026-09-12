"""F11-T3 / AC11, R6: the per-graph Mathlib image (docker tier).

Given the image built for the on-ramp graph's Mathlib pin, when the gate runs on an on-ramp node
inside it, then step 1 reports the pin resolved from the image — no ``lake exe cache get``, no
build, nothing fetched — and the run stays under §6's budget. Also the devcontainer's own
post-create inside that image, which must find the checkout at the sha the spec names.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

import pytest
from conftest import ONRAMP, ONRAMP_MATHLIB, ONRAMP_TARGET

from opn_gate import attestation, cli, schemas

pytestmark = pytest.mark.docker

PROVED = "fact-pos"
GRAPH_IN_CONTAINER = "/home/opn/graph"


def test_mathlib_image_hit(
    onramp_graph_repo: tuple[Path, str],
    mathlib_image: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC11: reproduce the proved node through the sandbox on the Mathlib image."""
    graph, commit = onramp_graph_repo
    started = time.monotonic()
    code = cli.main(
        [
            "reproduce",
            "--graph",
            str(graph),
            "--commit",
            commit,
            "--node",
            PROVED,
            "--image",
            mathlib_image,
            "--out",
            str(tmp_path / "a"),
            "--no-build",
        ]
    )
    elapsed = time.monotonic() - started
    captured = capsys.readouterr()
    assert code == cli.EXIT_PASS, captured.err[-3000:] + captured.out[-3000:]
    doc = schemas.load_json(tmp_path / "a" / "attestation.json")
    assert doc["verdict"] == "pass" and doc["mathlib_sha"] == ONRAMP_MATHLIB
    assert [(s["step"], s["result"]) for s in doc["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    step1 = doc["steps"][0]["diagnostic"]
    assert step1["code"] == "mathlib-pinned" and step1["details"]["mathlib_sha"] == ONRAMP_MATHLIB
    # The image hit: nothing fetched Mathlib's cache and nothing built it during the run.
    streams = captured.out + captured.err
    assert "cache get" not in streams and "lake build" not in streams
    print(f"F11 §6 / AC11: reproduce {PROVED} on the Mathlib image in {elapsed:.1f}s")
    assert elapsed < 600

    # D-5 on a Mathlib graph: a second run is byte-identical after masking, and the sha is what
    # the record carries — no path from inside the image reaches it.
    code = cli.main(
        [
            "reproduce",
            "--graph",
            str(graph),
            "--commit",
            commit,
            "--node",
            PROVED,
            "--image",
            mathlib_image,
            "--out",
            str(tmp_path / "b"),
            "--no-build",
        ]
    )
    capsys.readouterr()
    assert code == cli.EXIT_PASS
    other = schemas.load_json(tmp_path / "b" / "attestation.json")
    assert attestation.compare(doc, other) == []
    assert "/opt/opn/mathlib" not in json.dumps(doc)


def docker(*args: str, input: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["docker", *args], capture_output=True, check=False, input=input)


def test_postcreate_finds_the_pinned_mathlib_in_the_image(
    mathlib_image: str, tmp_path: Path
) -> None:
    """R6: the devcontainer's post-create proves the image carries the graph's Mathlib pin, at
    the sha the spec names, without fetching anything."""
    name = f"opn-onramp-{uuid.uuid4().hex[:12]}"
    script = (
        "set -euo pipefail\n"
        f"export GRAPH={GRAPH_IN_CONTAINER} NETWORK=/opt/opn/network\n"
        'time bash "$NETWORK/gate/devcontainer/post-create.sh"\n'
    )
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
        mathlib_image,
        "bash",
        "-c",
        script,
    )
    assert created.returncode == 0, created.stderr.decode()
    try:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:

            def owned(info: tarfile.TarInfo) -> tarfile.TarInfo:
                info.uid = info.gid = 1000
                info.uname = info.gname = "opn"
                return info

            tar.add(str(ONRAMP), arcname="graph", filter=owned)
        copied = docker("cp", "-", f"{name}:/home/opn", input=buf.getvalue())
        assert copied.returncode == 0, copied.stderr.decode()
        run = docker("start", "--attach", name)
        out, err = run.stdout.decode(errors="replace"), run.stderr.decode(errors="replace")
        (tmp_path / "post-create.log").write_text(out + "\n--- stderr ---\n" + err)
        assert run.returncode == 0, (out[-3000:], err[-3000:])
    finally:
        docker("rm", "-f", name)
    assert f"{ONRAMP_TARGET} pins Mathlib {ONRAMP_MATHLIB}: present in the image" in out
    assert "post-create: done" in out
    assert "cache get" not in out + err and "elan toolchain install" not in out + err
