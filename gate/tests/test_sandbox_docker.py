"""F00-T7: the step-3 sandbox (R12; AC25, AC26). make verify-lean (docker tier)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import TUTORIAL, make_context, node_dir

from opn_gate import pipeline, sandbox
from opn_gate.sandbox import Caps, SandboxToolchain
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import WitnessRequest

pytestmark = pytest.mark.docker

NETWORK_PROBE = (
    "\n#eval do\n"
    '  let out ← IO.Process.output {cmd := "getent", args := #["hosts", "example.com"]}\n'
    "  if out.exitCode != 0 then\n"
    '    throw (IO.userError s!"no network: getent exited {out.exitCode}")\n'
)
SPIN = "\npartial def OpnSpin.spin (n : Nat) : Nat := OpnSpin.spin (n + 1)\n#eval OpnSpin.spin 0\n"


def sandboxed(ctx: RunContext, image: str, caps: Caps) -> SandboxToolchain:
    return SandboxToolchain(image, caps, read_only=[node_dir(ctx)], read_write=[ctx.workdir])


def test_container_is_isolated(sandbox_image: str) -> None:
    """R12: no network, non-root, clean environment, caps applied."""
    sb = SandboxToolchain(sandbox_image, Caps(1, 512, 30))
    proc = sb._exec(["sh", "-c", "id -u; env | sort; getent hosts example.com; echo rc=$?"])
    lines = proc.stdout.splitlines()
    assert lines[0] == "1000"
    env_lines = [ln for ln in lines if "=" in ln and not ln.startswith("rc=")]
    assert {ln.split("=")[0] for ln in env_lines} <= {
        "ELAN_HOME",
        "HOME",
        "HOSTNAME",
        "PATH",
        "PWD",
        "LC_ALL",
    }
    assert lines[-1] == "rc=2"  # getent: name not found — no resolver, no network


def test_no_network(sandbox_image: str, tmp_path: Path) -> None:
    """AC25: a proof that reaches for the network during elaboration fails at step 4."""
    ctx = make_context(tmp_path)
    proof = node_dir(ctx) / "Proof.lean"
    proof.write_text(proof.read_text() + NETWORK_PROBE)
    ctx.toolchain = sandboxed(ctx, sandbox_image, Caps.from_spec(ctx.spec))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "elaboration-failed"
    texts = " ".join(m["text"] for m in verdict.diagnostic.details["messages"])
    assert "no network" in texts


def test_wallclock_cap(sandbox_image: str, tmp_path: Path) -> None:
    """AC26: caps of 1 cpu, 1 GiB, 30 s; a looping proof fails by timeout inside the cap."""
    ctx = make_context(
        tmp_path, spec_overrides={"step3_caps": {"cpu": 1, "memory_mib": 1024, "wallclock_s": 30}}
    )
    proof = node_dir(ctx) / "Proof.lean"
    proof.write_text(proof.read_text() + SPIN)
    ctx.toolchain = sandboxed(ctx, sandbox_image, Caps.from_spec(ctx.spec))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "timeout"
    assert "30s" in verdict.diagnostic.message


def test_no_containers_left_behind(sandbox_image: str) -> None:
    sb = SandboxToolchain(sandbox_image, Caps(1, 256, 10))
    sb._exec(["true"])
    with pytest.raises(subprocess.TimeoutExpired):
        sb._exec(["sleep", "60"], timeout_s=2)
    listing = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=opn-gate-", "-q"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert listing.stdout.strip() == ""
    assert sandbox.image_tag("leanprover/lean4:v4.33.1") == "opn-gate:leanprover-lean4-v4.33.1"
    assert TUTORIAL


def test_lean_pkg_in_image(sandbox_image: str, tmp_path: Path) -> None:
    """F01-AC15: the metaprograms inside the image give the golden output."""
    golden = json.loads(
        (Path(__file__).resolve().parent / "golden" / "witness-types.json").read_text()
    )
    ctx = make_context(tmp_path)
    work = ctx.workdir
    work.mkdir(parents=True, exist_ok=True)
    src = work / "Statement.lean"
    src.write_text((node_dir(ctx) / "Statement.lean").read_text(), encoding="utf-8")
    wit = work / "Witness.lean"
    wit.write_text((node_dir(ctx) / "Witness.lean").read_text(), encoding="utf-8")
    sb = SandboxToolchain(sandbox_image, Caps.from_spec(ctx.spec), read_write=[work])
    tc = sb.resolve(str(ctx.spec["lean_toolchain"]))
    req = WitnessRequest(
        src,
        "Nodes.«tutorial-and-swap».Statement",
        "OpnProp.and_swap",
        wit,
        "Nodes.«tutorial-and-swap».Witness",
    )
    result = sb.witness_type(tc, req, [work], timeout_s=120)
    assert result.ok, result
    assert result.doc["expected"] == golden["tutorial-and-swap"]["expected"]
    assert result.doc["defeq"] is True and result.doc["witness_axioms"] == []
