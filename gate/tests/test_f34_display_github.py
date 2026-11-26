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


def test_the_reader_takes_both_versions_and_the_login(tmp_path: Path) -> None:
    """F34-T14: ``names.load`` reads v1 and v2 records, and a v2 record's GitHub login."""
    import yaml  # noqa: PLC0415

    from opn_gate import names  # noqa: PLC0415

    base = {
        "name": "Grace",
        "link": None,
        "date": "2026-11-25",
        "via": "approval-key",
        "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKHDEGJlALYV4+SkVajmPDtD/Pu6CMzBMnH36leBU0mr",
        "signature": "-----BEGIN SSH SIGNATURE-----\nU1NIU0lH\n-----END SSH SIGNATURE-----\n",
    }
    (tmp_path / "names").mkdir()
    for pseudonym, extra in (
        ("old", {"schema": "display-name/v1"}),
        ("new", {"schema": "display-name/v2", "github": "grace-h"}),
    ):
        doc = {**base, "pseudonym": pseudonym, **extra}
        (tmp_path / "names" / f"{pseudonym}.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    found = names.latest(tmp_path)
    assert set(found) == {"old", "new"}
    assert found["new"].github == "grace-h" and found["old"].github is None
