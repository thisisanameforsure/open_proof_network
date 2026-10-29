"""F26-T3 / AC10 (F26-R2; D-9 v3.39): who may open a formalization review, and the background
opening on every existing target.

A ``review.yaml`` arriving by pull request is admitted only when the opener's role is one
``policy.json``'s ``review_openers`` lists (default: proposer, steward, curator), the opener holds
that role on the graph as the merge's parent tree has it (a listed curator, an active steward of
the target, or — for a proposer, until F26-T10's proposal record names one — the identity the
pull request acts for), and no review of this root version exists already unless the new record
names the old one in ``supersedes``. The ``network`` role is never admitted by pull request: the
background review is ``opn-gate review open``, which writes into a checkout for a curator's direct
commit and opens whatever the setting says.

Every signed record here is signed by a real ``ssh-keygen``, since a steward's standing is a
signature.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import ADVERSARIAL, copy_graph
from test_modes import CURATOR, write_curators

from opn_gate import (
    cli,
    config,
    intake,
    ledger,
    modes,
    panel,
    policy,
    review,
    review_open,
    schemas,
    steward,
)
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner

TARGET = "propositional"
ROOT = "and-swap-reassoc"
WORDS = "For all propositions p, q and r, (p and q) and r implies r and (q and p)."
ALICE = "alice-steward"  # an active steward of the target
BOB = "bob-proposer"  # anyone with a login and no role
STRANGER = "mallory"  # calls herself a curator; curators.json does not
SIGNER = SshKeygenSigner()
REVIEW = f"targets/{TARGET}/review/review.yaml"
DAY = "2026-10-12"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("review-policy-keys")
    out: dict[str, Path] = {}
    for who in (ALICE,):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


def panel_doc() -> dict[str, Any]:
    """The panel settings at their defaults, each dated, as ``policy/v4`` requires."""
    return {
        name: {"value": value, "since": DAY, "reason": "the default"}
        for name, value in panel.Settings().values().items()
    }


def policy_doc(roles: list[str] | None) -> dict[str, Any]:
    """A ``policy/v4`` file; ``None`` leaves ``review_openers`` to a ``policy/v3`` file, which has
    no such field, so the default applies."""
    doc: dict[str, Any] = {
        "schema": "policy/v3" if roles is None else "policy/v4",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "open",
        "panel": panel_doc(),
    }
    if roles is not None:
        doc["review_openers"] = {"roles": roles, "since": DAY, "evidence": "the pilot"}
    assert schemas.violations(doc, str(doc["schema"])) == []
    return doc


class Graph:
    """The propositional fixture with the owner listed as curator and Alice an active steward
    of the target; ``base`` serves the merge's parent tree from the files as they stood before
    the pull request, which is where the gate reads the policy, the curators and any review."""

    def __init__(
        self,
        tmp_path: Path,
        keys: dict[str, Path],
        roles: list[str] | None,
        *,
        informal: str | None = WORDS,
    ) -> None:
        self.root = copy_graph(tmp_path)
        write_curators(self.root, CURATOR)
        if informal is not None:  # the fixture predates F11 and has no target record
            intake.write_doc(
                self.target, samples.target_record(id=TARGET, informal=informal, curator=CURATOR)
            )
        (self.root / policy.FILE).write_bytes(schemas.canonical_json(policy_doc(roles)))
        steward.write(
            self.target, action=steward.COMMIT, login=ALICE, name="Alice",
            link="https://orcid.org/0000-0002-1825-0097", date="2026-10-01",
            key_path=keys[ALICE], signer=SIGNER,
        )  # fmt: skip
        self.base_files: dict[str, bytes] = {
            policy.FILE: (self.root / policy.FILE).read_bytes(),
            modes.CURATORS_FILE: (self.root / modes.CURATORS_FILE).read_bytes(),
        }

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    def opening(self, identity: str, role: str, **overrides: Any) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema": "review/v1",
            "target": TARGET,
            "opened_by": {"identity": identity, "role": role},
            "date": DAY,
            "words": "For all propositions p, q and r, (p and q) and r implies r and (q and p).",
            "cases": [],
            "concepts": [],
            "source": {"kind": "existing", "ref": ROOT},
            "tracking": None,
            "supersedes": None,
        }
        doc.update(overrides)
        return doc

    def check(self, doc: dict[str, Any], *, author: str) -> list[str]:
        """The codes the gate answers for a pull request by ``author`` adding ``doc``."""
        dest = self.root / REVIEW
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        classification = modes.classify(
            [Change("A", REVIEW)],
            author=author,
            curators=modes.load_curators(self.root),
            graph_root=self.root,
        )
        assert classification.mode == "review", classification.problems
        problems = modes.check(self.root, classification, base=self.base, signer=SIGNER)
        return [p.code for p in problems]


# --- the setting (AC10) ------------------------------------------------------------------------


def test_the_default_admits_each_of_the_three_roles_when_held(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """``policy/v3`` has no ``review_openers``; the default lets a listed curator, an active
    steward and a proposer open, each acting for themselves on the pull request."""
    g = Graph(tmp_path, keys, roles=None)
    assert g.check(g.opening(CURATOR, "curator"), author=CURATOR) == []
    assert g.check(g.opening(ALICE, "steward"), author=ALICE) == []
    assert g.check(g.opening(BOB, "proposer"), author=BOB) == []


def test_curators_only_refuses_a_steward_by_name(tmp_path: Path, keys: dict[str, Path]) -> None:
    g = Graph(tmp_path, keys, roles=["curator"])
    assert g.check(g.opening(ALICE, "steward"), author=ALICE) == ["review-opener-not-allowed"]
    assert g.check(g.opening(BOB, "proposer"), author=BOB) == ["review-opener-not-allowed"]
    assert g.check(g.opening(CURATOR, "curator"), author=CURATOR) == []


def test_the_setting_is_read_from_the_parent_tree_not_the_pull_request(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """A pull request cannot widen the setting for itself: the checkout says all three, the
    base says curators only, and the base wins."""
    g = Graph(tmp_path, keys, roles=None)
    g.base_files[policy.FILE] = schemas.canonical_json(policy_doc(["curator"]))
    assert g.check(g.opening(ALICE, "steward"), author=ALICE) == ["review-opener-not-allowed"]


# --- the role is held --------------------------------------------------------------------------


def test_a_curator_not_listed_is_not_held(tmp_path: Path, keys: dict[str, Path]) -> None:
    g = Graph(tmp_path, keys, roles=None)
    assert g.check(g.opening(STRANGER, "curator"), author=STRANGER) == ["review-opener-not-held"]


def test_a_steward_not_active_is_not_held(tmp_path: Path, keys: dict[str, Path]) -> None:
    g = Graph(tmp_path, keys, roles=None)
    assert g.check(g.opening(BOB, "steward"), author=BOB) == ["review-opener-not-held"]


def test_the_opener_must_be_who_the_pull_request_acts_for(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """A listed curator's name in the record does not make a stranger's pull request theirs;
    and a proposer is whoever the pull request acts for, nobody else (until F26-T10's proposal
    record names one)."""
    g = Graph(tmp_path, keys, roles=None)
    assert g.check(g.opening(CURATOR, "curator"), author=STRANGER) == ["review-opener-not-held"]
    assert g.check(g.opening(BOB, "proposer"), author=STRANGER) == ["review-opener-not-held"]


def test_a_service_pull_request_acts_for_the_record_s_identity(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """F18-Q7's precedent: the service opens as itself and the record carries who asked."""
    g = Graph(tmp_path, keys, roles=None)
    service = config.DEFAULT_SERVICE_LOGIN
    assert g.check(g.opening(ALICE, "steward"), author=service) == []
    assert g.check(g.opening(BOB, "steward"), author=service) == ["review-opener-not-held"]


# --- network by hand ---------------------------------------------------------------------------


def test_the_network_role_is_refused_in_a_pull_request_whoever_opens_it(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """And the setting cannot admit it: ``policy/v4`` lists only the three roles."""
    g = Graph(tmp_path, keys, roles=None)
    assert g.check(g.opening("network", "network"), author=CURATOR) == ["review-network-by-hand"]
    widened = policy_doc(["curator"])
    widened["review_openers"]["roles"].append("network")
    assert schemas.violations(widened, "policy/v4") != []


# --- opened twice ------------------------------------------------------------------------------


def test_a_second_opening_names_the_first_or_is_refused(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    g = Graph(tmp_path, keys, roles=None)
    first = g.opening(CURATOR, "curator")
    g.base_files[REVIEW] = yaml.safe_dump(first, sort_keys=False).encode()
    again = g.opening(CURATOR, "curator", date="2026-10-13")
    assert g.check(again, author=CURATOR) == ["review-opened-twice"]
    assert g.check(again | {"supersedes": "some-other-node"}, author=CURATOR) == [
        "review-opened-twice"
    ]
    revised = g.opening(
        CURATOR, "curator", date="2026-10-13", supersedes=ROOT,
        source={"kind": "existing", "ref": f"{ROOT}-v2"},
    )  # fmt: skip
    assert g.check(revised, author=CURATOR) == []


# --- the background opening --------------------------------------------------------------------


def test_the_background_opening_writes_the_review_and_the_live_statement_as_a_candidate(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """Whatever the setting says (here: curators only), ``review open`` writes ``review.yaml``
    opened by the network and the root's ``Statement.lean`` as a ported candidate, byte for
    byte, named by its hash; both records validate."""
    g = Graph(tmp_path, keys, roles=["curator"])
    summary = review_open.open_review(g.root, TARGET, day=DAY)
    assert summary["ok"] is True and summary["root"] == ROOT
    head = review.opening(g.target)
    assert head is not None and schemas.violations(head, "review/v1") == []
    assert head["opened_by"] == {"identity": "network", "role": "network"}
    assert head["source"] == {"kind": "existing", "ref": ROOT}
    assert head["cases"] == [] and head["concepts"] == [] and head["supersedes"] is None
    assert head["tracking"] is None and head["date"] == DAY

    lean = (g.target / "nodes" / ROOT / "Statement.lean").read_bytes()
    digest = hashlib.sha256(lean).hexdigest()
    cid = f"c-{digest[:8]}"
    candidates = g.target / "review" / "candidates"
    assert sorted(p.name for p in candidates.iterdir()) == [f"{cid}.lean", f"{cid}.yaml"]
    assert (candidates / f"{cid}.lean").read_bytes() == lean
    doc = yaml.safe_load((candidates / f"{cid}.yaml").read_text(encoding="utf-8"))
    assert schemas.violations(doc, "candidate/v1") == []
    assert doc["id"] == cid and doc["statement_hash"] == digest
    assert doc["origin"] == "ported" and doc["source"] == {"kind": "existing", "ref": ROOT}
    assert doc["method"] == "other" and doc["models"] == [] and doc["read_others"] is None
    assert doc["author"] == "curator"  # the fixture has no ledger naming a statement line
    assert sorted(summary["written"]) == sorted(
        [REVIEW, f"targets/{TARGET}/review/candidates/{cid}.yaml",
         f"targets/{TARGET}/review/candidates/{cid}.lean"]
    )  # fmt: skip


def test_the_words_are_the_informal_statement_else_the_root_s_doc_comment(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    """A target with no record and a root with no doc comment has no words, and nothing is
    written (C7): the fixture's root is such a node."""
    bare = Graph(tmp_path / "bare", keys, roles=None, informal=None)
    summary = review_open.open_review(bare.root, TARGET, day=DAY)
    assert summary["ok"] is False and "no words" in summary["error"]
    assert not (bare.target / "review").exists()

    commented = Graph(tmp_path / "commented", keys, roles=None, informal=None)
    statement = commented.target / "nodes" / ROOT / "Statement.lean"
    statement.write_text(
        "/-! Reassociating a conjunction and swapping its ends. -/\n" + statement.read_text(),
        encoding="utf-8",
    )
    review_open.open_review(commented.root, TARGET, day=DAY)
    head = review.opening(commented.target)
    assert head is not None
    assert head["words"] == "Reassociating a conjunction and swapping its ends."
    (candidate,) = (commented.target / "review" / "candidates").glob("*.lean")
    assert candidate.read_bytes() == statement.read_bytes()  # the live text, comment and all

    g = Graph(tmp_path / "informal", keys, roles=None, informal="Conjunction is commutative.")
    review_open.open_review(g.root, TARGET, day=DAY)
    head2 = review.opening(g.target)
    assert head2 is not None and head2["words"] == "Conjunction is commutative."


def test_a_licence_header_is_not_the_words(tmp_path: Path, keys: dict[str, Path]) -> None:
    """A registry import opens with a plain ``/- … -/`` licence header, which is not a doc
    comment; with no informal statement the words are the record's paraphrase. erdos-52, -68,
    -172, -376 and -406 were opened with the Apache header as their words (2026-10-28 run,
    F-A4)."""
    g = Graph(tmp_path, keys, roles=None, informal=None)
    paraphrase = "Whether reassociating a conjunction and swapping its ends is harmless."
    intake.write_doc(
        g.target,
        samples.target_record(id=TARGET, informal=None, paraphrase=paraphrase, curator=CURATOR),
    )
    statement = g.target / "nodes" / ROOT / "Statement.lean"
    statement.write_text(
        "/-\nCopyright 2025 The Formal Conjectures Authors.\n\n"
        'Licensed under the Apache License, Version 2.0 (the "License");\n-/\n\n'
        + statement.read_text(),
        encoding="utf-8",
    )
    review_open.open_review(g.root, TARGET, day=DAY)
    head = review.opening(g.target)
    assert head is not None
    assert head["words"] == paraphrase


def test_the_candidate_is_credited_to_the_ledger_s_statement_line(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    g = Graph(tmp_path, keys, roles=None)
    entry = ledger.statement_entry(
        identity="carol", target=TARGET, node=ROOT, origin="authored",
        merge_commit="0" * 40, date="2026-09-08T12:00:00Z",
    )  # fmt: skip
    assert ledger.record(g.root, "carol", entry) is not None
    review_open.open_review(g.root, TARGET, day=DAY)
    (candidate,) = (g.target / "review" / "candidates").glob("*.yaml")
    assert yaml.safe_load(candidate.read_text(encoding="utf-8"))["author"] == "carol"


def test_a_target_with_a_review_is_left_alone(tmp_path: Path, keys: dict[str, Path]) -> None:
    g = Graph(tmp_path, keys, roles=None)
    first = review_open.open_review(g.root, TARGET, day=DAY)
    before = {p: p.read_bytes() for p in (g.target / "review").rglob("*") if p.is_file()}
    second = review_open.open_review(g.root, TARGET, day="2026-10-13")
    assert first["written"] and second["written"] == []
    assert second["ok"] is True and "exists" in second["skipped"]
    assert {p: p.read_bytes() for p in (g.target / "review").rglob("*") if p.is_file()} == before


def test_a_target_whose_root_cannot_be_found_writes_nothing(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    root = copy_graph(tmp_path, ADVERSARIAL)  # the one fixture with no single root
    summary = review_open.open_review(root, "adversarial", day=DAY)
    assert summary["ok"] is False and "root" in summary["error"]
    assert not (root / "targets" / "adversarial" / "review").exists()


def test_the_command_opens_every_target_once(
    tmp_path: Path, keys: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """``opn-gate review open --graph <checkout> --all``: one JSON line per target with a
    ``gate-spec.json``; a second run writes nothing and says so; nothing is pushed or committed."""
    g = Graph(tmp_path, keys, roles=["curator"])
    code = cli.main(["review", "open", "--graph", str(g.root), "--all", "--date", DAY])
    assert code == 0
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert [(d["target"], d["ok"]) for d in lines] == [(TARGET, True)]
    assert len(lines[0]["written"]) == 3
    assert review.opening(g.target) is not None

    code = cli.main(["review", "open", "--graph", str(g.root), "--target", TARGET])
    assert code == 0
    (line,) = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert line["written"] == [] and line["ok"] is True


def test_the_command_needs_a_target_or_all(tmp_path: Path, keys: dict[str, Path]) -> None:
    g = Graph(tmp_path, keys, roles=None)
    with pytest.raises(SystemExit):
        cli.main(["review", "open", "--graph", str(g.root)])
