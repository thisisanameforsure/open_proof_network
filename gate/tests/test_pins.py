"""F10-T3 / AC5: the image pin (R5, R6; F10-Q10) — one digest in gate-spec.json, the same one in
the devcontainer, and every other consumer reading it from the spec."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph

from opn_gate import cli, sandbox, schemas

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
DIGEST = "ghcr.io/thisisanameforsure/opn-gate@sha256:" + "ab" * 32


def _load_tool() -> Any:
    path = ROOT / "gate" / "tools" / "pin_image.py"
    spec = importlib.util.spec_from_file_location("pin_image", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pin_image = _load_tool()


def test_image_digest_consistent(tmp_path: Path) -> None:
    """AC5: after a pin, gate-spec.json's devcontainer_ref is a digest, devcontainer.json runs
    the same digest with the network's post-create command, and the check passes; a drift
    between the two, a tag instead of a digest, or no pin at all is named."""
    root = copy_graph(tmp_path)
    assert pin_image.check(root, TARGET) == [
        "devcontainer_ref is not an image digest reference: None",
        ".devcontainer/devcontainer.json is missing from the graph",
    ]
    written = pin_image.pin(
        root,
        TARGET,
        DIGEST,
        network_commit="1" * 40,
        api_url=None,
        cache_url="https://example.test/cache",
    )
    assert [p.relative_to(root).as_posix() for p in written] == [
        f"targets/{TARGET}/gate-spec.json",
        ".devcontainer/devcontainer.json",
    ]
    spec = schemas.load_json(root / "targets" / TARGET / "gate-spec.json", "gate-spec/v1")
    assert spec["devcontainer_ref"] == DIGEST and spec["network_commit"] == "1" * 40
    assert spec["olean_cache_url"] == "https://example.test/cache"  # F10-R7's pin rides along
    doc = json.loads((root / ".devcontainer" / "devcontainer.json").read_text())
    assert doc["image"] == DIGEST and doc["remoteUser"] == "opn"
    assert doc["postCreateCommand"] == pin_image.POST_CREATE
    assert doc["containerEnv"] == {
        "NETWORK": "/opt/opn/network",
        "GRAPH": "${containerWorkspaceFolder}",
    }
    assert "OPN_API" not in doc["containerEnv"]  # a hostname is configuration, never a default
    assert pin_image.check(root, TARGET) == []

    doc["image"] = "ghcr.io/thisisanameforsure/opn-gate:latest"
    (root / ".devcontainer" / "devcontainer.json").write_text(json.dumps(doc))
    [problem] = pin_image.check(root, TARGET)
    assert "not the pinned" in problem
    with pytest.raises(SystemExit, match="not an image digest reference"):
        pin_image.pin(
            root, TARGET, "ghcr.io/x/opn-gate:F10-done", network_commit=None, api_url=None
        )
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "gate.yml").write_text(
        "run: python -m opn_gate.cli gate --image ghcr.io/x@sha256:0\n"
    )
    assert any("gate.yml names an image itself" in p for p in pin_image.check(root, TARGET))


def test_spec_consumers_carry_no_image_of_their_own() -> None:
    """Q10: the precheck workflow and reproduce.sh (here) and gate.yml (in the graph, when it is
    checked out beside this repo) reach the image only through ensure_image, which reads the
    spec — so R5's 'the same digest' holds by construction."""
    for where, rel in pin_image.SPEC_CONSUMERS:
        path = (GRAPH_REPO if where == "graph" else ROOT) / rel
        if not path.is_file():
            assert where == "graph", rel  # only the graph's file may be absent (CI)
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(m in text for m in pin_image.IMAGE_MARKERS), rel


def test_ensure_image_pulls_the_pin_and_builds_without_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """R5: a pinned devcontainer_ref is pulled (once) and used as-is, never built; a graph
    without one gets the image built for its toolchain as before."""
    calls: list[str] = []
    present: set[str] = set()

    def pull(ref: str) -> str:
        calls.append(f"pull {ref}")
        return ref

    def build(gate_dir: Path, tc: str) -> str:
        calls.append(f"build {tc}")
        return f"built:{tc}"

    monkeypatch.setattr(sandbox, "image_exists", lambda ref: ref in present)
    monkeypatch.setattr(sandbox, "pull_image", pull)
    monkeypatch.setattr(sandbox, "build_image", build)
    pinned = {"devcontainer_ref": DIGEST, "lean_toolchain": "leanprover/lean4:v4.33.1"}
    assert cli.ensure_image(pinned, build=False) == DIGEST
    present.add(DIGEST)
    assert cli.ensure_image(pinned, build=False) == DIGEST
    assert calls == [f"pull {DIGEST}"]
    unpinned = {"devcontainer_ref": None, "lean_toolchain": "leanprover/lean4:v4.33.1"}
    with pytest.raises(cli.CliError, match="not present"):
        cli.ensure_image(unpinned, build=False)
    assert cli.ensure_image(unpinned, build=True) == "built:leanprover/lean4:v4.33.1"
    assert calls[-1] == "build leanprover/lean4:v4.33.1"


def test_pull_refuses_a_tag() -> None:
    with pytest.raises(sandbox.SandboxError, match="not an image digest reference"):
        sandbox.pull_image("ghcr.io/x/opn-gate:latest", docker="/bin/false")
    assert sandbox.is_digest_ref(DIGEST) and not sandbox.is_digest_ref(DIGEST[:-1])


def test_publish_workflow_shape() -> None:
    """R5: the publish workflow runs on every tag, holds packages:write and nothing else it
    could write with, builds from the repo root for the pinned toolchain, pushes, and prints the
    digest a graph pins; it never names a secret (C8)."""
    text = (ROOT / ".github" / "workflows" / "image-publish.yml").read_text(encoding="utf-8")
    assert 'tags: ["*"]' in text
    assert "packages: write" in text and "contents: read" in text
    assert "secrets." not in text and "github.token" in text
    assert "docker build -f gate/Dockerfile" in text and " ." in text
    assert "lean-toolchain" in text and "RepoDigests" in text
    assert "pin_image.py" in text
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "!gate/" in dockerignore and "!uv.lock" in dockerignore and "gate/tests/" in dockerignore
    dockerfile = (ROOT / "gate" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY gate/lean/ /opt/opn/lean/" in dockerfile and "uv sync --frozen" in dockerfile
    assert "OPN_LEAN_PKG_BIN=/opt/opn/lean/.lake/build/bin" in dockerfile
