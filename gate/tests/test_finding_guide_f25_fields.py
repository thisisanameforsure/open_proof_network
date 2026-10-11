"""F25-T11 (R18, AC18): every field, route and code F25 added is documented where an agent reads.

The guide is the one document an agent is given (F10-R1), and the MCP input schema is the one
document a client is given, so a field that lives in a graph schema and in neither of those is a
field nobody can send on purpose. This file holds the three surfaces to the schemas and the
tables they describe:

* every property of ``submission-meta/v2``'s ``automation`` block, and every property of
  ``registration/v1`` the service takes (its top level and the ``wrapper`` and ``proof``
  objects), is named in the guide as `code` text and described in the matching MCP tool's input
  schema (``submit_proof`` and ``precheck_submission`` carry the block; ``register_target`` the
  record);
* every route ``routes.ROUTES`` files under ``feature == "F25"`` is named in the guide, with its
  method, and has a purpose in ``PURPOSES`` (the index test holds the second half for every
  route; this one holds the first for F25's);
* every F25 code — the export's ``export-*``, the gate's ``registration-*`` and
  ``display-name-*``, the service's ``automation-*`` and ``classification-invalid`` — is in the
  catalog ``GET /errors.json`` serves with a remedy, and every one the catalog carries under
  those prefixes is named in the guide, so a code an agent meets has a sentence to read.

Red first (2026-10-11): against the guide as T4 left it, the registration record's fields and
the ``registration-*`` and ``display-name-*`` codes had no sentence, and ``POST /me/name`` and
``POST /registrations`` appeared only in the appendix table.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from opn_api import identity, routes
from opn_api.mcp import server
from opn_gate import codes

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
#: Backticked spans outside fenced blocks: the names the guide uses in its prose.
PROSE = re.sub(r"^```.*?^```[ \t]*$", "", GUIDE, flags=re.DOTALL | re.MULTILINE)
SPANS = set(re.findall(r"`([^`\n]+)`", PROSE))
SECTION = "## Registration in Palomar"
F25_PREFIXES = ("export-", "registration-", "display-name-", "automation-")
F25_SINGLETONS = ("classification-invalid",)
#: Fields of ``registration/v1`` the service writes itself, so no tool takes them (F25-R5:
#: ``submitted_by`` is the sign-in, never a field of the body; ``date`` is the day; ``schema``
#: and ``target`` are the file's place). The guide still names them.
WRITTEN_BY_THE_SERVICE = frozenset({"schema", "target", "submitted_by", "date"})


def schema(name: str) -> dict[str, object]:
    doc: dict[str, object] = json.loads(
        (ROOT / "gate" / "schemas" / f"{name}.json").read_text(encoding="utf-8")
    )
    return doc


def properties(node: dict[str, object]) -> dict[str, dict[str, object]]:
    props = node.get("properties")
    assert isinstance(props, dict), node
    return props


def named_in_guide(field: str) -> bool:
    """A field is named when some span is the field itself or a dotted/bracketed path to it."""
    return any(
        span == field or span.startswith(f"{field}.") or span.startswith(f"{field}[")
        for span in SPANS
    ) or any(re.search(rf'["`]{re.escape(field)}["`:]', span) for span in SPANS)


def described(prop: dict[str, object]) -> bool:
    return bool(str(prop.get("description", "")).strip())


def automation_block() -> dict[str, object]:
    doc = schema("submission-meta/v2")
    defs = doc["$defs"]
    assert isinstance(defs, dict)
    block = defs["automation"]
    assert isinstance(block, dict)
    return block


# --- the automation block ---


def test_every_automation_field_is_named_in_the_guide() -> None:
    block = automation_block()
    fields = set(properties(block))
    fields |= {f"tokens.{k}" for k in properties(properties(block)["tokens"])}
    missing = sorted(f for f in fields if not named_in_guide(f.split(".")[-1]))
    assert missing == [], f"automation fields the guide never names: {missing}"
    assert "`automation`" in PROSE


def test_every_automation_field_is_described_in_the_tools_that_take_it() -> None:
    block = automation_block()
    for tool_name in ("submit_proof", "precheck_submission"):
        tool = server.BY_NAME[tool_name]
        param = properties(tool.input_schema)["automation"]
        assert param.get("additionalProperties") is False, tool_name
        assert set(properties(param)) == set(properties(block)), tool_name
        assert param.get("required") == block.get("required"), tool_name
        undescribed = sorted(k for k, p in properties(param).items() if not described(p))
        assert undescribed == [], f"{tool_name}.automation: {undescribed}"
        tokens = properties(param)["tokens"]
        assert set(properties(tokens)) == {"input", "output"}, tool_name
        assert tokens.get("additionalProperties") is False, tool_name
    assert "automation" in server.BY_NAME["submit_proof"].input_schema["required"]
    assert "automation" not in server.BY_NAME["precheck_submission"].input_schema["required"]


# --- the registration record ---


def test_every_registration_field_is_named_in_the_guide() -> None:
    doc = schema("registration/v1")
    fields = set(properties(doc)) - {"schema"}
    for nested in ("wrapper", "proof"):
        fields |= set(properties(properties(doc)[nested]))
    missing = sorted(f for f in fields if not named_in_guide(f))
    assert missing == [], f"registration fields the guide never names: {missing}"
    assert "`registration/v1`" in PROSE


def test_every_registration_field_the_tool_takes_is_described() -> None:
    doc = schema("registration/v1")
    tool = server.BY_NAME["register_target"]
    params = properties(tool.input_schema)
    assert tool.input_schema.get("additionalProperties") is False
    expected = set(properties(doc)) - WRITTEN_BY_THE_SERVICE | {"target_id"}
    assert set(params) == expected, sorted(set(params) ^ expected)
    undescribed = sorted(k for k, p in params.items() if not described(p))
    assert undescribed == [], undescribed
    for nested in ("wrapper", "proof"):
        inner = params[nested]
        assert inner.get("additionalProperties") is False, nested
        assert set(properties(inner)) == set(properties(properties(doc)[nested])), nested
        assert inner.get("required") == properties(doc)[nested].get("required"), nested
    status = params["status"].get("enum")
    assert status == properties(doc)["status"].get("enum")
    # the service writes these, and the guide says so rather than inviting them in the body
    for field in sorted(WRITTEN_BY_THE_SERVICE - {"schema"}):
        assert f"`{field}`" in PROSE, field
    assert "`submitted_by` from the sign-in" in re.sub(r"\s+", " ", GUIDE)


def test_the_display_name_fields_are_named_and_described() -> None:
    tool = server.BY_NAME["set_display_name"]
    params = properties(tool.input_schema)
    assert tool.input_schema.get("additionalProperties") is False
    assert set(params) == {"name", "link"}
    assert all(described(p) for p in params.values())
    assert "null" in str(params["name"].get("type")), "null withdraws a name (F25-R6)"
    for word in ("`names/<pseudonym>.yaml`", "`display-name/v1`", "one-way publication"):
        assert word in GUIDE, word


# --- the routes ---


def test_every_f25_route_is_named_in_the_guide_and_has_a_purpose() -> None:
    f25 = [r for r in routes.ROUTES if r.feature == "F25"]
    assert {r.label for r in f25} == {"POST /me/name", "POST /registrations"}
    for spec in f25:
        assert f"`{spec.label}`" in PROSE, spec.label
        assert spec.label in routes.PURPOSES and routes.PURPOSES[spec.label].endswith(".")
    assert SECTION in GUIDE
    section = GUIDE[GUIDE.index(SECTION) : GUIDE.index("\n## ", GUIDE.index(SECTION) + 1)]
    for tool in ("set_display_name", "register_target", "list_registrations", "get_target"):
        assert f"MCP `{tool}`" in re.sub(r"\s+", " ", section), tool
    assert "## Registration in Palomar" in GUIDE[: GUIDE.index("\n## Rate limits")]


# --- the codes ---


def f25_codes() -> set[str]:
    return {c for c in codes.CATALOG if c.startswith(F25_PREFIXES)} | set(F25_SINGLETONS)


def test_every_f25_code_is_in_the_catalog_with_a_remedy() -> None:
    found = f25_codes()
    for prefix in F25_PREFIXES:
        assert any(c.startswith(prefix) for c in found), prefix
    for code in sorted(found):
        row = codes.CATALOG[code]
        assert len(row.remedy.strip()) > 20, code
        assert len(row.meaning.strip()) > 20, code


def test_every_f25_code_is_named_in_the_guide() -> None:
    missing = sorted(
        c
        for c in f25_codes()
        if f"`{c}`" not in PROSE and not any(s.endswith(f" {c}") for s in SPANS)
    )
    assert missing == [], f"F25 codes with no sentence in the guide: {missing}"


def test_the_shared_refusal_names_all_three_acts() -> None:
    """``not-steward-or-curator`` is met by approvals, literature confirmations and registrations
    (``approvals.py``, ``literature.py``, ``registrations.py``), so its meaning names all three."""
    row = codes.CATALOG["not-steward-or-curator"]
    for word in ("approve words", "literature", "registration"):
        assert word in row.meaning, word


# --- the DCO and the literature reference ---


def test_the_guide_names_both_licences_and_the_re_accept_rule() -> None:
    """F25-R18, D-23 v3.37: the DCO text names the two licences, and a version saved before the
    change is stale, which the guide says beside the token call."""
    token = GUIDE[GUIDE.index("## Getting a token") : GUIDE.index("## Precheck and submit")]
    for spdx in ("Apache-2.0", "CDLA-Permissive-2.0"):
        assert f"`{spdx}`" in token, spdx
        assert spdx in identity.DCO_TEXT, spdx
    assert "`dco-version-stale`" in token and "dco-version-stale" in codes.CATALOG
    assert "`GET /dco.json`" in token


def test_a_literature_record_may_cite_a_palomar_id() -> None:
    """D-25 v3.37: the reference form, in the section an agent reads before filing one."""
    literature = GUIDE[GUIDE.index("## Literature records") : GUIDE.index("## Glosses")]
    assert "`PALOMAR-YYYY-MM-DD-NNNNNN vN`" in literature
    assert "`PALOMAR-YYYY-MM-DD-NNNNNN vN`" in GUIDE[GUIDE.index(SECTION) :]
