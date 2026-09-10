"""F00-T6: the Signer seam over the platform ssh-keygen (fast tier: no Lean needed)."""

from __future__ import annotations

import subprocess
import tempfile
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


def test_verify_rejects_malformed_signature_and_key(keypair: tuple[Path, str]) -> None:
    """A signature that is not an SSH signature block, an empty one, or a public key that is
    not a key all verify as False — never as an exception a caller might mistake for a pass."""
    key, pub = keypair
    s = SshKeygenSigner()
    sig = s.sign(b"payload", key, "gate")
    assert not s.verify(b"payload", "not a signature", pub)
    assert not s.verify(b"payload", "", pub)
    assert not s.verify(b"payload", sig.value.replace("BEGIN SSH", "BEGIN XXX"), pub)
    assert not s.verify(b"payload", sig.value, "ssh-ed25519 AAAA notakey")
    assert not s.verify(b"payload", sig.value, "")
    assert s.verify(b"payload", sig.value, pub)  # the same inputs, untampered, still verify


def test_signature_is_bound_to_the_namespace(keypair: tuple[Path, str]) -> None:
    """The gate signs in its own namespace: a signature made over the same bytes in another
    namespace does not verify as an attestation signature."""
    key, pub = keypair
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp) / "payload"
        payload.write_bytes(b"payload")
        subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "file", str(payload)], check=True
        )
        foreign = (Path(tmp) / "payload.sig").read_text()
    assert "BEGIN SSH SIGNATURE" in foreign
    assert not SshKeygenSigner().verify(b"payload", foreign, pub)


def test_fingerprint_of_garbage_is_a_signer_error() -> None:
    with pytest.raises(signer.SignerError, match="ssh-keygen -lf failed"):
        SshKeygenSigner().fingerprint("not a public key")


def test_public_key_for_missing_key_is_a_signer_error(tmp_path: Path) -> None:
    with pytest.raises(signer.SignerError, match="cannot derive the public key"):
        signer.public_key_for(tmp_path / "nope")


def scripted_keygen(tmp_path: Path, body: str) -> str:
    script = tmp_path / "ssh-keygen"
    script.write_text("#!/bin/sh\n" + body)
    script.chmod(0o755)
    return str(script)


def test_keygen_failures_surface_as_signer_errors(
    keypair: tuple[Path, str], tmp_path: Path
) -> None:
    """Every non-zero or malformed answer from the binary is a SignerError naming the call;
    `verify` alone answers False, because a refusal to verify is a failed verification."""
    key, pub = keypair
    failing = SshKeygenSigner(scripted_keygen(tmp_path, 'echo "simulated" >&2\nexit 1\n'))
    with pytest.raises(signer.SignerError, match="sign failed: simulated"):
        failing.sign(b"x", key, "contributor")
    with pytest.raises(signer.SignerError, match="-lf failed: simulated"):
        failing.fingerprint(pub)
    assert failing.verify(b"x", "sig", pub) is False

    (tmp_path / "s").mkdir()
    silent = SshKeygenSigner(scripted_keygen(tmp_path / "s", "echo hello\nexit 0\n"))
    with pytest.raises(signer.SignerError, match="unexpected fingerprint output"):
        silent.fingerprint(pub)


def test_public_key_derived_without_pub_file(keypair: tuple[Path, str], tmp_path: Path) -> None:
    key, pub = keypair
    lone = tmp_path / "lone"
    lone.write_bytes(key.read_bytes())
    lone.chmod(0o600)
    assert signer.public_key_for(lone).split()[:2] == pub.split()[:2]
