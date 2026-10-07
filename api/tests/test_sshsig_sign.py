"""F23-T5: the api's SSHSIG *writer*, for the network's approval key (D-32 v3.33; C8).

The Lambda has no ``ssh-keygen`` (F06-Q6), so the service signs in Python. That is only safe if
OpenSSH agrees, so every signature made here is checked by the real ``ssh-keygen -Y verify`` (the
gate's verifier, ``SshKeygenSigner``) as well as by this module's own reader.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from opn_api import sshsig
from opn_gate.signer import NAMESPACE, SshKeygenSigner

PAYLOAD = b'{"schema": "steward/v2", "action": "commit"}'


def keygen(directory: Path, name: str, *extra: str) -> tuple[str, str]:
    key = directory / name
    subprocess.run(
        ["ssh-keygen", "-q", "-N", "", "-f", str(key), "-C", "opn-approval", *extra], check=True
    )
    return key.read_text(), (directory / f"{name}.pub").read_text().strip()


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    return keygen(tmp_path_factory.mktemp("approval"), "approval", "-t", "ed25519")


def test_ssh_keygen_verifies_a_python_signature(approval: tuple[str, str]) -> None:
    private, public = approval
    armored = sshsig.sign(PAYLOAD, private, namespace=NAMESPACE)
    assert SshKeygenSigner().verify(PAYLOAD, armored, public)
    assert not SshKeygenSigner().verify(PAYLOAD + b" ", armored, public)


def test_it_is_byte_for_byte_what_ssh_keygen_makes(tmp_path: Path) -> None:
    """ed25519 is deterministic, so the same key and payload give ssh-keygen's exact block."""
    private, _ = keygen(tmp_path, "same", "-t", "ed25519")
    made = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(tmp_path / "same"), "-n", NAMESPACE, "-"],
        input=PAYLOAD,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert sshsig.sign(PAYLOAD, private, namespace=NAMESPACE) == made


def test_the_reader_verifies_it_too(approval: tuple[str, str]) -> None:
    private, public = approval
    armored = sshsig.sign(PAYLOAD, private, namespace=NAMESPACE)
    assert sshsig.verify(PAYLOAD, armored, public, namespace=NAMESPACE)
    assert not sshsig.verify(PAYLOAD, armored, public, namespace="git")


def test_the_armor_is_the_one_the_schemas_accept(approval: tuple[str, str]) -> None:
    armored = sshsig.sign(PAYLOAD, approval[0], namespace=NAMESPACE)
    assert armored.startswith(sshsig.ARMOR_BEGIN + "\n")
    assert armored.endswith(sshsig.ARMOR_END + "\n")
    assert all(len(line) <= 76 for line in armored.splitlines())


def test_the_public_half_is_derived_from_the_private_key(approval: tuple[str, str]) -> None:
    private, public = approval
    derived = sshsig.public_key_of(private)
    assert derived.split()[:2] == public.split()[:2]
    assert sshsig.fingerprint(derived) == sshsig.fingerprint(public)


def test_a_key_that_is_not_ed25519_is_refused(tmp_path: Path) -> None:
    private, _ = keygen(tmp_path, "ecdsa", "-t", "ecdsa")
    with pytest.raises(sshsig.SshsigError):
        sshsig.sign(PAYLOAD, private, namespace=NAMESPACE)


def test_a_passphrase_key_or_garbage_is_refused(tmp_path: Path) -> None:
    key = tmp_path / "locked"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "secret", "-f", str(key)], check=True
    )
    for text in (key.read_text(), "not a key"):
        with pytest.raises(sshsig.SshsigError):
            sshsig.public_key_of(text)
