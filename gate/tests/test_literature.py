"""F08-T40 (D-3, D-25, D-32 v3.35): the literature record.

Three testers on erdos-1094 (2026-10-08) could not tell the open core (``--h2``) from a literature
theorem (``--h3``, Granville and Ramare 1996, never formalised) on the frontier: both read ``open``.
v3.35: any contributor may append ``nodes/<id>/literature/<timestamp>-<contributor>.yaml``
(``literature/v1``) saying what the literature says of the statement — ``open``, ``known`` or
``elementary`` — with references and a summary. Unsigned, it is a proposal, an ordinary append by
anyone, attributed like an annex (D-23), earning nothing. Signed by an active steward of the target
or a listed curator (``via: ssh`` under their own key; ``via: approval-key`` by the service for a
login signed in on the site, whose key must be ``keys/approval.pub`` in the merge's parent tree),
it is a confirmation: of the proposal it names in ``confirms``, or of a status it states itself.
The gate refuses a signed record whose signer is neither; a confirmation must name a record that
is on the node.

The products publish the latest confirmed status as the node's ``literature`` (with
``confirmed_by`` and ``confirmation``) and the latest proposal no later confirmation covers as
``literature_proposed`` — on graph.json's row, the frontier entry and CONTEXT.json (graph/v6,
frontier/v5, context/v5). A fact about the literature, never about difficulty: it changes no
status, blocks nothing and ranks nothing.

Every signed record here is signed by a real ``ssh-keygen``: the rules under test are about
signatures.
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

from opn_gate import context, layout, modes, products, schemas, signed, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

TARGET = "euclid-primes"
ALICE = "alice-steward"
BOB = "bob-prover"  # anyone: a pseudonym with no role
STRANGER = "mallory"
SERVICE = "open-proof-network[bot]"
SIGNER = SshKeygenSigner()
RENDERED = "5" * 40
NOW = "2026-10-08T12:00:00Z"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("literature-keys")
    out: dict[str, Path] = {}
    for who in ("approval", ALICE, CURATOR, STRANGER):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Graph:
    """A curated target with one node, the owner listed as curator, Alice an active steward (her
    own SSH key) and the approval key published; ``base`` is the pull request's parent tree."""

    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        self.root = copy_graph(tmp_path, publish=True)
        take_in(self.root, TARGET)
        write_curators(self.root, CURATOR)
        self.keys = keys
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / signed.APPROVAL_KEY_PATH).write_text(
            public_key_for(keys["approval"]) + "\n", encoding="utf-8"
        )
        steward.write(
            self.target, action=steward.COMMIT, login=ALICE, name="Alice",
            link="https://orcid.org/0000-0002-1825-0097", date="2026-10-01",
            key_path=keys[ALICE], signer=SIGNER,
        )  # fmt: skip
        [node_dir] = [p for p in (self.target / "nodes").iterdir() if p.is_dir()]
        self.node = node_dir.name
        self.base_files = {
            signed.APPROVAL_KEY_PATH: (self.root / signed.APPROVAL_KEY_PATH).read_bytes(),
            modes.CURATORS_FILE: (self.root / modes.CURATORS_FILE).read_bytes(),
        }

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET

    @property
    def node_dir(self) -> Path:
        return self.target / "nodes" / self.node

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    def document(self, **overrides: Any) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema": "literature/v1",
            "node": self.node,
            "contributor": BOB,
            "date": "2026-10-08T10:00:00Z",
            "status": "known",
            "references": [
                {
                    "title": "Granville and Ramaré, Explicit bounds on exponential sums",
                    "url": "https://doi.org/10.1112/S0025579300007686",
                    "note": "proves the statement for every n beyond the stated bound",
                }
            ],
            "summary": "A published proof exists; nothing formal.",
            "model_and_tooling": None,
            "confirms": None,
            "via": None,
            "key": None,
            "signature": None,
        }
        doc.update(overrides)
        return doc

    def write(self, doc: dict[str, Any], stamp: str = "20261008T100000Z") -> Change:
        name = f"{stamp}-{doc['contributor']}.yaml"
        path = self.node_dir / "literature" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return Change("A", path.relative_to(self.root).as_posix())

    def proposal(self, stamp: str = "20261008T100000Z", **overrides: Any) -> Change:
        return self.write(self.document(**overrides), stamp)

    def signed_by(
        self,
        who: str,
        *,
        key: str | None = None,
        via: str = signed.VIA_SSH,
        stamp: str = "20261008T110000Z",
        **overrides: Any,
    ) -> Change:
        date = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"
        doc = self.document(contributor=who, date=date, via=via, **overrides)
        doc = signed.sign(doc, self.keys[key or who], SIGNER)
        return self.write(doc, stamp)

    def codes(self, change: Change, *, opened_by: str = SERVICE) -> list[str]:
        classification = modes.classify([change], author=opened_by, graph_root=self.root)
        assert classification.ok, classification.as_dict()
        assert classification.mode == "append", classification.as_dict()
        return [d.code for d in modes.check(self.root, classification, base=self.base)]

    def render(self) -> products.Products:
        return products.generate(self.root, rendered_from=RENDERED, commit_time=NOW)

    def row(self, prod: products.Products) -> dict[str, Any]:
        doc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
        (row,) = [n for n in doc["nodes"] if n["node_id"] == self.node]
        return dict(row)

    def entry(self, prod: products.Products) -> dict[str, Any]:
        doc = json.loads(prod.files[Path("frontier.json")])
        (entry,) = [
            e for e in doc["entries"] if e["node_id"] == self.node and e["target_id"] == TARGET
        ]
        return dict(entry)

    def bundle(self, prod: products.Products) -> dict[str, Any]:
        return dict(json.loads(prod.files[Path(context.context_path(TARGET, self.node))]))


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


# --- the role and the layout --------------------------------------------------------------------


def test_the_role_is_registered_as_an_append(graph: Graph) -> None:
    change = graph.proposal()
    classification = modes.classify([change], author=BOB, graph_root=graph.root)
    assert classification.ok, classification.as_dict()
    assert classification.mode == "append"
    [located] = classification.located
    assert located.role == "literature" and located.node_id == graph.node


def test_a_node_carrying_a_literature_directory_passes_layout(graph: Graph) -> None:
    graph.proposal()
    assert layout.validate_node(graph.node_dir) == []


# --- a proposal is anyone's append ---------------------------------------------------------------


def test_an_unsigned_record_is_accepted_from_anyone(graph: Graph) -> None:
    assert graph.codes(graph.proposal(), opened_by=STRANGER) == []


def test_a_proposal_is_published_as_proposed_and_confirms_nothing(graph: Graph) -> None:
    graph.proposal()
    prod = graph.render()
    expected = {
        "status": "known",
        "record": f"literature/20261008T100000Z-{BOB}.yaml",
        "contributor": BOB,
    }
    row = graph.row(prod)
    assert row["literature"] is None
    assert row["literature_proposed"] == expected
    assert graph.entry(prod)["literature_proposed"] == expected
    assert graph.bundle(prod)["literature_proposed"] == expected
    assert graph.entry(prod)["literature"] is None and graph.bundle(prod)["literature"] is None
    assert schemas.violations(graph.bundle(prod), context.SCHEMA) == []


def test_a_proposal_changes_no_status_and_nothing_leaves_the_frontier(graph: Graph) -> None:
    before = graph.render()
    graph.proposal(status="elementary")
    after = graph.render()
    assert graph.row(after)["status"] == graph.row(before)["status"]
    assert graph.entry(after)["claimable"] == graph.entry(before)["claimable"]
    assert graph.entry(after)["needs"] == graph.entry(before)["needs"]


def test_a_proposal_that_confirms_is_refused(graph: Graph) -> None:
    graph.proposal()
    change = graph.proposal(
        stamp="20261008T103000Z", confirms=f"literature/20261008T100000Z-{BOB}.yaml"
    )
    assert graph.codes(change, opened_by=BOB) == ["literature-signature"]


def test_a_record_filed_under_another_node_is_refused(graph: Graph) -> None:
    assert graph.codes(graph.proposal(node="some-other-node")) == ["literature-node"]


# --- a signed record is a steward's or a curator's confirmation ----------------------------------


def test_a_steward_may_state_the_status_herself(graph: Graph) -> None:
    change = graph.signed_by(ALICE)
    assert graph.codes(change, opened_by=STRANGER) == [], "the signature binds, not the opener"
    prod = graph.render()
    own = f"literature/20261008T110000Z-{ALICE}.yaml"
    expected = {
        "status": "known",
        "record": own,
        "contributor": ALICE,
        "confirmed_by": ALICE,
        "confirmation": own,
    }
    assert graph.row(prod)["literature"] == expected
    assert graph.entry(prod)["literature"] == expected
    assert graph.bundle(prod)["literature"] == expected
    assert graph.row(prod)["literature_proposed"] is None
    assert schemas.violations(json.loads(prod.files[Path("frontier.json")])) == []


def test_a_steward_confirms_a_proposal_and_the_proposal_is_what_is_published(graph: Graph) -> None:
    graph.proposal()  # Bob's, 10:00
    proposal = f"literature/20261008T100000Z-{BOB}.yaml"
    change = graph.signed_by(ALICE, confirms=proposal, status="known")
    assert graph.codes(change) == []
    prod = graph.render()
    assert graph.row(prod)["literature"] == {
        "status": "known",
        "record": proposal,
        "contributor": BOB,
        "confirmed_by": ALICE,
        "confirmation": f"literature/20261008T110000Z-{ALICE}.yaml",
    }
    assert graph.row(prod)["literature_proposed"] is None, "the confirmed proposal is covered"


def test_a_later_proposal_is_proposed_beside_the_confirmed_status(graph: Graph) -> None:
    graph.signed_by(ALICE, status="open")
    graph.proposal(stamp="20261008T120000Z", status="known", date="2026-10-08T12:00:00Z")
    prod = graph.render()
    assert graph.row(prod)["literature"]["status"] == "open"
    assert graph.row(prod)["literature_proposed"] == {
        "status": "known",
        "record": f"literature/20261008T120000Z-{BOB}.yaml",
        "contributor": BOB,
    }


def test_an_earlier_proposal_is_covered_by_a_later_confirmation(graph: Graph) -> None:
    graph.proposal(status="elementary")  # 10:00, never confirmed, never contradicted by name
    graph.signed_by(ALICE, status="known")  # 11:00
    prod = graph.render()
    assert graph.row(prod)["literature"]["status"] == "known"
    assert graph.row(prod)["literature_proposed"] is None


def test_the_latest_confirmation_supersedes_an_earlier_one(graph: Graph) -> None:
    graph.signed_by(ALICE, status="open", stamp="20261008T110000Z")
    graph.signed_by(ALICE, status="known", stamp="20261008T130000Z")
    assert graph.row(graph.render())["literature"]["status"] == "known"


def test_a_curator_confirms_with_her_own_key_when_she_opens_the_pull_request(graph: Graph) -> None:
    change = graph.signed_by(CURATOR)
    assert graph.codes(change, opened_by=CURATOR) == []
    assert graph.codes(change, opened_by=STRANGER) == ["signer-not-opener"]
    assert graph.row(graph.render())["literature"]["confirmed_by"] == CURATOR


def test_a_signer_who_is_neither_steward_nor_curator_is_refused(graph: Graph) -> None:
    change = graph.signed_by(STRANGER)
    assert graph.codes(change, opened_by=STRANGER) == ["literature-signer-unlisted"]
    row = graph.row(graph.render())
    assert row["literature"] is None, "a signed record that does not count confirms nothing"
    assert row["literature_proposed"] is None, "and is not a proposal either"


def test_a_tampered_signature_is_refused(graph: Graph) -> None:
    change = graph.signed_by(ALICE)
    path = graph.root / change.path
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["status"] = "elementary"  # re-grading after the fact
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert graph.codes(change) == ["literature-signature"]
    assert graph.row(graph.render())["literature"] is None


def test_a_half_signed_record_is_refused(graph: Graph) -> None:
    change = graph.proposal(via=signed.VIA_SSH)  # via without key or signature
    assert graph.codes(change) == ["literature-signature"]


def test_a_confirmation_must_name_a_record_on_the_node(graph: Graph) -> None:
    change = graph.signed_by(ALICE, confirms="literature/20261001T000000Z-nobody.yaml")
    assert graph.codes(change) == ["literature-record-unknown"]


# --- the approval key: the service's act for a signed-in steward or curator ----------------------


def test_an_approval_key_confirmation_by_a_curator_is_accepted(graph: Graph) -> None:
    change = graph.signed_by(CURATOR, key="approval", via=signed.VIA_APPROVAL_KEY)
    assert graph.codes(change, opened_by=SERVICE) == []
    assert graph.row(graph.render())["literature"]["confirmed_by"] == CURATOR


def test_an_approval_key_record_under_another_key_is_refused(graph: Graph) -> None:
    change = graph.signed_by(CURATOR, key=CURATOR, via=signed.VIA_APPROVAL_KEY)
    assert graph.codes(change, opened_by=SERVICE) == ["literature-signature"]
    assert graph.row(graph.render())["literature"] is None


def test_the_approval_key_is_read_from_the_parent_tree(graph: Graph) -> None:
    """A pull request that replaces keys/approval.pub in its own tree brings no key."""
    (graph.root / signed.APPROVAL_KEY_PATH).write_text(
        public_key_for(graph.keys[STRANGER]) + "\n", encoding="utf-8"
    )
    change = graph.signed_by(CURATOR, key=STRANGER, via=signed.VIA_APPROVAL_KEY)
    assert graph.codes(change, opened_by=SERVICE) == ["literature-signature"]


def test_an_approval_key_record_for_a_stranger_is_refused(graph: Graph) -> None:
    change = graph.signed_by(STRANGER, key="approval", via=signed.VIA_APPROVAL_KEY)
    assert graph.codes(change, opened_by=SERVICE) == ["literature-signer-unlisted"]


# --- derive, never rewrite -----------------------------------------------------------------------


def test_removing_the_records_restores_every_product(graph: Graph) -> None:
    before = graph.render().files
    graph.proposal()
    graph.signed_by(ALICE)
    assert graph.render().files != before
    for p in (graph.node_dir / "literature").iterdir():
        p.unlink()
    (graph.node_dir / "literature").rmdir()
    assert graph.render().files == before
