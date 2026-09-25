"""F16-T7 / R8, R10, AC9 (the logic), AC10 (the not-attempted rule): the connection runner.

The runner is driven end to end against the real api on a loopback port, with a stand-in harness
(``fixtures/clients/fake_harness.py``) built on the official MCP client. What these tests pin is
where the verdict comes from: the server's record. A harness that prints "Connected" and exits 0
without connecting fails; a token form that sends the variable unexpanded fails; a missing binary
or credential is ``not-attempted`` and never counts as a pass.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from opn_gate import clients

ROOT = Path(__file__).resolve().parents[2]
FAKE = Path(__file__).parent / "fixtures" / "clients" / "fake_harness.py"


def _load_runner() -> Any:
    path = ROOT / "gate" / "tools" / "harness_check.py"
    spec = importlib.util.spec_from_file_location("harness_check", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def registry(mode: str, **list_check: Any) -> clients.Registry:
    """One synthetic entry whose "binary" is the stand-in in ``mode``."""
    real = clients.load()
    command = f"{sys.executable} {FAKE} {mode} fake.json"
    return clients.parse(
        {
            "schema": clients.REGISTRY_SCHEMA,
            "server": real.server,
            "token_env": real.token_env,
            "entries": [
                {
                    "id": "fake",
                    "name": "Fake",
                    "transport": "streamable-http",
                    "snippets": [
                        {
                            "title": "reads",
                            "kind": "file",
                            "path": "fake.json",
                            "scope": "project",
                            "format": "json",
                            "auth": "none",
                            "required_keys": ["url"],
                            "template": '{"url": "{{mcp_url}}"}',
                        },
                        {
                            "title": "writes",
                            "kind": "file",
                            "path": "fake.json",
                            "scope": "project",
                            "format": "json",
                            "auth": "bearer",
                            "required_keys": ["url", "headers"],
                            "template": (
                                '{"url": "{{mcp_url}}", '
                                '"headers": {"Authorization": "Bearer ${{{token_env}}}"}}'
                            ),
                        },
                    ],
                    "instructions": {"reads_agents_md": True, "how": "reads it"},
                    "headless": {"template": "true", "approve": "nothing"},
                    "list_check": {"template": command, "rpc": ["initialize", "tools/list"]}
                    | list_check,
                    "profile": {
                        "sources": [
                            {"url": "https://example.test", "accessed": "2026-09-25", "claim": "x"}
                        ]
                    },
                    "verified": None,
                }
            ],
        }
    )


@pytest.fixture(scope="module")
def served() -> Iterator[Any]:
    s = runner.serve()
    yield s
    s.stop()


def run(served: Any, reg: clients.Registry, auth: str = "none") -> Any:
    return runner.check(served, reg, reg.by_id("fake"), auth=auth)


def test_a_connecting_harness_passes(served: Any) -> None:
    result = run(served, registry("connect", expect="Connected"))
    assert result.state == runner.PASS, result
    assert {"initialize", "tools/list"} <= set(result.rpc_seen)


def test_a_harness_that_says_connected_and_is_not_fails(served: Any) -> None:
    """The oracle is the server: exit 0 and the word "Connected" are not a connection."""
    result = run(served, registry("lie", expect="Connected"))
    assert result.state == runner.FAIL
    assert "saw no initialize, tools/list" in result.reason


def test_the_bearer_arrives_expanded(served: Any) -> None:
    result = run(served, registry("connect"), auth="bearer")
    assert result.state == runner.PASS, result
    assert result.bearer == "expected"


def test_an_unexpanded_bearer_fails(served: Any) -> None:
    """A harness that sends ``Bearer ${OPN_TOKEN}`` literally: named, never a pass."""
    result = run(served, registry("raw-header"), auth="bearer")
    assert result.state == runner.FAIL
    assert result.bearer == "unexpanded"


def test_the_expected_output_is_required_too(served: Any) -> None:
    result = run(served, registry("connect", expect="text the harness never prints"))
    assert result.state == runner.FAIL
    assert "does not contain" in result.reason


def test_missing_binary_is_not_attempted(served: Any) -> None:
    reg = registry("connect")
    entry = reg.by_id("fake")
    missing = clients.Entry(**{**entry.__dict__, "list_check": "no-such-harness-binary mcp list"})
    result = runner.check(served, reg, missing)
    assert result.state == runner.NOT_ATTEMPTED
    assert "no-such-harness-binary is not installed" in result.reason


def test_missing_credential_is_not_attempted(served: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPN_TEST_HARNESS_CREDENTIAL", raising=False)
    result = run(served, registry("connect", requires_env=["OPN_TEST_HARNESS_CREDENTIAL"]))
    assert result.state == runner.NOT_ATTEMPTED
    assert "OPN_TEST_HARNESS_CREDENTIAL" in result.reason


def test_not_attempted_is_not_pass() -> None:
    """AC10 / R10: a verdict with anything not attempted is not a pass, and neither is none."""
    ok = runner.Result("a", "none", runner.PASS, "")
    skipped = runner.Result("b", "none", runner.NOT_ATTEMPTED, "no binary")
    assert runner.verdict([ok])
    assert not runner.verdict([ok, skipped])
    assert not runner.verdict([])


def test_program_skips_environment_assignments() -> None:
    assert runner.program("GEMINI_CLI_TRUST_WORKSPACE=true gemini mcp list") == "gemini"
    assert runner.program("claude mcp list") == "claude"


def test_the_record_keeps_no_token(served: Any) -> None:
    """C9: the recorder classifies the bearer and never stores its value."""
    run(served, registry("connect"), auth="bearer")
    for seen in served.recorder.seen:
        assert seen.bearer in {"none", "expected", "unexpanded", "other"}
        assert not any(len(v) >= 40 for v in vars(seen).values() if isinstance(v, str))


def _report(tmp: Path, name: str, *results: Any) -> Path:
    path = tmp / name
    path.write_text(json.dumps({"results": [dict(vars(r)) for r in results]}), encoding="utf-8")
    return path


def test_drift_names_versions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC11 / R11: the latest release failing where the pin passes is red, naming both."""
    pinned = _report(
        tmp_path, "pinned.json", runner.Result("gemini-cli", "none", runner.PASS, "ok", "0.61.0")
    )
    latest = _report(
        tmp_path,
        "latest.json",
        runner.Result("gemini-cli", "none", runner.FAIL, "the server saw no initialize", "0.62.0"),
    )
    assert runner.main(["--compare", str(pinned), str(latest)]) == 1
    out = capsys.readouterr().out
    assert "gemini-cli (none): passes at 0.61.0, fail at 0.62.0" in out


def test_drift_writes_nothing(tmp_path: Path) -> None:
    """Both passing: green, and the comparison touches no file."""
    same = runner.Result("claude-code", "none", runner.PASS, "ok", "2.1.282")
    pinned = _report(tmp_path, "pinned.json", same)
    latest = _report(tmp_path, "latest.json", same)
    before = {p: p.stat().st_mtime_ns for p in tmp_path.iterdir()}
    assert runner.main(["--compare", str(pinned), str(latest)]) == 0
    assert {p: p.stat().st_mtime_ns for p in tmp_path.iterdir()} == before
