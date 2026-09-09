"""Sign a precheck result with the precheck key (F06-R4, R6; C8 item 2).

    python -m precheck.sign --result out/result.json --key <private key>

Separate from ``precheck.job`` on purpose: the step that runs a contributor's Lean is granted no
secret, exactly as the authoritative gate keeps step 3 and the signing job apart (C8). This reads
the result the job wrote, signs its attestation as kind ``service``, and writes the file back.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from opn_gate import attestation, schemas, signer
from precheck.job import sign_service


class SignError(RuntimeError):
    """The result cannot be signed; the caller decides whether that fails the workflow."""


def sign_result(result_path: Path, key_path: Path) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"cannot read {result_path}: {exc}"
        raise SignError(msg) from exc
    doc = result.get("attestation")
    if not isinstance(doc, dict) or doc.get("schema") not in attestation.ACCEPTED_SCHEMAS:
        msg = f"{result_path} carries no attestation to sign"
        raise SignError(msg)
    try:
        signed = sign_service(doc, key_path)
    except (signer.SignerError, schemas.SchemaError) as exc:
        msg = f"signing failed: {exc}"
        raise SignError(msg) from exc
    result["attestation"] = signed
    result_path.write_bytes(schemas.canonical_json(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opn-precheck-sign", description=__doc__.split("\n\n")[0])
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path, help="the precheck private key")
    args = parser.parse_args(argv)
    try:
        result = sign_result(args.result, args.key)
    except SignError as exc:
        sys.stderr.write(f"opn-precheck-sign: {exc}\n")
        return 2
    key_id = result["attestation"]["signature"]["key_id"]
    sys.stdout.write(json.dumps({"signed": str(args.result), "key_id": key_id}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
