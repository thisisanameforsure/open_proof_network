"""The steward panel from the site: ``POST /motions``, ``POST /votes``, ``POST /writeups``, the
invitation path on ``POST /stewards`` and ``GET /session``'s ``awaiting`` (F24-R8; D-32 v3.34,
D-35 v3.34).

Each route writes its record (``motion/v1``, ``vote/v1``, ``writeup/v2``) as the signed-in GitHub
login, dated today (UTC), ``via: approval-key``, signs it with the network's approval key
(``stewards.sign_record``), validates it against its schema and opens it as the next numbered file
on an ``append/`` branch, exactly as an open-admission steward record is, answering the same
receipt. A motion carries the voting settings of the graph's ``policy.json`` at the current
commit (``Settings.motion_settings``).

Before anything opens, each route refuses by name what the gate would refuse at the merge. The
rules are never re-derived here: the files the gate's panel library reads are copied from the
committed graph into a scratch tree (``materialise``) and ``opn_gate.panel`` and
``opn_gate.writeup`` answer over it, with signatures verified in Python (``HostVerifier``: the
function has no ``ssh-keygen``). Whether a record counts is still the gate's, at the merge.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, pending, ratelimit, session, stewards, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.glosses import HostVerifier
from opn_gate import explainers, glosses, ledger, modes, schemas, steward, writeup
from opn_gate import panel as panelmod
from opn_gate import policy as policymod

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

VIA = "approval-key"
MOTION_FIELDS: tuple[str, ...] = ("target", "kind", "subject")
VOTE_FIELDS: tuple[str, ...] = ("target", "motion", "vote")
#: ``writeup/v2``'s fields a caller may send; the signer, date, via, key and signature are ours.
WRITEUP_FIELDS: tuple[str, ...] = (
    "target", "action", "writeup", "kind", "title", "url", "authors", "model", "arxiv",
    "journal", "doi",
)  # fmt: skip
RECORD_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")
YAML_SUFFIXES = (".yaml", ".yml")
#: The target directories the panel library reads (F24-R2 to R5).
PANEL_DIRS: tuple[str, ...] = (
    steward.DIR,
    panelmod.MOTIONS_DIR,
    panelmod.VOTES_DIR,
    writeup.DIR,
)


# --- the scratch tree -----------------------------------------------------------------------------


class _Copier:
    """Copies committed graph files into ``root`` under their graph paths, listing through the
    per-head listing cache (``session.listing``)."""

    def __init__(self, ctx: Context, root: Path) -> None:
        self.ctx = ctx
        self.root = root

    def copy(self, path: str) -> bytes | None:
        body = pending.optional_committed(self.ctx, path)
        if body is not None:
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        return body

    def copy_dir(self, directory: str) -> list[str]:
        names = [n for n in session.listing(self.ctx, directory) if n.endswith(YAML_SUFFIXES)]
        for name in names:
            self.copy(f"{directory}/{name}")
        return names


def materialise(
    ctx: Context, root: Path, target_ids: Iterable[str], *, unstewarded: bool = True
) -> Path:
    """Fill ``root`` with what ``opn_gate.panel`` and ``opn_gate.writeup`` read for each target:
    ``policy.json``, ``curators.json``, the target's stewards, motions, votes and write-up
    records, its words signatures (signed acts, which keep a steward from lapsing), and the
    ledger file of every login its steward records name (a prover votes uncounted). With
    ``unstewarded`` false, a target with no steward record gets nothing beyond its (empty)
    stewards directory, which is all the cap reads of it. Answers ``root``."""
    host = _Copier(ctx, root)
    host.copy(policymod.FILE)
    host.copy(modes.CURATORS_FILE)
    logins: set[str] = set()
    for target_id in target_ids:
        base = f"targets/{target_id}"
        (root / base).mkdir(parents=True, exist_ok=True)
        records = host.copy_dir(f"{base}/{steward.DIR}")
        if not records and not unstewarded:
            continue
        for directory in PANEL_DIRS[1:]:
            host.copy_dir(f"{base}/{directory}")
        host.copy_dir(f"{base}/{glosses.GLOSS_DIR}/{glosses.SIGNED_DIR}")
        for node in session.listing(ctx, f"{base}/nodes"):
            node_dir = f"{base}/nodes/{node}"
            host.copy_dir(f"{node_dir}/{glosses.GLOSS_DIR}/{glosses.SIGNED_DIR}")
            host.copy_dir(f"{node_dir}/{explainers.EXPLAINER_DIR}/{explainers.SIGNED_DIR}")
        for name in records:
            doc = _yaml(root / base / steward.DIR / name)
            login = doc.get("login") if isinstance(doc, dict) else None
            if isinstance(login, str) and steward.LOGIN_RE.match(login):
                logins.add(login)
    for login in sorted(logins):
        host.copy(f"{ledger.LEDGER_DIR}/{login}.json")
    return root


def _yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_bytes())
    except (OSError, yaml.YAMLError):
        return None


@contextmanager
def scratch(ctx: Context, target_ids: Iterable[str], *, unstewarded: bool = True) -> Iterator[Path]:
    """A materialised tree that lives for the request. A committed record the gate's readers
    cannot read is an outage, never a guess (C7)."""
    with tempfile.TemporaryDirectory(prefix="opn-panel-") as tmp:
        root = materialise(ctx, Path(tmp), target_ids, unstewarded=unstewarded)
        try:
            yield root
        except schemas.SchemaError as exc:
            raise ApiError(503, "graph-unreadable", str(exc)) from exc


class World:
    """What the rules read about one target on one day, over a materialised tree."""

    def __init__(self, ctx: Context, root: Path, target_id: str) -> None:
        self.root = root
        self.target_id = target_id
        self.target_dir = root / "targets" / target_id
        self.today = ctx.clock.now().astimezone(dt.UTC).date()
        self.signer = HostVerifier()
        self.curators = frozenset(session.curator_logins(ctx))
        self.settings = panelmod.current_settings(root)

    def members(self) -> tuple[str, ...]:
        return panelmod.members(
            self.root, self.target_id, self.today, settings=self.settings, signer=self.signer
        )

    def tallies(self) -> list[panelmod.Tally]:
        return panelmod.tallies(
            self.root, self.target_id, today=self.today, signer=self.signer, curators=self.curators
        )

    def voters(self, n: int) -> tuple[frozenset[str], frozenset[str]]:
        return panelmod.voters(
            self.root, self.target_id, n, signer=self.signer, curators=self.curators
        )

    def views(self) -> list[writeup.View]:
        return writeup.views(
            self.root, self.target_id, today=self.today, signer=self.signer, curators=self.curators
        )

    def next_path(self, directory: str) -> str:
        found = self.target_dir / directory
        taken = [
            int(m.group("n"))
            for p in (found.iterdir() if found.is_dir() else ())
            if (m := RECORD_RE.match(p.name)) is not None
        ]
        return f"targets/{self.target_id}/{directory}/{max(taken, default=0) + 1}.yaml"


# --- the shared write -----------------------------------------------------------------------------


def _signed_in(ctx: Context, request: Request, fields: dict[str, Any]) -> tuple[str, str]:
    """(login, target): the login a record is written as, and a target the graph has."""
    login = stewards.github_login(request.state.identity)
    target = fields.get("target")
    if not isinstance(target, str) or not target:
        raise stewards.bad("target is required: a target id", field="target")
    appends.known_target(ctx, target)
    return login, target


def _open(  # noqa: PLR0913 — one record, its home and its description
    ctx: Context,
    held: Identity,
    doc: dict[str, Any],
    schema: str,
    *,
    path: str,
    kind: str,
    subject: str,
) -> Response:
    """Sign, validate and open ``doc`` as an append, answering F23's receipt."""
    private, public = stewards.approval_key(ctx)
    signed_doc = stewards.sign_record(doc, private, public)
    appends.validated(signed_doc, schema)
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=yaml.safe_dump(signed_doc, sort_keys=False, allow_unicode=True),
        subject=subject,
        what=f"{kind} record",
        kind=kind,
        target_id=str(doc["target"]),
        node_id=None,
        written=json.dumps({k: v for k, v in doc.items() if k != "date"}, sort_keys=True),
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)


def _limit(ctx: Context, scope: str, login: str) -> None:
    """F24 §6: the same limits as ``POST /stewards``."""
    ratelimit.enforce(
        ctx, scope, login.casefold(), limit=ctx.settings.stewards_per_day, seconds=ratelimit.DAY_S
    )


def _shaped(doc: dict[str, Any], schema: str) -> None:
    """A record that cannot satisfy its schema is refused before the graph is read; the key and
    signature are placeholders here and are checked again once signed."""
    probe = {**doc, "key": "ssh-ed25519 AAAA", "signature": PLACEHOLDER_SIGNATURE}
    appends.validated(probe, schema)


PLACEHOLDER_SIGNATURE = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"


# --- POST /motions --------------------------------------------------------------------------------


async def post_motions(ctx: Context, request: Request) -> Response:
    """R8: open a motion as a member of the target's panel or a listed curator."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, MOTION_FIELDS)
    login, target_id = _signed_in(ctx, request, fields)
    kind, subject = fields.get("kind"), fields.get("subject")
    if kind not in panelmod.KINDS:
        raise stewards.bad(f"kind is one of {', '.join(panelmod.KINDS)}", field="kind")
    if not isinstance(subject, dict):
        raise stewards.bad("subject is an object, as motion/v1 sets out", field="subject")
    stewards.approval_key(ctx)
    _limit(ctx, "motion", login)
    with scratch(ctx, [target_id]) as root:
        world = World(ctx, root, target_id)
        doc = {
            "schema": panelmod.MOTION_SCHEMA,
            "target": target_id,
            "kind": kind,
            "subject": subject,
            "opened_by": login,
            "settings": world.settings.motion_settings(),
            "date": world.today.isoformat(),
            "via": VIA,
        }
        _shaped(doc, panelmod.MOTION_SCHEMA)
        members = world.members()
        if login not in members and login not in world.curators:
            raise ApiError(
                409,
                "not-panel-member",
                f"{login} is not on the panel of {target_id} and not a curator; only they open "
                "motions",
            )
        if kind == panelmod.INVITE:
            invitee = str(subject["login"])
            if invitee in members:
                raise ApiError(
                    409, "invitee-already-member", f"{invitee} is already on {target_id}'s panel"
                )
            if any(
                t.kind == panelmod.INVITE
                and t.state == panelmod.OPEN
                and t.subject.get("login") == invitee
                for t in world.tallies()
            ):
                raise ApiError(
                    409,
                    "invitation-open",
                    f"{invitee} already has an open invitation on {target_id}",
                )
        if kind == panelmod.VERIFY_WRITEUP:
            _record(world, int(subject["writeup"]))
        path = world.next_path(panelmod.MOTIONS_DIR)
    return _open(
        ctx, held, doc, panelmod.MOTION_SCHEMA, path=path, kind="motion",
        subject=f"motion {kind}: {login} on {target_id}",
    )  # fmt: skip


# --- POST /votes ----------------------------------------------------------------------------------


async def post_votes(ctx: Context, request: Request) -> Response:
    """R8: vote on an open motion, as a login whose vote the gate would read."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, VOTE_FIELDS)
    login, target_id = _signed_in(ctx, request, fields)
    n, vote = fields.get("motion"), fields.get("vote")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise stewards.bad("motion is the motion's number, an integer", field="motion")
    if vote not in (panelmod.YES, panelmod.NO):
        raise stewards.bad(f"vote is {panelmod.YES!r} or {panelmod.NO!r}", field="vote")
    stewards.approval_key(ctx)
    _limit(ctx, "vote", login)
    with scratch(ctx, [target_id]) as root:
        world = World(ctx, root, target_id)
        found = next((t for t in world.tallies() if t.n == n), None)
        if found is None:
            raise ApiError(404, "motion-unknown", f"{target_id} has no motion {n}")
        if world.today > found.closes:
            raise ApiError(409, "window-closed", f"motion {n} closed on {found.closes.isoformat()}")
        if found.state != panelmod.OPEN:
            raise ApiError(409, "motion-decided", f"motion {n} is already {found.state}")
        counted, uncounted = world.voters(n)
        if login not in counted | uncounted:
            raise ApiError(
                409,
                "voter-not-eligible",
                f"{login} was not on {target_id}'s panel when motion {n} was opened, so the gate "
                "would not read the vote",
            )
        doc = {
            "schema": panelmod.VOTE_SCHEMA,
            "target": target_id,
            "motion": n,
            "login": login,
            "vote": vote,
            "date": world.today.isoformat(),
            "via": VIA,
        }
        path = world.next_path(panelmod.VOTES_DIR)
    return _open(
        ctx, held, doc, panelmod.VOTE_SCHEMA, path=path, kind="vote",
        subject=f"vote {vote} on motion {n}: {login} on {target_id}",
    )  # fmt: skip


# --- POST /writeups -------------------------------------------------------------------------------


def _record(world: World, n: int) -> writeup.View:
    found = next((v for v in world.views() if v.n == n), None)
    if found is None:
        raise ApiError(
            409, "writeup-unknown", f"{world.target_id} has no write-up record {n} that counts"
        )
    return found


async def post_writeups(ctx: Context, request: Request) -> Response:
    """R8: record a write-up (anyone signed in), or act on one as a listed author."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, WRITEUP_FIELDS)
    login, target_id = _signed_in(ctx, request, fields)
    action = fields.get("action")
    stewards.approval_key(ctx)
    doc: dict[str, Any] = {"schema": writeup.SCHEMA_V2, "target": target_id, "action": action}
    doc |= {k: fields[k] for k in WRITEUP_FIELDS[2:] if fields.get(k) is not None}
    doc |= {"signer": login, "via": VIA}
    _limit(ctx, "writeup", login)
    with scratch(ctx, [target_id]) as root:
        world = World(ctx, root, target_id)
        doc["date"] = world.today.isoformat()
        _shaped(doc, writeup.SCHEMA_V2)
        if action != writeup.RECORD:
            found = _record(world, int(doc["writeup"]))
            if login not in found.authors:
                raise ApiError(
                    409, "not-an-author", f"{login} is not an author of write-up {found.n}"
                )
            if action == writeup.AUTHOR_SIGN and login in found.signed:
                raise ApiError(409, "already-signed", f"{login} has already signed {found.n}")
        path = world.next_path(writeup.DIR)
    return _open(
        ctx, held, doc, writeup.SCHEMA_V2, path=path, kind="writeup",
        subject=f"write-up {action}: {login} on {target_id}",
    )  # fmt: skip


# --- POST /stewards: the invitation and the cap ---------------------------------------------------


def admission_problem(
    ctx: Context, target_id: str, login: str, motion: int | None, *, self_admitted: bool
) -> None:
    """R8 on a commitment: ``self`` is refused once the target has a panel member
    (``invitation-required``); a ``motion`` must be a passed invitation of ``login``
    (``invitation-invalid``); and no login takes more stewardships than the cap
    (``steward-cap``). A curator-admitted commitment (reviewed admission) meets the cap only."""
    targets = session.target_ids(ctx)
    with scratch(ctx, targets, unstewarded=False) as root:
        materialise(ctx, root, [target_id])  # the asked-for target in full, stewards or none
        world = World(ctx, root, target_id)
        if motion is None:
            if self_admitted and world.members():
                raise ApiError(
                    409,
                    "invitation-required",
                    f"{target_id} has a steward panel: a new steward joins by its invitation "
                    "(a motion), named in the commitment",
                )
        else:
            why = panelmod.passed_invitation(
                root, target_id, motion, login, today=world.today, signer=world.signer,
                curators=world.curators,
            )  # fmt: skip
            if why is not None:
                raise ApiError(409, "invitation-invalid", why)
        held = panelmod.stewardships(
            root, login, world.today, settings=world.settings, signer=world.signer
        )
        if target_id not in held and len(held) >= world.settings.cap:
            raise ApiError(
                409,
                "steward-cap",
                f"{login} already stewards {len(held)} problems, the cap ({world.settings.cap})",
            )


# --- GET /session: what waits for the login -------------------------------------------------------


def awaiting(ctx: Context, login: str | None) -> dict[str, list[dict[str, Any]]]:
    """The open motions on which ``login``'s vote would count and they have not voted, and the
    passed invitations naming them that they have not accepted (F24-R8). Only targets with a
    motion are read in full."""
    out: dict[str, list[dict[str, Any]]] = {"votes": [], "invitations": []}
    if not login:
        return out
    targets = [t for t in session.target_ids(ctx) if session.listing(ctx, f"targets/{t}/motions")]
    if not targets:
        return out
    with scratch(ctx, targets) as root:
        for target_id in targets:
            world = World(ctx, root, target_id)
            voted = {v.motion for v in panelmod.load_votes(world.target_dir) if v.login == login}
            accepted = {
                r.admitted_by
                for r in steward.load(world.target_dir)
                if r.login == login and r.action == steward.COMMIT
            }
            members: tuple[str, ...] | None = None
            for t in world.tallies():
                if t.state == panelmod.OPEN and t.n not in voted and login in world.voters(t.n)[0]:
                    out["votes"].append(
                        {
                            "target": target_id,
                            "motion": t.n,
                            "kind": t.kind,
                            "subject": t.subject,
                            "closes": t.closes.isoformat(),
                        }
                    )
                elif (
                    t.state == panelmod.PASSED
                    and t.kind == panelmod.INVITE
                    and t.subject.get("login") == login
                    and f"{steward.MOTION_PREFIX}{t.n}" not in accepted
                ):
                    members = world.members() if members is None else members
                    if login not in members:
                        out["invitations"].append(
                            {"target": target_id, "motion": t.n, "note": t.subject.get("note")}
                        )
    return out
