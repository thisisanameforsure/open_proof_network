"""F13-T3, T4: ``POST /check`` and its call log — the mapped environment, the gate-gap lint,
``Defs`` inlining, the named refusals, the limits and the in-flight cap, and the record every
call past the body and the limit leaves (F13-R3 to R10; AC3 to AC8).

Every test drives the route through the fake graph host and ``FakeAxle``: the hosted checker is
never reached, and what the route forwards is read back from the fake's recorded calls.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Any

import httpx
import pytest
import samples
from api_fakes import AXLE_OKAY, FakeAxle, Harness, make_harness
from mcp_client import NODE, NODE_DIR, STATEMENT, TARGET, seed_node

from opn_api import routes
from opn_api.axle import AxleAnswer, AxleError
from opn_gate import schemas

PIN = "0df444a360eaa60ab8c11dca51a86af692955474"  # gate/mathlib-pins.txt, v4.33.1
PROOF = "theorem OpnProp.and_reassoc : True := by\n  trivial\n"


def harness_with(env: dict[str, str] | None = None, axle: Any = None) -> Harness:
    return make_harness(env, **({"axle": axle} if axle is not None else {}))


def seed(
    h: Harness,
    *,
    sha: str | None = PIN,
    statement: str = STATEMENT,
    defs: dict[str, str] | None = None,
) -> None:
    """The fixture node, its target pinned to ``sha``, with the statement and definitions given."""
    seed_node(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=sha)
    )
    files[NODE_DIR + "Statement.lean"] = statement.encode()
    for stem, source in (defs or {}).items():
        files[f"targets/{TARGET}/defs/{stem}.lean"] = source.encode()
    h.context.files.clear()


def post(h: Harness, body: dict[str, Any], headers: dict[str, str] | None = None) -> httpx.Response:
    response: httpx.Response = h.client.post("/check", json=body, headers=headers or {})
    return response


def refused(r: httpx.Response, status: int, code: str) -> dict[str, Any]:
    assert r.status_code == status, r.text
    doc: dict[str, Any] = r.json()
    assert doc["error"] == code, r.text
    return doc


def test_the_routes_are_registered() -> None:
    """R8, R10, Q2: the check is open with D-35 v3.14's row; the record read needs a bearer."""
    (post_spec,) = [r for r in routes.ROUTES if r.label == "POST /check"]
    assert post_spec.d35 == "POST /check" and not post_spec.authenticated
    (get_spec,) = [r for r in routes.ROUTES if r.label == "GET /checks/{check_id}"]
    assert get_spec.d35 is None and get_spec.authenticated
    assert post_spec.feature == get_spec.feature == "F13"


def test_check_and_verify_forward_to_the_mapped_environment() -> None:
    """AC3: the pin's environment, the node's statement for verify, the body verbatim."""
    h = harness_with()
    seed(h)
    r = post(h, {"target_id": TARGET, "content": PROOF})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["authoritative"] is False and doc["service"] == "axle"
    assert (doc["environment"], doc["exact"], doc["mode"]) == ("lean-4.33.1", True, "check")
    assert doc["note"] is None
    assert doc["result"] == AXLE_OKAY and doc["lint"] == [] and doc["inlined_defs"] == []
    (call,) = h.axle.calls
    assert (call.method, call.content, call.environment) == ("check", PROOF, "lean-4.33.1")
    assert call.timeout_s == h.settings.check_timeout_s

    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": PROOF, "mode": "verify"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "verify" and r.json()["lint"] == []
    verify = h.axle.calls[-1]
    assert (verify.method, verify.formal_statement) == ("verify_proof", STATEMENT)


def test_each_gate_gap_is_warned() -> None:
    """AC4: a changed header, a helper above the theorem and a leftover sorry are each named,
    and the text is still forwarded untouched."""
    h = harness_with()
    seed(h)
    content = (
        "import Mathlib\n\n"
        "lemma helper : True := trivial\n\n"
        "theorem OpnProp.and_reassoc : True := by\n  sorry\n"
    )
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content})
    assert r.status_code == 200, r.text
    lint = r.json()["lint"]
    assert [w["code"] for w in lint] == ["imports-differ", "helper-declarations", "sorry-present"]
    assert (lint[0]["expected"], lint[0]["got"]) == ([], ["Mathlib"])
    assert lint[1]["declarations"] == ["lemma helper"]
    assert h.axle.calls[-1].content == content

    quiet = "-- sorry is only named here\n/-- lemma in a doc comment -/\n" + PROOF
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": quiet})
    assert r.json()["lint"] == [], r.text

    r = post(h, {"target_id": TARGET, "content": content})  # no node: nothing to compare against
    assert [w["code"] for w in r.json()["lint"]] == ["sorry-present"]


def test_defs_are_inlined() -> None:
    """AC5: the statement's Defs module and what it imports, dependencies first, in place of the
    import lines the checker cannot resolve."""
    h = harness_with()
    seed(
        h,
        statement="import Defs.Fact\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n",
        defs={
            "Base": "def Opn.base : Nat := 1\n",
            "Fact": "import Defs.Base\n\ndef Opn.fact : Nat := Opn.base\n",
        },
    )
    content = "import Defs.Fact\n\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content})
    assert r.status_code == 200, r.text
    assert r.json()["inlined_defs"] == ["Defs.Base", "Defs.Fact"]
    assert r.json()["lint"] == []  # the header matches the statement's
    sent = h.axle.calls[-1].content
    assert "import Defs" not in sent
    assert sent.index("def Opn.base") < sent.index("def Opn.fact") < sent.index("theorem OpnProp")


DEFS = {
    "Base": "def Opn.base : Nat := 1\n",
    "Fact": "import Defs.Base\n\ndef Opn.fact : Nat := Opn.base\n",
}
DEFS_STATEMENT = "import Defs.Fact\n\ntheorem OpnProp.and_reassoc : Opn.fact = 1 := by\n  sorry\n"
DEFS_PROOF = "import Defs.Fact\n\ntheorem OpnProp.and_reassoc : Opn.fact = 1 := by\n  rfl\n"


def test_verify_inlines_the_defs_into_the_formal_statement_too() -> None:
    """AC5, F13-T11 (the 2026-09-19 primes run): the checker compiles the formal statement on its
    own, so a statement over the target's definitions needs them as much as the proof does.
    Forwarded raw, every verify on a target with ``defs/`` answered ``okay: null`` with an unknown
    identifier, which the guide reads as a defect in the node."""
    h = harness_with()
    seed(h, statement=DEFS_STATEMENT, defs=DEFS)
    body = {"target_id": TARGET, "node_id": NODE, "content": DEFS_PROOF, "mode": "verify"}
    r = post(h, body)
    assert r.status_code == 200, r.text
    call = h.axle.calls[-1]
    assert call.method == "verify_proof" and call.formal_statement is not None
    for sent in (call.content, call.formal_statement):
        assert "import Defs" not in sent
        assert sent.index("def Opn.base") < sent.index("def Opn.fact") < sent.index("theorem Opn")
    assert call.formal_statement.rstrip().endswith("sorry")  # the statement, not the proof


def test_defs_are_inlined_from_the_content_when_no_node_is_named() -> None:
    """F13-T11: a proposer's statement is not a node yet, so the content's own ``import Defs.*``
    lines name what to inline; a module the target does not have is refused by name."""
    h = harness_with()
    seed(h, defs=DEFS)
    r = post(h, {"target_id": TARGET, "content": DEFS_PROOF})
    assert r.status_code == 200, r.text
    assert r.json()["inlined_defs"] == ["Defs.Base", "Defs.Fact"]
    sent = h.axle.calls[-1].content
    assert "import Defs" not in sent
    assert sent.index("def Opn.base") < sent.index("def Opn.fact") < sent.index("theorem OpnProp")

    calls = len(h.axle.calls)
    r = post(h, {"target_id": TARGET, "content": "import Defs.Nope\n\n" + PROOF})
    doc = refused(r, 400, "defs-unknown")
    assert "Defs.Nope" in doc["message"] and len(h.axle.calls) == calls

    # With a node, a module the content adds beyond the statement's is inlined as well: the lint
    # already says the headers differ, and an unknown identifier would say nothing useful.
    seed(h, defs=DEFS)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": DEFS_PROOF})
    assert r.json()["inlined_defs"] == ["Defs.Base", "Defs.Fact"], r.text
    assert [w["code"] for w in r.json()["lint"]] == ["imports-differ"]


def test_refusals_are_named_and_logged() -> None:
    """AC6: a refusal of the body is named and leaves no record (Q11); a refusal past the limit
    is named, carries its log id and leaves a record with its code; the checker's own failure
    is upstream-unavailable with its status in both the answer and the record."""
    h = harness_with({"OPN_API_CHECK_MAX_BYTES": "200"})
    seed(h)
    base = {"target_id": TARGET, "content": PROOF}
    doc = refused(post(h, {**base, "stray": 1}), 400, "unknown-field")
    assert "stray" in doc["message"]
    refused(post(h, {**base, "target_id": "Bad!"}), 400, "target-id-invalid")
    refused(post(h, {**base, "node_id": "Bad!"}), 400, "node-id-invalid")
    refused(post(h, {**base, "mode": "fast"}), 400, "mode-invalid")
    refused(post(h, {**base, "mode": "verify"}), 400, "node-id-required")
    refused(post(h, {**base, "content": "  "}), 400, "content-missing")
    refused(post(h, {**base, "content": "x" * 201}), 413, "content-too-large")
    assert h.store.checks == {}  # nothing past the body yet

    for body, status, code in (
        ({**base, "target_id": "nowhere"}, 404, "target-unknown"),
        ({**base, "node_id": "no-such-node"}, 404, "node-unknown"),
    ):
        doc = refused(post(h, body), status, code)
        assert h.store.checks[doc["details"]["log_id"]].outcome == code
    assert h.axle.calls == []

    seed(h, sha="1" * 40)  # a pin the mapping does not list
    doc = refused(post(h, base), 422, "no-hosted-environment")
    assert doc["details"]["mathlib_sha"] == "1" * 40 and "1" * 40 in doc["message"]
    record = h.store.checks[doc["details"]["log_id"]]
    assert (record.outcome, record.environment) == ("no-hosted-environment", None)
    assert h.axle.calls == []

    failing = FakeAxle(replies=[AxleError("AXLE check returned 503", status=503)])
    h = harness_with(axle=failing)
    seed(h)
    doc = refused(post(h, base), 502, "upstream-unavailable")
    assert doc["details"]["upstream_status"] == 503 and "503" in doc["message"]
    record = h.store.checks[doc["details"]["log_id"]]
    assert (record.outcome, record.upstream_status, record.environment) == (
        "upstream-unavailable",
        503,
        "lean-4.33.1",
    )


def test_limits_and_concurrency_cap() -> None:
    """AC7: per address without a token, per identity with one, a bad token refused, and a check
    beyond the in-flight cap waits its budget and is then refused rather than forwarded."""
    body = {"target_id": TARGET, "content": PROOF}
    h = harness_with({"OPN_API_ANONYMOUS_CHECKS_PER_DAY": "2", "OPN_API_CHECKS_PER_HOUR": "1"})
    seed(h)
    assert [post(h, body).status_code for _ in range(2)] == [200, 200]
    refused(post(h, body), 429, "rate-limited")
    token = h.token_for("code_alice", "alice")
    assert post(h, body, h.auth(token)).status_code == 200  # a different subject
    over = post(h, body, h.auth(token))
    refused(over, 429, "rate-limited")
    assert int(over.headers["Retry-After"]) > 0
    refused(post(h, body, {"Authorization": "Bearer nonsense"}), 401, "invalid-token")
    assert len(h.store.checks) == 3  # the three answered calls; the refused ones are not logged

    blocking = Blocking()
    h = harness_with({"OPN_API_CHECK_CONCURRENCY": "1", "OPN_API_CHECK_TIMEOUT_S": "1"}, blocking)
    seed(h)
    first: list[httpx.Response] = []
    worker = threading.Thread(target=lambda: first.append(post(h, body)))
    worker.start()
    try:
        assert blocking.entered.wait(10), "the first check never reached the checker"
        busy = refused(post(h, body), 503, "checker-busy")
        assert busy["details"]["log_id"] and blocking.entries == 1  # never reached the checker
    finally:
        blocking.release.set()
        worker.join(15)
    assert [r.status_code for r in first] == [200]


def test_log_readable_only_by_owner(caplog: pytest.LogCaptureFixture) -> None:
    """AC8, R9, R10: the record carries the content's hash and size, the answer's facts and the
    lint codes, never the text; its identity reads it back, another identity and an anonymous
    call's record answer not-found, and the log line names the call without the text."""
    reply = {
        **AXLE_OKAY,
        "okay": False,
        "lean_messages": {"errors": ["e1", "e2"], "warnings": [], "infos": []},
        "info": {"request_id": "req-42"},
    }
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h)
    marked_text = "theorem OpnProp.and_reassoc : True := by\n  sorry -- UNIQUE-MARKER\n"
    alice = h.token_for("code_alice", "alice")
    with caplog.at_level(logging.INFO, logger="opn_api.checks"):
        r = post(h, {"target_id": TARGET, "node_id": NODE, "content": marked_text}, h.auth(alice))
    assert r.status_code == 200, r.text
    log_id = r.json()["log_id"]

    got = h.client.get(f"/checks/{log_id}", headers=h.auth(alice))
    assert got.status_code == 200, got.text
    record = got.json()
    assert "content" not in record and "UNIQUE-MARKER" not in got.text
    assert record["content_sha256"] == hashlib.sha256(marked_text.encode()).hexdigest()
    assert record["content_bytes"] == len(marked_text.encode())
    assert (record["caller_kind"], record["outcome"], record["okay"]) == (
        "identity",
        "answered",
        False,
    )
    assert (record["error_count"], record["axle_request_id"]) == (2, "req-42")
    assert record["lint"] == ["sorry-present"] and record["environment"] == "lean-4.33.1"

    bob = h.token_for("code_bob", "bob")
    refused(h.client.get(f"/checks/{log_id}", headers=h.auth(bob)), 404, "check-unknown")
    refused(h.client.get(f"/checks/{log_id}"), 401, "unauthenticated")
    refused(h.client.get("/checks/01NOSUCHCHECK", headers=h.auth(alice)), 404, "check-unknown")

    anonymous = post(h, {"target_id": TARGET, "content": PROOF})
    anon_id = anonymous.json()["log_id"]
    anon = h.store.checks[anon_id]
    assert (
        anon.caller_kind == "address" and len(anon.caller) == 64 and "testclient" not in anon.caller
    )
    refused(h.client.get(f"/checks/{anon_id}", headers=h.auth(alice)), 404, "check-unknown")

    lines = [rec.getMessage() for rec in caplog.records if rec.name == "opn_api.checks"]
    assert any(f"id={log_id}" in line and "outcome=answered" in line for line in lines), lines
    assert all("UNIQUE-MARKER" not in line for line in lines)


def test_a_store_failure_does_not_fail_the_check() -> None:
    """C7, R9: the check is answered even when its record cannot be written; the log id is null."""
    h = harness_with()
    seed(h)

    def broken(record: Any) -> None:
        msg = "table unavailable"
        raise RuntimeError(msg)

    h.store.put_check = broken  # type: ignore[method-assign]
    r = post(h, {"target_id": TARGET, "content": PROOF})
    assert r.status_code == 200, r.text
    assert r.json()["log_id"] is None


def test_a_new_application_never_inherits_an_old_cap() -> None:
    """R8, Q8: the in-flight cap belongs to its application. The first version kept semaphores
    in a table keyed by ``id(ctx)``; CPython hands a collected Context's address to the next one
    (189 of 200 rounds in the probe, task-4.txt), so a cap-1 application inherited a cap-8
    semaphore and let a second check through — once in a full suite run, never alone."""
    import gc  # noqa: PLC0415

    body = {"target_id": TARGET, "content": PROOF}
    for _ in range(20):
        old = harness_with()
        seed(old)
        assert post(old, body).status_code == 200  # its cap now exists
        del old
        gc.collect()
        blocking = Blocking()
        h = harness_with(
            {"OPN_API_CHECK_CONCURRENCY": "1", "OPN_API_CHECK_TIMEOUT_S": "1"}, blocking
        )
        seed(h)
        assert h.context.check_slots is None  # nothing carried over, whatever its address
        worker = threading.Thread(target=lambda h=h: post(h, body))
        worker.start()
        try:
            assert blocking.entered.wait(10)
            refused(post(h, body), 503, "checker-busy")
        finally:
            blocking.release.set()
            worker.join(15)


def test_hosted_checkers_route_publishes_the_mapping() -> None:
    """AC9, R11, Q12: open, the committed mapping as data, and each listed target's pin and
    environment from targets/index.json; a Mathlib-free target maps to the core entry (Q9)."""
    h = harness_with()
    r = h.client.get("/hosted-checkers.json")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert (doc["schema"], doc["service"], doc["endpoint"], doc["authoritative"]) == (
        "hosted-checkers/v1",
        "axle",
        "POST /check",
        False,
    )
    assert doc["pins"][PIN]["environment"] == "lean-4.33.1" and doc["pins"][PIN]["exact"] is True
    assert doc["core"]["environment"] == "lean-4.33.1" and doc["core"]["mathlib_tag"] is None
    assert doc["targets"]["propositional"] == {
        "mathlib_sha": None,
        "environment": "lean-4.33.1",
        "exact": False,
    }


def test_an_unreadable_mapping_is_a_named_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """C7, T4: a package without the mapping answers 503 naming it on both routes, never a
    pin with no checker."""
    from opn_gate import hosted  # noqa: PLC0415

    def broken(path: Any = None) -> hosted.HostedMapping:
        msg = "hosted-checkers.yaml is not hosted-checkers/v1"
        raise hosted.MappingError(msg)

    monkeypatch.setattr(hosted, "load", broken)
    h = harness_with()
    seed(h)
    doc = refused(
        post(h, {"target_id": TARGET, "content": PROOF}), 503, "hosted-checkers-unreadable"
    )
    assert "hosted-checkers.yaml" in doc["message"]
    refused(h.client.get("/hosted-checkers.json"), 503, "hosted-checkers-unreadable")


def test_a_core_only_target_is_checked_in_the_core_environment() -> None:
    """Q9 (Mike, 2026-09-14): a graph that pins no Mathlib — the tutorial — is forwarded to the
    mapping's core environment, and the answer says it is not exact and why."""
    from opn_gate import hosted  # noqa: PLC0415

    h = harness_with()
    seed(h, sha=None)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": PROOF, "mode": "verify"})
    assert r.status_code == 200, r.text
    core = hosted.load().core
    assert core is not None
    doc = r.json()
    assert (doc["environment"], doc["exact"], doc["note"]) == (core.environment, False, core.note)
    assert (h.axle.calls[-1].method, h.axle.calls[-1].environment) == (
        "verify_proof",
        core.environment,
    )
    assert h.store.checks[doc["log_id"]].environment == core.environment


class Blocking(FakeAxle):
    """A checker that holds its first call until released, so a second call meets the cap."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.entries = 0  # counted on entry: ``calls`` records a call only once it is answered

    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        self.entries += 1
        self.entered.set()
        self.release.wait(15)
        return super().check(content, environment=environment, timeout_s=timeout_s)
