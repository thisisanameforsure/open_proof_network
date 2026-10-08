"""F24-T3 / AC4, AC5, AC7: the gate admits the panel's records (R4, R10; D-32 v3.34).

Motions, votes, ``writeup/v2`` acts and ``steward/v3`` commitments, each judged by the gate on its
own clock (``opn_gate.clock``), against the approval key, ``policy.json`` and ``curators.json`` of
the merge's parent tree. Every refusal is a named diagnostic code (AC7); a valid record of each
kind passes. Every record is signed by a real ``ssh-keygen``: the rules are about signatures.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from test_modes import CURATOR, write_curators

from opn_gate import clock, modes, panel, policy, schemas, signed, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

TARGET = "euclid-primes"
SIGNER = SshKeygenSigner()
SERVICE = "open-proof-network[bot]"
#: The gate's day in every test here.
TODAY = dt.date(2026, 10, 9)


def day(offset: int = 0) -> str:
    return (TODAY + dt.timedelta(days=offset)).isoformat()


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("panel-keys")
    out: dict[str, Path] = {}
    for who in ("approval", "stranger"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


@pytest.fixture(autouse=True)
def gate_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clock, "today", lambda: TODAY)


class Graph:
    """A curated target, the owner listed as curator, the approval key published. ``base`` is
    the parent tree: the key, the curators and the policy as they stood before the pull request.
    Records written with ``merged=True`` stand in the tree already; the others are the pull
    request's own and come back as a ``Change``."""

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

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    def set_policy(
        self, *, admission: str = policy.OPEN, settings: panel.Settings | None = None
    ) -> None:
        settings = settings or panel.Settings()
        doc = {
            "schema": "policy/v3",
            "steward_rule": {"enforced": False, "since": None, "evidence": None},
            "steward_admission": admission,
            "panel": {
                name: {"value": value, "since": "2026-10-01", "reason": "a test's setting"}
                for name, value in settings.values().items()
            },
        }
        data = schemas.canonical_json(schemas.validate(doc, "policy/v3"))
        (self.root / policy.FILE).write_bytes(data)
        self.base_files[policy.FILE] = data

    def write(
        self,
        sub: str,
        doc: dict[str, Any],
        *,
        target: str = TARGET,
        key: str = "approval",
        name: str | None = None,
    ) -> Change:
        directory = self.root / "targets" / target / sub
        directory.mkdir(parents=True, exist_ok=True)
        n = len(list(directory.glob("*.yaml"))) + 1
        doc = signed.sign({"target": target, **doc, "via": "approval-key"}, self.keys[key], SIGNER)
        path = directory / (name or f"{n}.yaml")
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return Change("A", path.relative_to(self.root).as_posix())

    def commit(
        self, login: str, on: int = -30, admitted_by: str = "self", *, target: str = TARGET
    ) -> Change:
        return self.write(
            "stewards",
            {
                "schema": "steward/v3",
                "action": "commit",
                "login": login,
                "name": login.title(),
                "link": None,
                "commitment": steward.COMMITMENT,
                "date": day(on),
                "admitted_by": admitted_by,
            },
            target=target,
        )

    def motion(
        self,
        by: str,
        on: int = 0,
        kind: str = "invite",
        subject: dict[str, Any] | None = None,
        settings: panel.Settings | None = None,
        **extra: Any,
    ) -> Change:
        return self.write(
            "motions",
            {
                "schema": "motion/v1",
                "kind": kind,
                "subject": subject or {"login": "newcomer"},
                "opened_by": by,
                "settings": (settings or panel.Settings()).motion_settings(),
                "date": day(on),
            },
            **extra,
        )

    def vote(self, login: str, motion: int, vote: str = "yes", on: int = 0, **extra: Any) -> Change:
        return self.write(
            "votes",
            {"schema": "vote/v1", "motion": motion, "login": login, "vote": vote, "date": day(on)},
            **extra,
        )

    def record(self, by: str, authors: list[str], on: int = 0, **extra: Any) -> Change:
        return self.write(
            "writeup",
            {
                "schema": "writeup/v2",
                "action": "record",
                "kind": "paper",
                "title": "Euclid, revisited",
                "url": "https://example.org/euclid.pdf",
                "authors": authors,
                "signer": by,
                "date": day(on),
            },
            **extra,
        )

    def act(self, by: str, writeup: int, action: str = "author-sign", on: int = 0) -> Change:
        return self.write(
            "writeup",
            {
                "schema": "writeup/v2",
                "action": action,
                "writeup": writeup,
                "signer": by,
                "date": day(on),
            },
        )

    def codes(self, *changes: Change, opened_by: str = SERVICE) -> list[str]:
        classification = modes.classify(list(changes), author=opened_by, graph_root=self.root)
        assert classification.ok, classification.as_dict()
        assert classification.mode == "steward"
        return [d.code for d in modes.check(self.root, classification, base=self.base)]


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


def tamper(graph: Graph, change: Change, field: str, value: Any) -> None:
    path = graph.root / change.path
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc[field] = value
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


# --- motions ------------------------------------------------------------------------------------


def test_a_members_invitation_passes(graph: Graph) -> None:
    graph.commit("ann")
    assert graph.codes(graph.motion("ann")) == []


def test_a_curators_motion_passes_on_a_target_with_no_panel(graph: Graph) -> None:
    assert graph.codes(graph.motion(CURATOR)) == []


def test_a_motion_by_someone_off_the_panel_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    assert "motion-opener" in graph.codes(graph.motion("mallory"))


def test_a_lapsed_stewards_motion_is_refused_unless_it_is_their_new_act(graph: Graph) -> None:
    """A steward whose last act is past the lapse leaves the panel. A motion is itself an act on
    its own date, so it brings them back (AC4: "comes back on a new act")."""
    graph.commit("ann", on=-400)
    assert graph.codes(graph.motion("ann")) == []


def test_a_motion_dated_two_days_off_the_gates_clock_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    assert "motion-date" in graph.codes(graph.motion("ann", on=-2))
    assert "motion-date" in graph.codes(graph.motion("ann", on=2, subject={"login": "b"}))


def test_a_motion_dated_one_day_off_is_admitted(graph: Graph) -> None:
    graph.commit("ann")
    assert graph.codes(graph.motion("ann", on=-1)) == []


def test_a_motion_whose_settings_are_not_the_policys_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    graph.set_policy(settings=panel.Settings(window_days=21))
    assert "motion-settings" in graph.codes(graph.motion("ann"))
    assert graph.codes(graph.motion("ann", settings=panel.Settings(window_days=21))) == []


def test_a_tampered_motion_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    change = graph.motion("ann")
    tamper(graph, change, "opened_by", CURATOR)
    assert "motion-signature" in graph.codes(change)


def test_a_motion_signed_by_another_key_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    assert "motion-signature" in graph.codes(graph.motion("ann", key="stranger"))


def test_a_motion_for_another_target_or_unnumbered_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    change = graph.motion("ann")
    tamper(graph, change, "target", "elsewhere")
    assert "motion-target" in graph.codes(change)
    assert "motion-name" in graph.codes(graph.motion("ann", name="first.yaml"))


def test_an_invitation_of_a_member_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    graph.commit("ben")
    assert "motion-invite-member" in graph.codes(graph.motion("ann", subject={"login": "ben"}))


def test_a_second_open_invitation_for_one_login_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    graph.commit("ben")
    graph.motion("ann", on=-3)
    assert "motion-invite-open" in graph.codes(graph.motion("ben"))
    assert graph.codes(graph.motion("ben", subject={"login": "other"})) == []


def test_an_invitation_after_a_failed_one_is_admitted(graph: Graph) -> None:
    """Only an *open* invitation blocks a second: once the first has been decided, ask again."""
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-60)
    graph.motion("ann", on=-30)
    graph.vote("ben", 1, "no", on=-29)
    assert graph.codes(graph.motion("ann")) == []


def test_verify_writeup_names_an_existing_write_up(graph: Graph) -> None:
    graph.commit("ann")
    unknown = graph.motion("ann", kind="verify-writeup", subject={"writeup": 1})
    assert "motion-writeup-unknown" in graph.codes(unknown)
    (graph.root / unknown.path).unlink()
    graph.record("ann", ["ann"], on=-5)
    assert graph.codes(graph.motion("ann", kind="verify-writeup", subject={"writeup": 1})) == []


# --- votes --------------------------------------------------------------------------------------


def two_stewards_and_a_motion(graph: Graph, on: int = -3) -> None:
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-60)
    graph.motion("ann", on=on)


def test_a_members_vote_passes(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    assert graph.codes(graph.vote("ben", 1)) == []


def test_a_vote_and_its_motion_in_one_pull_request(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-60)
    assert graph.codes(graph.motion("ann"), graph.vote("ann", 1)) == []


def test_a_vote_on_a_motion_that_does_not_exist_is_refused(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    assert "vote-motion-unknown" in graph.codes(graph.vote("ben", 7))


def test_a_vote_outside_the_window_is_refused(graph: Graph) -> None:
    two_stewards_and_a_motion(graph, on=-20)
    assert "vote-window" in graph.codes(graph.vote("ben", 1))


def test_the_window_is_the_motions_own_settings(graph: Graph) -> None:
    """The window is the one the motion was opened under, whatever policy.json now says."""
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-60)
    graph.motion("ann", on=-20, settings=panel.Settings(window_days=30))
    assert graph.codes(graph.vote("ben", 1)) == []


def test_a_vote_dated_before_its_motion_is_refused(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.commit("ben", on=-60)
    graph.motion("ann", on=1)
    assert "vote-window" in graph.codes(graph.vote("ben", 1, on=0))


def test_a_non_members_vote_is_refused(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    assert "vote-not-member" in graph.codes(graph.vote("mallory", 1))


def test_a_steward_who_joined_after_the_motion_may_not_vote(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    graph.commit("cat", on=-1, admitted_by=CURATOR)
    assert "vote-not-member" in graph.codes(graph.vote("cat", 1))


def test_a_vote_off_the_gates_clock_is_refused(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    assert "vote-date" in graph.codes(graph.vote("ben", 1, on=-2))


def test_a_tampered_or_misfiled_vote_is_refused(graph: Graph) -> None:
    two_stewards_and_a_motion(graph)
    change = graph.vote("ben", 1)
    tamper(graph, change, "vote", "no")
    assert "vote-signature" in graph.codes(change)
    other = graph.vote("ben", 1, key="stranger")
    assert "vote-signature" in graph.codes(other)
    misfiled = graph.vote("ben", 1)
    tamper(graph, misfiled, "target", "elsewhere")
    assert "vote-target" in graph.codes(misfiled)
    assert "vote-name" in graph.codes(graph.vote("ben", 1, name="mine.yaml"))


def test_curators_vote_where_curators_count(graph: Graph) -> None:
    """On a write-up motion of a panel of provers only, curators count in the panel's place
    (F24-R3), so a curator's vote is admitted."""
    from opn_gate import ledger  # noqa: PLC0415

    graph.commit("ann", on=-60)
    entry = ledger.proof_entry(
        identity="ann", target=TARGET, node="root", artifact_type="proof",
        artifact="nodes/root/Proof.lean", merge_commit="a" * 40, date="2026-09-01T00:00:00Z",
    )  # fmt: skip
    assert entry is not None
    ledger.write(graph.root, ledger.append(ledger.load(graph.root, "ann"), entry))
    graph.record("ann", ["ann"], on=-10)
    graph.motion("ann", on=-3, kind="verify-writeup", subject={"writeup": 1})
    assert graph.codes(graph.vote(CURATOR, 1)) == []


# --- write-ups (writeup/v2) ----------------------------------------------------------------------


def test_anyone_may_record_a_write_up(graph: Graph) -> None:
    assert graph.codes(graph.record("someone", ["someone", "another"])) == []


def test_an_author_signs_and_a_second_signature_is_refused(graph: Graph) -> None:
    graph.record("someone", ["someone", "another"], on=-2)
    assert graph.codes(graph.act("another", 1)) == []
    assert "writeup-signed-twice" in graph.codes(graph.act("another", 1))
    assert "writeup-signed-twice" in graph.codes(graph.act("someone", 1))


def test_a_write_up_act_by_a_non_author_is_refused(graph: Graph) -> None:
    graph.record("someone", ["someone"], on=-2)
    assert "writeup-not-author" in graph.codes(graph.act("mallory", 1))
    assert "writeup-not-author" in graph.codes(graph.act("mallory", 1, action="withdrawn"))


def test_a_write_up_act_on_no_record_is_refused(graph: Graph) -> None:
    graph.record("someone", ["someone"], on=-2)
    assert "writeup-unknown" in graph.codes(graph.act("someone", 9))
    assert "writeup-unknown" in graph.codes(graph.act("someone", 1 + 1))  # an act is no record


def test_a_write_up_act_off_the_gates_clock_is_refused(graph: Graph) -> None:
    assert "writeup-date" in graph.codes(graph.record("someone", ["someone"], on=-5))


def test_a_v2_write_up_signed_by_another_key_is_refused(graph: Graph) -> None:
    assert "writeup-signature" in graph.codes(graph.record("x", ["x"], key="stranger"))


def test_a_v1_write_up_keeps_its_rule(graph: Graph) -> None:
    """``writeup/v1`` is still only a steward's or a curator's to sign (F15-R6)."""
    from opn_gate import writeup  # noqa: PLC0415

    path = writeup.write(
        graph.root / "targets" / TARGET, kind="paper", title="t", url="https://example.org/a",
        date=day(), signer_login="someone", key_path=graph.keys["stranger"], signer=SIGNER,
    )  # fmt: skip
    change = Change("A", path.relative_to(graph.root).as_posix())
    assert graph.codes(change) == ["writeup-signer"]


# --- admission (AC5) -----------------------------------------------------------------------------


def test_the_first_stewards_self_commit_is_admitted(graph: Graph) -> None:
    assert graph.codes(graph.commit("ann", on=0)) == []


def test_a_second_stewards_self_commit_is_refused(graph: Graph) -> None:
    graph.commit("ann")
    assert "steward-invitation-required" in graph.codes(graph.commit("ben", on=0))


def test_self_is_admitted_again_when_the_panel_has_lapsed(graph: Graph) -> None:
    graph.commit("ann", on=-400)
    assert graph.codes(graph.commit("ben", on=0)) == []


def test_a_passed_invitation_admits_the_login_it_names(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.motion(CURATOR, on=-1, subject={"login": "ben"})  # a curator's invitation passes at once
    assert graph.codes(graph.commit("ben", on=0, admitted_by="motion:1")) == []


def test_a_passed_invitation_admits_under_reviewed_too(graph: Graph) -> None:
    graph.set_policy(admission=policy.REVIEWED)
    graph.commit("ann", on=-60, admitted_by=CURATOR)
    graph.motion(CURATOR, on=-1, subject={"login": "ben"})
    assert graph.codes(graph.commit("ben", on=0, admitted_by="motion:1")) == []


def test_an_invitation_admits_nobody_else(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.motion(CURATOR, on=-1, subject={"login": "ben"})
    assert "steward-invitation" in graph.codes(graph.commit("cat", on=0, admitted_by="motion:1"))


def test_an_open_or_missing_invitation_admits_nobody(graph: Graph) -> None:
    graph.commit("ann", on=-60)
    graph.commit("dan", on=-60)
    graph.motion("ann", on=-1, subject={"login": "ben"})  # open: two members, a window to run
    assert "steward-invitation" in graph.codes(graph.commit("ben", on=0, admitted_by="motion:1"))
    assert "steward-invitation" in graph.codes(graph.commit("ben", on=0, admitted_by="motion:9"))


@pytest.mark.parametrize("admission", [policy.OPEN, policy.REVIEWED])
def test_a_curators_admission_is_always_accepted(graph: Graph, admission: str) -> None:
    graph.set_policy(admission=admission)
    graph.commit("ann", admitted_by=CURATOR)
    assert graph.codes(graph.commit("ben", on=0, admitted_by=CURATOR)) == []


# --- the cap (AC4) -------------------------------------------------------------------------------


def stewarding(graph: Graph, login: str, n: int, *, on: int = -30) -> None:
    for i in range(n):
        graph.commit(login, on=on, admitted_by=CURATOR, target=f"cap-{i}")


def test_a_fifth_stewardship_is_admitted(graph: Graph) -> None:
    stewarding(graph, "ann", 4)
    assert graph.codes(graph.commit("ann", on=0)) == []


def test_a_sixth_stewardship_is_refused(graph: Graph) -> None:
    stewarding(graph, "ann", 5)
    assert "steward-cap" in graph.codes(graph.commit("ann", on=0))
    assert "steward-cap" in graph.codes(graph.commit("ann", on=0, admitted_by=CURATOR))


def test_lapsed_stewardships_do_not_count_toward_the_cap(graph: Graph) -> None:
    stewarding(graph, "ann", 4)
    graph.commit("ann", on=-400, admitted_by=CURATOR, target="cap-old")
    assert graph.codes(graph.commit("ann", on=0)) == []


def test_the_cap_is_the_policys(graph: Graph) -> None:
    graph.set_policy(settings=panel.Settings(cap=2))
    stewarding(graph, "ann", 2)
    assert "steward-cap" in graph.codes(graph.commit("ann", on=0))
