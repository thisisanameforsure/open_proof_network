"""F13-T18: ``/check`` drops Mathlib's naming-linter warning on the node's own gate-generated
name, and nothing else (testers 2026-09-24, finding 7; ruling D6).

Found by the erdos-69 HTTP agent at 12:32:36Z: a verify-mode check on the hole
``erdos-69--h2-v2--h1-v2--h4`` came back with AXLE's Mathlib style linter warning that
``erdos_69__h2_v2__h1_v2__h4`` "contains '__'". The gate writes a hole's theorem under its node id
with ``-`` made ``_`` (``postmerge.child_statement``), so every hole's name has a ``__`` in it, and
a contributor cannot rename a node's theorem: the warning is noise on every check of every hole.

Mechanism and ruling D6 (Mike, 2026-09-24): the service drops a lean warning only when it is the
``linter.style.nameCheck`` warning *and* the declaration it names is the node's own
gate-generated one. Every other warning passes through verbatim, a contributor's own ``__`` name
included, and the call log records what the checker said, not what was shown.
"""

from __future__ import annotations

import copy
from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle
from mcp_client import NODE, TARGET
from test_checks import harness_with, post, seed

#: The fixture node stands in for the live hole: what makes a name the gate's is that it is the
#: node's id with ``-`` made ``_`` and is the theorem its statement declares, as
#: ``postmerge.child_statement`` writes every hole (live: ``erdos_69__h2_v2__h1_v2__h4``). The
#: fixture graph has no hole, so the linter's line below names ``and_reassoc``, which has no
#: ``__``; the rule under test is whose name it is, not what the name looks like.
HOLE = NODE
DECL = HOLE.replace("-", "_")
STATEMENT = f"import Init\n\ntheorem {DECL} : True := by\n  sorry\n"
PROOF = f"theorem {DECL} : True := by\n  trivial\n"


def name_check(decl: str, at: str = "-:3:8-3:34") -> str:
    """Mathlib's ``linter.style.nameCheck`` warning, as AXLE's ``lean_messages`` carry it."""
    return (
        f"{at}: warning: The declaration '{decl}' contains '__', which does not follow naming "
        "conventions. Consider using single underscores instead.\n\n"
        "Note: This linter can be disabled with `set_option linter.style.nameCheck false`"
    )


DEPRECATED = "-:4:2-4:10: warning: `push_neg` has been deprecated: use `push Not` instead"


def reply(*warnings: str) -> dict[str, Any]:
    return {
        **AXLE_OKAY,
        "lean_messages": {"errors": [], "warnings": list(warnings), "infos": []},
    }


def check(
    body_reply: dict[str, Any],
    content: str = PROOF,
    node: str | None = HOLE,
    statement: str = STATEMENT,
) -> Any:
    h = harness_with(axle=FakeAxle(replies=[body_reply]))
    seed(h, statement=statement)
    body: dict[str, Any] = {"target_id": TARGET, "content": content, "mode": "check"}
    if node is not None:
        body["node_id"] = node
    r = post(h, body)
    assert r.status_code == 200, r.text
    return h, r.json()


def test_the_gate_generated_name_warning_is_dropped() -> None:
    _, doc = check(reply(name_check(DECL)))
    assert doc["result"]["lean_messages"]["warnings"] == []
    assert doc["dropped_warnings"] == [{"linter": "linter.style.nameCheck", "declaration": DECL}]


def test_a_contributors_own_double_underscore_name_still_warns() -> None:
    """A helper the contributor named ``my__lemma`` is theirs to rename: it stays."""
    theirs = name_check("my__lemma", at="-:6:8-6:17")
    _, doc = check(reply(name_check(DECL), theirs))
    assert doc["result"]["lean_messages"]["warnings"] == [theirs]
    _, doc = check(reply(theirs), node=None)  # no node: nothing is the gate's
    assert doc["result"]["lean_messages"]["warnings"] == [theirs]
    assert doc["dropped_warnings"] == []


def test_a_node_whose_theorem_is_not_the_generated_name_keeps_the_warning() -> None:
    """The id alone does not make a name the gate's: an authored node's statement declares its
    author's name, and a warning on a lookalike is the author's to act on."""
    authored = "import Init\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
    _, doc = check(reply(name_check(DECL)), statement=authored)
    assert doc["result"]["lean_messages"]["warnings"] == [name_check(DECL)]
    assert doc["dropped_warnings"] == []


def test_other_warnings_are_untouched() -> None:
    _, doc = check(reply(DEPRECATED, name_check(DECL)))
    assert doc["result"]["lean_messages"]["warnings"] == [DEPRECATED]
    _, doc = check(reply(DEPRECATED))
    assert doc["result"] == reply(DEPRECATED)  # verbatim when nothing is dropped
    assert doc["dropped_warnings"] == []


def test_the_call_log_counts_what_axle_said_not_what_was_shown() -> None:
    said = reply(name_check(DECL))
    said["okay"] = False
    said["lean_messages"]["errors"] = ["-:4:2-4:9: error: unsolved goals"]
    kept = copy.deepcopy(said)
    h, doc = check(said)
    assert said == kept  # the checker's body is not edited in place; the answer is a copy
    record = h.store.checks[doc["log_id"]]
    assert (record.okay, record.error_count) == (False, 1)
    assert doc["okay"] is False
