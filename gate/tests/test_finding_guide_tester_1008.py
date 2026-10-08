"""F10-T18: the guide says what the gate does, where the 2026-10-08 testers found it did not.

A tester ran erdos-1094 on 2026-10-08 (``engineering/evidence/testers-2026-10-08/``). Two places
where the guide and the gate disagreed, the gate being right in both, each now read against the
code or the schema that makes it true (log, 2026-09-11: docs are tests):

* **The annex citation.** The guide listed "The skeleton cites the annex it came from" among the
  rules the gate enforces mechanically. Tester A's partials #441 and #448 cited no annex, passed,
  and their holes are ``origin: compiler-derived`` on the record, which is D-12 #5 and D-28's
  ``submit_proof`` row as written: partial holes enter the frontier as ``compiler-derived``
  children, "or as skeleton-hole children where the file cites an annex (v3.12, D-31)". What the
  gate checks is a citation that is *made* (``postmerge.check_annex_citation`` at step 2, and the
  stepped annex's names at step 4); nothing checks for one that is absent.
* **The approach record's caps.** ``blocked_on`` is capped at 200 characters by
  ``approach-record/v1`` and the guide did not say so; nor did it give the cap of ``route`` or
  ``model_and_tooling``. The caps are read from the schema here, so a change to one fails this
  test until the guide says the new number.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from opn_gate import codes, postmerge, schemas

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


SKELETON = flat(
    GUIDE.split("## Skeletonization", 1)[1].split("**An annex may name its steps", 1)[0]
)
APPROACH = flat(
    GUIDE.split("A route that never reached a formal statement is an approach record", 1)[1].split(
        "```json", 1
    )[0]
)


# --- the annex citation ---------------------------------------------------------------------------


def test_the_guide_does_not_say_every_skeleton_must_cite() -> None:
    """The bullet that made the citation a mechanical rule of every partial is gone."""
    assert "The skeleton cites the annex it came from" not in FLAT


@pytest.mark.parametrize(
    ("what", "sentence"),
    [
        ("a cited partial is a skeleton", "A partial that cites an annex is a skeleton"),
        ("its holes", f"its holes are created with origin `{postmerge.ORIGIN_SKELETON}`"),
        ("an uncited partial passes", "A partial that cites no annex is accepted"),
        ("its holes", f"its holes are created with origin `{postmerge.ORIGIN_COMPILER}`"),
        ("nothing checks an absence", "nothing checks for a citation that is not there"),
    ],
)
def test_the_guide_says_what_a_citation_changes(what: str, sentence: str) -> None:
    assert sentence in SKELETON, what


@pytest.mark.parametrize("code", ["annex-uncited", "annex-malformed", "annex-step-missing"])
def test_the_citation_refusals_the_guide_names_are_the_gates(code: str) -> None:
    """What *is* mechanical about a citation, by the codes the gate answers with."""
    assert code in codes.CATALOG
    assert f"`{code}`" in SKELETON


def test_the_origin_rule_is_the_writers() -> None:
    """The two sentences above are the post-merge writer's rule, over the guide's own example."""
    cited = "theorem t : True := by\n  -- annex: " + "a" * 64 + "\n  have h : True := sorry\n"
    plain = "theorem t : True := by\n  have h : True := sorry\n  exact h\n"
    assert postmerge.child_origin(cited) == postmerge.ORIGIN_SKELETON
    assert postmerge.child_origin(plain) == postmerge.ORIGIN_COMPILER


# --- the approach record's caps -------------------------------------------------------------------

#: Fields the service writes, not the caller (the guide says so in the same paragraph).
SERVICE_SET = {"schema", "target", "contributor", "date"}


def caps(schema_id: str) -> dict[str, int]:
    """Every caller-sent string field's ``maxLength``, directly or in a ``oneOf`` branch."""
    out: dict[str, int] = {}
    props: dict[str, Any] = schemas.load_schema(schema_id)["properties"]
    for field, spec in props.items():
        if field in SERVICE_SET:
            continue
        for branch in [spec, *spec.get("oneOf", [])]:
            if isinstance(branch.get("maxLength"), int):
                out[field] = branch["maxLength"]
    return out


def test_the_schema_has_the_caps_this_test_reads() -> None:
    """The test is not vacuous: the finding's cap is among those read."""
    found = caps("approach-record/v1")
    assert found["blocked_on"] == 200
    assert set(found) == {"route", "blocked_on", "model_and_tooling"}


@pytest.mark.parametrize("field", sorted(caps("approach-record/v1")))
def test_the_guide_states_each_cap(field: str) -> None:
    cap = caps("approach-record/v1")[field]
    assert f"`{field}` (at most {cap} characters)" in APPROACH, field


def test_the_guide_says_a_long_field_is_refused() -> None:
    """The service answers ``400`` naming the field: ``field-too-long`` for a top-level cap,
    ``record-invalid`` for one inside a ``oneOf`` (``model_and_tooling``), so the guide names
    neither code (``engineering/evidence/F10/task-18.txt``)."""
    assert "A value over its cap is refused with `400`, naming the field" in APPROACH


# --- two sentences handed over by the lead (service-side findings B5, F05-Q19) -------------------


def test_the_closing_case_can_be_read_without_mcp() -> None:
    """``get_node``'s ``closing.context_import`` is ``layout.imports_own_context`` over the
    statement alone (F04-Q27, F09-Q13), so the guide says how to read it from the file."""
    from opn_api.mcp import reads  # noqa: PLC0415

    node = "erdos-1"
    line = f"import Nodes.«{node}».Context"
    assert reads.closing_route(node, f"import Mathlib\n{line}\n")["context_import"] == "statement"
    assert reads.closing_route(node, "import Mathlib\n")["context_import"] == "proof"
    assert "Without MCP, read the node's `Statement.lean`" in FLAT
    assert "is not in `CONTEXT.json`" in FLAT


def test_the_listing_says_its_waiting_on_is_a_last_read() -> None:
    """``GET /submissions.json``'s ``queue`` carries the last per-id read and its time."""
    from opn_api import pending  # noqa: PLC0415

    assert '"waiting_on_read_at": read_at' in inspect.getsource(pending.entry_queue)
    assert "is the last per-id read, whatever its age" in FLAT
    assert "compare `queue.waiting_on_read_at` with now" in FLAT


def test_the_guide_says_a_new_hole_may_be_products_pending() -> None:
    """F06-T14 (the lead's hand-over): a hole prechecked before the service has read a commit
    that carries it answers ``409 products-pending`` with ``details.graph_commit``."""
    assert "the service has not yet read a commit that carries the hole" in FLAT
    assert "`Retry-After` and `details.graph_commit`" in FLAT


NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def test_the_mechanical_rules_heading_counts_its_list() -> None:
    """The heading said "Three rules the gate enforces mechanically" over five bullets, the last
    of which is "a claim, not a refusal" (seen by the T18 agent; fixed by the lead)."""
    head = re.search(r"^(\w+) rules the gate enforces mechanically([^:\n]*):\n", GUIDE, re.M)
    assert head is not None
    bullets: list[str] = []
    for line in GUIDE[head.end() :].splitlines():
        if line.startswith("- **"):
            bullets.append(line[4:].split("**", 1)[0])
        elif line and not line.startswith(" ") and bullets:
            break  # the first paragraph after the list
    assert bullets
    claims = [b for b in bullets if "claim, not a refusal" in b]
    assert NUMBERS[head.group(1).lower()] == len(bullets) - len(claims), (head.group(0), bullets)
    if claims:
        assert "claim" in head.group(2), head.group(0)
