"""F00-T1: the one config module (R17; C6, C8)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from opn_gate import config

GATE_PKG = Path(__file__).resolve().parents[1] / "opn_gate"
ENV_ACCESS = re.compile(r"\bos\.environ\b|\bos\.getenv\b|\bos\.putenv\b|\benviron\[")


def test_defaults_documented_and_applied() -> None:
    s = config.load({})
    assert s.runner == "local"
    assert s.log_level == "INFO"
    assert s.elan_home == Path.home() / ".elan"
    assert s.diagnostic_max_bytes == 8192
    assert s.gate_signing_key is None
    assert s.precheck_signing_key is None


def test_env_overrides() -> None:
    s = config.load(
        {
            "OPN_RUNNER": "hosted",
            "OPN_LOG_LEVEL": "DEBUG",
            "OPN_ELAN_HOME": "/opt/elan",
            "OPN_DIAGNOSTIC_MAX_BYTES": "1024",
            "OPN_GATE_SIGNING_KEY": "-----BEGIN OPENSSH PRIVATE KEY-----\nabc",
        }
    )
    assert s.runner == "hosted"
    assert s.log_level == "DEBUG"
    assert s.elan_home == Path("/opt/elan")
    assert s.diagnostic_max_bytes == 1024
    assert s.gate_signing_key is not None and s.gate_signing_key.startswith("-----BEGIN")


def test_empty_secret_is_absent() -> None:
    assert config.load({"OPN_GATE_SIGNING_KEY": ""}).gate_signing_key is None


@pytest.mark.parametrize(
    "env",
    [
        {"OPN_RUNNER": "cloud"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "many"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "0"},
    ],
)
def test_bad_values_fail_at_load(env: dict[str, str]) -> None:
    with pytest.raises(config.ConfigError):
        config.load(env)


def test_repr_never_shows_secrets() -> None:
    s = config.load({"OPN_GATE_SIGNING_KEY": "SUPERSECRET", "OPN_PRECHECK_SIGNING_KEY": "S2"})
    text = repr(s)
    assert "SUPERSECRET" not in text
    assert "S2" not in text
    assert "<set>" in text


def test_only_config_module_reads_the_environment() -> None:
    """R17: nothing in opn_gate touches os.environ except config.py."""
    offenders = [
        str(p.relative_to(GATE_PKG))
        for p in GATE_PKG.rglob("*.py")
        if p.name != "config.py" and ENV_ACCESS.search(p.read_text())
    ]
    assert offenders == []
