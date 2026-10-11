"""F25-T4 / AC4 (admission half), AC5 (the mode): the two records D-3 v3.37 puts outside the node.

``targets/<id>/registrations/<date>-<n>.yaml`` (``registration/v1``) is admitted only from a listed
curator or an active steward of the target, named in ``submitted_by`` and equal to whoever the pull
request acts for: the opener, or, for a pull request the service opened, the record's own author
(F18-Q7). It names a node of its target and the passing attestation of that node's merge, and the
graph commit it was exported from is one of the record's history when the checkout has one.
``names/<pseudonym>.yaml`` (``display-name/v1``) is admitted only for the pseudonym the pull
request acts for, signed: by the approval key of the merge's parent tree through the service, or by
a listed curator's own key when they open it themselves.

Each is a mode of its own, so the mode table's fallthrough — ``return "append"`` for whatever
was left over, which swallowed the first steward record (log, 2026-09-17) — cannot read either as
an append; and mixing either with anything else is refused.

Every signed record here is signed by a real ``ssh-keygen``: the rules under test are about
signatures and keys.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import copy_graph
from test_modes import CURATOR, write_curators

from opn_gate import config, modes, paths, schemas, signed, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

TARGET = "propositional"
NODE = "tutorial-and-swap"
ALICE = "alice-steward"  # an active steward of the target, her own key
BOB = "bob-prover"  # anyone: a pseudonym and login with no role and no pairing
STRANGER = "mallory"
SERVICE = config.DEFAULT_SERVICE_LOGIN
CURATOR_PSEUDONYM = f"{CURATOR}-pseudonym"  # what test_modes.write_curators pairs the login with
SIGNER = SshKeygenSigner()
ATTESTATION = "000038"
REGISTRATION = f"targets/{TARGET}/registrations/2026-10-12-1.yaml"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("registration-keys")
    out: dict[str, Path] = {}
    for who in ("approval", "other", ALICE, CURATOR, BOB):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Graph:
    """The propositional fixture with the owner listed as curator, Alice an active steward (her
    own key), the approval key published, and a passing attestation of ``NODE``'s merge."""

    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        self.root = copy_graph(tmp_path)
        self.keys = keys
        write_curators(self.root, CURATOR)
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / signed.APPROVAL_KEY_PATH).write_text(
            public_key_for(keys["approval"]) + "\n", encoding="utf-8"
        )
        steward.write(
            self.target, action=steward.COMMIT, login=ALICE, name="Alice",
            link="https://orcid.org/0000-0002-1825-0097", date="2026-10-01",
            key_path=keys[ALICE], signer=SIGNER,
        )  # fmt: skip
        self.attest(ATTESTATION, node_id=NODE)
        self.base_files = {
            signed.APPROVAL_KEY_PATH: (self.root / signed.APPROVAL_KEY_PATH).read_bytes(),
            modes.CURATORS_FILE: (self.root / modes.CURATORS_FILE).read_bytes(),
        }

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    def attest(self, number: str, **overrides: Any) -> None:
        where = self.root / "attestations"
        where.mkdir(exist_ok=True)
        doc = samples.attestation(graph_id=TARGET, **overrides)
        (where / f"{number}.json").write_bytes(schemas.canonical_json(doc))

    # -- registrations --

    def registration(self, **overrides: Any) -> dict[str, Any]:
        doc = samples.registration(
            target=TARGET, proof={"node": NODE, "attestation": ATTESTATION}, submitted_by=CURATOR
        )
        doc.update(overrides)
        return doc

    def write_registration(
        self, doc: dict[str, Any], path: str = REGISTRATION, status: str = "A"
    ) -> Change:
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return Change(status, path)  # type: ignore[arg-type]

    # -- display names --

    def name_doc(self, pseudonym: str, **overrides: Any) -> dict[str, Any]:
        doc = samples.display_name(pseudonym=pseudonym)
        doc.pop("key")
        doc.pop("signature")
        doc.update(overrides)
        return doc

    def approval_signed(self, pseudonym: str, *, key: str = "approval", **over: Any) -> Change:
        doc = signed.sign(
            self.name_doc(pseudonym, via=signed.VIA_APPROVAL_KEY, **over), self.keys[key], SIGNER
        )
        return self.write_name(doc)

    def ssh_signed(self, pseudonym: str, *, key: str, **over: Any) -> Change:
        doc = signed.sign(
            self.name_doc(pseudonym, via=signed.VIA_SSH, **over), self.keys[key], SIGNER
        )
        return self.write_name(doc)

    def write_name(self, doc: dict[str, Any], stem: str | None = None, status: str = "A") -> Change:
        path = f"{paths.NAMES_DIR}/{stem or doc['pseudonym']}.yaml"
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return Change(status, path)  # type: ignore[arg-type]

    # -- the gate --

    def classify(self, *changes: Change, opened_by: str = SERVICE) -> modes.Classification:
        return modes.classify(changes, author=opened_by, graph_root=self.root)

    def codes(self, *changes: Change, opened_by: str = SERVICE, mode: str) -> list[str]:
        classification = self.classify(*changes, opened_by=opened_by)
        if not classification.ok:
            return [d.code for d in classification.problems]
        assert classification.mode == mode, classification.as_dict()
        return [d.code for d in modes.check(self.root, classification, base=self.base)]


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


# --- the paths and the modes ---------------------------------------------------------------------


def test_the_two_paths_have_roles_of_their_own() -> None:
    where = paths.locate(REGISTRATION)
    assert where is not None
    assert (where.role, where.target_id, where.node_id) == ("registration", TARGET, None)
    name = paths.locate(f"names/{BOB}.yaml")
    assert name is not None
    assert (name.role, name.target_id, name.node_id) == ("display-name", paths.GRAPH_SCOPE, None)
    assert paths.locate(f"names/{BOB}.txt") is None
    assert paths.locate("names/not a pseudonym.yaml") is None
    assert paths.locate(f"names/sub/{BOB}.yaml") is None
    assert paths.locate(f"targets/{TARGET}/registrations/sub/x.yaml") is None
    assert paths.SCHEMAS_FOR_ROLE["registration"] == ("registration/v1",)
    assert paths.SCHEMAS_FOR_ROLE["display-name"] == ("display-name/v1",)


def test_each_record_alone_is_its_own_mode(graph: Graph) -> None:
    c = graph.classify(graph.write_registration(graph.registration()))
    assert c.ok and c.mode == "registration", c.as_dict()
    assert c.target_id == TARGET and c.node_id is None
    n = graph.classify(graph.approval_signed(BOB))
    assert n.ok and n.mode == "display-name", n.as_dict()
    assert n.target_id == paths.GRAPH_SCOPE


def test_the_fallthrough_cannot_read_either_as_an_append() -> None:
    """The 2026-09-17 shape: ``_mode_for`` ends in ``return "append"`` for what is left, and a
    role nobody placed fell into it. Neither of these is an append to that table."""
    assert modes._mode_for({"registration"}) is None
    assert modes._mode_for({"display-name"}) is None
    assert "registration" not in paths.APPEND_ROLES
    assert "display-name" not in paths.APPEND_ROLES


def test_mixing_either_with_anything_else_is_refused(graph: Graph) -> None:
    registration = graph.write_registration(graph.registration())
    postmortem = Change("A", f"targets/{TARGET}/nodes/{NODE}/attempts/2026-10-12-x.yaml")
    assert graph.codes(registration, postmortem, mode="registration") == ["mode-mixed"]
    steward_record = Change("A", f"targets/{TARGET}/stewards/9.yaml")
    assert graph.codes(registration, steward_record, mode="registration") == ["mode-mixed"]
    name = graph.approval_signed(BOB)
    # The graph-root scope (the policy.json precedent): a target's file beside it is two scopes.
    assert graph.codes(name, registration, mode="display-name") == ["mode-multi-target"]
    assert graph.codes(name, Change("M", paths.POLICY_FILE), mode="display-name") == ["mode-mixed"]


def test_a_registration_is_append_only_and_a_name_may_be_replaced(graph: Graph) -> None:
    doc = graph.registration()
    graph.write_registration(doc)
    modified = graph.write_registration(doc | {"status": "registered"}, status="M")
    assert graph.codes(modified, mode="registration") == ["path-forbidden"]
    assert "display-name" in paths.MODIFIABLE_ROLES, "a later record replaces the file (R6)"
    graph.approval_signed(BOB)
    replaced = graph.approval_signed(BOB, name=None)
    assert graph.codes(Change("M", replaced.path), mode="display-name") == []


# --- registrations: who ---------------------------------------------------------------------------


def test_a_curators_registration_through_the_service_passes(graph: Graph) -> None:
    assert graph.codes(graph.write_registration(graph.registration()), mode="registration") == []


def test_a_stewards_registration_passes(graph: Graph) -> None:
    change = graph.write_registration(graph.registration(submitted_by=ALICE))
    assert graph.codes(change, mode="registration") == []
    assert graph.codes(change, opened_by=ALICE, mode="registration") == []


def test_a_submitter_who_is_neither_curator_nor_steward_is_refused(graph: Graph) -> None:
    change = graph.write_registration(graph.registration(submitted_by=BOB))
    assert graph.codes(change, opened_by=BOB, mode="registration") == ["registration-not-curator"]
    assert graph.codes(change, mode="registration") == ["registration-not-curator"]


def test_a_hand_opened_registration_must_be_opened_by_its_submitter(graph: Graph) -> None:
    change = graph.write_registration(graph.registration())
    assert graph.codes(change, opened_by=CURATOR, mode="registration") == []
    assert graph.codes(change, opened_by=STRANGER, mode="registration") == [
        "registration-not-opener"
    ]
    assert graph.codes(change, opened_by=ALICE, mode="registration") == ["registration-not-opener"]


def test_a_stepped_down_steward_is_no_longer_a_steward(graph: Graph) -> None:
    steward.write(
        graph.target, action=steward.STEP_DOWN, login=ALICE, name="Alice",
        link="https://orcid.org/0000-0002-1825-0097", date="2026-10-02",
        key_path=graph.keys[ALICE], signer=SIGNER,
    )  # fmt: skip
    change = graph.write_registration(graph.registration(submitted_by=ALICE))
    assert graph.codes(change, mode="registration") == ["registration-not-curator"]


# --- registrations: what ------------------------------------------------------------------------


def test_the_record_names_the_target_it_sits_under(graph: Graph) -> None:
    change = graph.write_registration(graph.registration(target="euclid-primes"))
    assert graph.codes(change, mode="registration") == ["registration-target-mismatch"]


def test_the_file_is_named_date_n(graph: Graph) -> None:
    for bad in ("notes.yaml", "2026-10-12.yaml", "2026-10-12-0.yaml", "20261012-1.yaml"):
        change = graph.write_registration(
            graph.registration(), path=f"targets/{TARGET}/registrations/{bad}"
        )
        assert graph.codes(change, mode="registration") == ["registration-name"], bad
    good = graph.write_registration(
        graph.registration(), path=f"targets/{TARGET}/registrations/2026-10-12-12.yaml"
    )
    assert graph.codes(good, mode="registration") == []


def test_the_proof_node_is_a_node_of_the_target(graph: Graph) -> None:
    change = graph.write_registration(
        graph.registration(proof={"node": "no-such-node", "attestation": ATTESTATION})
    )
    assert graph.codes(change, mode="registration") == ["registration-proof-unknown"]


def test_the_attestation_exists_names_the_node_and_passed(graph: Graph) -> None:
    missing = graph.write_registration(
        graph.registration(proof={"node": NODE, "attestation": "000999"})
    )
    assert graph.codes(missing, mode="registration") == ["registration-attestation-unknown"]
    graph.attest("000040", node_id="and-reassoc")
    other_node = graph.write_registration(
        graph.registration(proof={"node": NODE, "attestation": "000040"})
    )
    assert graph.codes(other_node, mode="registration") == ["registration-attestation-mismatch"]
    graph.attest("000041", node_id=NODE, verdict="fail", first_failing_step=4)
    failed = graph.write_registration(
        graph.registration(proof={"node": NODE, "attestation": "000041"})
    )
    assert graph.codes(failed, mode="registration") == ["registration-attestation-mismatch"]
    (graph.root / "attestations" / "000042.json").write_text("not json", encoding="utf-8")
    unreadable = graph.write_registration(
        graph.registration(proof={"node": NODE, "attestation": "000042"})
    )
    assert graph.codes(unreadable, mode="registration") == ["registration-attestation-mismatch"]


def test_a_withdrawn_or_rejected_record_needs_no_url(graph: Graph) -> None:
    for status in ("withdrawn", "rejected", "submitted"):
        change = graph.write_registration(
            graph.registration(status=status, url=None, version=None, registry_id=None)
        )
        assert graph.codes(change, mode="registration") == [], status


def test_a_record_that_does_not_validate_is_refused_by_schema(graph: Graph) -> None:
    change = graph.write_registration(graph.registration(status="pending"))
    assert graph.codes(change, mode="registration") == ["record-invalid"]
    change = graph.write_registration(graph.registration(graph_commit="abc"))
    assert graph.codes(change, mode="registration") == ["record-invalid"]


def _git(root: Path, *args: str) -> str:
    env = config.child_environment(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.org",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.org",
        },
        drop=config.GIT_REPO_VARIABLES,
    )
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=env
    )
    return proc.stdout.strip()


def test_the_graph_commit_is_in_the_checkouts_history_when_it_has_one(graph: Graph) -> None:
    """A commit the graph never had cannot be the one the wrapper was exported from. Checked by
    git when the checkout is a repository; a plain tree (every fixture, the service's scratch
    copy) cannot answer and is not asked."""
    not_a_repo = graph.write_registration(graph.registration(graph_commit="e" * 40))
    assert graph.codes(not_a_repo, mode="registration") == [], "no .git: the question is skipped"
    _git(graph.root, "init", "-q")
    _git(graph.root, "add", "-A")
    _git(graph.root, "commit", "-q", "-m", "seed")
    head = _git(graph.root, "rev-parse", "HEAD")
    assert graph.codes(not_a_repo, mode="registration") == ["registration-commit-unknown"]
    at_head = graph.write_registration(graph.registration(graph_commit=head))
    assert graph.codes(at_head, mode="registration") == []


# --- display names ------------------------------------------------------------------------------


def test_the_service_writes_a_name_for_the_bearers_pseudonym(graph: Graph) -> None:
    assert graph.codes(graph.approval_signed(BOB), mode="display-name") == []
    assert graph.codes(graph.approval_signed(BOB, name=None, link=None), mode="display-name") == []


def test_a_hand_opened_approval_key_record_is_its_openers_pseudonym(graph: Graph) -> None:
    """The service is the only writer with the approval key (D-3 v3.37), but a record it signed
    could be carried in a hand-opened pull request; it then counts for the opener's pseudonym
    alone, read through curators.json's pairing (``acting_names``)."""
    change = graph.approval_signed(CURATOR_PSEUDONYM)
    assert graph.codes(change, opened_by=CURATOR, mode="display-name") == []
    assert graph.codes(change, opened_by=STRANGER, mode="display-name") == [
        "display-name-not-owner"
    ]
    assert graph.codes(graph.approval_signed(BOB), opened_by=CURATOR, mode="display-name") == [
        "display-name-not-owner"
    ]


def test_an_approval_key_record_carries_the_parents_approval_key(graph: Graph) -> None:
    change = graph.approval_signed(BOB, key="other")
    assert graph.codes(change, mode="display-name") == ["signature-invalid"]
    graph.base_files.pop(signed.APPROVAL_KEY_PATH)
    assert graph.codes(graph.approval_signed(BOB), mode="display-name") == ["signature-invalid"]


def test_a_tampered_or_missing_signature_is_refused(graph: Graph) -> None:
    change = graph.approval_signed(BOB)
    path = graph.root / change.path
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["name"] = "Somebody Else"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert graph.codes(change, mode="display-name") == ["display-name-unsigned"]
    unsigned = graph.write_name(graph.name_doc(BOB, via="approval-key", key=None, signature=None))
    # Two fields fail the schema (key, signature), one diagnostic each: refused before any
    # signature question is asked.
    assert set(graph.codes(unsigned, mode="display-name")) == {"record-invalid"}


def test_the_file_stem_is_the_pseudonym(graph: Graph) -> None:
    doc = signed.sign(graph.name_doc(BOB, via="approval-key"), graph.keys["approval"], SIGNER)
    change = graph.write_name(doc, stem=STRANGER)
    assert graph.codes(change, mode="display-name") == ["display-name-stem-mismatch"]


def test_a_curator_may_sign_her_own_name_with_her_key_and_open_it(graph: Graph) -> None:
    change = graph.ssh_signed(CURATOR_PSEUDONYM, key=CURATOR)
    assert graph.codes(change, opened_by=CURATOR, mode="display-name") == []
    assert graph.codes(change, opened_by=STRANGER, mode="display-name") == [
        "display-name-not-owner"
    ]


def test_an_ssh_record_for_an_unpaired_pseudonym_is_refused(graph: Graph) -> None:
    """Nothing on the graph pairs an ordinary contributor's pseudonym with a GitHub login (the
    pairing is the service's, D-19), so a hand-opened SSH-signed name has no owner the gate can
    name: the holder uses POST /me/name (F25-Q, proposed)."""
    change = graph.ssh_signed(BOB, key=BOB)
    assert graph.codes(change, opened_by=BOB, mode="display-name") == ["display-name-ssh-unpaired"]
    # The service signs with the approval key and nothing else (C7): an ssh record it opened is
    # nobody's.
    assert graph.codes(graph.ssh_signed(BOB, key=BOB), mode="display-name") == [
        "display-name-ssh-unpaired"
    ]


def test_the_check_as_the_service_runs_it_agrees(graph: Graph) -> None:
    """``modes.check_as_service`` is the route's pre-flight: one function, so neither restates."""
    doc = signed.sign(graph.name_doc(BOB, via="approval-key"), graph.keys["approval"], SIGNER)
    content = yaml.safe_dump(doc, sort_keys=False).encode()
    assert modes.check_as_service(graph.root, f"names/{BOB}.yaml", content, signer=SIGNER) == []
    wrong_stem = modes.check_as_service(
        graph.root, f"names/{STRANGER}.yaml", content, signer=SIGNER
    )
    assert [d.code for d in wrong_stem] == ["display-name-stem-mismatch"]
    registration = yaml.safe_dump(graph.registration(), sort_keys=False).encode()
    assert modes.check_as_service(graph.root, REGISTRATION, registration, signer=SIGNER) == []
