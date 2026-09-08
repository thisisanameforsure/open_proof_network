"""The ``Signer`` seam: ssh-keygen -Y sign / verify (conventions §1; F00-R11, C8).

One mechanism for every signature kind: an OpenSSH signature over the attestation's signed
bytes (``attestation.signed_bytes``) in the ``opn-attestation`` namespace. ``kind`` says whose
key it was — ``gate`` (C8 item 1), ``service`` (item 2) or ``contributor`` (pregate.sh --sign).
The key id is the OpenSSH SHA256 fingerprint of the public key.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

NAMESPACE = "opn-attestation"
SignatureKind = Literal["gate", "service", "contributor"]


class SignerError(RuntimeError):
    """ssh-keygen refused to sign or the key could not be read."""


@dataclass(frozen=True)
class Signature:
    kind: SignatureKind
    key_id: str
    value: str  # the armored OpenSSH signature block


class Signer(Protocol):
    def sign(self, payload: bytes, key_path: Path, kind: SignatureKind) -> Signature: ...

    def verify(self, payload: bytes, signature: str, public_key: str) -> bool: ...

    def fingerprint(self, public_key: str) -> str: ...


class SshKeygenSigner:
    """The real seam, over the platform's ssh-keygen."""

    def __init__(self, ssh_keygen: str = "ssh-keygen") -> None:
        self.ssh_keygen = ssh_keygen

    def sign(self, payload: bytes, key_path: Path, kind: SignatureKind) -> Signature:
        with tempfile.TemporaryDirectory(prefix="opn-sign-") as tmp:
            target = Path(tmp) / "payload"
            target.write_bytes(payload)
            proc = subprocess.run(
                [self.ssh_keygen, "-Y", "sign", "-f", str(key_path), "-n", NAMESPACE, str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                msg = f"ssh-keygen -Y sign failed: {proc.stderr.strip()}"
                raise SignerError(msg)
            value = (Path(tmp) / "payload.sig").read_text(encoding="utf-8")
        public_key = _public_key_for(key_path)
        return Signature(kind=kind, key_id=self.fingerprint(public_key), value=value)

    def verify(self, payload: bytes, signature: str, public_key: str) -> bool:
        with tempfile.TemporaryDirectory(prefix="opn-verify-") as tmp:
            allowed = Path(tmp) / "allowed_signers"
            allowed.write_text(f"opn {public_key.strip()}\n", encoding="utf-8")
            sig = Path(tmp) / "payload.sig"
            sig.write_text(signature, encoding="utf-8")
            proc = subprocess.run(
                [
                    self.ssh_keygen,
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed),
                    "-I",
                    "opn",
                    "-n",
                    NAMESPACE,
                    "-s",
                    str(sig),
                ],
                input=payload,
                capture_output=True,
                check=False,
            )
            return proc.returncode == 0

    def fingerprint(self, public_key: str) -> str:
        with tempfile.TemporaryDirectory(prefix="opn-fp-") as tmp:
            pub = Path(tmp) / "key.pub"
            pub.write_text(public_key.strip() + "\n", encoding="utf-8")
            proc = subprocess.run(
                [self.ssh_keygen, "-lf", str(pub)], capture_output=True, text=True, check=False
            )
        if proc.returncode != 0:
            msg = f"ssh-keygen -lf failed: {proc.stderr.strip()}"
            raise SignerError(msg)
        parts = proc.stdout.split()
        if len(parts) < 2 or not parts[1].startswith("SHA256:"):
            msg = f"unexpected fingerprint output: {proc.stdout!r}"
            raise SignerError(msg)
        return parts[1]


def _public_key_for(key_path: Path) -> str:
    pub = key_path.with_name(key_path.name + ".pub")
    if pub.is_file():
        return pub.read_text(encoding="utf-8").strip()
    proc = subprocess.run(
        ["ssh-keygen", "-y", "-f", str(key_path)], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        msg = f"cannot derive the public key for {key_path}: {proc.stderr.strip()}"
        raise SignerError(msg)
    return proc.stdout.strip()


def public_key_for(key_path: Path) -> str:
    return _public_key_for(key_path)
