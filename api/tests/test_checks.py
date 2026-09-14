"""F13-T3: ``POST /check`` — the mapped environment, the gate-gap lint, ``Defs`` inlining, the
named refusals, the limits and the in-flight cap (F13-R3 to R8; AC3 to AC7).

Every test drives the route through the fake graph host and ``FakeAxle``: the hosted checker is
never reached, and what the route forwards is read back from the fake's recorded calls.
"""

from __future__ import annotations

import threading
from typing import Any

import httpx
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


def test_the_route_is_open_and_names_its_d35_row() -> None:
    """R8, Q2: no bearer demanded by the table; D-35 v3.14's row, verbatim."""
    (spec,) = [r for r in routes.ROUTES if r.label == "POST /check"]
    assert spec.d35 == "POST /check" and not spec.authenticated and spec.feature == "F13"


def test_check_and_verify_forward_to_the_mapped_environment() -> None:
    """AC3: the pin's environment, the node's statement for verify, the body verbatim."""
    h = harness_with()
    seed(h)
    r = post(h, {"target_id": TARGET, "content": PROOF})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["authoritative"] is False and doc["service"] == "axle"
    assert (doc["environment"], doc["exact"], doc["mode"]) == ("lean-4.33.0", False, "check")
    assert "toolchain" in doc["note"]
    assert doc["result"] == AXLE_OKAY and doc["lint"] == [] and doc["inlined_defs"] == []
    (call,) = h.axle.calls
    assert (call.method, call.content, call.environment) == ("check", PROOF, "lean-4.33.0")
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


def refused(r: httpx.Response, status: int, code: str) -> dict[str, Any]:
    assert r.status_code == status, r.text
    doc: dict[str, Any] = r.json()
    assert doc["error"] == code, r.text
    return doc


def test_refusals_are_named_and_logged() -> None:
    """AC6 (the naming half; T4 adds the log): each refusal before the checker reaches nothing,
    and the checker's own failure is upstream-unavailable with its status."""
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
    refused(post(h, {**base, "target_id": "nowhere"}), 404, "target-unknown")
    refused(post(h, {**base, "node_id": "no-such-node"}), 404, "node-unknown")
    assert h.axle.calls == []

    seed(h, sha=None)  # a Mathlib-free graph, like the tutorial's (Q9)
    doc = refused(post(h, base), 422, "no-hosted-environment")
    assert doc["details"] == {"mathlib_sha": None} and "Mathlib-free" in doc["message"]
    seed(h, sha="1" * 40)  # a pin the mapping does not list
    refused(post(h, base), 422, "no-hosted-environment")
    assert h.axle.calls == []

    failing = FakeAxle(replies=[AxleError("AXLE check returned 503", status=503)])
    h = harness_with(axle=failing)
    seed(h)
    doc = refused(post(h, base), 502, "upstream-unavailable")
    assert doc["details"] == {"upstream_status": 503} and "503" in doc["message"]


def test_limits_and_concurrency_cap() -> None:
    """AC7: per address without a token, per identity with one, a bad token refused, and a check
    beyond the in-flight cap waits its budget and is then refused rather than forwarded."""
    body = {"target_id": TARGET, "content": PROOF}
    h = harness_with({"OPN_API_ANONYMOUS_CHECKS_PER_DAY": "2", "OPN_API_CHECKS_PER_HOUR": "1"})
    seed(h)
    assert [post(h, body).status_code for _ in range(2)] == [200, 200]
    r = refused(post(h, body), 429, "rate-limited")
    token = h.token_for("code_alice", "alice")
    assert post(h, body, h.auth(token)).status_code == 200  # a different subject
    over = post(h, body, h.auth(token))
    refused(over, 429, "rate-limited")
    assert int(over.headers["Retry-After"]) > 0
    refused(post(h, body, {"Authorization": "Bearer nonsense"}), 401, "invalid-token")
    assert r  # the anonymous refusal above carried the standard body

    blocking = Blocking()
    h = harness_with({"OPN_API_CHECK_CONCURRENCY": "1", "OPN_API_CHECK_TIMEOUT_S": "1"}, blocking)
    seed(h)
    first: list[httpx.Response] = []
    worker = threading.Thread(target=lambda: first.append(post(h, body)))
    worker.start()
    try:
        assert blocking.entered.wait(10), "the first check never reached the checker"
        busy = refused(post(h, body), 503, "checker-busy")
        assert busy and blocking.entries == 1  # the second check never reached the checker
    finally:
        blocking.release.set()
        worker.join(15)
    assert [r.status_code for r in first] == [200]


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
