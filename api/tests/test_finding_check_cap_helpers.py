"""F13-T33 (the owner, 2026-10-14): the fast check runs at the gate's cap and reads helpers as the
gate does.

The gate's ``lean`` calls carry ``maxHeartbeats`` 1000000 (F02-T15), and step 2 takes private
helper declarations before the statement's theorem (F00-T11). A fast check at AXLE's default
200000 would refuse proofs the gate admits, and a lint that flags every helper would call a
passing proof a refusal. AXLE takes Lean options as ``global_options`` on both ``check`` and
``verify_proof`` (its tool docs, read 2026-10-14; a live probe answered "less than the current
maximum of 1000000"), so the text a contributor sends is forwarded unchanged.
"""

from __future__ import annotations

import json

import pytest
from mcp_client import NODE, TARGET
from test_axle import BASE, Script, script  # noqa: F401 — the scripted transport fixture
from test_checks import harness_with, post, seed

from opn_api.axle import HttpxAxle
from opn_gate import config

OPTIONS = {"maxHeartbeats": config.MAX_HEARTBEATS}


def test_check_asks_axle_for_the_gate_s_cap(script: Script) -> None:  # noqa: F811
    script.answer(json={"okay": True, "info": {}})
    HttpxAxle(base_url=BASE).check("import Mathlib\n", environment="lean-4.33.1", timeout_s=60)
    assert json.loads(script.requests[0].content)["global_options"] == OPTIONS


def test_verify_asks_axle_for_the_gate_s_cap(script: Script) -> None:  # noqa: F811
    script.answer(json={"okay": True, "info": {}})
    HttpxAxle(base_url=BASE).verify_proof(
        "proof", formal_statement="stmt", environment="lean-4.33.1", timeout_s=30
    )
    assert json.loads(script.requests[0].content)["global_options"] == OPTIONS


HELPED = (
    "private theorem t : True := trivial\n\ntheorem OpnProp.and_reassoc : True := by\n  exact t\n"
)


@pytest.mark.parametrize("mode", ["check", "verify"])
def test_a_private_helper_is_not_a_gate_refusal(mode: str) -> None:
    h = harness_with()
    seed(h)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": HELPED, "mode": mode})
    assert r.status_code == 200, r.text
    assert r.json()["lint"] == [], r.json()["lint"]
    assert h.axle.calls[-1].content == HELPED


def test_a_forbidden_helper_is_the_gate_s_refusal() -> None:
    h = harness_with()
    seed(h)
    content = "set_option maxHeartbeats 0 in\n" + HELPED
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content, "mode": "verify"})
    assert r.status_code == 200, r.text
    lint = r.json()["lint"]
    assert [w["code"] for w in lint] == ["helper-forbidden"], lint
    assert lint[0]["token"] == "set_option" and lint[0]["line"] == 1  # noqa: S105 — a Lean token
    assert r.json()["okay"] is False
