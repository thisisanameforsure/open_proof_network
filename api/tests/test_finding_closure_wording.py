"""F28-T11 (bug B5, the 2026-11-19 agent run): the two service sentences a proof meets on a node
proved by closure say so.

A node the post-merge closure sweep proved has a ``closure.json`` and no ``Proof.lean`` (D-12
v3.42). The service already treats it as proved, so a ``Proof.lean`` offered for it is refused
``proof-replaces-merged`` and an open proof pull request is moved to an alternate. Both told the
contributor something false about that node: that it "already has a merged Proof.lean", and that
"this node's proof merged from another pull request first". The sentences name both ways a node
is proved, so the reader of either is not sent looking for a file that does not exist.
"""

from __future__ import annotations

import pytest
from api_fakes import Harness
from test_finding_racer_alternate import racing

from opn_api.app import ApiError
from opn_api.submissions import check_placement
from opn_gate.paths import Claim


def test_the_refusal_of_a_proof_on_a_proved_node_names_closure_too() -> None:
    claim = Claim("propositional", "and-reassoc")
    with pytest.raises(ApiError) as caught:
        check_placement(
            claim,
            {claim.node_prefix + "Proof.lean": "theorem x : True := trivial\n"},
            artifact_type="proof",
            proved=True,
            tutorial=False,
        )
    assert caught.value.code == "proof-replaces-merged"
    message = caught.value.message
    assert "already has a merged Proof.lean" not in message
    assert "closure" in message
    assert "-alternate.lean" in message  # the remedy is unchanged


def test_the_racer_comment_does_not_say_another_pull_request_proved_it(harness: Harness) -> None:
    _node, loser = racing(harness)
    harness.client.get(f"/submissions/{loser.id}")
    (comment,) = [c for c in harness.githost.comments if c.number == 12]
    assert "merged from another pull request first" not in comment.body
    assert "closure" in comment.body
