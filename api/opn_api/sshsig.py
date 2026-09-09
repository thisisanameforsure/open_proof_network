"""Verify an OpenSSH ``SSHSIG`` signature without an ``ssh-keygen`` binary (F06-R5, R6; C8).

The gate signs with ``ssh-keygen -Y sign`` (``opn_gate.signer``), because the gate always runs
where OpenSSH is installed. The api does not: its runtime is a Lambda image with no OpenSSH, so
it cannot shell out to verify the precheck attestation it downloads. This module is the reading
half of that one seam — it parses the armored signature and the committed public key, and hands
the bytes to ``cryptography``'s Ed25519 verifier. Nothing here implements a primitive: the
format work is parsing, the mathematics is the library's (F06-Q5).

Only ``ssh-ed25519`` is accepted, because C8 item 1 and item 2 are both ed25519 keys and an
unexpected algorithm on a signature the network trusts is a refusal, not a fallback (C7).

The wire formats are OpenSSH's ``PROTOCOL.sshsig`` and RFC 4253 §6.6:

    signature blob   "SSHSIG" · uint32 version · string publickey · string namespace
                     · string reserved · string hash_algorithm · string signature
    signed bytes     "SSHSIG" · string namespace · string reserved · string hash_algorithm
                     · string H(message)
    inner signature  string algorithm · string 64 raw bytes
    ed25519 key      string "ssh-ed25519" · string 32 raw bytes
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import struct

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAGIC = b"SSHSIG"
SIG_VERSION = 1
KEY_TYPE = b"ssh-ed25519"
ED25519_KEY_BYTES = 32
ED25519_SIG_BYTES = 64
HASHES = {b"sha256": hashlib.sha256, b"sha512": hashlib.sha512}
ARMOR_BEGIN = "-----BEGIN SSH SIGNATURE-----"
ARMOR_END = "-----END SSH SIGNATURE-----"


class SshsigError(ValueError):
    """The signature or the public key is malformed, or uses an algorithm we do not accept."""


# --- the SSH wire format -------------------------------------------------------------------------


def _read_string(blob: bytes, offset: int) -> tuple[bytes, int]:
    """One length-prefixed string, and the offset after it (RFC 4253 §6.6)."""
    if offset + 4 > len(blob):
        msg = "truncated: no length prefix"
        raise SshsigError(msg)
    (length,) = struct.unpack_from(">I", blob, offset)
    end = offset + 4 + length
    if end > len(blob):
        msg = f"truncated: a {length}-byte string does not fit"
        raise SshsigError(msg)
    return blob[offset + 4 : end], end


def _string(value: bytes) -> bytes:
    return struct.pack(">I", len(value)) + value


# --- public keys ---------------------------------------------------------------------------------


def public_key_blob(authorized_key: str) -> bytes:
    """The raw key blob of an ``ssh-ed25519 AAAA… comment`` line."""
    parts = authorized_key.strip().split()
    if len(parts) < 2 or parts[0] != KEY_TYPE.decode():
        msg = "not an ssh-ed25519 public key line"
        raise SshsigError(msg)
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (binascii.Error, ValueError) as exc:
        msg = "the public key is not valid base64"
        raise SshsigError(msg) from exc
    _ed25519_key(blob)  # refuse a line whose base64 is not an ed25519 key
    return blob


def fingerprint(authorized_key: str) -> str:
    """The OpenSSH SHA256 fingerprint, the form an attestation's ``key_id`` takes."""
    digest = hashlib.sha256(public_key_blob(authorized_key)).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def _ed25519_key(blob: bytes) -> Ed25519PublicKey:
    algorithm, offset = _read_string(blob, 0)
    if algorithm != KEY_TYPE:
        msg = f"unsupported key algorithm {algorithm!r}; only ssh-ed25519 is accepted"
        raise SshsigError(msg)
    raw, offset = _read_string(blob, offset)
    if len(raw) != ED25519_KEY_BYTES or offset != len(blob):
        msg = "malformed ssh-ed25519 public key blob"
        raise SshsigError(msg)
    return Ed25519PublicKey.from_public_bytes(raw)


# --- signatures ----------------------------------------------------------------------------------


def unarmor(armored: str) -> bytes:
    """The signature blob inside the ``-----BEGIN SSH SIGNATURE-----`` block."""
    text = armored.strip()
    if not text.startswith(ARMOR_BEGIN) or not text.endswith(ARMOR_END):
        msg = "the signature is not an armored SSH SIGNATURE block"
        raise SshsigError(msg)
    body = "".join(text[len(ARMOR_BEGIN) : -len(ARMOR_END)].split())
    try:
        return base64.b64decode(body, validate=True)
    except (binascii.Error, ValueError) as exc:
        msg = "the signature body is not valid base64"
        raise SshsigError(msg) from exc


def verify(payload: bytes, armored: str, authorized_key: str, *, namespace: str) -> bool:
    """True when ``armored`` is a signature over ``payload`` by ``authorized_key``.

    A malformed input raises ``SshsigError``; a well-formed signature that simply does not match
    returns False. The caller treats both as a refusal, but only the first is a bug in the
    producer rather than a wrong key (C7).
    """
    blob = unarmor(armored)
    if not blob.startswith(MAGIC):
        msg = "the signature blob has no SSHSIG preamble"
        raise SshsigError(msg)
    offset = len(MAGIC)
    if offset + 4 > len(blob):
        msg = "the signature blob has no version"
        raise SshsigError(msg)
    (version,) = struct.unpack_from(">I", blob, offset)
    if version != SIG_VERSION:
        msg = f"unsupported SSHSIG version {version}"
        raise SshsigError(msg)
    offset += 4
    key_blob, offset = _read_string(blob, offset)
    sig_namespace, offset = _read_string(blob, offset)
    reserved, offset = _read_string(blob, offset)
    hash_name, offset = _read_string(blob, offset)
    inner, offset = _read_string(blob, offset)
    if offset != len(blob):
        msg = "trailing bytes after the SSHSIG signature"
        raise SshsigError(msg)

    if sig_namespace != namespace.encode():
        # A signature made for another purpose must not verify here (that is what the namespace
        # is for), so this is a refusal rather than a mismatch.
        return False
    if key_blob != public_key_blob(authorized_key):
        return False
    hasher = HASHES.get(hash_name)
    if hasher is None:
        msg = f"unsupported hash algorithm {hash_name!r}"
        raise SshsigError(msg)

    algorithm, sig_offset = _read_string(inner, 0)
    raw_signature, sig_offset = _read_string(inner, sig_offset)
    if algorithm != KEY_TYPE or sig_offset != len(inner):
        msg = f"unsupported signature algorithm {algorithm!r}; only ssh-ed25519 is accepted"
        raise SshsigError(msg)
    if len(raw_signature) != ED25519_SIG_BYTES:
        msg = "malformed ed25519 signature"
        raise SshsigError(msg)

    signed = (
        MAGIC
        + _string(sig_namespace)
        + _string(reserved)
        + _string(hash_name)
        + _string(hasher(payload).digest())
    )
    try:
        _ed25519_key(key_blob).verify(raw_signature, signed)
    except InvalidSignature:
        return False
    return True
