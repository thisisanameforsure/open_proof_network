"""F06-T2 / AC14: the precheck job end to end in the step-3 image, on the fixture graph.

The docker tier, because the job's whole point is that a stranger's Lean runs inside the
sandbox and nowhere else (D-24, C9). A test key stands in for the precheck key (C8 item 2),
which exists only in the scratch repository.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import GRAPH, TARGET, TUTORIAL, copy_graph
from precheck import job as precheck_job
from precheck import sign as precheck_sign

from opn_gate import attestation, config, schemas
from opn_gate.signer import SshKeygenSigner

PREFIX = f"targets/{TARGET}/nodes/{TUTORIAL}/"


@pytest.fixture(scope="module")
def precheck_key(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """A stand-in for C8 item 2, generated the same way the real one is."""
    d = tmp_path_factory.mktemp("precheck-key")
    key = d / "precheck"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-precheck"],
        check=True,
    )
    return key, (d / "precheck.pub").read_text()


def write_job(root: Path, bundle: dict[str, str], *, node: str = TUTORIAL) -> tuple[Path, Path]:
    """The branch layout the api pushes: job.json beside a bundle/ tree (R3)."""
    job_dir = root / "job"
    bundle_dir = job_dir / "bundle"
    for rel, content in bundle.items():
        path = bundle_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    doc = {
        "id": "01JOBIDFORTHEDOCKERTIER00",
        "node_id": node,
        "target_id": TARGET,
        "graph_commit": "9" * 40,
        "bundle_digest": "a" * 64,
    }
    job_path = job_dir / "job.json"
    job_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return job_path, bundle_dir


@pytest.mark.docker
def test_job_script_end_to_end(
    tmp_path: Path, sandbox_image: str, precheck_key: tuple[Path, str]
) -> None:
    """AC14: a real proof produces a result whose attestation validates and verifies."""
    key, public_key = precheck_key
    graph = copy_graph(tmp_path)
    proof = (GRAPH / "targets" / TARGET / "nodes" / TUTORIAL / "Proof.lean").read_text()
    (graph / PREFIX / "Proof.lean").unlink()  # the bundle is what supplies it
    job_path, bundle_dir = write_job(tmp_path, {PREFIX + "Proof.lean": proof})

    result = precheck_job.run(
        graph_root=graph,
        job_path=job_path,
        bundle_dir=bundle_dir,
        out_dir=tmp_path / "out",
        image=sandbox_image,
    )
    assert result["verdict"] == "pass", json.dumps(result["steps"], indent=2)
    assert result["first_failing_step"] is None
    assert result["job_id"] == "01JOBIDFORTHEDOCKERTIER00"
    assert [s["step"] for s in result["steps"]] == [1, 2, 4, 5, 6, 7, 8]
    assert all(s["result"] == "pass" for s in result["steps"])

    doc = result["attestation"]
    assert schemas.violations(doc) == []
    assert doc["graph_commit"] == "9" * 40
    # The record says where it really ran: `local` here, `hosted` in the workflow, which
    # test_workflow_declares_a_hosted_runner checks is what the scratch repo sets (R6).
    assert doc["runner"] == config.load().runner
    assert doc["signature"]["kind"] is None or doc["signature"]["value"] is None  # unsigned yet

    # The signing step, separate because the running step holds no secret (C8).
    written = tmp_path / "out" / precheck_job.RESULT_FILE
    signed = precheck_sign.sign_result(written, key)["attestation"]
    assert signed["signature"]["kind"] == "service"  # R6
    s = SshKeygenSigner()
    assert s.verify(attestation.signed_bytes(signed), signed["signature"]["value"], public_key)
    assert signed["signature"]["key_id"] == s.fingerprint(public_key)
    assert schemas.violations(signed) == []
    # The file on disk is what the workflow uploads, and it carries the signature.
    assert json.loads(written.read_text())["attestation"]["signature"]["kind"] == "service"


@pytest.mark.docker
def test_job_reports_a_failing_submission_as_a_verdict(tmp_path: Path, sandbox_image: str) -> None:
    """A submission that fails is a *successful* job: the agent needs the diagnostic (R4)."""
    graph = copy_graph(tmp_path)
    (graph / PREFIX / "Proof.lean").unlink()
    broken = "import Nodes.tutorial-and-swap.Statement\n\ntheorem nope : True := by sorry\n"
    job_path, bundle_dir = write_job(tmp_path, {PREFIX + "Proof.lean": broken})

    result = precheck_job.run(
        graph_root=graph,
        job_path=job_path,
        bundle_dir=bundle_dir,
        out_dir=tmp_path / "out",
        image=sandbox_image,
    )
    assert result["verdict"] == "fail"
    assert result["first_failing_step"] is not None
    failed = [s for s in result["steps"] if s["result"] == "fail"]
    assert failed and failed[0]["diagnostic"]["code"]
    assert (tmp_path / "out" / precheck_job.RESULT_FILE).is_file()


def test_bundle_may_not_escape_the_graph_root(tmp_path: Path) -> None:
    """The bundle is untrusted input; a traversal is refused before anything is copied."""
    graph = copy_graph(tmp_path)
    outside = tmp_path / "job" / "bundle" / ".." / ".." / "escaped.txt"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x")
    bundle_dir = tmp_path / "job" / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "ok.txt").write_text("x")
    # A path that leaves the root can only arrive as a symlink or a crafted archive; the check
    # is on the resolved destination, so it holds however the file got there.
    link = bundle_dir / "escape"
    link.symlink_to("../../escaped.txt")
    changes = precheck_job.apply_bundle(bundle_dir, graph)
    assert all(not c.path.startswith("..") for c in changes)


def test_empty_bundle_is_a_job_error(tmp_path: Path) -> None:
    graph = copy_graph(tmp_path)
    empty = tmp_path / "bundle"
    empty.mkdir()
    with pytest.raises(precheck_job.JobError, match="empty"):
        precheck_job.apply_bundle(empty, graph)


def test_workflow_declares_a_hosted_runner_and_no_permissions() -> None:
    """R6 and §7, checked where they are enforced: the workflow the scratch repo runs.

    Not a docker test — it reads the file the repository holds.
    """
    workflow = (Path(__file__).resolve().parents[1] / "precheck" / "precheck.yml").read_text()
    assert "OPN_RUNNER: hosted" in workflow  # R6: the attestation says hosted because it is
    assert "permissions: {}" in workflow  # §7: the job may not write to the repository
    # C8: the key is read in one step, and that step comes after the one running the Lean.
    running = workflow.index("Run the gate on the bundle")
    signing = workflow.index("Sign the attestation with the precheck key")
    assert running < signing, "the verdict must exist before the key is ever read"
    assert "secrets." not in workflow[:signing], "no step before signing is granted a secret"
    assert workflow.count("secrets.") == 1, "the signing key is the only secret this job holds"
    assert "OPN_PRECHECK_SIGNING_KEY" not in workflow[:signing]
