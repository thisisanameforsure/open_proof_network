"""F06-T3: the api's SSHSIG reader (F06-R5, R6).

The gate signs with ``ssh-keygen``; the api verifies without it. That is only safe if the two
agree exactly, so every test here checks the reader against real ``ssh-keygen`` output rather
than against a fixture this repository generated.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest

from opn_api import sshsig
from opn_gate.signer import NAMESPACE, SshKeygenSigner

PAYLOAD = b'{"schema": "attestation/v3", "verdict": "pass"}'


@pytest.fixture(scope="module")
def keypair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    d = tmp_path_factory.mktemp("sshsig")
    key = d / "id_test"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-test"],
        check=True,
    )
    return key, (d / "id_test.pub").read_text().strip()


def test_fingerprint_matches_ssh_keygen(keypair: tuple[Path, str]) -> None:
    key, pub = keypair
    listed = subprocess.run(
        ["ssh-keygen", "-lf", str(key.with_suffix(".pub"))],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()[1]
    assert sshsig.fingerprint(pub) == listed
    assert sshsig.fingerprint(pub) == SshKeygenSigner().fingerprint(pub)


def test_verifies_a_real_ssh_keygen_signature(keypair: tuple[Path, str]) -> None:
    key, pub = keypair
    signature = SshKeygenSigner().sign(PAYLOAD, key, "service")
    assert sshsig.verify(PAYLOAD, signature.value, pub, namespace=NAMESPACE)
    assert not sshsig.verify(PAYLOAD + b" ", signature.value, pub, namespace=NAMESPACE)


def test_the_namespace_is_part_of_what_is_verified(keypair: tuple[Path, str]) -> None:
    """A signature made for another purpose must not verify as an attestation."""
    key, pub = keypair
    elsewhere = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "git", "-"],
        input=PAYLOAD,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert sshsig.verify(PAYLOAD, elsewhere, pub, namespace="git")
    assert not sshsig.verify(PAYLOAD, elsewhere, pub, namespace=NAMESPACE)


def test_another_key_does_not_verify(keypair: tuple[Path, str], tmp_path: Path) -> None:
    key, _pub = keypair
    other = tmp_path / "other"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
    signature = SshKeygenSigner().sign(PAYLOAD, key, "service")
    assert not sshsig.verify(
        PAYLOAD, signature.value, (tmp_path / "other.pub").read_text(), namespace=NAMESPACE
    )


def test_malformed_input_is_an_error_not_a_false_verdict(keypair: tuple[Path, str]) -> None:
    """C7: garbage is named as garbage; it never quietly reads as "does not verify"."""
    key, pub = keypair
    good = SshKeygenSigner().sign(PAYLOAD, key, "service").value
    for bad in (
        "just some text",
        "-----BEGIN SSH SIGNATURE-----\n!!!!\n-----END SSH SIGNATURE-----",
        _reblob(good, lambda raw: raw[: len(raw) // 2]),
        _reblob(good, lambda raw: raw + b"\x00"),
        _reblob(good, lambda raw: raw[:6] + b"\x00\x00\x00\x09" + raw[10:]),
    ):
        with pytest.raises(sshsig.SshsigError):
            sshsig.verify(PAYLOAD, bad, pub, namespace=NAMESPACE)


def test_a_public_key_line_must_be_ed25519() -> None:
    for bad in ("", "ssh-rsa AAAAB3NzaC1yc2E= someone", "ssh-ed25519 not-base64", "ssh-ed25519"):
        with pytest.raises(sshsig.SshsigError):
            sshsig.fingerprint(bad)


def _reblob(armored: str, mangle: object) -> str:
    """Re-armor a signature whose blob has been altered by ``mangle``."""
    raw = sshsig.unarmor(armored)
    assert callable(mangle)
    body = base64.b64encode(mangle(raw)).decode()
    return f"{sshsig.ARMOR_BEGIN}\n{body}\n{sshsig.ARMOR_END}\n"
