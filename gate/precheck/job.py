"""The precheck job (F06-R4; D-4, D-24, D-28, D-35).

    python -m precheck.job --graph <checkout> --job <job.json> --bundle <dir> --out <dir>
                           [--key <precheck private key>]

This runs inside the scratch repository's workflow, on GitHub's throwaway VM, which is the only
place a stranger's Lean may run (D-24, C9). It applies the bundle to the graph checkout, runs
the same gate steps the authoritative run does — 1, 2 and 4 to 8, inside the step-3 image — and
writes ``result.json`` {verdict, steps, diagnostics, attestation}. With ``--key`` the attestation
is signed as kind ``service`` (C8 item 2); without one it is emitted unsigned, which is what the
docker-tier test uses before a key exists.

It is the same codebase as the authoritative gate and ``pregate.sh`` (D-4: three invocations,
one codebase), so a precheck pass means the same thing a gate pass does, minus step 9 and minus
the authority.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from opn_gate import attestation, config, layout, pipeline, sandbox, schemas, signer
from opn_gate.cli import ensure_image
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext

RESULT_FILE = "result.json"
JOB_FIELDS: tuple[str, ...] = ("id", "node_id", "target_id", "graph_commit", "bundle_digest")


class JobError(RuntimeError):
    """The job cannot run at all. Distinct from a submission that fails the gate."""


def load_job(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"cannot read {path}: {exc}"
        raise JobError(msg) from exc
    missing = [f for f in JOB_FIELDS if not doc.get(f)]
    if missing:
        msg = f"{path} is missing {', '.join(missing)}"
        raise JobError(msg)
    return dict(doc)


def apply_bundle(bundle_dir: Path, graph_root: Path) -> list[Change]:
    """Copy the bundle over the checkout, returning the diff it represents.

    Paths in the bundle are relative to the graph root, as the api validated them (F06-R1).
    A path that escapes the root is a refusal, not a copy: the bundle is untrusted input.
    """
    changes: list[Change] = []
    root = graph_root.resolve()
    for source in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        rel = source.relative_to(bundle_dir).as_posix()
        dest = (root / rel).resolve()
        if not dest.is_relative_to(root):
            msg = f"bundle path escapes the graph root: {rel}"
            raise JobError(msg)
        changes.append(Change("M" if dest.is_file() else "A", rel))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, dest)
    if not changes:
        msg = f"the bundle at {bundle_dir} is empty"
        raise JobError(msg)
    return changes


def build_context(
    graph_root: Path,
    job: dict[str, Any],
    changes: list[Change],
    workdir: Path,
    *,
    image: str | None,
) -> RunContext:
    target_id = str(job["target_id"])
    node_id = str(job["node_id"])
    spec_path = layout.gate_spec_path(graph_root, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise JobError(msg) from exc
    tag = image or ensure_image(str(spec["lean_toolchain"]), build=True)
    node_dir = layout.graph_nodes_dir(graph_root, target_id) / node_id
    toolchain = sandbox.SandboxToolchain(
        tag, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
    )
    settings = config.load()
    return RunContext(
        graph_root=graph_root,
        claim=Claim(target_id, node_id),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=changes,
        workdir=workdir,
        toolchain=toolchain,
        settings=settings,
    )


def sign_service(doc: dict[str, Any], key_path: Path) -> dict[str, Any]:
    """C8 item 2: the precheck key is the job's only secret, and this is its only use."""
    out = dict(doc)
    sig = signer.SshKeygenSigner().sign(attestation.signed_bytes(out), key_path, "service")
    out["signature"] = {
        "kind": "service",
        "key_id": sig.key_id,
        "value": sig.value,
        "timestamp": doc["signature"]["timestamp"],
    }
    return schemas.validate(out, str(doc["schema"]))


def run(
    *,
    graph_root: Path,
    job_path: Path,
    bundle_dir: Path,
    out_dir: Path,
    key_path: Path | None = None,
    image: str | None = None,
) -> dict[str, Any]:
    """Run the job and return the result document; also written to ``out_dir/result.json``."""
    job = load_job(job_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    changes = apply_bundle(bundle_dir, graph_root)
    ctx = build_context(graph_root, job, changes, out_dir / "work", image=image)
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=str(job["graph_commit"]))
    if key_path is not None:
        doc = sign_service(doc, key_path)
    result = {
        "job_id": str(job["id"]),
        "node_id": str(job["node_id"]),
        "bundle_digest": str(job["bundle_digest"]),
        "verdict": verdict.verdict,
        "first_failing_step": verdict.first_failing_step,
        "steps": verdict.as_dict(ctx.settings.diagnostic_max_bytes)["steps"],
        "attestation": doc,
    }
    (out_dir / RESULT_FILE).write_bytes(schemas.canonical_json(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opn-precheck-job", description=__doc__.split("\n\n")[0])
    parser.add_argument("--graph", required=True, type=Path, help="the graph checkout")
    parser.add_argument("--job", required=True, type=Path, help="job.json from the branch")
    parser.add_argument("--bundle", required=True, type=Path, help="the bundle directory")
    parser.add_argument("--out", required=True, type=Path, help="where result.json is written")
    parser.add_argument("--key", type=Path, help="the precheck private key (C8 item 2)")
    parser.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    args = parser.parse_args(argv)
    try:
        result = run(
            graph_root=args.graph.resolve(),
            job_path=args.job,
            bundle_dir=args.bundle,
            out_dir=args.out,
            key_path=args.key,
            image=args.image,
        )
    except (JobError, schemas.SchemaError, sandbox.SandboxError) as exc:
        # The job could not run. That is not a verdict, and the api reports it as `error` (R5).
        sys.stderr.write(f"opn-precheck-job: {exc}\n")
        sys.stdout.write(json.dumps({"error": str(exc)}) + "\n")
        return 2
    sys.stdout.write(json.dumps({"verdict": result["verdict"], "job_id": result["job_id"]}) + "\n")
    # A failing submission is a successful job: the workflow must still upload the artifact.
    return 0


if __name__ == "__main__":
    sys.exit(main())
