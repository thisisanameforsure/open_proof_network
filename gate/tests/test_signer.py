"""F00-T6: the Signer seam over the platform ssh-keygen (fast tier: no Lean needed)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from opn_gate import signer
from opn_gate.signer import SshKeygenSigner


@pytest.fixture(scope="module")
def keypair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    d = tmp_path_factory.mktemp("keys")
    key = d / "id_test"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-test"],
        check=True,
    )
    return key, (d / "id_test.pub").read_text().strip()


def test_sign_and_verify_roundtrip(keypair: tuple[Path, str]) -> None:
    key, pub = keypair
    s = SshKeygenSigner()
    sig = s.sign(b'{"a": 1}\n', key, "contributor")
    assert sig.kind == "contributor"
    assert sig.key_id.startswith("SHA256:")
    assert sig.key_id == s.fingerprint(pub)
    assert "-----BEGIN SSH SIGNATURE-----" in sig.value
    assert s.verify(b'{"a": 1}\n', sig.value, pub)
    assert not s.verify(b'{"a": 2}\n', sig.value, pub)


def test_verify_rejects_other_key(keypair: tuple[Path, str], tmp_path: Path) -> None:
    key, _pub = keypair
    other = tmp_path / "other"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
    sig = SshKeygenSigner().sign(b"payload", key, "gate")
    assert not SshKeygenSigner().verify(b"payload", sig.value, (tmp_path / "other.pub").read_text())


def test_missing_key_is_a_signer_error(tmp_path: Path) -> None:
    with pytest.raises(signer.SignerError):
        SshKeygenSigner().sign(b"x", tmp_path / "nope", "contributor")


def test_public_key_derived_without_pub_file(keypair: tuple[Path, str], tmp_path: Path) -> None:
    key, pub = keypair
    lone = tmp_path / "lone"
    lone.write_bytes(key.read_bytes())
    lone.chmod(0o600)
    assert signer.public_key_for(lone).split()[:2] == pub.split()[:2]
