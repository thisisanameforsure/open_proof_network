"""F24-T7: a steward restates their commitment to change the name the page shows (F24-Q15).

A commitment from a login already active on the target is a *restatement*: it admits nobody, so
the gate asks no admission of it (no invitation, no curator, no cap), and the active set takes
the name and link from the newest counting commitment while ``since``, ``admitted_by`` and
``via`` stay the commitment that made the login active. No record is rewritten: the old name
stays on the record beside the new one, and reverting the restatement restores it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_modes import CURATOR
from test_modes_panel import TARGET, TODAY, Graph, day, keys  # noqa: F401 — keys is a fixture

from opn_gate import clock, panel, policy, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner

SIGNER = SshKeygenSigner()


@pytest.fixture(autouse=True)
def gate_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clock, "today", lambda: TODAY)


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:  # noqa: F811
    return Graph(tmp_path, keys)


def restate(
    graph: Graph,
    login: str,
    name: str,
    *,
    on: int = 0,
    admitted_by: str = steward.SELF,
    link: str | None = None,
    target: str = TARGET,
) -> Change:
    return graph.write(
        "stewards",
        {
            "schema": "steward/v3",
            "action": "commit",
            "login": login,
            "name": name,
            "link": link,
            "commitment": steward.COMMITMENT,
            "date": day(on),
            "admitted_by": admitted_by,
        },
        target=target,
    )


def active(graph: Graph) -> list[steward.Steward]:
    return steward.active(graph.root / "targets" / TARGET, SIGNER)


# --- the active set ------------------------------------------------------------------------------


def test_the_newest_commitment_names_the_steward(graph: Graph) -> None:
    graph.commit("ann", on=-5)
    restate(graph, "ann", "Ann Smith", link="https://example.org/ann")
    [ann] = active(graph)
    assert (ann.name, ann.link) == ("Ann Smith", "https://example.org/ann")


def test_a_restatement_keeps_the_date_and_admission_it_restates(graph: Graph) -> None:
    graph.commit("ann", on=-5, admitted_by=CURATOR)
    restate(graph, "ann", "Ann Smith")
    [ann] = active(graph)
    assert ann.since == day(-5)
    assert ann.admitted_by == CURATOR


def test_a_restatement_does_not_change_the_order_of_the_stewards(graph: Graph) -> None:
    graph.commit("ann", on=-5)
    graph.commit("ben", on=-4, admitted_by=CURATOR)
    restate(graph, "ann", "Ann Smith")
    assert [s.login for s in active(graph)] == ["ann", "ben"]


def test_after_a_step_down_a_new_commitment_starts_afresh(graph: Graph) -> None:
    """A commitment after a step-down is not a restatement: its own date and name."""
    graph.commit("ann", on=-9)
    graph.write(
        "stewards",
        {
            "schema": "steward/v3",
            "action": "step-down",
            "login": "ann",
            "name": "Ann",
            "link": None,
            "commitment": steward.STEP_DOWN_SENTENCE,
            "date": day(-8),
            "admitted_by": steward.SELF,
        },
    )
    restate(graph, "ann", "Ann Smith", on=-1)
    [ann] = active(graph)
    assert (ann.name, ann.since) == ("Ann Smith", day(-1))


# --- admission -----------------------------------------------------------------------------------


def test_a_restatement_needs_no_invitation_when_the_panel_has_others(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-30, admitted_by=CURATOR)
    assert graph.codes(restate(graph, "ann", "Ann Smith")) == []


def test_a_restatement_needs_no_curator_under_reviewed(graph: Graph) -> None:
    graph.set_policy(admission=policy.REVIEWED)
    graph.commit("ann", on=-60, admitted_by=CURATOR)
    assert graph.codes(restate(graph, "ann", "Ann Smith", admitted_by=CURATOR)) == []


def test_a_restatement_carries_the_admission_it_restates(graph: Graph) -> None:
    """No restatement may rewrite how its steward was admitted on the record."""
    graph.commit("ann", on=-60)
    assert "steward-admission" in graph.codes(restate(graph, "ann", "Ann", admitted_by=CURATOR))
    assert "steward-admission" in graph.codes(restate(graph, "ann", "Ann", admitted_by="motion:1"))


def test_a_restatement_is_not_held_to_a_cap_lowered_since(graph: Graph) -> None:
    graph.commit("ann", on=-30)
    for i in range(3):
        graph.commit("ann", on=-30, admitted_by=CURATOR, target=f"cap-{i}")
    graph.set_policy(settings=panel.Settings(cap=2))
    assert graph.codes(restate(graph, "ann", "Ann Smith")) == []


def test_a_new_steward_still_needs_an_invitation(graph: Graph) -> None:
    """The exemption is for a login already active, never for a newcomer."""
    graph.commit("ann", on=-60)
    assert "steward-invitation-required" in graph.codes(restate(graph, "ben", "Ben"))


def test_a_returning_steward_still_needs_an_invitation(graph: Graph) -> None:
    """A login that stepped down is not active, so its commitment is admitted afresh."""
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-50, admitted_by=CURATOR)
    graph.write(
        "stewards",
        {
            "schema": "steward/v3",
            "action": "step-down",
            "login": "ben",
            "name": "Ben",
            "link": None,
            "commitment": steward.STEP_DOWN_SENTENCE,
            "date": day(-40),
            "admitted_by": steward.SELF,
        },
    )
    assert "steward-invitation-required" in graph.codes(restate(graph, "ben", "Ben B."))
