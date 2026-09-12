"""F00-T1: the one config module (R17; C6, C8)."""

from __future__ import annotations

import os
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
        {"OPN_RUNNER": ""},
        {"OPN_RUNNER": "Local"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "many"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "0"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "-1"},
        {"OPN_DIAGNOSTIC_MAX_BYTES": ""},
        {"OPN_DIAGNOSTIC_MAX_BYTES": "1.5"},
    ],
)
def test_bad_values_fail_at_load(env: dict[str, str]) -> None:
    with pytest.raises(config.ConfigError) as info:
        config.load(env)
    key = next(iter(env))
    assert key in str(info.value)  # the diagnostic names the variable


def test_bad_log_level_fails_at_load() -> None:
    """C7, F08-Q18: an unknown OPN_LOG_LEVEL is refused at load, naming the variable, and a
    known one is accepted in any case and normalised to the name logging knows."""
    with pytest.raises(config.ConfigError, match="OPN_LOG_LEVEL"):
        config.load({"OPN_LOG_LEVEL": "LOUD"})
    assert config.load({"OPN_LOG_LEVEL": "debug"}).log_level == "DEBUG"


def test_paths_expand_the_home_directory_and_pr_author_defaults() -> None:
    s = config.load(
        {"OPN_ELAN_HOME": "~/elan-x", "OPN_LEAN_PKG_BIN": "~/pkg/bin", "OPN_PR_AUTHOR": "alice"}
    )
    assert s.elan_home == Path.home() / "elan-x"
    assert s.lean_pkg_bin == Path.home() / "pkg" / "bin"
    assert s.pr_author == "alice"
    assert config.load({}).lean_pkg_bin == config.DEFAULT_LEAN_PKG_BIN
    assert config.load({}).pr_author is None
    assert config.load({"OPN_PR_AUTHOR": ""}).pr_author is None
    assert config.DEFAULT_LEAN_PKG_BIN.parts[-4:] == ("lean", ".lake", "build", "bin")


def test_child_environment_adds_without_mutating(monkeypatch: pytest.MonkeyPatch) -> None:
    """The toolchain seam's child gets the inherited environment plus its extras; the parent's
    environment is untouched, and `None` extras copy it as is."""
    monkeypatch.setenv("OPN_TEST_MARKER", "parent")
    child = config.child_environment({"LEAN_PATH": "/x", "OPN_TEST_MARKER": "child"})
    assert child["LEAN_PATH"] == "/x" and child["OPN_TEST_MARKER"] == "child"
    assert os.environ["OPN_TEST_MARKER"] == "parent"
    assert "LEAN_PATH" not in os.environ or os.environ["LEAN_PATH"] != "/x"
    plain = config.child_environment(None)
    assert plain["OPN_TEST_MARKER"] == "parent" and plain is not os.environ


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


# --- F11-R9 §6: the Stage 0 listed-target count is config, not a constant (C6) ------------------


def test_listed_targets_max_defaults_and_reads() -> None:
    assert config.load({}).listed_targets_max == config.DEFAULT_LISTED_TARGETS_MAX == 5
    assert config.load({"OPN_LISTED_TARGETS_MAX": "12"}).listed_targets_max == 12
    assert config.load({"OPN_LISTED_TARGETS_MAX": "0"}).listed_targets_max == 0


@pytest.mark.parametrize("value", ["five", "-1", "", "3.5"])
def test_a_bad_listed_targets_max_fails_at_load(value: str) -> None:
    """C7: a configured value is refused when it is read, never later."""
    with pytest.raises(config.ConfigError, match="OPN_LISTED_TARGETS_MAX"):
        config.load({"OPN_LISTED_TARGETS_MAX": value})


def test_the_count_is_not_in_the_repr_by_accident() -> None:
    """C8: the repr exists so secrets stay out of it; a new field has to be in it deliberately."""
    assert "listed_targets_max=5" in repr(config.load({}))
    assert "gate_signing_key=None" in repr(config.load({}))


def test_mathlib_home_is_config_with_a_documented_default(tmp_path: Path) -> None:
    """F11-R6: where Mathlib checkouts live is read from the environment, once, with a default
    under the home directory; the image sets its own (gate/Dockerfile)."""
    assert config.load({}).mathlib_home == config.DEFAULT_MATHLIB_HOME
    assert Path.home() / ".opn" / "mathlib" == config.DEFAULT_MATHLIB_HOME
    custom = config.load({"OPN_MATHLIB_HOME": str(tmp_path / "ml")})
    assert custom.mathlib_home == tmp_path / "ml"
    assert "mathlib_home=" in repr(custom) and str(tmp_path / "ml") in repr(custom)


# --- F12-R6, R7, Q5: the model is config, its key is a secret (C6, C8) ---------------------------


def test_model_is_config_and_its_key_is_a_secret() -> None:
    assert config.load({}).model == config.DEFAULT_MODEL == "claude-opus-5"
    assert config.load({}).model_api_key is None
    s = config.load({"OPN_MODEL": "claude-sonnet-5", "OPN_MODEL_API_KEY": "sk-ant-SECRET"})
    assert s.model == "claude-sonnet-5" and s.model_api_key == "sk-ant-SECRET"
    assert "sk-ant-SECRET" not in repr(s) and "model_api_key=<set>" in repr(s)
    assert config.load({"OPN_MODEL_API_KEY": ""}).model_api_key is None
    assert "model_api_key" in config.SECRET_NAMES


@pytest.mark.parametrize("value", ["sixty", "0", "-5", "", "inf"])
def test_a_bad_qa_budget_fails_at_load(value: str) -> None:
    with pytest.raises(config.ConfigError, match="OPN_QA_ATTEMPT_BUDGET_S"):
        config.load({"OPN_QA_ATTEMPT_BUDGET_S": value})
    with pytest.raises(config.ConfigError, match="OPN_QA_SUBJECT_BUDGET_S"):
        config.load({"OPN_QA_SUBJECT_BUDGET_S": value})


def test_qa_budgets_default_and_read() -> None:
    s = config.load({})
    assert (s.qa_attempt_budget_s, s.qa_subject_budget_s) == (60.0, 300.0)
    s = config.load({"OPN_QA_ATTEMPT_BUDGET_S": "7.5", "OPN_QA_SUBJECT_BUDGET_S": "40"})
    assert (s.qa_attempt_budget_s, s.qa_subject_budget_s) == (7.5, 40.0)
