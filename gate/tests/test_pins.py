"""F10-T3 / AC5: the image pin (R5, R6; F10-Q10) — one digest in gate-spec.json, the same one in
the devcontainer, and every other consumer reading it from the spec."""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph

from opn_gate import cli, config, sandbox, schemas

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

    def build(gate_dir: Path, tc: str, *, mathlib_sha: str | None = None) -> str:
        calls.append(f"build {tc}" + (f" mathlib {mathlib_sha[:12]}" if mathlib_sha else ""))
        return f"built:{tc}" + (f"-mathlib-{mathlib_sha[:12]}" if mathlib_sha else "")

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
    # F11-R6: a Mathlib pin selects the image built for that commit — a different tag, and the
    # sha handed to the build — while a pinned digest is still taken as-is.
    mathlib = {**unpinned, "mathlib_sha": "0df444a360eaa60ab8c11dca51a86af692955474"}
    assert (
        cli.ensure_image(mathlib, build=True)
        == "built:leanprover/lean4:v4.33.1-mathlib-0df444a360ea"
    )
    assert calls[-1] == "build leanprover/lean4:v4.33.1 mathlib 0df444a360ea"
    present.add("opn-gate:leanprover-lean4-v4.33.1-mathlib-0df444a360ea")
    assert (
        cli.ensure_image(mathlib, build=False)
        == "opn-gate:leanprover-lean4-v4.33.1-mathlib-0df444a360ea"
    )
    assert cli.ensure_image({**mathlib, "devcontainer_ref": DIGEST}, build=False) == DIGEST


def test_pull_refuses_a_tag() -> None:
    with pytest.raises(sandbox.SandboxError, match="not an image digest reference"):
        sandbox.pull_image("ghcr.io/x/opn-gate:latest", docker="/bin/false")
    assert sandbox.is_digest_ref(DIGEST) and not sandbox.is_digest_ref(DIGEST[:-1])


#: Docker's own tag grammar: a leading alphanumeric or underscore, then up to 127 more of
#: alphanumeric, underscore, period or dash.
DOCKER_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}")


def test_publish_workflow_tag_is_derived_by_the_shell_alone() -> None:
    """The image tag comes from a shell expression in the publish workflow, so run the real line
    rather than read it (F10-R5).

    The first tag push ever made published nothing: the line piped the ref through
    ``tr -c 'A-Za-z0-9_.-\\n' '-'``, and GNU tr on the runner reads ``.-\\n`` as a reverse range
    and exits 1, while BSD tr on the laptop accepts the same set silently. No static reading of
    the file could tell those two apart, and no laptop run could reproduce it — so the guard is
    that the expression uses no external program at all, plus its output for real refs.
    """
    text = (ROOT / ".github" / "workflows" / "image-publish.yml").read_text(encoding="utf-8")
    line = next(ln.strip() for ln in text.splitlines() if ln.strip().startswith("tag="))
    assert "|" not in line, f"the tag must not depend on an external program: {line}"
    for ref, want in (("F12-done", "F12-done"), ("v1.2.3", "v1.2.3"), ("feat/x y@1", "feat-x-y-1")):
        script = f'GITHUB_REF_NAME={shlex.quote(ref)}\n{line}\nprintf %s "$tag"'
        proc = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script], capture_output=True, text=True, check=True
        )
        assert proc.stdout == want
        assert DOCKER_TAG.fullmatch(proc.stdout), f"{proc.stdout!r} is not a docker tag"


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
    # F11-R6: one image per Mathlib pin, from the same Dockerfile and the same install script
    # a laptop runs; the workflow builds the matrix the pins file lists and labels each image
    # with the Mathlib it carries, which pin_image.py --verify reads back.
    assert "ARG MATHLIB_SHA=" in dockerfile and "install-mathlib.sh" in dockerfile
    assert "OPN_MATHLIB_HOME=/opt/opn/mathlib" in dockerfile
    assert "gate/mathlib-pins.txt" in text and "matrix" in text
    assert "MATHLIB_SHA=$MATHLIB_SHA" in text and "network.openproof.mathlib_sha=" in text
    pins = (ROOT / "gate" / "mathlib-pins.txt").read_text(encoding="utf-8")
    listed = [
        line.split("#", 1)[0].strip() for line in pins.splitlines() if line.split("#", 1)[0].strip()
    ]
    assert listed and all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in listed)
    script = (ROOT / "gate" / "scripts" / "install-mathlib.sh").read_text(encoding="utf-8")
    assert (
        "lake exe cache get" in script and "MATHLIB_SHA" in script and "OPN_MATHLIB_HOME" in script
    )


def test_verify_checks_the_mathlib_label_against_the_pin(tmp_path: Path) -> None:
    """F11-R6: an image pinned on a Mathlib graph must carry that Mathlib — a plain image would
    pass --check and fail at step 1 inside the sandbox — and a Mathlib image pinned on a
    Mathlib-free graph is the same mismatch the other way."""
    docker = tmp_path / "docker"
    labels = tmp_path / "labels.json"
    docker.write_text(
        f'#!/bin/sh\ncase "$1" in\n  pull) exit 0 ;;\n  image) cat "{labels}" ;;\nesac\n'
    )
    docker.chmod(0o755)
    sha = "0df444a360eaa60ab8c11dca51a86af692955474"
    labels.write_text(
        json.dumps({pin_image.REVISION_LABEL: "1" * 40, pin_image.MATHLIB_LABEL: sha})
    )
    assert pin_image.verify(DIGEST, "1" * 40, mathlib_sha=sha, docker=str(docker)) == []
    [problem] = pin_image.verify(DIGEST, "1" * 40, mathlib_sha=None, docker=str(docker))
    assert "Mathlib label" in problem and "None" in problem
    labels.write_text(json.dumps({pin_image.REVISION_LABEL: "1" * 40, pin_image.MATHLIB_LABEL: ""}))
    [problem] = pin_image.verify(DIGEST, "1" * 40, mathlib_sha=sha, docker=str(docker))
    assert f"not the graph's mathlib_sha '{sha}'" in problem
    problems = pin_image.verify(DIGEST, "2" * 40, mathlib_sha=sha, docker=str(docker))
    assert len(problems) == 2 and "revision label" in problems[0]


# --- finding 7 (2026-09-13): the order of step 9 in the graph's gate.yml -------------------------
#
# The workflow is the graph's file (D-35), read here from the fetched remote because the local
# clone's main is stale; skipped where the graph is not checked out beside this repo (CI) or has
# no origin/main. A static read of the YAML, never a run of it.

STEP9_REASON = (
    "finding 7 (D-4 step order, C8, F07-Q16): the graph's gate job evaluates step 9 before the "
    "sandbox, so a valid non-certified submission is a red check within seconds and its build "
    "never runs; the mark stays until Phase 2 lands the split gate.yml on the graph; "
    "fix: F07-T8 (Mike, 2026-09-13)"
)


def _live_gate_jobs() -> dict[str, Any]:
    """The ``jobs`` of the graph's gate.yml at ``origin/main``."""
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    proc = subprocess.run(
        ["git", "-C", str(GRAPH_REPO), "show", "origin/main:.github/workflows/gate.yml"],
        capture_output=True,
        text=True,
        check=False,
        env=config.child_environment(drop=config.GIT_REPO_VARIABLES),  # the hook exports GIT_DIR
    )
    if proc.returncode != 0:
        pytest.skip(f"origin/main:.github/workflows/gate.yml is not readable: {proc.stderr[:200]}")
    doc = yaml.safe_load(proc.stdout)
    assert isinstance(doc, dict) and isinstance(doc.get("jobs"), dict), "gate.yml has no jobs"
    jobs: dict[str, Any] = doc["jobs"]
    return jobs


def _job_named(jobs: dict[str, Any], prefix: str) -> dict[str, Any] | None:
    for job in jobs.values():
        if isinstance(job, dict) and str(job.get("name", "")).lower().startswith(prefix):
            return job
    return None


def test_the_gate_jobs_build_step_holds_no_secret_and_no_write_permission() -> None:
    """C8 today, and after F07-T8: the job that runs contributor Lean is granted read
    permissions only, names no ``secrets.``, and its build step (``Run the gate``) carries no
    token at all (the log, 2026-09-09: no step before signing is granted any secret)."""
    jobs = _live_gate_jobs()
    gate = jobs["gate"]
    perms = gate.get("permissions") or {}
    assert perms and all(v == "read" for v in perms.values()), perms
    assert "secrets." not in json.dumps(gate)
    build = next(s for s in gate["steps"] if s.get("name") == "Run the gate")
    assert "secrets." not in json.dumps(build) and "github.token" not in json.dumps(build)


@pytest.mark.xfail(strict=True, reason=STEP9_REASON)
def test_step_9_is_its_own_job_after_the_sandbox_build() -> None:
    """D-4's order: the sandbox build (steps 1-8) is job ``gate``, which exports the classify
    step's ``needs_review`` and ``tutorial`` as job outputs; step 9 is a job of its own that
    ``needs: gate``, runs only when the gate says a review is needed, holds nothing beyond
    ``pull-requests: read``, names no secret, and prints its verdict to the step summary — so
    a valid submission shows build green + review pending, and the build always runs."""
    jobs = _live_gate_jobs()
    gate = jobs["gate"]
    review = _job_named(jobs, "step 9")
    assert review is not None, "no job named 'step 9 …' in the graph's gate.yml"
    needs = review.get("needs")
    assert needs == "gate" or (isinstance(needs, list) and "gate" in needs), needs
    assert "needs.gate.outputs.needs_review" in str(review.get("if", "")), review.get("if")
    perms = review.get("permissions") or {}
    assert set(perms.items()) <= {("pull-requests", "read")}, perms
    text = json.dumps(review)
    assert "secrets." not in text
    assert "$GITHUB_STEP_SUMMARY" in text, "the step-9 job writes no step summary"
    outputs = gate.get("outputs") or {}
    assert {"needs_review", "tutorial"} <= set(outputs), outputs
    in_gate = [
        s.get("name") for s in gate["steps"] if str(s.get("name", "")).lower().startswith("step 9")
    ]
    assert in_gate == [], f"the gate job still evaluates step 9 itself: {in_gate}"
