"""F16-T2 / AC1, AC13: the connector registry validates, and each of its rules refuses by name.

The registry is network configuration the site and the guide render (F16-R1). Its rules are
what keep a connector a client of the plain protocol: no host in a template (R2), no token in
one (R6), no placeholder beyond the four R13 allows, a sourced profile for every harness, and a
read-only snippet for every harness. Each refusal below breaks exactly one rule and asserts the
message names it, so a rule that silently stops firing fails here.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import clients

FIXTURES = Path(__file__).parent / "fixtures" / "clients"


def raw() -> dict[str, Any]:
    doc = yaml.safe_load(clients.REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def test_registry_valid() -> None:
    assert clients.problems(raw()) == []
    registry = clients.load()
    assert registry.server == "open-proof-network"
    assert registry.token_env == "OPN_TOKEN"  # noqa: S105 — a variable's name, not a secret
    assert {e.id for e in registry.entries} >= {
        "claude-code",
        "codex-cli",
        "gemini-cli",
        "copilot",
        "cursor",
    }


def _entry(doc: dict[str, Any], entry_id: str) -> dict[str, Any]:
    return next(e for e in doc["entries"] if e["id"] == entry_id)


def _break_host(doc: dict[str, Any]) -> None:
    _entry(doc, "claude-code")["snippets"][0]["template"] = (
        "claude mcp add --transport http {{server}} https://api.example.org/mcp"
    )


def _break_token(doc: dict[str, Any]) -> None:
    _entry(doc, "cursor")["snippets"][1]["template"] = (
        '{"mcpServers": {"{{server}}": {"url": "{{mcp_url}}", '
        '"headers": {"Authorization": "Bearer ' + "A" * 43 + '"}}}}'
    )


def _break_bearer_literal(doc: dict[str, Any]) -> None:
    _entry(doc, "cursor")["snippets"][1]["template"] = (
        '{"mcpServers": {"{{server}}": {"url": "{{mcp_url}}", '
        '"headers": {"Authorization": "Bearer paste-it-here"}}}}'
    )


def _break_placeholder(doc: dict[str, Any]) -> None:
    _entry(doc, "codex-cli")["snippets"][0]["template"] = "codex mcp add {{server}} --url {{api}}"


def _break_prompt_outside_headless(doc: dict[str, Any]) -> None:
    _entry(doc, "codex-cli")["list_check"]["template"] = 'codex exec "{{prompt}}"'


def _break_transport(doc: dict[str, Any]) -> None:
    _entry(doc, "gemini-cli")["transport"] = "sse"


def _break_bridge(doc: dict[str, Any]) -> None:
    _entry(doc, "gemini-cli")["transport"] = "stdio-bridge"


def _break_sources(doc: dict[str, Any]) -> None:
    _entry(doc, "copilot")["profile"]["sources"] = []


def _break_source_url(doc: dict[str, Any]) -> None:
    _entry(doc, "copilot")["profile"]["sources"][0]["url"] = "http://insecure.example/docs"


def _break_file_keys(doc: dict[str, Any]) -> None:
    del _entry(doc, "claude-code")["snippets"][1]["required_keys"]


def _break_no_read_snippet(doc: dict[str, Any]) -> None:
    entry = _entry(doc, "cursor")
    entry["snippets"] = [s for s in entry["snippets"] if s["auth"] != "none"]


def _break_duplicate(doc: dict[str, Any]) -> None:
    doc["entries"].append(copy.deepcopy(_entry(doc, "cursor")))


def _break_server_name(doc: dict[str, Any]) -> None:
    doc["server"] = "open_proof"


def _break_profile_server_chars(doc: dict[str, Any]) -> None:
    _entry(doc, "cursor")["profile"]["server_forbidden_chars"] = "-"


def _break_verified(doc: dict[str, Any]) -> None:
    _entry(doc, "cursor")["verified"] = {
        "version": "1.0",
        "date": "2026-09-24",
        "evidence": "somewhere/else.txt",
    }


REFUSALS = {
    "literal host": (_break_host, "names a host"),
    "token literal": (_break_token, "token literal"),
    "bearer value literal": (_break_bearer_literal, "token literal"),
    "unknown placeholder": (_break_placeholder, "placeholder {{api}}"),
    "prompt outside headless": (_break_prompt_outside_headless, "placeholder {{prompt}}"),
    "unknown transport": (_break_transport, "transport"),
    "bridge unnamed": (_break_bridge, "'bridge' is a required property"),
    "no profile source": (_break_sources, "sources"),
    "insecure source": (_break_source_url, "sources/0/url"),
    "file without required keys": (_break_file_keys, "'required_keys' is a required property"),
    "no read snippet": (_break_no_read_snippet, "no snippet for reads without a token"),
    "duplicate id": (_break_duplicate, "duplicate id 'cursor'"),
    "underscore server": (_break_server_name, "server: 'open_proof' does not match"),
    "profile forbids a server character": (
        _break_profile_server_chars,
        "cursor: server name 'open-proof-network' contains ['-']",
    ),
    "evidence elsewhere": (_break_verified, "verified"),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_registry_refusals(case: str) -> None:
    breaker, expected = REFUSALS[case]
    doc = raw()
    breaker(doc)
    found = clients.problems(doc)
    assert any(expected in p for p in found), found
    with pytest.raises(clients.RegistryError, match=None):
        clients.parse(doc)


def test_missing_file_is_named(tmp_path: Path) -> None:
    with pytest.raises(clients.RegistryError, match=r"nope\.yaml"):
        clients.load(tmp_path / "nope.yaml")


def _fixture_name(snippet: clients.Snippet) -> str:
    assert snippet.path is not None
    return Path(snippet.path).name


@pytest.mark.parametrize("entry_id", [e.id for e in clients.load().entries])
def test_new_entry_is_tested(entry_id: str) -> None:
    """AC13 / R15, the checklist: an entry is accepted with no new test code once its documented
    examples are beside it and its profile is sourced; a missing one fails naming the item."""
    entry = clients.load().by_id(entry_id)
    folder = FIXTURES / entry_id
    missing = []
    if not (folder / "SOURCE.md").is_file():
        missing.append("SOURCE.md (where the examples came from)")
    for snippet in entry.snippets:
        if snippet.kind == "file" and not (folder / _fixture_name(snippet)).is_file():
            missing.append(f"{_fixture_name(snippet)} (the documented {snippet.path})")
    if any(s.kind == "command" for s in entry.snippets) and not (folder / "commands.txt").is_file():
        missing.append("commands.txt (the documented commands)")
    assert not missing, f"{entry_id}: checklist items missing: {missing}"
    assert entry.profile.sources, f"{entry_id}: profile has no source"
