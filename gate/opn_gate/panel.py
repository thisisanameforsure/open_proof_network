"""The steward panel (F24-R1 to R4; D-32 v3.34).

A target's **panel** is its stewards who have not lapsed. The panel acts by **motions**
(``targets/<id>/motions/<n>.yaml``), decided by **votes** (``targets/<id>/votes/<n>.yaml``), and
everything here is derived from those records and the steward records: nothing is rewritten, so
one revert undoes any of it (D-32 v3.34; the owner's four principles).

The rules, in one place:

* **Settings.** Every number lives in ``policy.json``'s ``panel`` (``Settings``), with defaults
  when the file is absent or older. A motion carries the voting settings it was opened under and is
  decided by those, so a policy change reaches only motions opened after it.
* **Who is on the panel.** On a given day, the stewards whose latest counting record dated on or
  before it is a commit and whose latest signed act on the target is no more than
  ``lapse_days`` before it (``members``). Signed acts are steward records, motions, votes,
  write-up records and words signatures (``last_acts``).
* **Who counts.** The panel as it stood on the motion's date. On ``verify-writeup`` and
  ``authorship-threshold``, a member holding proof credit on the target votes but is not counted;
  when no member remains counted, listed curators count in the panel's place.
* **When it passes.** At once for an invitation opened by a curator, or for any motion whose
  opener is the only counted member. Otherwise, after its window, when the counted yes votes are at
  least the threshold share of counted votes, more than the no votes, and at least ``minimum``
  when the counted panel has ``minimum_from`` or more members. Abstentions count neither way.

A record whose signature does not verify counts for nothing, as a steward record does. Words
signatures are read as merged (the gate verified each before it merged) and are not re-verified
here, since they only ever extend a steward's activity.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import ledger, schemas, signed, steward
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

MOTION_SCHEMA = "motion/v1"
VOTE_SCHEMA = "vote/v1"
MOTIONS_DIR = "motions"
VOTES_DIR = "votes"
INVITE = "invite"
VERIFY_WRITEUP = "verify-writeup"
AUTHORSHIP_THRESHOLD = "authorship-threshold"
KINDS: tuple[str, ...] = (INVITE, VERIFY_WRITEUP, AUTHORSHIP_THRESHOLD)
#: The motions on which a member who holds proof credit votes uncounted (D-32 v3.34).
PROVER_EXCLUDED: frozenset[str] = frozenset({VERIFY_WRITEUP, AUTHORSHIP_THRESHOLD})
OPEN, PASSED, FAILED = "open", "passed", "failed"
YES, NO = "yes", "no"
_FILE_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")
_WORDS_SIGNATURES: frozenset[str] = frozenset(
    {
        "gloss-signature/v1",
        "gloss-signature/v2",
        "gloss-signature/v3",
        "explainer-signature/v1",
        "explainer-signature/v2",
        "explainer-signature/v3",
    }
)
#: The policy.json names, in the order the rules page shows them.
SETTING_NAMES: tuple[str, ...] = (
    "vote_threshold",
    "vote_window_days",
    "vote_minimum",
    "vote_minimum_from",
    "steward_cap",
    "steward_lapse_days",
)


class PanelError(ValueError):
    """A question about the panel that has no answer: an unknown motion, for one."""


# --- settings ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    """The panel's numbers (F24-R1). Defaults are the owner's rulings of 2026-10-08."""

    threshold: tuple[int, int] = (1, 2)
    window_days: int = 14
    minimum: int = 2
    minimum_from: int = 3
    cap: int = 5
    lapse_days: int = 183
    #: ``(name, since, reason)`` for each setting read from policy.json; empty for defaults.
    provenance: tuple[tuple[str, str | None, str | None], ...] = field(default=(), compare=False)

    def values(self) -> dict[str, Any]:
        return {
            "vote_threshold": {"numerator": self.threshold[0], "denominator": self.threshold[1]},
            "vote_window_days": self.window_days,
            "vote_minimum": self.minimum,
            "vote_minimum_from": self.minimum_from,
            "steward_cap": self.cap,
            "steward_lapse_days": self.lapse_days,
        }

    def motion_settings(self) -> dict[str, Any]:
        """What a motion copies when it is opened (``motion/v1``'s ``settings``)."""
        values = self.values()
        return {k: values[k] for k in SETTING_NAMES[:4]}

    def as_dict(self) -> dict[str, Any]:
        """``{name: {value, since, reason}}``, as ``targets-index/v9`` publishes it."""
        known = {name: (since, reason) for name, since, reason in self.provenance}
        values = self.values()
        return {
            name: {
                "value": values[name],
                "since": known.get(name, (None, None))[0],
                "reason": known.get(name, (None, None))[1],
            }
            for name in SETTING_NAMES
        }


def settings_of(panel_doc: dict[str, Any]) -> Settings:
    """``Settings`` from a validated ``policy/v3`` ``panel`` object."""
    t = panel_doc["vote_threshold"]["value"]
    return Settings(
        threshold=(int(t["numerator"]), int(t["denominator"])),
        window_days=int(panel_doc["vote_window_days"]["value"]),
        minimum=int(panel_doc["vote_minimum"]["value"]),
        minimum_from=int(panel_doc["vote_minimum_from"]["value"]),
        cap=int(panel_doc["steward_cap"]["value"]),
        lapse_days=int(panel_doc["steward_lapse_days"]["value"]),
        provenance=tuple(
            (name, panel_doc[name].get("since"), panel_doc[name].get("reason"))
            for name in SETTING_NAMES
        ),
    )


def voting_settings_of(motion_settings: dict[str, Any], base: Settings) -> Settings:
    """The voting settings a motion carries, over ``base`` for the rest (cap and lapse)."""
    t = motion_settings["vote_threshold"]
    return Settings(
        threshold=(int(t["numerator"]), int(t["denominator"])),
        window_days=int(motion_settings["vote_window_days"]),
        minimum=int(motion_settings["vote_minimum"]),
        minimum_from=int(motion_settings["vote_minimum_from"]),
        cap=base.cap,
        lapse_days=base.lapse_days,
    )


def current_settings(graph_root: Path) -> Settings:
    from opn_gate import policy  # noqa: PLC0415 — policy imports this module for Settings

    return policy.load(graph_root).panel


# --- records -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Motion:
    n: int
    kind: str
    subject: dict[str, Any]
    opened_by: str
    date: dt.date
    settings: dict[str, Any]
    path: Path
    doc: dict[str, Any]


@dataclass(frozen=True)
class Vote:
    n: int
    motion: int
    login: str
    vote: str
    date: dt.date
    path: Path
    doc: dict[str, Any]


def day_of(text: str) -> dt.date:
    return dt.date.fromisoformat(str(text)[:10])


def _numbered(directory: Path, what: str) -> list[tuple[int, Path]]:
    if not directory.is_dir():
        return []
    out: list[tuple[int, Path]] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        m = _FILE_RE.match(path.name)
        if m is None:
            msg = f"{path}: a {what} record is {directory.name}/<n>.yaml (F24-R2, R3)"
            raise schemas.SchemaError(msg)
        out.append((int(m.group("n")), path))
    out.sort()
    return out


def motion_of(doc: dict[str, Any], path: Path, n: int) -> Motion:
    return Motion(
        n=n,
        kind=str(doc["kind"]),
        subject=dict(doc["subject"]),
        opened_by=str(doc["opened_by"]),
        date=day_of(doc["date"]),
        settings=dict(doc["settings"]),
        path=path,
        doc=doc,
    )


def vote_of(doc: dict[str, Any], path: Path, n: int) -> Vote:
    return Vote(
        n=n,
        motion=int(doc["motion"]),
        login=str(doc["login"]),
        vote=str(doc["vote"]),
        date=day_of(doc["date"]),
        path=path,
        doc=doc,
    )


def load_motions(target_dir: Path) -> list[Motion]:
    """Every motion, in file order. A file that is not one, or does not validate, raises."""
    return [
        motion_of(schemas.load_yaml(path, MOTION_SCHEMA), path, n)
        for n, path in _numbered(target_dir / MOTIONS_DIR, "motion")
    ]


def load_votes(target_dir: Path) -> list[Vote]:
    return [
        vote_of(schemas.load_yaml(path, VOTE_SCHEMA), path, n)
        for n, path in _numbered(target_dir / VOTES_DIR, "vote")
    ]


class _Verified:
    """Signature verdicts, one ``ssh-keygen`` per record per derivation."""

    def __init__(self, signer: Signer) -> None:
        self.signer = signer
        self.seen: dict[Path, bool] = {}

    def __call__(self, path: Path, doc: dict[str, Any]) -> bool:
        if path not in self.seen:
            self.seen[path] = signed.verifies(doc, self.signer)
            if not self.seen[path]:
                log.warning("%s counts for nothing: the signature does not verify", path)
        return self.seen[path]


# --- signed acts and lapse ---------------------------------------------------------------------


def _target_dir(graph_root: Path, target_id: str) -> Path:
    return graph_root / "targets" / target_id


def _words_signatures(target_dir: Path) -> list[tuple[str, str]]:
    """(signer, date) of every valid words signature under the target (read as merged)."""
    out: list[tuple[str, str]] = []
    for path in sorted(target_dir.rglob("*.yaml")):
        if path.parent.name != "signed" or path.parent.parent.name not in ("gloss", "explainer"):
            continue
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError:
            continue
        if doc.get("schema") in _WORDS_SIGNATURES:
            out.append((str(doc["signer"]), str(doc["date"])))
    return out


def words_signers(target_dir: Path) -> frozenset[str]:
    return frozenset(login for login, _ in _words_signatures(target_dir))


def acts(
    graph_root: Path, target_id: str, *, signer: Signer, verified: _Verified | None = None
) -> dict[str, list[dt.date]]:
    """Every signed act on the target, by login: the days of their counting steward records,
    motions opened, votes, write-up records and words signatures (F24-R4)."""
    from opn_gate import writeup  # noqa: PLC0415 — writeup reads the panel for its stages

    target_dir = _target_dir(graph_root, target_id)
    verified = verified or _Verified(signer)
    out: dict[str, list[dt.date]] = {}

    def add(login: str, date: str | dt.date) -> None:
        out.setdefault(login, []).append(date if isinstance(date, dt.date) else day_of(date))

    for checked in steward.check(steward.load(target_dir), signer):
        if checked.counts:
            add(checked.record.login, checked.record.date)
    for motion in load_motions(target_dir):
        if verified(motion.path, motion.doc):
            add(motion.opened_by, motion.date)
    for vote in load_votes(target_dir):
        if verified(vote.path, vote.doc):
            add(vote.login, vote.date)
    for record in writeup.load_any(target_dir):
        if verified(record.path, record.doc):
            add(record.signer, record.date)
    for login, date in _words_signatures(target_dir):
        add(login, date)
    return out


def last_acts(graph_root: Path, target_id: str, *, signer: Signer) -> dict[str, dt.date]:
    """Each login's latest signed act on the target."""
    return {login: max(days) for login, days in acts(graph_root, target_id, signer=signer).items()}


def _admitted_by_motion(record: steward.Record) -> int | None:
    admitted = record.admitted_by or ""
    if admitted.startswith(steward.MOTION_PREFIX):
        return int(admitted[len(steward.MOTION_PREFIX) :])
    return None


def _active_on(
    target_dir: Path, on: dt.date, signer: Signer, *, before_motion: int | None = None
) -> list[str]:
    """The logins whose latest counting steward record dated on or before ``on`` is a commit,
    in the order they became active. With ``before_motion``, a commitment admitted by that motion
    or a later one is left out: it cannot have been on the panel the motion was put to, whatever
    day it was made (F24-T5 Q-a)."""
    current: dict[str, None] = {}
    for checked in steward.check(steward.load(target_dir), signer):
        record = checked.record
        if not checked.counts or day_of(record.date) > on:
            continue
        admitted = _admitted_by_motion(record)
        if before_motion is not None and admitted is not None and admitted >= before_motion:
            continue
        if record.action == steward.COMMIT:
            current.setdefault(record.login, None)
        else:
            current.pop(record.login, None)
    return list(current)


def lapsed(last: dt.date | None, on: dt.date, settings: Settings) -> bool:
    return last is None or (on - last).days > settings.lapse_days


def members(  # noqa: PLR0913 — the target, the day, and how to read it
    graph_root: Path,
    target_id: str,
    on: dt.date,
    *,
    settings: Settings,
    signer: Signer,
    verified: _Verified | None = None,
    before_motion: int | None = None,
) -> tuple[str, ...]:
    """The panel on day ``on``: active stewards whose latest act on or before ``on`` is within
    ``lapse_days`` of it."""
    target_dir = _target_dir(graph_root, target_id)
    active = _active_on(target_dir, on, signer, before_motion=before_motion)
    if not active:
        return ()
    by_login = acts(graph_root, target_id, signer=signer, verified=verified)
    out: list[str] = []
    for login in active:
        before = [d for d in by_login.get(login, []) if d <= on]
        if not lapsed(max(before, default=None), on, settings):
            out.append(login)
    return tuple(out)


def stewardships(
    graph_root: Path, login: str, on: dt.date, *, settings: Settings, signer: Signer
) -> tuple[str, ...]:
    """The targets on whose panel ``login`` sits on day ``on``, across the graph (the cap)."""
    targets = graph_root / "targets"
    if not targets.is_dir():
        return ()
    out: list[str] = []
    for target_dir in sorted(p for p in targets.iterdir() if p.is_dir()):
        if not (target_dir / steward.DIR).is_dir():
            continue
        if login in members(graph_root, target_dir.name, on, settings=settings, signer=signer):
            out.append(target_dir.name)
    return tuple(out)


# --- tallies -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tally:
    """A motion with its state on a given day (F24-R2, R3), in the shape the index publishes."""

    n: int
    state: str
    yes: int
    no: int
    closes: dt.date
    uncounted: tuple[str, ...] = ()
    kind: str = INVITE
    subject: dict[str, Any] = field(default_factory=dict)
    opened_by: str = ""
    opened: dt.date | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "kind": self.kind,
            "subject": self.subject,
            "opened_by": self.opened_by,
            "opened": self.opened.isoformat() if self.opened else self.closes.isoformat(),
            "closes": self.closes.isoformat(),
            "state": self.state,
            "yes": self.yes,
            "no": self.no,
            "uncounted": list(self.uncounted),
        }


def passes(yes: int, no: int, *, counted_members: int, settings: Settings) -> bool:
    """The rule a decided motion is judged by (F24-R2, Q2)."""
    counted = yes + no
    numerator, denominator = settings.threshold
    if counted == 0 or yes * denominator < numerator * counted or yes <= no:
        return False
    return counted_members < settings.minimum_from or counted >= settings.minimum


@dataclass(frozen=True)
class _Counted:
    """Who a motion's votes are counted from (F24-R3)."""

    panel: tuple[str, ...]
    provers: frozenset[str]
    counted: frozenset[str]


def _who_counts(  # noqa: PLR0913 — the motion and its world
    graph_root: Path,
    target_id: str,
    motion: Motion,
    *,
    base: Settings,
    curators: frozenset[str],
    verified: _Verified,
) -> _Counted:
    panel = members(
        graph_root, target_id, motion.date, settings=base, signer=verified.signer,
        verified=verified, before_motion=motion.n,
    )  # fmt: skip
    provers: frozenset[str] = frozenset()
    if motion.kind in PROVER_EXCLUDED:
        provers = frozenset(m for m in panel if ledger.holds_proof_line(graph_root, m, target_id))
    counted = frozenset(panel) - provers
    if not counted and motion.kind in PROVER_EXCLUDED:
        counted = curators
    return _Counted(panel, provers, counted)


def _latest_votes(
    motion: Motion, votes: list[Vote], who: _Counted, closes: dt.date, verified: _Verified
) -> dict[str, Vote]:
    """Each voter's latest valid vote on ``motion`` inside its window."""
    latest: dict[str, Vote] = {}
    for vote in votes:
        if vote.motion != motion.n or not (motion.date <= vote.date <= closes):
            continue
        if vote.login not in who.counted | who.provers or not verified(vote.path, vote.doc):
            continue
        held = latest.get(vote.login)
        if held is None or (vote.date, vote.n) >= (held.date, held.n):
            latest[vote.login] = vote
    return latest


def _decide(  # noqa: PLR0913 — the motion, its world, and the day
    graph_root: Path,
    target_id: str,
    motion: Motion,
    votes: list[Vote],
    *,
    today: dt.date,
    base: Settings,
    curators: frozenset[str],
    verified: _Verified,
) -> Tally:
    settings = voting_settings_of(motion.settings, base)
    closes = motion.date + dt.timedelta(days=settings.window_days)

    def result(state: str, yes: int = 0, no: int = 0, uncounted: tuple[str, ...] = ()) -> Tally:
        return Tally(
            motion.n, state, yes, no, closes, uncounted, kind=motion.kind,
            subject=motion.subject, opened_by=motion.opened_by, opened=motion.date,
        )  # fmt: skip

    if not verified(motion.path, motion.doc):
        return result(FAILED)
    who = _who_counts(
        graph_root, target_id, motion, base=base, curators=curators, verified=verified
    )
    if motion.opened_by not in who.panel and motion.opened_by not in curators:
        return result(FAILED)
    if (motion.kind == INVITE and motion.opened_by in curators) or who.counted == {
        motion.opened_by
    }:
        return result(PASSED)
    latest = _latest_votes(motion, votes, who, closes, verified)
    yes = sum(1 for v in latest.values() if v.login in who.counted and v.vote == YES)
    no = sum(1 for v in latest.values() if v.login in who.counted and v.vote == NO)
    uncounted = tuple(sorted(login for login in latest if login not in who.counted))
    if today <= closes:
        return result(OPEN, yes, no, uncounted)
    decided = passes(yes, no, counted_members=len(who.counted), settings=settings)
    return result(PASSED if decided else FAILED, yes, no, uncounted)


def tallies(
    graph_root: Path,
    target_id: str,
    *,
    today: dt.date,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> list[Tally]:
    """Every motion on the target with its state on ``today``, in file order."""
    target_dir = _target_dir(graph_root, target_id)
    motions = load_motions(target_dir)
    if not motions:
        return []
    votes = load_votes(target_dir)
    base = current_settings(graph_root)
    verified = _Verified(signer)
    return [
        _decide(
            graph_root,
            target_id,
            m,
            votes,
            today=today,
            base=base,
            curators=curators,
            verified=verified,
        )
        for m in motions
    ]


def tally(  # noqa: PLR0913 — the motion, and how to read it
    graph_root: Path,
    target_id: str,
    n: int,
    *,
    today: dt.date,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> Tally:
    """Motion ``n`` with its state on ``today``; ``PanelError`` when there is no such motion."""
    for found in tallies(graph_root, target_id, today=today, signer=signer, curators=curators):
        if found.n == n:
            return found
    msg = f"targets/{target_id}/{MOTIONS_DIR}/{n}.yaml does not exist"
    raise PanelError(msg)


def voters(
    graph_root: Path,
    target_id: str,
    n: int,
    *,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> tuple[frozenset[str], frozenset[str]]:
    """(counted, uncounted) for motion ``n``: whose votes count, and the provers whose votes are
    recorded but not counted (F24-R3). A login in neither is not a voter on that motion, which is
    what the service refuses before it opens a vote (F24-R8). ``PanelError`` for no such motion."""
    target_dir = _target_dir(graph_root, target_id)
    motion = next((m for m in load_motions(target_dir) if m.n == n), None)
    if motion is None:
        msg = f"targets/{target_id}/{MOTIONS_DIR}/{n}.yaml does not exist"
        raise PanelError(msg)
    who = _who_counts(
        graph_root, target_id, motion, base=current_settings(graph_root), curators=curators,
        verified=_Verified(signer),
    )  # fmt: skip
    return who.counted, who.provers


def passed_invitation(  # noqa: PLR0913 — the invitation, the invitee, and how to read it
    graph_root: Path,
    target_id: str,
    n: int,
    login: str,
    *,
    today: dt.date,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> str | None:
    """Why ``motion:<n>`` does not admit ``login`` on ``today`` (F24-R4), or ``None`` when it
    does: the motion must exist, be an invitation naming the login, and have passed."""
    try:
        found = tally(graph_root, target_id, n, today=today, signer=signer, curators=curators)
    except PanelError as exc:
        return str(exc)
    if found.kind != INVITE or found.subject.get("login") != login:
        return f"motion {n} is not an invitation of {login}"
    if found.state != PASSED:
        return f"motion {n} is {found.state}, not passed"
    return None


def eligible_voters(
    graph_root: Path,
    target_id: str,
    n: int,
    *,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Whose vote on motion ``n`` is read at all (F24-R3): counted, or listed uncounted — the
    panel as it stood on the motion's date, or the curators where curators count. The gate's
    question for a vote (F24-R10); ``PanelError`` when there is no such motion."""
    target_dir = _target_dir(graph_root, target_id)
    motion = next((m for m in load_motions(target_dir) if m.n == n), None)
    if motion is None:
        msg = f"targets/{target_id}/{MOTIONS_DIR}/{n}.yaml does not exist"
        raise PanelError(msg)
    who = _who_counts(
        graph_root, target_id, motion, base=current_settings(graph_root), curators=curators,
        verified=_Verified(signer),
    )  # fmt: skip
    return who.counted | who.provers
