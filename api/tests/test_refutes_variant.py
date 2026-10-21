"""F08-T45 (D-30 v3.46): a ``refutes`` variant through the service and the MCP.

``POST /proposals/variant`` takes the label with its ``relation_proof``; the refusal for a
missing proof names the implication the label claims (``variant → ¬root``); the relation
pre-flight (F13-T23) runs for it as for ``resolves`` and ``partial``, with the gate's own
program asked under the label ``refutes``; and ``propose_variant``'s schema admits the label.
"""

from __future__ import annotations

from typing import Any

from mcp_client import TARGET, McpClient
from test_finding_preflight_refusals import (
    RELATION,
    harness,
    opened_nothing,
    related,
    relation_calls,
    variant,
)
from test_finding_witness_preflight import RIGHT, STATEMENT, token
from test_proposals import pushed

from opn_api.mcp import writes

REFUTES_EXPECTED = "V → ¬R"


def refuting(**overrides: Any) -> dict[str, Any]:
    """The checker's answer for a refutes proof: the expected type is the root's negation."""
    doc = related(**overrides)
    info = doc["lean_messages"]["infos"][0].replace('"expected": "V → R"', '"expected": "V → ¬R"')
    doc["lean_messages"] = {**doc["lean_messages"], "infos": [info]}
    return doc


def test_a_refutes_label_without_a_proof_names_the_roots_negation() -> None:
    h = harness()
    r = variant(h, relation="refutes", relation_proof=None)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "relation-proof-required"
    assert "variant → ¬root" in r.json()["message"], r.json()["message"]
    opened_nothing(h)


def test_a_refuting_variant_is_preflighted_under_its_own_label() -> None:
    """The relation program is sent with ``refutes`` as the label, so the checker computes
    ``variant → ¬root`` from the gate's own ``expectedRelationType``; a matching proof opens
    and the receipt says so, and the pushed Relation.lean carries the label line."""
    h = harness(relations=(refuting(),))
    r = variant(h, relation="refutes")
    assert r.status_code == 201, r.text
    assert r.json()["relation_preflight"] == "matched"
    (sent,) = relation_calls(h)
    assert 'RelationLabel.ofString? "refutes"' in sent.content
    node_id = r.json()["node_id"]
    relation = pushed(h)[f"targets/{TARGET}/nodes/{node_id}/Relation.lean"]
    assert relation.startswith("-- relation: refutes\n"), relation[:80]


def test_a_refuting_proof_of_the_root_itself_is_the_wrong_direction() -> None:
    h = harness(relations=(refuting(matches=False),))
    r = variant(h, relation="refutes")
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "relation-direction"
    assert doc["details"]["expected"] == REFUTES_EXPECTED
    assert "refutes" in doc["message"]
    opened_nothing(h)


def test_mcp_propose_variant_admits_the_label() -> None:
    (tool,) = [t for t in writes.TOOLS if t.name == "propose_variant"]
    relation = tool.input_schema["properties"]["relation"]
    assert "refutes" in relation["enum"], relation
    assert "refutes" in tool.description, tool.description


def test_mcp_propose_variant_sends_a_refutes_proposal() -> None:
    h = harness(relations=(refuting(),))
    bearer = token(h)
    with h.client:
        result = McpClient(h).call(
            "propose_variant",
            {
                "target_id": TARGET,
                "stmt": STATEMENT,
                "witness": RIGHT,
                "relation": "refutes",
                "relation_proof": RELATION,
            },
            token=bearer,
        )
    assert not result.isError, result.structuredContent
    out = result.structuredContent
    assert out is not None and out["body"]["relation_preflight"] == "matched", out
    assert len(h.githost.pulls) == 1
