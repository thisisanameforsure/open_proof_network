"""F24-T2 / AC2 to AC4: the steward panel by derivation (D-32 v3.34).

Every record here is signed by a real ``ssh-keygen`` through the ``Signer`` seam, as the steward
tests are, because a record whose signature does not verify must count for nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import ledger, panel, policy, signed, steward
from opn_gate.signer import SshKeygenSigner

SIGNER = SshKeygenSigner()
D0 = dt.date(2026, 10, 1)


def day(offset: int) -> str:
    return (D0 + dt.timedelta(days=offset)).isoformat()


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("keys") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path), "-C", "approval"],
        check=True,
    )
    return path


class World:
    """One graph with one target, ``t``, and helpers that append signed records to it."""

    def __init__(self, root: Path, key: Path) -> None:
        self.root = root
        self.key = key
        self.target = root / "targets" / "t"
        self.target.mkdir(parents=True)
        self.curators: list[str] = []

    def _write(self, sub: str, doc: dict[str, Any]) -> Path:
        directory = self.target / sub
        directory.mkdir(exist_ok=True)
        n = len(list(directory.glob("*.yaml"))) + 1
        doc = signed.sign({**doc, "target": "t", "via": "approval-key"}, self.key, SIGNER)
        path = directory / f"{n}.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return path

    def commit(self, login: str, on: int = 0, admitted_by: str = "self") -> Path:
        return self._write(
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
        )

    def step_down(self, login: str, on: int) -> Path:
        return self._write(
            "stewards",
            {
                "schema": "steward/v3",
                "action": "step-down",
                "login": login,
                "name": login.title(),
                "link": None,
                "commitment": steward.STEP_DOWN_SENTENCE,
                "date": day(on),
                "admitted_by": "self",
            },
        )

    def motion(
        self,
        by: str,
        on: int,
        kind: str = "invite",
        subject: dict[str, Any] | None = None,
        settings: panel.Settings | None = None,
    ) -> int:
        settings = settings or panel.Settings()
        path = self._write(
            "motions",
            {
                "schema": "motion/v1",
                "kind": kind,
                "subject": subject or {"login": "newcomer"},
                "opened_by": by,
                "settings": settings.motion_settings(),
                "date": day(on),
            },
        )
        return int(path.stem)

    def vote(self, login: str, motion: int, vote: str, on: int) -> Path:
        return self._write(
            "votes",
            {"schema": "vote/v1", "motion": motion, "login": login, "vote": vote, "date": day(on)},
        )

    def words_signature(self, kind: str, signer: str, on: int) -> Path:
        """A valid, signed ``<kind>-signature/v3`` under node ``root`` (``kind``: gloss or
        explainer)."""
        directory = self.target / "nodes" / "root" / kind / "signed"
        directory.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": f"{kind}-signature/v3",
            "target": "t",
            "node": "root",
            kind: "0" * 64,
            "affirmation": "I have read this against the Lean it names.",
            "signer": signer,
            "date": day(on),
            "via": "approval-key",
        }
        path = directory / f"{'0' * 64}-{len(list(directory.iterdir())) + 1}.yaml"
        doc = signed.sign(doc, self.key, SIGNER)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return path

    def prover(self, login: str) -> None:
        entry = ledger.proof_entry(
            identity=login, target="t", node="root", artifact_type="proof",
            artifact="nodes/root/Proof.lean", merge_commit="a" * 40, date=f"{day(0)}T00:00:00Z",
        )  # fmt: skip
        assert entry is not None
        ledger.write(self.root, ledger.append(ledger.load(self.root, login), entry))

    def state(self, n: int, today: int) -> panel.Tally:
        return panel.tally(
            self.root, "t", n, today=D0 + dt.timedelta(days=today), signer=SIGNER,
            curators=frozenset(self.curators),
        )  # fmt: skip


@pytest.fixture
def world(tmp_path: Path, key: Path) -> World:
    return World(tmp_path / "graph", key)


def five(w: World) -> None:
    for login in ("ann", "ben", "cat", "dan", "eve"):
        w.commit(login, 0, admitted_by="carol")


# --- AC2: tallies ---------------------------------------------------------------------------------


def test_two_of_five_voting_yes_passes_and_silence_counts_neither_way(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 3)
    assert world.state(n, 10).state == "open"
    result = world.state(n, 16)
    assert (result.state, result.yes, result.no) == ("passed", 2, 0)
    assert result.closes == dt.date(2026, 10, 16)


def test_one_of_five_fails_on_the_minimum(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    assert world.state(n, 16).state == "failed"


def test_one_vote_passes_a_panel_of_two(world: World) -> None:
    world.commit("ann", 0)
    world.commit("ben", 0, admitted_by="carol")
    n = world.motion("ann", 1)
    world.vote("ben", n, "yes", 2)
    assert world.state(n, 16).state == "passed"


def test_a_tie_fails(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "no", 2)
    assert world.state(n, 16).state == "failed"


def test_a_majority_with_a_dissent_passes(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    for login, vote in (("ann", "yes"), ("ben", "yes"), ("cat", "no")):
        world.vote(login, n, vote, 2)
    assert world.state(n, 16).state == "passed"


def test_two_thirds_needs_two_of_three(world: World) -> None:
    five(world)
    two_thirds = panel.Settings(threshold=(2, 3))
    n = world.motion("ann", 1, settings=two_thirds)
    for login, vote in (("ann", "yes"), ("ben", "yes"), ("cat", "no")):
        world.vote(login, n, vote, 2)
    assert world.state(n, 16).state == "passed"
    m = world.motion("ann", 1, settings=two_thirds)
    for login, vote in (("ann", "yes"), ("ben", "yes"), ("cat", "no"), ("dan", "no")):
        world.vote(login, m, vote, 2)
    assert world.state(m, 16).state == "failed"


def test_a_vote_after_the_window_is_not_counted(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 16)  # the window closes on day 15
    result = world.state(n, 30)
    assert (result.state, result.yes) == ("failed", 1)


def test_a_vote_before_the_motion_is_not_counted(world: World) -> None:
    five(world)
    n = world.motion("ann", 5)
    world.vote("ann", n, "yes", 4)
    world.vote("ben", n, "yes", 6)
    assert world.state(n, 30).yes == 1


def test_a_non_members_vote_is_not_counted(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("stranger", n, "yes", 2)
    assert world.state(n, 16).state == "failed"


def test_a_steward_who_joined_after_the_motion_does_not_count(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.commit("late", 3, admitted_by="carol")
    world.vote("ann", n, "yes", 4)
    world.vote("late", n, "yes", 4)
    assert world.state(n, 16).yes == 1


def test_a_steward_who_stepped_down_before_the_motion_does_not_count(world: World) -> None:
    five(world)
    world.step_down("eve", 1)
    n = world.motion("ann", 2)
    world.vote("eve", n, "yes", 3)
    assert world.state(n, 30).yes == 0


def test_the_latest_vote_counts(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "no", 2)
    world.vote("ben", n, "yes", 5)
    result = world.state(n, 16)
    assert (result.yes, result.no, result.state) == (2, 0, "passed")


def test_a_vote_whose_signature_does_not_verify_counts_for_nothing(world: World) -> None:
    five(world)
    n = world.motion("ann", 1)
    world.vote("ann", n, "yes", 2)
    forged = world.vote("ben", n, "yes", 2)
    doc = yaml.safe_load(forged.read_text())
    doc["vote"] = "no"  # the body no longer matches its signature
    forged.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert world.state(n, 16).no == 0


def test_a_curators_invitation_passes_at_once(world: World) -> None:
    five(world)
    world.curators = ["carol"]
    n = world.motion("carol", 1)
    assert world.state(n, 1).state == "passed"


def test_a_lone_members_motion_passes_at_once(world: World) -> None:
    world.commit("ann", 0)
    n = world.motion("ann", 1)
    assert world.state(n, 1).state == "passed"


def test_a_motion_by_someone_off_the_panel_fails(world: World) -> None:
    five(world)
    n = world.motion("stranger", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 2)
    assert world.state(n, 16).state == "failed"


def test_the_motions_own_settings_decide_it_not_todays_policy(world: World) -> None:
    """R1: a change to policy.json applies only from the next motion opened."""
    five(world)
    n = world.motion("ann", 1, settings=panel.Settings(window_days=30))
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 20)
    assert world.state(n, 20).state == "open"
    assert world.state(n, 32).state == "passed"


# --- AC3: provers ---------------------------------------------------------------------------------


def test_a_provers_vote_is_uncounted_on_the_write_up_motions(world: World) -> None:
    five(world)
    world.prover("ann")
    n = world.motion("ben", 1, kind="verify-writeup", subject={"writeup": 1})
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 2)
    result = world.state(n, 16)
    assert (result.yes, result.uncounted, result.state) == (1, ("ann",), "failed")


def test_a_provers_vote_counts_on_an_invitation(world: World) -> None:
    five(world)
    world.prover("ann")
    n = world.motion("ben", 1)
    world.vote("ann", n, "yes", 2)
    world.vote("ben", n, "yes", 2)
    assert world.state(n, 16).state == "passed"


def test_when_every_member_proved_the_curators_vote(world: World) -> None:
    world.commit("ann", 0)
    world.commit("ben", 0, admitted_by="carol")
    world.prover("ann")
    world.prover("ben")
    world.curators = ["carol", "dora"]
    n = world.motion("ann", 1, kind="authorship-threshold", subject={"threshold": 0.1})
    world.vote("ann", n, "yes", 2)
    world.vote("carol", n, "yes", 2)
    result = world.state(n, 16)
    assert (result.yes, result.uncounted, result.state) == (1, ("ann",), "passed")


def test_a_lone_prover_does_not_pass_a_write_up_motion_on_their_own(world: World) -> None:
    world.commit("ann", 0)
    world.prover("ann")
    n = world.motion("ann", 1, kind="verify-writeup", subject={"writeup": 1})
    assert world.state(n, 1).state == "open"


# --- AC4: lapse -----------------------------------------------------------------------------------


def test_a_quiet_steward_lapses_and_comes_back_on_a_new_act(world: World) -> None:
    world.commit("ann", 0)
    world.commit("ben", 0, admitted_by="carol")
    settings = panel.Settings(lapse_days=30)
    on = D0 + dt.timedelta(days=40)
    members = panel.members(world.root, "t", on, settings=settings, signer=SIGNER)
    assert members == ()
    n = world.motion("ann", 41)
    assert panel.members(world.root, "t", on + dt.timedelta(days=1), settings=settings,
                         signer=SIGNER) == ("ann",)  # fmt: skip
    world.vote("ben", n, "yes", 42)
    assert panel.members(world.root, "t", on + dt.timedelta(days=2), settings=settings,
                         signer=SIGNER) == ("ann", "ben")  # fmt: skip


def test_a_words_signature_is_a_signed_act(world: World) -> None:
    world.commit("ann", 0)
    world.words_signature("gloss", "ann", 50)
    acts = panel.last_acts(world.root, "t", signer=SIGNER)
    assert acts["ann"] == D0 + dt.timedelta(days=50)


def test_stewardships_count_unlapsed_ones_across_the_graph(world: World, key: Path) -> None:
    for t in ("a", "b", "c"):
        other = World.__new__(World)
        other.root, other.key, other.curators = world.root, key, []
        other.target = world.root / "targets" / t
        other.target.mkdir(parents=True)
        other._write = World._write.__get__(other)  # type: ignore[method-assign]
        other.commit("ann", 0 if t != "c" else -400)
    on = D0 + dt.timedelta(days=10)
    assert panel.stewardships(world.root, "ann", on, settings=panel.Settings(), signer=SIGNER) == (
        "a",
        "b",
    )


# --- settings -------------------------------------------------------------------------------------


def test_settings_default_without_a_policy_file(tmp_path: Path) -> None:
    assert policy.load(tmp_path).panel == panel.Settings()
    assert panel.Settings().as_dict()["vote_window_days"] == {
        "value": 14,
        "since": None,
        "reason": None,
    }


def test_settings_read_from_a_v3_policy(tmp_path: Path) -> None:
    def setting(value: Any) -> dict[str, Any]:
        return {"value": value, "since": "2026-10-08", "reason": "why"}

    doc = {
        "schema": "policy/v3",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "open",
        "panel": {
            "vote_threshold": setting({"numerator": 2, "denominator": 3}),
            "vote_window_days": setting(21),
            "vote_minimum": setting(3),
            "vote_minimum_from": setting(4),
            "steward_cap": setting(7),
            "steward_lapse_days": setting(90),
        },
    }
    (tmp_path / "policy.json").write_text(json.dumps(doc), encoding="utf-8")
    loaded = policy.load(tmp_path)
    assert loaded.admission == "open"
    s = loaded.panel
    assert (s.threshold, s.window_days, s.minimum, s.minimum_from, s.cap, s.lapse_days) == (
        (2, 3),
        21,
        3,
        4,
        7,
        90,
    )
    assert s.as_dict()["steward_cap"] == setting(7)


# --- F24-T5: who may vote on a motion, for the service's refusals --------------------------------


def test_voters_names_the_counted_and_the_uncounted_provers(world: World) -> None:
    """``panel.voters``: on a write-up motion a prover is a voter but uncounted; on an
    invitation the same prover counts; with every member a prover, the curators count; and an
    unknown motion is ``PanelError``."""
    world.commit("ann", 0)
    world.commit("ben", 0, admitted_by="carol")
    world.prover("ann")
    world.curators = ["carol"]
    curators = frozenset(world.curators)
    verify = world.motion("ben", 1, kind="verify-writeup", subject={"writeup": 1})
    invite = world.motion("ben", 1)
    assert panel.voters(world.root, "t", verify, signer=SIGNER, curators=curators) == (
        frozenset({"ben"}),
        frozenset({"ann"}),
    )
    assert panel.voters(world.root, "t", invite, signer=SIGNER, curators=curators) == (
        frozenset({"ann", "ben"}),
        frozenset(),
    )
    world.prover("ben")
    assert panel.voters(world.root, "t", verify, signer=SIGNER, curators=curators) == (
        curators,
        frozenset({"ann", "ben"}),
    )
    with pytest.raises(panel.PanelError):
        panel.voters(world.root, "t", 99, signer=SIGNER, curators=curators)
