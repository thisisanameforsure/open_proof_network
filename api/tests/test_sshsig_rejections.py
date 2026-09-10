"""SSHSIG reader refusals by field (F06-R5, R6; C7).

``test_sshsig.py`` proves the reader against real ``ssh-keygen`` output and that truncation is
an error. These take a real signature apart field by field and put one wrong thing back, so each
refusal in ``opn_api.sshsig`` is reached on purpose rather than by whatever a truncation happened
to hit.
"""

from __future__ import annotations

import base64
import struct
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from opn_api import sshsig
from opn_gate.signer import NAMESPACE, SshKeygenSigner

PAYLOAD = b'{"schema": "attestation/v4", "verdict": "pass"}'


@pytest.fixture(scope="module")
def keypair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    d = tmp_path_factory.mktemp("sshsig")
    key = d / "id_test"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-test"],
        check=True,
    )
    return key, (d / "id_test.pub").read_text().strip()


@dataclass(frozen=True)
class Fields:
    version: int
    key: bytes
    namespace: bytes
    reserved: bytes
    hash_name: bytes
    algorithm: bytes
    signature: bytes


def take_apart(armored: str) -> Fields:
    blob = sshsig.unarmor(armored)
    assert blob.startswith(sshsig.MAGIC)
    offset = len(sshsig.MAGIC)
    (version,) = struct.unpack_from(">I", blob, offset)
    offset += 4
    strings = []
    for _ in range(5):
        (length,) = struct.unpack_from(">I", blob, offset)
        strings.append(blob[offset + 4 : offset + 4 + length])
        offset += 4 + length
    key, namespace, reserved, hash_name, inner = strings
    (alg_len,) = struct.unpack_from(">I", inner, 0)
    algorithm = inner[4 : 4 + alg_len]
    (sig_len,) = struct.unpack_from(">I", inner, 4 + alg_len)
    signature = inner[8 + alg_len : 8 + alg_len + sig_len]
    return Fields(version, key, namespace, reserved, hash_name, algorithm, signature)


def put_together(f: Fields) -> str:
    s = sshsig._string
    inner = s(f.algorithm) + s(f.signature)
    blob = (
        sshsig.MAGIC
        + struct.pack(">I", f.version)
        + s(f.key)
        + s(f.namespace)
        + s(f.reserved)
        + s(f.hash_name)
        + s(inner)
    )
    body = base64.b64encode(blob).decode()
    return f"{sshsig.ARMOR_BEGIN}\n{body}\n{sshsig.ARMOR_END}\n"


def test_round_trip_is_faithful(keypair: tuple[Path, str]) -> None:
    """The helper reassembles what it took apart; otherwise every case below is meaningless."""
    key, pub = keypair
    good = SshKeygenSigner().sign(PAYLOAD, key, "service").value
    assert sshsig.unarmor(put_together(take_apart(good))) == sshsig.unarmor(good)
    assert sshsig.verify(PAYLOAD, put_together(take_apart(good)), pub, namespace=NAMESPACE)


@pytest.mark.parametrize(
    ("label", "change", "fragment"),
    [
        ("version 2", {"version": 2}, "version"),
        ("md5 hash", {"hash_name": b"md5"}, "hash algorithm"),
        ("rsa inner algorithm", {"algorithm": b"ssh-rsa"}, "signature algorithm"),
        ("63-byte signature", {"signature": b"\x00" * 63}, "malformed ed25519 signature"),
        ("65-byte signature", {"signature": b"\x00" * 65}, "malformed ed25519 signature"),
    ],
)
def test_wrong_algorithm_or_version_is_an_error_not_false(
    keypair: tuple[Path, str], label: str, change: dict[str, object], fragment: str
) -> None:
    """C7: an unexpected algorithm on a trusted signature is a refusal that names itself."""
    key, pub = keypair
    good = take_apart(SshKeygenSigner().sign(PAYLOAD, key, "service").value)
    with pytest.raises(sshsig.SshsigError, match=fragment):
        sshsig.verify(PAYLOAD, put_together(replace(good, **change)), pub, namespace=NAMESPACE)  # type: ignore[arg-type]


def test_altered_reserved_field_does_not_verify(keypair: tuple[Path, str]) -> None:
    """The reserved string is inside the signed bytes; changing it is a mismatch, not garbage."""
    key, pub = keypair
    good = take_apart(SshKeygenSigner().sign(PAYLOAD, key, "service").value)
    assert not sshsig.verify(
        PAYLOAD, put_together(replace(good, reserved=b"x")), pub, namespace=NAMESPACE
    )


def test_key_blob_of_another_type_is_refused_by_the_key_check(keypair: tuple[Path, str]) -> None:
    """A signature whose embedded key is not the committed key is False before any algorithm
    is examined — the committed key decides, never the signature's own claim about its key."""
    key, pub = keypair
    good = take_apart(SshKeygenSigner().sign(PAYLOAD, key, "service").value)
    rsa_blob = sshsig._string(b"ssh-rsa") + sshsig._string(b"\x01\x00\x01")
    assert not sshsig.verify(
        PAYLOAD, put_together(replace(good, key=rsa_blob)), pub, namespace=NAMESPACE
    )


def test_sha512_is_accepted_as_a_hash(keypair: tuple[Path, str]) -> None:
    """Both of OpenSSH's hash names are legal; the reader must not be sha256-only by accident."""
    key, pub = keypair
    signed = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, "-O", "hashalg=sha512", "-"],
        input=PAYLOAD,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert take_apart(signed).hash_name == b"sha512"
    assert sshsig.verify(PAYLOAD, signed, pub, namespace=NAMESPACE)


def test_signature_over_a_different_payload_of_the_same_length_is_false(
    keypair: tuple[Path, str],
) -> None:
    key, pub = keypair
    signature = SshKeygenSigner().sign(PAYLOAD, key, "service").value
    other = PAYLOAD[:-2] + b'"}'[::-1]
    assert len(other) == len(PAYLOAD)
    assert not sshsig.verify(other, signature, pub, namespace=NAMESPACE)


def test_public_key_line_with_a_wrong_length_blob_is_refused() -> None:
    short = base64.b64encode(sshsig._string(b"ssh-ed25519") + sshsig._string(b"\x00" * 31))
    with pytest.raises(sshsig.SshsigError, match="malformed"):
        sshsig.fingerprint(f"ssh-ed25519 {short.decode()} comment")
