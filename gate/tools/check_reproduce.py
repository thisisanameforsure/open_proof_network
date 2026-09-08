"""F00-T9 / AC28: check a committed attestation from a laptop.

    uv run python gate/tools/check_reproduce.py <attestation-id> [--graph PATH] [--out DIR]

Given the id of a committed attestation (``attestations/<id>.json`` in the graph repo), this
tool (1) verifies the CI signature against the committed ``keys/gate.pub``, (2) re-runs the gate
on the merge commit inside the step-3 image via ``reproduce.sh``, and (3) reports whether the
reproduction is identical to the committed record once the D-5 fields are masked. Exit 0 only
when both the signature verifies and the reproduction is identical.

The graph checkout defaults to the sibling ``../open_proof_network_graph`` (D-35); pass
``--graph`` for any other clone. Nothing here trusts the service or the CI: the inputs are the
graph history, the pinned tooling, and a local docker.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import attestation, postmerge, schemas
from opn_gate.signer import SshKeygenSigner

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("attestation_id", help="e.g. 000002")
    parser.add_argument("--graph", type=Path, default=ROOT.parent / "open_proof_network_graph")
    parser.add_argument("--out", type=Path, help="reproduction output directory")
    args = parser.parse_args(argv)

    graph = args.graph.resolve()
    committed_path = graph / "attestations" / f"{args.attestation_id}.json"
    committed = schemas.load_json(committed_path)
    public_key = (graph / "keys" / "gate.pub").read_text(encoding="utf-8")

    signature_ok = postmerge.verify(committed, public_key, SshKeygenSigner())
    print(f"signature: {'verifies' if signature_ok else 'DOES NOT VERIFY'} against keys/gate.pub")
    print(f"  kind={committed['signature']['kind']} key_id={committed['signature']['key_id']}")

    merge_commit = committed["merge_commit"]
    if not merge_commit:
        print("attestation has no merge_commit; nothing to reproduce")
        return 1
    out = (args.out or Path(tempfile.mkdtemp(prefix="opn-check-"))).resolve()
    print(f"reproducing merge commit {merge_commit} for node {committed['node_id']} in {out}")
    proc = subprocess.run(
        [
            str(ROOT / "gate" / "reproduce.sh"),
            "--graph",
            str(graph),
            "--commit",
            merge_commit,
            "--node",
            committed["node_id"],
            "--target",
            committed["graph_id"],
            "--out",
            str(out),
            "--compare",
            str(committed_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr.strip():
        sys.stderr.write(proc.stderr)
    reproduced = schemas.load_json(out / "attestation.json")
    differing = attestation.compare(committed, attestation.with_step9(reproduced, committed))
    summary = {"signature_ok": signature_ok, "identical": not differing, "differing": differing}
    print(json.dumps(summary))
    return 0 if signature_ok and not differing else 1


if __name__ == "__main__":
    sys.exit(main())
