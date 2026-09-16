"""Signed records: one canonical body, signed and verified through the ``Signer`` seam (F15-T2,
T3; R1, R6, R8; C9).

Three F15 records carry a contributor's own signature — a steward's commitment or step-down, an
explainer signature, a write-up record. Each is a YAML document whose ``key`` field is the
signer's SSH public key and whose ``signature`` field is an OpenSSH SSHSIG block over the rest of
the document, serialised the one way every record is (``schemas.canonical_json``, sorted keys).
Signing and verifying go through ``opn_gate.signer`` — ``ssh-keygen -Y`` where the gate runs —
so the api never verifies one of these (F15 §7: they are evidentiary, checked at the gate).

The body is the document *without* ``signature`` and *with* ``key``: a signature therefore binds
the key it verifies under, and a record re-keyed after the fact stops verifying. The namespace is
the seam's one namespace; the record's own ``schema`` field separates the kinds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opn_gate import schemas
from opn_gate.signer import Signer, SshKeygenSigner, public_key_for

SIGNATURE_FIELD = "signature"
KEY_FIELD = "key"


def body(doc: dict[str, Any]) -> bytes:
    """The bytes a record's signature is over: everything but the signature, canonically."""
    return schemas.canonical_json({k: v for k, v in doc.items() if k != SIGNATURE_FIELD})


def sign(doc: dict[str, Any], key_path: Path, signer: Signer) -> dict[str, Any]:
    """``doc`` with ``key`` set to the public half of ``key_path`` and ``signature`` over the
    body. The signer's ``SignerError`` propagates: a record that cannot be signed is not written."""
    out = {k: v for k, v in doc.items() if k != SIGNATURE_FIELD}
    out[KEY_FIELD] = public_key_for(key_path)
    out[SIGNATURE_FIELD] = signer.sign(body(out), key_path, "contributor").value
    return out


def verifies(doc: dict[str, Any], signer: Signer) -> bool:
    """Whether the record's signature verifies under its own key. A record with no key or no
    signature, or with either malformed, verifies as ``False`` — never as an exception a caller
    could mistake for a pass (C7)."""
    key = doc.get(KEY_FIELD)
    signature = doc.get(SIGNATURE_FIELD)
    if not isinstance(key, str) or not isinstance(signature, str) or not key or not signature:
        return False
    return signer.verify(body(doc), signature, key)


def default_signer() -> Signer:
    """The platform's ssh-keygen: the gate's only verifier for these records (F15 §7)."""
    return SshKeygenSigner()
