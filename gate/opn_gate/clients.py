"""The connector registry (F16-R1 to R7, R13): ``gate/clients/registry.yaml``, read once.

Network configuration, not a gate check: no step imports this module and no verdict depends on
it (D-1, F16-R12). It lives in ``opn_gate`` for the reason ``hosted`` does: the site, which
renders the Docs page from it, runs with ``gate`` and ``site`` on its path and never the api
(F16-Q10). The api's tests import it to hold the MCP tool surface to each harness's profile.

A connector is a client of the plain protocol. Its templates may name only the MCP URL, the
server name, the token's environment variable and, for a headless run, the prompt (R13), and
never a host (R2) or a token (R6): ``load`` refuses a registry that breaks any of these, and
``render`` is the one place a template becomes text.
"""

from __future__ import annotations

import json
import re
import shlex
import textwrap
import tomllib
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from opn_gate import schemas

CLIENTS_DIR = schemas.SCHEMAS_DIR.parent / "clients"
REGISTRY_PATH = CLIENTS_DIR / "registry.yaml"
SCHEMA_PATH = CLIENTS_DIR / "registry.schema.json"
REGISTRY_SCHEMA = "harness-clients/v1"

#: R13: the only placeholders a template may use, and where each may appear.
PLACEHOLDERS = frozenset({"mcp_url", "server", "token_env"})
HEADLESS_PLACEHOLDERS = PLACEHOLDERS | {"prompt"}
PLACEHOLDER_RE = re.compile(r"\{\{([^{}]*)\}\}")
#: R2: a scheme in a template is a hard-coded host.
SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")
#: R6: a write token is 32 random bytes in unpadded url-safe base64 (``opn_api.auth.new_token``),
#: 43 characters; and a bearer value must be a variable reference, never the value itself.
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])|Bearer\s+(?![$])\S")
#: The keys under which a harness's config file lists its servers by name (``*`` in a key path).
SERVER_CONTAINERS = frozenset({"mcpServers", "servers", "mcp_servers", "context_servers"})


class RegistryError(ValueError):
    """The registry is missing, unreadable, or breaks one of its rules; the message names it."""


@dataclass(frozen=True)
class Snippet:
    title: str
    kind: str  # command | file
    format: str  # shell | json | toml
    auth: str  # none | bearer
    template: str
    path: str | None = None
    scope: str | None = None
    required_keys: tuple[str, ...] = ()
    forbidden_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Source:
    url: str
    accessed: str
    claim: str


@dataclass(frozen=True)
class Profile:
    """What the harness's MCP client is known to refuse, drop or cut (R5, R16, R17)."""

    sources: tuple[Source, ...]
    max_tools: int | None = None
    name_format: str | None = None
    name_pattern: str | None = None
    max_name_length: int | None = None
    server_forbidden_chars: str | None = None
    forbidden_keywords: tuple[str, ...] = ()
    result_cap_tokens: int | None = None
    requires_readonly_hint: bool = False


@dataclass(frozen=True)
class Verified:
    version: str
    date: str
    evidence: str


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    transport: str
    snippets: tuple[Snippet, ...]
    reads_agents_md: bool
    instructions: str
    headless: str
    approve: str
    list_check: str
    list_expect: str | None
    list_rpc: tuple[str, ...]
    list_env: dict[str, str]
    list_requires_env: tuple[str, ...]
    list_timeout_s: int
    profile: Profile
    verified: Verified | None
    bridge: str | None = None


@dataclass(frozen=True)
class Registry:
    server: str
    token_env: str
    entries: tuple[Entry, ...]

    def by_id(self, entry_id: str) -> Entry:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        msg = f"no connector {entry_id!r}"
        raise KeyError(msg)


@dataclass(frozen=True)
class Rendered:
    """One snippet as a contributor pastes it: the command, or the file's whole contents."""

    entry: str
    title: str
    kind: str
    format: str
    auth: str
    text: str
    path: str | None = None
    scope: str | None = None


# --- loading --------------------------------------------------------------------------------------


def _plain(doc: Any) -> Any:
    """YAML reads an unquoted ``2026-09-24`` as a date; the schema speaks JSON, so round-trip."""
    return json.loads(json.dumps(doc, default=str))


def _templates(doc: Mapping[str, Any]) -> Iterator[tuple[str, str, frozenset[str]]]:
    """Every template in the document as (where, text, placeholders it may use)."""
    for entry in doc.get("entries", []):
        eid = entry.get("id", "?")
        for i, snippet in enumerate(entry.get("snippets", [])):
            yield f"{eid}.snippets[{i}]", snippet.get("template", ""), PLACEHOLDERS
        headless, listing = entry.get("headless", {}), entry.get("list_check", {})
        yield f"{eid}.headless", headless.get("template", ""), HEADLESS_PLACEHOLDERS
        yield f"{eid}.list_check", listing.get("template", ""), PLACEHOLDERS
        yield f"{eid}.list_check.expect", listing.get("expect", ""), PLACEHOLDERS
        for name, value in listing.get("env", {}).items():
            yield f"{eid}.list_check.env.{name}", str(value), frozenset()


def problems(doc: Any) -> list[str]:
    """Every rule the document breaks, each naming where and which rule; empty when it is valid."""
    doc = _plain(doc)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    found = [
        f"schema: {'/'.join(str(p) for p in err.absolute_path) or '$'}: {err.message}"
        for err in sorted(
            jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path)
        )
    ]
    if found or not isinstance(doc, dict):
        return found
    ids = [entry["id"] for entry in doc["entries"]]
    found += [f"duplicate id {eid!r}" for eid in sorted({i for i in ids if ids.count(i) > 1})]
    for where, text, allowed in _templates(doc):
        for name in PLACEHOLDER_RE.findall(text):
            if name not in allowed:
                found.append(f"{where}: placeholder {{{{{name}}}}} is not one of {sorted(allowed)}")
        if SCHEME_RE.search(text):
            found.append(f"{where}: names a host; use {{{{mcp_url}}}} (F16-R2)")
        if TOKEN_RE.search(text):
            found.append(f"{where}: carries a token literal (F16-R6)")
    for entry in doc["entries"]:
        forbidden = entry["profile"].get("server_forbidden_chars") or ""
        bad = sorted({c for c in doc["server"] if c in forbidden})
        if bad:
            found.append(f"{entry['id']}: server name {doc['server']!r} contains {bad}")
        if not entry["snippets"] or not any(s["auth"] == "none" for s in entry["snippets"]):
            found.append(f"{entry['id']}: no snippet for reads without a token (F16-R6)")
    return found


def _entry(raw: Mapping[str, Any]) -> Entry:
    profile = dict(raw["profile"])
    sources = tuple(Source(**s) for s in profile.pop("sources"))
    profile["forbidden_keywords"] = tuple(profile.get("forbidden_keywords", ()))
    return Entry(
        id=raw["id"],
        name=raw["name"],
        transport=raw["transport"],
        bridge=raw.get("bridge"),
        snippets=tuple(
            Snippet(
                **{
                    **s,
                    "required_keys": tuple(s.get("required_keys", ())),
                    "forbidden_keys": tuple(s.get("forbidden_keys", ())),
                }
            )
            for s in raw["snippets"]
        ),
        reads_agents_md=raw["instructions"]["reads_agents_md"],
        instructions=raw["instructions"]["how"],
        headless=raw["headless"]["template"],
        approve=raw["headless"]["approve"],
        list_check=raw["list_check"]["template"],
        list_expect=raw["list_check"].get("expect"),
        list_rpc=tuple(raw["list_check"]["rpc"]),
        list_env=dict(raw["list_check"].get("env", {})),
        list_requires_env=tuple(raw["list_check"].get("requires_env", ())),
        list_timeout_s=int(raw["list_check"].get("timeout_s", 60)),
        profile=Profile(sources=sources, **profile),
        verified=Verified(**raw["verified"]) if raw["verified"] else None,
    )


def parse(doc: Any) -> Registry:
    """A validated registry from its parsed document, or ``RegistryError`` naming every problem."""
    found = problems(doc)
    if found:
        raise RegistryError("; ".join(found))
    doc = _plain(doc)
    return Registry(
        server=doc["server"],
        token_env=doc["token_env"],
        entries=tuple(_entry(e) for e in doc["entries"]),
    )


@lru_cache(maxsize=4)
def load(path: Path = REGISTRY_PATH) -> Registry:
    """The registry at ``path``. Cached for the life of the process, like ``hosted.load``."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        msg = f"{path.name}: {exc}"
        raise RegistryError(msg) from exc
    return parse(doc)


# --- rendering ------------------------------------------------------------------------------------


def fill(template: str, values: Mapping[str, str]) -> str:
    """The template with each ``{{name}}`` replaced; an unknown name is a ``RegistryError``."""

    def one(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            msg = f"placeholder {{{{{name}}}}} has no value here"
            raise RegistryError(msg)
        return values[name]

    return PLACEHOLDER_RE.sub(one, template)


def values(registry: Registry, mcp_url: str) -> dict[str, str]:
    return {"mcp_url": mcp_url, "server": registry.server, "token_env": registry.token_env}


def render_snippet(registry: Registry, entry: Entry, snippet: Snippet, mcp_url: str) -> Rendered:
    """One snippet as pasted text. A file is re-serialised from its parsed form, so what renders
    is what parses (R4): JSON indented two spaces, TOML exactly as the template writes it."""
    text = fill(snippet.template, values(registry, mcp_url))
    if snippet.format == "json":
        text = json.dumps(json.loads(text), indent=2) + "\n"
    elif snippet.format == "toml":
        tomllib.loads(text)
    else:
        shlex.split(text)
    return Rendered(
        entry=entry.id,
        title=snippet.title,
        kind=snippet.kind,
        format=snippet.format,
        auth=snippet.auth,
        text=text.strip() if snippet.format == "shell" else text,
        path=snippet.path,
        scope=snippet.scope,
    )


def render(registry: Registry, entry: Entry, mcp_url: str) -> list[Rendered]:
    """Every snippet of ``entry`` against ``mcp_url``, in registry order (R3)."""
    return [render_snippet(registry, entry, s, mcp_url) for s in entry.snippets]


def render_headless(registry: Registry, entry: Entry, mcp_url: str, prompt: str) -> str:
    return fill(entry.headless, {**values(registry, mcp_url), "prompt": prompt})


def render_list_check(registry: Registry, entry: Entry, mcp_url: str) -> tuple[str, str | None]:
    """The level-2 command and the text its output must contain, if any (R8). What decides the
    check is the server's record of the calls in ``entry.list_rpc``, never this text alone."""
    v = values(registry, mcp_url)
    return fill(entry.list_check, v), fill(entry.list_expect, v) if entry.list_expect else None


def parsed(rendered: Rendered) -> Any:
    """A rendered file's document, or a command's argv."""
    if rendered.format == "json":
        return json.loads(rendered.text)
    if rendered.format == "toml":
        return tomllib.loads(rendered.text)
    return shlex.split(rendered.text)


def key_paths(doc: Any, prefix: str = "") -> set[str]:
    """Every dotted key path in a document; a server's own name under a server container is
    ``*``, so two documents that register different names compare by shape (R4)."""
    out: set[str] = set()
    if isinstance(doc, dict):
        container = prefix.rsplit(".", 1)[-1] in SERVER_CONTAINERS
        for key, value in doc.items():
            path = f"{prefix}.{'*' if container else key}" if prefix else str(key)
            out.add(path)
            out |= key_paths(value, path)
    return out


# --- the guide section ----------------------------------------------------------------------------

GUIDE_BEGIN = "<!-- connectors:begin (generated from gate/clients/registry.yaml; F16-R3) -->"
GUIDE_END = "<!-- connectors:end -->"


def guide_section(registry: Registry, mcp_url: str = "$OPN_API/mcp") -> str:
    """The text between the guide's two markers: one row per harness with its id, its one-line
    registration, the file it can use instead, and how it finds this guide. The full snippets,
    the token forms and the headless commands are on the site's Docs page, which knows the
    service's URL; the guide names only ``$OPN_API``, which the reader has already set."""
    lines = [
        GUIDE_BEGIN,
        "",
        "| Harness | Id | Register the server | Or the file | Reads this guide |",
        "|---|---|---|---|---|",
    ]
    for entry in sorted(registry.entries, key=lambda e: e.name.lower()):
        rendered = render(registry, entry, mcp_url)
        command = next((r for r in rendered if r.kind == "command" and r.auth == "none"), None)
        files = [r for r in rendered if r.kind == "file"]
        file = next((r for r in files if r.auth == "none"), files[0] if files else None)
        reads = "yes" if entry.reads_agents_md else entry.instructions
        lines.append(
            f"| {entry.name} | `{entry.id}` "
            f"| {f'`{command.text}`' if command else 'no command; use the file'} "
            f"| {f'`{file.path}`' if file else '—'} | {reads} |"
        )
    paragraph = (
        f"Writes carry your token as `Authorization: Bearer ${registry.token_env}`. Most "
        "harnesses read headers only when they start, so after `get_token`, export "
        f"`{registry.token_env}` and restart the harness. Every harness's token form, headless "
        "command and known limits are on the site's Docs page. Put the harness's id in "
        "`tooling.harness` when you submit; it is recorded, never checked (D-23, D-1)."
    )
    lines += ["", *textwrap.wrap(paragraph, width=100), "", GUIDE_END]
    return "\n".join(lines)


def replace_section(document: str, section: str) -> str:
    """``document`` with the text between the markers replaced by ``section``; a document without
    exactly one pair of markers is a ``RegistryError``."""
    if document.count(GUIDE_BEGIN) != 1 or document.count(GUIDE_END) != 1:
        msg = "the guide must carry exactly one pair of connector markers"
        raise RegistryError(msg)
    head, _, rest = document.partition(GUIDE_BEGIN)
    _, _, tail = rest.partition(GUIDE_END)
    return head + section + tail


# --- the profile check ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolView:
    """What the profile check needs of one MCP tool; the api's tests build these from ``TOOLS``."""

    name: str
    input_schema: Mapping[str, Any]
    read_only: bool | None


@dataclass(frozen=True)
class Violation:
    harness: str
    tool: str | None
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.harness}: {self.tool or '(surface)'}: {self.rule}: {self.detail}"


def _keywords(schema: Any) -> Iterator[str]:
    if isinstance(schema, dict):
        for key, value in schema.items():
            yield key
            if key != "properties":
                yield from _keywords(value)
            else:
                for sub in value.values():
                    yield from _keywords(sub)
    elif isinstance(schema, list):
        for value in schema:
            yield from _keywords(value)


def check_profile(registry: Registry, entry: Entry, tools: Sequence[ToolView]) -> list[Violation]:
    """Every way the tool surface breaks ``entry``'s profile (R5, R17)."""
    p, out = entry.profile, []
    if p.max_tools is not None and len(tools) > p.max_tools:
        out.append(Violation(entry.id, None, "max_tools", f"{len(tools)} > {p.max_tools}"))
    for tool in tools:
        name = (p.name_format or "{tool}").format(server=registry.server, tool=tool.name)
        if p.max_name_length is not None and len(name) > p.max_name_length:
            detail = f"{name!r} is {len(name)} > {p.max_name_length}"
            out.append(Violation(entry.id, tool.name, "max_name_length", detail))
        if p.name_pattern is not None and not re.fullmatch(p.name_pattern, name):
            out.append(Violation(entry.id, tool.name, "name_pattern", f"{name!r}"))
        used = set(_keywords(tool.input_schema)) & set(p.forbidden_keywords)
        for keyword in sorted(used):
            out.append(Violation(entry.id, tool.name, "forbidden_keywords", keyword))
        if p.requires_readonly_hint and tool.read_only is None:
            out.append(Violation(entry.id, tool.name, "requires_readonly_hint", "no readOnlyHint"))
    return out


def estimated_tokens(text: str) -> int:
    """A conservative token estimate for a result (R16): four characters to a token."""
    return (len(text) + 3) // 4


def check_result(entries: Iterable[Entry], tool: str, text: str) -> list[Violation]:
    """Every connector whose result cap ``text`` would exceed (R16)."""
    tokens = estimated_tokens(text)
    return [
        Violation(e.id, tool, "result_cap_tokens", f"~{tokens} tokens > {cap}")
        for e in entries
        if (cap := e.profile.result_cap_tokens) is not None and tokens > cap
    ]


def smallest_result_cap(entries: Iterable[Entry]) -> tuple[str, int] | None:
    capped = [(e.id, cap) for e in entries if (cap := e.profile.result_cap_tokens) is not None]
    return min(capped, key=lambda c: c[1]) if capped else None


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m opn_gate.clients --guide gate/agents/AGENTS.md [--check]``: rewrite the guide's
    connector section from the registry, or with ``--check`` exit 1 when it is stale (R3)."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="opn_gate.clients")
    parser.add_argument("--guide", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    current = args.guide.read_text(encoding="utf-8")
    wanted = replace_section(current, guide_section(load()))
    if args.check:
        if wanted != current:
            print(f"{args.guide}: the connector section is stale; rerun without --check")
            return 1
        return 0
    args.guide.write_text(wanted, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
