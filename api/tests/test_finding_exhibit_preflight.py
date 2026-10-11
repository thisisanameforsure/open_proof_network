"""F13-T22: a defect claim's or revision request's exhibit is compiled before anything opens.

The owner's principle (2026-09-24): a thing the gate will refuse for not compiling should be "an
error sent back to the user", not a pull request. ``POST /defect-claims`` (and
``POST /revision-requests`` with an exhibit) applied D-16's mechanical pre-triage and opened the
append; the exhibit met Lean only in the gate's sandbox (``opn-gate exhibits``), so an exhibit
that does not elaborate became a pull request refused ``exhibit-elaboration`` a queue slot later
— as two prose exhibits were on 2026-09-17 (log). The hosted fast checker can answer that
question with what the service already has: the exhibit, and the node's committed statement,
Context and definitions inlined where the exhibit imports them, exactly as the gate stages them
(``exhibits.stage_node``). F13-T31: the gate's staging compiles the Context and not the
Statement, so the exhibits here import the Context; one importing the Statement is not sent
(``test_finding_exhibit_preflight_staging.py``).

So the route now sends that text to the checker first and refuses ``422 exhibit-elaboration``
with Lean's errors when the checker says it does not compile. It never refuses on anything
weaker: no Lean error, no verdict, no checker, a Mathlib-free pin — all let the append open as
before, and the receipt's ``exhibit_preflight`` says which. A circularity claim's exhibit, and one
that imports a node other than the claim's own, are not sent (``skipped``): the first is checked
by the gate with a relation program the checker is not sent, the second names modules only the
gate's staging supplies.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, Harness
from test_finding_circular_claim import VALID as CIRCULAR
from test_finding_circular_claim import add_ancestor
from test_finding_witness_preflight import DEP, DEP_STATEMENT, harness, token

from opn_api.axle import AxleError

NODE_MODULE = f"Nodes.«{DEP}»"
CONTEXT_PATH = f"targets/propositional/nodes/{DEP}/Context.lean"
#: The node's committed Context: one dependency's signature, as D-3 has it.
DEP_CONTEXT = (
    "/-! Declared dependencies (D-4 step 8): `and-swap`. -/\n\n"
    "theorem OpnProp.and_swap_dep : True := by\n  sorry\n"
)
#: An exhibit about the node, importing its Context, the module the gate stages for it (F08-R7;
#: F13-T31 restated it from the Statement, which the gate's staging never compiles).
EXHIBIT = (
    f"import {NODE_MODULE}.Context\n\n"
    "theorem exhibit_vacuous : OpnProp.and_swap_dep = OpnProp.and_swap_dep := rfl\n"
)
#: The Lean error an exhibit that does not elaborate gets (AXLE's lean_messages shape).
UNKNOWN = "-:3:26-3:46: error: unknown identifier 'OpnProp.and_reasoc'"


def fails(*errors: str) -> dict[str, Any]:
    return {
        **AXLE_OKAY,
        "okay": False,
        "lean_messages": {"errors": list(errors), "warnings": [], "infos": []},
    }


def claim(h: Harness, exhibit: str = EXHIBIT, **extra: Any) -> Any:
    h.githost.files.setdefault(CONTEXT_PATH, DEP_CONTEXT.encode())
    body = {"stmt_ref": DEP, "class": "junk-value", "line": 1, "exhibit": exhibit, **extra}
    return h.client.post("/defect-claims", json=body, headers=h.auth(token(h)))


def revision(h: Harness, exhibit: str | None) -> Any:
    h.githost.files.setdefault(CONTEXT_PATH, DEP_CONTEXT.encode())
    evidence: dict[str, Any] = {"text": "the statement is vacuous"}
    if exhibit is not None:
        evidence["exhibit"] = exhibit
    body = {"node_id": DEP, "defect_class": "vacuity", "evidence": evidence}
    return h.client.post("/revision-requests", json=body, headers=h.auth(token(h)))


def test_an_exhibit_that_does_not_elaborate_opens_no_pull_request() -> None:
    h = harness(fails(UNKNOWN))
    r = claim(h)
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "exhibit-elaboration"
    assert doc["details"]["errors"] == [UNKNOWN]
    record = h.store.checks[doc["details"]["log_id"]]
    assert (record.outcome, record.okay) == ("answered", False)
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_an_exhibit_that_elaborates_opens_and_the_receipt_says_so() -> None:
    h = harness(AXLE_OKAY)
    r = claim(h)
    assert r.status_code == 201, r.text
    assert r.json()["exhibit_preflight"] == "elaborates"
    assert len(h.githost.pulls) == 1
    (sent,) = h.axle.calls
    assert sent.method == "check"
    # The node's Context stands in for the import the checker cannot resolve, before the
    # exhibit, as the gate's staging supplies it; the statement is not inlined (F13-T31).
    assert "import Nodes." not in sent.content
    assert sent.content.index("theorem OpnProp.and_swap_dep") < sent.content.index(
        "theorem exhibit_vacuous"
    )
    assert "theorem OpnProp.and_reassoc" not in sent.content


def test_an_exhibit_importing_only_the_nodes_context_gets_the_context() -> None:
    h = harness(AXLE_OKAY)
    h.githost.files[CONTEXT_PATH] = b"theorem Opn.context_marker : True := trivial\n"
    h.context.files.clear()
    r = claim(h, f"import {NODE_MODULE}.Context\n\ntheorem e : True := Opn.context_marker\n")
    assert r.status_code == 201, r.text
    (sent,) = h.axle.calls
    assert "Opn.context_marker : True := trivial" in sent.content
    assert "theorem OpnProp.and_reassoc" not in sent.content  # not imported, not inlined


def test_a_checker_that_cannot_decide_lets_the_claim_open_as_before() -> None:
    for reply, word in (
        (AxleError("AXLE check returned 502", status=502), "unavailable"),
        (fails(), "inconclusive"),  # okay false with no Lean error: nothing to name
        ({**AXLE_OKAY, "okay": None, "user_error": "no verdict"}, "inconclusive"),
    ):
        h = harness(reply)
        r = claim(h)
        assert r.status_code == 201, r.text
        assert r.json()["exhibit_preflight"] == word
        assert len(h.githost.pulls) == 1
    h = harness(sha="f" * 40)  # a pin no hosted checker serves
    r = claim(h)
    assert (r.status_code, r.json()["exhibit_preflight"]) == (201, "unavailable"), r.text
    assert h.axle.calls == []


def test_an_exhibit_naming_another_nodes_module_is_not_sent() -> None:
    h = harness(fails(UNKNOWN))
    r = claim(h, "import Nodes.«tutorial-and-swap».Statement\n\ntheorem e : True := trivial\n")
    assert r.status_code == 201, r.text
    assert r.json()["exhibit_preflight"] == "skipped"
    assert h.axle.calls == []


def test_a_circularity_claims_exhibit_is_the_gates_to_check() -> None:
    h = harness(fails(UNKNOWN))
    add_ancestor(h)
    r = h.client.post("/defect-claims", json=CIRCULAR, headers=h.auth(token(h)))
    assert r.status_code == 201, r.text
    assert r.json()["exhibit_preflight"] == "skipped"
    assert h.axle.calls == []


def test_a_revision_requests_exhibit_is_elaborated_too() -> None:
    h = harness(fails(UNKNOWN))
    r = revision(h, EXHIBIT)
    assert (r.status_code, r.json()["error"]) == (422, "exhibit-elaboration"), r.text
    assert h.githost.pulls == []


def test_a_revision_request_without_an_exhibit_spends_no_check() -> None:
    h = harness(fails(UNKNOWN))
    r = revision(h, None)
    assert r.status_code == 201, r.text
    assert "exhibit_preflight" not in r.json()
    assert h.axle.calls == []


def test_the_context_is_the_committed_one() -> None:
    """The checker is sent the node's Context as merged, not anything the caller wrote; F13-T31
    restated this from the statement, which an exhibit may no longer import."""
    h = harness(AXLE_OKAY)
    assert claim(h).status_code == 201
    assert DEP_CONTEXT.split("\n\n", 1)[1].strip() in h.axle.calls[0].content
    assert DEP_STATEMENT.strip() not in h.axle.calls[0].content
