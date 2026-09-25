"""F16-T3 / AC2, AC3: every connector renders to text that names only the configured service,
carries no token, parses in its own format and has the shape its harness documents.

The documented examples under ``fixtures/clients/<id>/`` are dated copies of each harness's own
docs (their ``SOURCE.md`` says where from). The shape test runs both ways: nothing we render is a
key the harness does not document (a typo like ``httpURL`` is caught), and every key the entry
says is required is rendered (Claude Code silently skips an entry with no ``type``; Gemini reads
``url`` as SSE, so the Gemini entry forbids it and requires ``httpUrl``).
"""

from __future__ import annotations

import json
import re
import shlex
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import clients

FIXTURES = Path(__file__).parent / "fixtures" / "clients"
TEST_URL = "https://mcp.test.invalid/mcp"
REGISTRY = clients.load()
ENTRIES = [e.id for e in REGISTRY.entries]
URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'`]+")


def everything(entry: clients.Entry) -> list[str]:
    """Every text a connector can put in front of a contributor or a harness."""
    texts = [r.text for r in clients.render(REGISTRY, entry, TEST_URL)]
    texts.append(clients.render_headless(REGISTRY, entry, TEST_URL, "read AGENTS.md"))
    texts.extend(t for t in clients.render_list_check(REGISTRY, entry, TEST_URL) if t)
    return texts


@pytest.mark.parametrize("entry_id", ENTRIES)
def test_no_hostname(entry_id: str) -> None:
    """AC2 / R2: the only URL in any rendered text is the one the renderer was given."""
    for text in everything(REGISTRY.by_id(entry_id)):
        urls = set(URL_RE.findall(text))
        assert urls <= {TEST_URL}, (entry_id, urls)


@pytest.mark.parametrize("entry_id", ENTRIES)
def test_no_token_literal(entry_id: str) -> None:
    """AC2 / R6: no rendered text carries a token, and every bearer form reads a variable."""
    entry = REGISTRY.by_id(entry_id)
    for text in everything(entry):
        assert not clients.TOKEN_RE.search(text), (entry_id, text)
    bearers = [r for r in clients.render(REGISTRY, entry, TEST_URL) if r.auth == "bearer"]
    for rendered in bearers:
        assert (REGISTRY.token_env in rendered.text) or ("${input:" in rendered.text), rendered


@pytest.mark.parametrize("entry_id", ENTRIES)
def test_parses(entry_id: str) -> None:
    """AC3 / R4: files parse in their format; commands split as a shell would."""
    for rendered in clients.render(REGISTRY, REGISTRY.by_id(entry_id), TEST_URL):
        if rendered.format == "json":
            json.loads(rendered.text)
        elif rendered.format == "toml":
            tomllib.loads(rendered.text)
        else:
            assert shlex.split(rendered.text)


def documented_file(entry_id: str, path: str) -> Any:
    name = FIXTURES / entry_id / Path(path).name
    text = name.read_text(encoding="utf-8")
    return tomllib.loads(text) if name.suffix == ".toml" else json.loads(text)


def documented_commands(entry_id: str) -> list[list[str]]:
    text = (FIXTURES / entry_id / "commands.txt").read_text(encoding="utf-8")
    return [shlex.split(line) for line in text.splitlines() if line.strip()]


def flags(argv: list[str]) -> set[str]:
    return {a.split("=", 1)[0] for a in argv if a.startswith("-")}


def shape_problems(registry: clients.Registry, entry: clients.Entry) -> list[str]:
    """Every way ``entry``'s rendered snippets differ from what its harness documents."""
    out: list[str] = []
    for snippet, rendered in zip(
        entry.snippets, clients.render(registry, entry, TEST_URL), strict=True
    ):
        if rendered.kind == "file":
            assert rendered.path is not None
            ours = clients.key_paths(clients.parsed(rendered))
            theirs = clients.key_paths(documented_file(entry.id, rendered.path))
            out += [f"{rendered.path}: undocumented key {k}" for k in sorted(ours - theirs)]
            out += [f"{rendered.path}: missing {k}" for k in snippet.required_keys if k not in ours]
            out += [
                f"{rendered.path}: required but undocumented {k}"
                for k in snippet.required_keys
                if k not in theirs
            ]
            out += [f"{rendered.path}: forbidden {k}" for k in snippet.forbidden_keys if k in ours]
        else:
            argv = clients.parsed(rendered)
            documented = documented_commands(entry.id)
            if not any(argv[:3] == d[:3] for d in documented):
                out.append(f"undocumented command {argv[:3]}")
            known = set().union(*(flags(d) for d in documented))
            out += [f"undocumented flag {f}" for f in sorted(flags(argv) - known)]
    return out


@pytest.mark.parametrize("entry_id", ENTRIES)
def test_matches_documented_shape(entry_id: str) -> None:
    """AC3 / R4: rendered keys are documented keys; required keys are rendered; forbidden keys
    are not; a command is the documented subcommand with documented flags only."""
    assert shape_problems(REGISTRY, REGISTRY.by_id(entry_id)) == []


def _mutant(entry_id: str, index: int, template: str) -> clients.Registry:
    doc = yaml.safe_load(clients.REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = next(e for e in doc["entries"] if e["id"] == entry_id)
    entry["snippets"][index]["template"] = template
    return clients.parse(doc)


MUTANTS: dict[str, tuple[str, int, str, str]] = {
    # Claude Code skips an .mcp.json entry with no type and still exits 0.
    "claude without type": (
        "claude-code",
        1,
        '{"mcpServers": {"{{server}}": {"url": "{{mcp_url}}"}}}',
        "missing mcpServers.*.type",
    ),
    # Gemini reads url as SSE.
    "gemini url for http": (
        "gemini-cli",
        1,
        '{"mcpServers": {"{{server}}": {"url": "{{mcp_url}}"}}, '
        '"context": {"fileName": ["AGENTS.md"]}}',
        "forbidden mcpServers.*.url",
    ),
    "gemini key typo": (
        "gemini-cli",
        1,
        '{"mcpServers": {"{{server}}": {"httpURL": "{{mcp_url}}"}}, '
        '"context": {"fileName": ["AGENTS.md"]}}',
        "undocumented key mcpServers.*.httpURL",
    ),
    # VS Code uses servers where the others use mcpServers.
    "vscode with mcpServers": (
        "copilot",
        1,
        '{"mcpServers": {"{{server}}": {"type": "http", "url": "{{mcp_url}}"}}}',
        "undocumented key mcpServers",
    ),
    "codex invented flag": (
        "codex-cli",
        1,
        "codex mcp add {{server}} --url {{mcp_url}} --bearer-token {{token_env}}",
        "undocumented flag --bearer-token",
    ),
    "codex invented field": (
        "codex-cli",
        2,
        '[mcp_servers.{{server}}]\nurl = "{{mcp_url}}"\nbearer_token_env_var = "{{token_env}}"\n'
        'default_tools_approval_mode = "approve"\nbearer_token = "x"\n',
        "undocumented key mcp_servers.*.bearer_token",
    ),
}


@pytest.mark.parametrize("case", sorted(MUTANTS))
def test_shape_mutants_caught(case: str) -> None:
    """Each trap the research found, written into the real registry, fails the shape check with a
    message naming the key or flag: the check is shown to see what it is for."""
    entry_id, index, template, expected = MUTANTS[case]
    registry = _mutant(entry_id, index, template)
    found = shape_problems(registry, registry.by_id(entry_id))
    assert any(expected in p for p in found), found


def test_guide_section_names_no_host() -> None:
    section = clients.guide_section(REGISTRY)
    assert not URL_RE.search(section)
    assert section.startswith(clients.GUIDE_BEGIN)
    assert section.endswith(clients.GUIDE_END)
    for entry in REGISTRY.entries:
        assert entry.name in section
