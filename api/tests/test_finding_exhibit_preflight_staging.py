"""F13-T31: the exhibit pre-flight allows exactly the node modules the gate's staging compiles.

The audit of 2026-10-04 found the two sides apart. ``checks.EXHIBIT_NODE_MODULES`` let an exhibit
import its own node's ``Statement``, and the pre-flight inlined the committed statement and sent
the checker a text that compiles; but the gate's staging (``exhibits.stage_node``, and since
F02-T14 ``exhibits.compiled_exhibit`` for a circularity claim) compiles the target's ``Defs`` and
the node's ``Context`` only, so ``import Nodes.«<id>».Statement`` has no olean to load and the gate
refuses the exhibit ``exhibit-elaboration``. The receipt said ``elaborates`` and the pull request
failed a queue slot later: the pre-flight vouched for a text the gate never compiles.

The rule: the pre-flight's set is the gate's own constant (``exhibits.EXHIBIT_NODE_MODULES``), so
an exhibit importing its node's ``Statement`` is not sent (``skipped``, as one naming another
node's module already was) and no hosted check is spent on it.
"""

from __future__ import annotations

from api_fakes import AXLE_OKAY
from test_finding_exhibit_preflight import NODE_MODULE, claim
from test_finding_witness_preflight import harness

from opn_api import checks
from opn_gate import exhibits

STATEMENT_EXHIBIT = (
    f"import {NODE_MODULE}.Statement\n\n"
    "theorem exhibit_vacuous : OpnProp.and_reassoc = OpnProp.and_reassoc := rfl\n"
)


def test_an_exhibit_importing_its_nodes_statement_is_not_vouched_for() -> None:
    """The gate cannot compile it (no Statement olean is staged), so the checker is not asked
    and the receipt does not say ``elaborates``."""
    h = harness(AXLE_OKAY)
    r = claim(h, STATEMENT_EXHIBIT)
    assert r.status_code == 201, r.text
    assert r.json()["exhibit_preflight"] == "skipped"
    assert h.axle.calls == []


def test_the_preflight_set_is_the_gates() -> None:
    assert checks.EXHIBIT_NODE_MODULES == exhibits.EXHIBIT_NODE_MODULES
