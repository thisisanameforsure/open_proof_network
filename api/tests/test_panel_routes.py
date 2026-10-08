"""F24-T5 / AC9: ``POST /motions``, ``POST /votes``, ``POST /writeups``, the invitation path on
``POST /stewards``, and ``GET /session``'s ``awaiting`` (R8; D-32 v3.34, D-35 v3.34).

The shape that lands is what is tested: each pushed file is validated against its published
schema, its signature checked under the approval key's public half, and then merged into the
tree the fake host serves, so the gate's own ``panel.tallies`` and ``writeup.views`` read it back
over a copy of that tree. Every refusal answers its code with nothing pushed.

The fixture graph is ``test_glosses_route``'s: the owner listed as curator, ``alice`` an
SSH-signed steward of ``propositional`` since 2026-10-04; the clock stands at 2026-10-09.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, TARGET, make_keys, make_tree, serve
from test_web_session import ENV, sign_in, web_headers

from opn_api import sshsig
from opn_api.githost import GitHubUser
from opn_gate import ledger, panel, schemas, signed, steward, writeup
from opn_gate.signer import NAMESPACE, SshKeygenSigner

TODAY = dt.date(2026, 10, 9)
SIGNER = SshKeygenSigner()
SECOND = "second"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    key = tmp_path_factory.mktemp("approval") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "approval"],
        check=True,
    )
    return key.read_text(), key.with_suffix(".pub").read_text().strip()


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    # A session outlives the test's clock moves (a day back to open a motion, two weeks on to
    # close a window); its own expiry is F23's and tested there.
    h = make_harness({**ENV, "OPN_API_WEB_SESSION_TTL_S": str(60 * 86400), **env})
    h.clock.current = dt.datetime(2026, 10, 9, 12, 0, 0, tzinfo=dt.UTC)
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    h.githost.users["code_dave"] = GitHubUser("dave", 1004, "2019-01-01T00:00:00Z")
    serve(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


class Who:
    """A cookie per login, signed in once."""

    def __init__(self, h: Harness) -> None:
        self.h = h
        self.cookies: dict[str, str] = {}

    def __call__(self, login: str) -> dict[str, str]:
        code = {"alice": "code_alice", "bob": "code_bob", CURATOR: "code_owner"}.get(
            login, f"code_{login}"
        )
        if login not in self.cookies:
            self.cookies[login] = sign_in(self.h, code)
        return web_headers(self.cookies[login])


@pytest.fixture
def who(h: Harness) -> Who:
    return Who(h)


def post(h: Harness, route: str, headers: dict[str, str], **body: Any) -> Any:
    return h.client.post(route, json={"target": TARGET, **body}, headers=headers)


def landed(h: Harness, response: Any, schema: str, public: str) -> dict[str, Any]:
    """The one pushed file, read through its schema; its signature verifies under the
    approval key, by the gate's verifier and by the service's."""
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"pr_number", "pr_url", "branch", "path"}
    assert body["branch"].startswith("append/")
    push = h.githost.pushes[-1]
    assert list(push.files) == [body["path"]]
    doc = schemas.validate(yaml.safe_load(push.files[body["path"]]), schema)
    assert doc["via"] == "approval-key" and doc["date"] == TODAY.isoformat()
    assert signed.same_key(doc["key"], public)
    assert signed.verifies(doc, SIGNER)
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)
    return dict(doc)


def merge(h: Harness, tree: Path, response: Any) -> None:
    path = response.json()["path"]
    target = tree / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(h.githost.pushes[-1].files[path], encoding="utf-8")
    serve(h, tree)


def copy_of(tree: Path) -> Path:
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    return over


def tallies(tree: Path) -> list[panel.Tally]:
    return panel.tallies(
        copy_of(tree), TARGET, today=TODAY, signer=SIGNER, curators=frozenset({CURATOR})
    )


def nothing_pushed(h: Harness, before: int, r: Any, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    assert r.json()["error"] == code, r.text
    assert len(h.githost.pushes) == before


def invite(h: Harness, who: Who, by: str, login: str, note: str | None = None) -> Any:
    subject: dict[str, Any] = {"login": login}
    if note:
        subject["note"] = note
    return post(h, "/motions", who(by), kind="invite", subject=subject)


def admit_carol(h: Harness, tree: Path, who: Who) -> None:
    """alice, the panel's only member, invites carol (passes at once) the day before; carol
    accepts today. (Accepted the same day, the invitation would read as open again: F24-Q,
    proposed, in the report.)"""
    h.clock.advance(days=-1)
    merge(h, tree, invite(h, who, "alice", "carol", "the second half"))
    h.clock.advance(days=1)
    merge(h, tree, post(h, "/stewards", who("carol"), **accept(1)))


def accept(n: int | None, **over: Any) -> dict[str, Any]:
    form: dict[str, Any] = {"action": "commit", "name": "Carol C.", "link": None, "accept": True}
    if n is not None:
        form["motion"] = n
    return {**form, **over}


# --- POST /motions --------------------------------------------------------------------------------


def test_a_member_opens_an_invitation_that_the_gate_tallies(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    """AC9: a ``motion/v1`` opened by alice, the settings copied from the policy (defaults
    here), and alone on the panel her motion passes at once."""
    r = invite(h, who, "alice", "carol", "the second half")
    doc = landed(h, r, "motion/v1", approval[1])
    assert r.json()["path"] == f"targets/{TARGET}/motions/1.yaml"
    assert doc["opened_by"] == "alice" and doc["kind"] == "invite"
    assert doc["subject"] == {"login": "carol", "note": "the second half"}
    assert doc["settings"] == panel.Settings().motion_settings()
    assert h.githost.pushes[-1].author is not None
    assert h.githost.pushes[-1].author.name == "alice"
    merge(h, tree, r)
    [found] = tallies(tree)
    assert (found.n, found.state, found.subject["login"]) == (1, "passed", "carol")


def test_a_motion_copies_the_policy_settings(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    write_policy(tree, cap=5, window=21)
    serve(h, tree)
    doc = landed(h, invite(h, who, "alice", "carol"), "motion/v1", approval[1])
    assert doc["settings"]["vote_window_days"] == 21


def test_a_curator_may_open_a_motion(h: Harness, who: Who, approval: tuple[str, str]) -> None:
    doc = landed(h, invite(h, who, CURATOR, "dave"), "motion/v1", approval[1])
    assert doc["opened_by"] == CURATOR


def test_a_non_member_may_not_open_a_motion(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = invite(h, who, "bob", "dave")
    nothing_pushed(h, before, r, 409, "not-panel-member")


def test_an_invitee_already_on_the_panel_is_refused(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = invite(h, who, CURATOR, "alice")
    nothing_pushed(h, before, r, 409, "invitee-already-member")


def test_a_second_open_invitation_for_one_login_is_refused(
    h: Harness, tree: Path, who: Who
) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))  # two members: this one stays open
    assert [t.state for t in tallies(tree)] == ["passed", "open"]
    before = len(h.githost.pushes)
    nothing_pushed(h, before, invite(h, who, "alice", "dave"), 409, "invitation-open")


def test_a_verify_motion_must_name_a_write_up(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/motions", who("alice"), kind="verify-writeup", subject={"writeup": 4})
    nothing_pushed(h, before, r, 409, "writeup-unknown")


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "promote", "subject": {"login": "dave"}},
        {"kind": "invite", "subject": {"writeup": 1}},
        {"kind": "invite", "subject": "dave"},
        {"kind": "authorship-threshold", "subject": {"threshold": -1}},
    ],
)
def test_a_malformed_motion_is_400(h: Harness, who: Who, body: dict[str, Any]) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/motions", who("alice"), **body)
    assert r.status_code == 400, r.text
    assert len(h.githost.pushes) == before


# --- POST /votes ----------------------------------------------------------------------------------


def test_a_members_vote_is_counted(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))
    r = post(h, "/votes", who("alice"), motion=2, vote="yes")
    doc = landed(h, r, "vote/v1", approval[1])
    assert (doc["login"], doc["motion"], doc["vote"]) == ("alice", 2, "yes")
    assert r.json()["path"] == f"targets/{TARGET}/votes/1.yaml"
    merge(h, tree, r)
    found = tallies(tree)[1]
    assert (found.state, found.yes, found.no) == ("open", 1, 0)


def test_a_non_member_may_not_vote(h: Harness, tree: Path, who: Who) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))
    before = len(h.githost.pushes)
    r = post(h, "/votes", who("bob"), motion=2, vote="yes")
    nothing_pushed(h, before, r, 409, "voter-not-eligible")


def test_an_unknown_motion_is_refused(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/votes", who("alice"), motion=9, vote="yes")
    nothing_pushed(h, before, r, 404, "motion-unknown")


def test_a_decided_motion_takes_no_vote(h: Harness, tree: Path, who: Who) -> None:
    merge(h, tree, invite(h, who, "alice", "carol"))  # passed at once
    before = len(h.githost.pushes)
    r = post(h, "/votes", who("alice"), motion=1, vote="no")
    nothing_pushed(h, before, r, 409, "motion-decided")


def test_a_closed_window_takes_no_vote(h: Harness, tree: Path, who: Who) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))
    h.clock.advance(days=15)
    before = len(h.githost.pushes)
    r = post(h, "/votes", who("alice"), motion=2, vote="yes")
    nothing_pushed(h, before, r, 409, "window-closed")


@pytest.mark.parametrize("body", [{"motion": "2", "vote": "yes"}, {"motion": 2, "vote": "maybe"}])
def test_a_malformed_vote_is_400(h: Harness, who: Who, body: dict[str, Any]) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/votes", who("alice"), **body)
    assert r.status_code == 400, r.text
    assert len(h.githost.pushes) == before


# --- POST /writeups -------------------------------------------------------------------------------

PAPER = {"kind": "paper", "title": "On the matter", "url": "https://example.org/paper.pdf"}


def views(tree: Path) -> list[writeup.View]:
    return writeup.views(
        copy_of(tree), TARGET, today=TODAY, signer=SIGNER, curators=frozenset({CURATOR})
    )


def test_anyone_records_and_an_authors_signature_moves_the_stage(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    """AC9: bob records a paper naming alice as author (``written``); alice, a steward, signs
    it and it is ``steward-signed``."""
    r = post(h, "/writeups", who("bob"), action="record", authors=["bob", "alice"], **PAPER)
    doc = landed(h, r, "writeup/v2", approval[1])
    assert (doc["signer"], doc["authors"]) == ("bob", ["bob", "alice"])
    assert r.json()["path"] == f"targets/{TARGET}/writeup/1.yaml"
    merge(h, tree, r)
    assert [(v.n, v.stage) for v in views(tree)] == [(1, "written")]
    s = post(h, "/writeups", who("alice"), action="author-sign", writeup=1)
    assert landed(h, s, "writeup/v2", approval[1])["action"] == "author-sign"
    merge(h, tree, s)
    [found] = views(tree)
    assert (found.stage, found.signed) == ("steward-signed", ("bob", "alice"))


def test_a_non_author_may_not_act_on_a_write_up(h: Harness, tree: Path, who: Who) -> None:
    merge(h, tree, post(h, "/writeups", who("bob"), action="record", authors=["bob"], **PAPER))
    before = len(h.githost.pushes)
    r = post(h, "/writeups", who("alice"), action="arxiv", writeup=1, arxiv="2610.01234")
    nothing_pushed(h, before, r, 409, "not-an-author")


def test_an_author_signs_once(h: Harness, tree: Path, who: Who) -> None:
    merge(h, tree, post(h, "/writeups", who("bob"), action="record", authors=["bob"], **PAPER))
    before = len(h.githost.pushes)
    r = post(h, "/writeups", who("bob"), action="author-sign", writeup=1)
    nothing_pushed(h, before, r, 409, "already-signed")


def test_an_act_must_name_a_record(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/writeups", who("bob"), action="author-sign", writeup=3)
    nothing_pushed(h, before, r, 409, "writeup-unknown")


@pytest.mark.parametrize(
    "body",
    [
        {"action": "publish", "writeup": 1},
        {"action": "record", "kind": "paper", "title": "T", "url": "https://x.org", "writeup": 1},
        {"action": "arxiv", "writeup": 1},
        {"action": "record", **PAPER},  # no authors
    ],
)
def test_a_malformed_writeup_is_400(h: Harness, who: Who, body: dict[str, Any]) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/writeups", who("bob"), **body)
    assert r.status_code == 400, r.text
    assert len(h.githost.pushes) == before


# --- POST /stewards: the invitation path ----------------------------------------------------------


def test_an_invited_commitment_is_a_v3_record_the_gate_admits(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    merge(h, tree, invite(h, who, "alice", "carol"))
    r = post(h, "/stewards", who("carol"), **accept(1))
    doc = landed(h, r, "steward/v3", approval[1])
    assert (doc["login"], doc["admitted_by"]) == ("carol", "motion:1")
    over = copy_of(tree)
    assert panel.passed_invitation(over, TARGET, 1, "carol", today=TODAY, signer=SIGNER) is None
    merge(h, tree, r)
    members = panel.members(copy_of(tree), TARGET, TODAY, settings=panel.Settings(), signer=SIGNER)
    assert members == ("alice", "carol")


def test_self_is_refused_when_the_target_has_a_panel(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/stewards", who("carol"), **accept(None))
    nothing_pushed(h, before, r, 409, "invitation-required")


def test_a_motion_that_is_not_carols_passed_invitation_is_refused(
    h: Harness, tree: Path, who: Who
) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))  # open, not passed
    before = len(h.githost.pushes)
    for n in (1, 2, 7):  # carol's invitation, an open one, an unknown one
        r = post(h, "/stewards", who("dave"), **accept(n, name="Dave"))
        nothing_pushed(h, before, r, 409, "invitation-invalid")


def test_the_cap_is_refused_before_anything_opens(
    h: Harness, tree: Path, who: Who, keys: dict[str, Path]
) -> None:
    """carol already stewards ``second``; with a cap of 1 her accepting alice's invitation on
    ``propositional`` would be a second stewardship."""
    write_policy(tree, cap=1, window=14)
    add_second_target(tree)
    steward_record(tree, SECOND, "carol", "2026-10-05")
    serve(h, tree)
    merge(h, tree, invite(h, who, "alice", "carol"))
    before = len(h.githost.pushes)
    r = post(h, "/stewards", who("carol"), **accept(1))
    nothing_pushed(h, before, r, 409, "steward-cap")


def test_a_first_steward_still_commits_by_self(
    h: Harness, tree: Path, who: Who, approval: tuple[str, str]
) -> None:
    """With no panel member (alice steps down), ``self`` is admitted as F23 had it."""
    steward_record(tree, TARGET, "alice", "2026-10-06", action="step-down")
    serve(h, tree)
    doc = landed(h, post(h, "/stewards", who("carol"), **accept(None)), "steward/v2", approval[1])
    assert doc["admitted_by"] == "self"


def test_a_step_down_takes_no_motion(h: Harness, who: Who) -> None:
    before = len(h.githost.pushes)
    r = post(h, "/stewards", who("alice"), **accept(1, action="step-down", name="Alice"))
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid", r.text
    assert len(h.githost.pushes) == before


# --- GET /session: what waits for the login -------------------------------------------------------


def awaiting(h: Harness, who: Who, login: str) -> dict[str, Any]:
    r = h.client.get("/session", headers=who(login))
    assert r.status_code == 200, r.text
    return dict(r.json()["awaiting"])


def test_nothing_waits_on_a_quiet_graph(h: Harness, who: Who) -> None:
    assert awaiting(h, who, "alice") == {"votes": [], "invitations": []}


def test_signed_out_has_no_awaiting(h: Harness) -> None:
    assert "awaiting" not in h.client.get("/session").json()


def test_an_invitation_waits_for_its_invitee_until_accepted(
    h: Harness, tree: Path, who: Who
) -> None:
    merge(h, tree, invite(h, who, "alice", "carol", "the second half"))
    assert awaiting(h, who, "carol") == {
        "votes": [],
        "invitations": [{"target": TARGET, "motion": 1, "note": "the second half"}],
    }
    merge(h, tree, post(h, "/stewards", who("carol"), **accept(1)))
    assert awaiting(h, who, "carol")["invitations"] == []


def test_an_open_motion_waits_for_each_member_until_they_vote(
    h: Harness, tree: Path, who: Who
) -> None:
    admit_carol(h, tree, who)
    merge(h, tree, invite(h, who, "carol", "dave"))
    closes = (TODAY + dt.timedelta(days=14)).isoformat()
    expected = {
        "target": TARGET,
        "motion": 2,
        "kind": "invite",
        "subject": {"login": "dave"},
        "closes": closes,
    }
    assert awaiting(h, who, "alice")["votes"] == [expected]
    assert awaiting(h, who, "carol")["votes"] == [expected]
    assert awaiting(h, who, "bob")["votes"] == []
    merge(h, tree, post(h, "/votes", who("alice"), motion=2, vote="yes"))
    assert awaiting(h, who, "alice")["votes"] == []
    assert awaiting(h, who, "dave")["invitations"] == []  # open, not passed


def test_a_provers_uncounted_vote_does_not_wait(h: Harness, tree: Path, who: Who) -> None:
    admit_carol(h, tree, who)
    prover(tree, "alice")
    serve(h, tree)
    merge(h, tree, post(h, "/writeups", who("bob"), action="record", authors=["bob"], **PAPER))
    # alice, a prover, opens it: carol is the one counted member, and alice's own vote would not
    # count, so only carol is waited for.
    merge(h, tree, post(h, "/motions", who("alice"), kind="verify-writeup", subject={"writeup": 1}))
    assert awaiting(h, who, "alice")["votes"] == []
    assert [v["motion"] for v in awaiting(h, who, "carol")["votes"]] == [2]


# --- the materialisation --------------------------------------------------------------------------


def test_the_materialised_tree_holds_what_the_rules_read(h: Harness, tree: Path, who: Who) -> None:
    from opn_api import panel as panelroutes  # noqa: PLC0415

    admit_carol(h, tree, who)
    prover(tree, "alice")
    serve(h, tree)
    root = tree.parent / "scratch"
    panelroutes.materialise(h.context, root, [TARGET])
    target = root / "targets" / TARGET
    assert sorted(p.name for p in (target / "stewards").iterdir()) == ["1.yaml", "2.yaml"]
    assert sorted(p.name for p in (target / "motions").iterdir()) == ["1.yaml"]
    assert (root / "curators.json").is_file()
    assert ledger.holds_proof_line(root, "alice", TARGET)
    assert panel.members(root, TARGET, TODAY, settings=panel.Settings(), signer=SIGNER) == (
        "alice",
        "carol",
    )


# --- helpers that write the graph directly --------------------------------------------------------


def write_policy(tree: Path, *, cap: int, window: int) -> None:
    def setting(value: Any) -> dict[str, Any]:
        return {"value": value, "since": "2026-10-08", "reason": "a test"}

    doc = {
        "schema": "policy/v3",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "open",
        "panel": {
            "vote_threshold": setting({"numerator": 1, "denominator": 2}),
            "vote_window_days": setting(window),
            "vote_minimum": setting(2),
            "vote_minimum_from": setting(3),
            "steward_cap": setting(cap),
            "steward_lapse_days": setting(183),
        },
    }
    (tree / "policy.json").write_text(json.dumps(doc), encoding="utf-8")


def add_second_target(tree: Path) -> None:
    index = json.loads((Path(__file__).parent / "fixtures" / "targets-index.json").read_text())
    entry = dict(index["targets"][0])
    entry["target_id"] = SECOND
    index["targets"].append(entry)
    (tree / "targets" / "index.json").write_text(json.dumps(index), encoding="utf-8")


def steward_record(
    tree: Path, target_id: str, login: str, date: str, action: str = steward.COMMIT
) -> None:
    """A ``steward/v2`` record signed by a throwaway key, as an SSH-free record merged by hand
    would be under the approval key."""
    key = tree.parent / f"{login}-{target_id}-key"
    if not key.exists():
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", login],
            check=True,
        )
    directory = tree / "targets" / target_id / "stewards"
    directory.mkdir(parents=True, exist_ok=True)
    n = len(list(directory.glob("*.yaml"))) + 1
    doc = {
        "schema": "steward/v2",
        "target": target_id,
        "action": action,
        "login": login,
        "name": login.title(),
        "link": None,
        "commitment": steward.SENTENCE_FOR[action],
        "date": date,
        "via": "approval-key",
        "admitted_by": "self",
    }
    doc = signed.sign(doc, key, SIGNER)
    (directory / f"{n}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def prover(tree: Path, login: str) -> None:
    entry = ledger.proof_entry(
        identity=login, target=TARGET, node="and-reassoc", artifact_type="proof",
        artifact="nodes/and-reassoc/Proof.lean", merge_commit="a" * 40,
        date="2026-10-01T00:00:00Z",
    )  # fmt: skip
    assert entry is not None
    ledger.write(tree, ledger.append(ledger.load(tree, login), entry))
