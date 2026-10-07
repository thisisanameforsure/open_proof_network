"""F23-T2 / AC6: ``steward/v2`` at the gate (R9; D-32 v3.33, D-22 v3.33).

A v2 record is made through the service for a login signed in with GitHub, signed with the
network's approval key (``via: approval-key``), or with the steward's own SSH key (``via: ssh``).
The gate admits one only when an approval-key record's ``key`` is the graph's
``keys/approval.pub`` *in the merge's parent tree* — so a pull request cannot bring its own key —
and its ``admitted_by`` agrees with ``policy.json``'s ``steward_admission`` in that tree: ``self``
only under ``open`` (also when there is no policy file, or a ``policy/v1`` one); under
``reviewed``, a login ``curators.json`` lists. A step-down of either version ends a commitment of
either version for the same login.

Every record is signed by a real ``ssh-keygen``: the rule under test is about signatures.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from test_modes import CURATOR, write_curators

from opn_gate import modes, policy, schemas, signed, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

TARGET = "euclid-primes"
ALICE = "alice-steward"
LINK = "https://orcid.org/0000-0002-1825-0097"
SIGNER = SshKeygenSigner()
SERVICE = "open-proof-network[bot]"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """The network's approval key, Alice's own key and a stranger's."""
    d = tmp_path_factory.mktemp("steward-v2-keys")
    out: dict[str, Path] = {}
    for who in ("approval", ALICE, "stranger"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Graph:
    """A curated target with the owner listed as curator and the approval key published. The
    pull request's base is what stood before the record was written (``base``)."""

    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        self.root = copy_graph(tmp_path)
        take_in(self.root, TARGET)
        write_curators(self.root, CURATOR)
        self.keys = keys
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / signed.APPROVAL_KEY_PATH).write_text(
            public_key_for(keys["approval"]) + "\n", encoding="utf-8"
        )
        self.base_files: dict[str, bytes] = {
            signed.APPROVAL_KEY_PATH: (self.root / signed.APPROVAL_KEY_PATH).read_bytes(),
            modes.CURATORS_FILE: (self.root / modes.CURATORS_FILE).read_bytes(),
        }

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    def set_policy(self, admission: str | None) -> None:
        """``policy.json`` on the base: ``None`` for a v1 file (no admission field)."""
        rule = {"enforced": False, "since": None, "evidence": None}
        doc: dict[str, Any] = (
            {"schema": "policy/v1", "steward_rule": rule}
            if admission is None
            else {"schema": "policy/v2", "steward_rule": rule, "steward_admission": admission}
        )
        data = schemas.canonical_json(doc)
        (self.root / policy.FILE).write_bytes(data)
        self.base_files[policy.FILE] = data

    def v2(
        self,
        *,
        action: str = steward.COMMIT,
        login: str = ALICE,
        admitted_by: str = steward.SELF,
        key: str = "approval",
        via: str = signed.VIA_APPROVAL_KEY,
        link: str | None = None,
    ) -> Change:
        doc = steward.document_v2(
            target_id=TARGET, action=action, login=login, name="Alice", link=link,
            date="2026-10-07", admitted_by=admitted_by, via=via,
        )  # fmt: skip
        doc = schemas.validate(signed.sign(doc, self.keys[key], SIGNER), steward.SCHEMA_V2)
        path = steward.next_path(self.target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return Change("A", path.relative_to(self.root).as_posix())

    def v1(self, action: str = steward.COMMIT, *, key: str = ALICE) -> Path:
        if action == steward.COMMIT:
            return steward.write(
                self.target, action=action, login=ALICE, name="Alice", link=LINK,
                date="2026-09-16", key_path=self.keys[key], signer=SIGNER,
            )  # fmt: skip
        return steward.write(
            self.target, action=action, login=ALICE, date="2026-09-16",
            key_path=self.keys[key], signer=SIGNER,
        )  # fmt: skip

    def codes(self, change: Change, *, opened_by: str = SERVICE) -> list[str]:
        classification = modes.classify([change], author=opened_by, graph_root=self.root)
        assert classification.ok, classification.as_dict()
        return [d.code for d in modes.check(self.root, classification, base=self.base)]

    def active(self) -> list[steward.Steward]:
        return steward.active(self.target, SIGNER)


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


# --- the approval key ---------------------------------------------------------------------------


def test_an_approval_key_record_is_admitted_under_open(graph: Graph) -> None:
    """No policy file means ``open``: a self-admitted record signed with the published key is
    admitted, and the login is active, marked self-admitted, with no identity link."""
    assert graph.codes(graph.v2()) == []
    [alice] = graph.active()
    assert alice.login == ALICE and alice.admitted_by == steward.SELF and alice.link is None


def test_a_record_signed_by_another_key_is_refused(graph: Graph) -> None:
    """AC6: an approval-key record whose signature verifies under its own key, which is not the
    graph's approval key, is refused ``steward-signature``."""
    assert "steward-signature" in graph.codes(graph.v2(key="stranger"))


def test_the_approval_key_is_read_from_the_parent_tree(graph: Graph) -> None:
    """A pull request that replaces ``keys/approval.pub`` in its own tree does not change the
    key it is judged against: the base's key is the one."""
    (graph.root / signed.APPROVAL_KEY_PATH).write_text(
        public_key_for(graph.keys["stranger"]) + "\n", encoding="utf-8"
    )
    assert "steward-signature" in graph.codes(graph.v2(key="stranger"))


def test_without_a_published_approval_key_no_approval_record_is_admitted(graph: Graph) -> None:
    del graph.base_files[signed.APPROVAL_KEY_PATH]
    (graph.root / signed.APPROVAL_KEY_PATH).unlink()
    assert "steward-signature" in graph.codes(graph.v2())


def test_a_tampered_record_is_refused(graph: Graph) -> None:
    change = graph.v2()
    path = graph.root / change.path
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["login"] = "mallory"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert "steward-signature" in graph.codes(change)


def test_an_ssh_v2_record_needs_no_approval_key(graph: Graph) -> None:
    """``via: ssh`` is the steward's own key, as v1: it verifies under itself."""
    assert graph.codes(graph.v2(key=ALICE, via=signed.VIA_SSH, link=LINK)) == []


# --- admission ----------------------------------------------------------------------------------


@pytest.mark.parametrize("admission", [None, "open"])
def test_self_is_the_only_admission_under_open(graph: Graph, admission: str | None) -> None:
    """A policy/v1 file, or policy/v2 ``open``: ``self`` is admitted, a curator is not."""
    graph.set_policy(admission)
    assert graph.codes(graph.v2()) == []
    assert "steward-admission" in graph.codes(graph.v2(admitted_by=CURATOR))


def test_self_under_reviewed_is_refused(graph: Graph) -> None:
    """AC6: under ``reviewed`` a record that admits itself is refused."""
    graph.set_policy("reviewed")
    assert "steward-admission" in graph.codes(graph.v2())


def test_reviewed_admits_a_listed_curator_only(graph: Graph) -> None:
    graph.set_policy("reviewed")
    assert graph.codes(graph.v2(admitted_by=CURATOR)) == []
    other = graph.v2(admitted_by="not-a-curator")
    assert "steward-admission" in graph.codes(other)


def test_the_curators_are_read_from_the_parent_tree(graph: Graph) -> None:
    """A curator listed only in the pull request's own tree admits nobody."""
    graph.set_policy("reviewed")
    write_curators(graph.root, CURATOR, "newcomer")
    assert "steward-admission" in graph.codes(graph.v2(admitted_by="newcomer"))


def test_policy_v2_loads() -> None:
    assert {"policy/v1", "policy/v2"} <= policy.SCHEMAS


def test_the_admission_of_a_policy(graph: Graph) -> None:
    assert policy.load(graph.root).admission == "open"
    graph.set_policy(None)
    assert policy.load(graph.root).admission == "open"
    graph.set_policy("reviewed")
    assert policy.load(graph.root).admission == "reviewed"
    assert json.loads((graph.root / policy.FILE).read_text())["steward_admission"] == "reviewed"


# --- either version ends either version ---------------------------------------------------------


def test_an_ssh_commit_is_ended_by_an_approval_key_step_down(graph: Graph) -> None:
    """AC6: an SSH v1 commit followed by a v2 step-down for the same login: not active."""
    graph.v1()
    assert [s.login for s in graph.active()] == [ALICE]
    change = graph.v2(action=steward.STEP_DOWN)
    assert graph.codes(change) == []
    assert graph.active() == []


def test_an_approval_key_commit_is_ended_by_an_ssh_step_down(graph: Graph) -> None:
    graph.v2()
    assert [s.login for s in graph.active()] == [ALICE]
    path = graph.v1(steward.STEP_DOWN)
    assert graph.codes(Change("A", path.relative_to(graph.root).as_posix())) == []
    assert graph.active() == []


def test_two_ssh_records_still_need_the_same_key(graph: Graph) -> None:
    """F15-R1 unchanged between two SSH records: a stranger's key cannot step Alice down."""
    graph.v1()
    change = graph.v2(action=steward.STEP_DOWN, key="stranger", via=signed.VIA_SSH)
    assert "steward-key" in graph.codes(change)
    assert [s.login for s in graph.active()] == [ALICE]


def test_a_step_down_from_nobody_is_refused(graph: Graph) -> None:
    assert "steward-not-active" in graph.codes(graph.v2(action=steward.STEP_DOWN))
