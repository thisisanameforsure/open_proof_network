"""F34-T13 (R22; D-19 v3.51 (ii)): a display name may carry the GitHub login its pseudonym is
paired with, written by the service from its own record of the pairing and never by hand. A
curator's own record may carry the login the graph pairs with her (``curators.json``)."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_modes import CURATOR
from test_modes_registration import (
    BOB,
    CURATOR_PSEUDONYM,
    STRANGER,
    Graph,
    keys,  # noqa: F401 — the signing keys fixture
)


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:  # noqa: F811 — the imported fixture
    return Graph(tmp_path, keys)


def test_the_service_writes_the_github_login(graph: Graph) -> None:
    change = graph.approval_signed(BOB, schema="display-name/v2", github="bob-on-github")
    assert graph.codes(change, mode="display-name") == []


def test_a_curator_may_carry_the_login_the_graph_pairs_with_her(graph: Graph) -> None:
    change = graph.ssh_signed(
        CURATOR_PSEUDONYM, key=CURATOR, schema="display-name/v2", github=CURATOR
    )
    assert graph.codes(change, opened_by=CURATOR, mode="display-name") == []


def test_a_hand_written_github_login_is_refused(graph: Graph) -> None:
    change = graph.ssh_signed(
        CURATOR_PSEUDONYM, key=CURATOR, schema="display-name/v2", github="someone-else"
    )
    assert graph.codes(change, opened_by=CURATOR, mode="display-name") == [
        "display-name-github-unverified"
    ]
    carried = graph.approval_signed(CURATOR_PSEUDONYM, schema="display-name/v2", github=STRANGER)
    assert graph.codes(carried, opened_by=CURATOR, mode="display-name") == [
        "display-name-github-unverified"
    ]
