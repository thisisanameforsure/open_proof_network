"""The drafter's run (F20-T10; R15-R18, R20, R21; Q6-Q9): ``opn-gate gloss draft``.

What a run does, in order:

1. **Reads the coverage report** (``glosses.coverage``, R20) of the graph checkout and picks its
   subjects: in mode ``new``, every file or merged proof artifact with no chain at all (what a
   merge has just created, R17); in mode ``uncovered``, everything the report calls uncovered,
   including a gloss of since-changed text and a chain wholly withdrawn (the backfill, R21); or
   the files a list names, one graph path per line. A ``Context.lean`` is never drafted (it is
   covered by the statements it restates), and a root's statement is offered to the library,
   which skips it by rule (F20-Q11).
2. **Builds each subject** from files alone, running no Lean (§6): a gloss subject is the file's
   text at its hash and the current glosses of what it imports (a definition module for
   ``Defs.*``; the restated statements for the node's own ``Context``); an explainer subject is
   the artifact's committed ``outline/v1`` and nothing else. No outline is reported as such, and
   the artifact is never drafted from its source.
3. **Drafts** them with ``drafter.draft_many`` under the configured caps (C6), checking every draft
   with the gate's own R1-R6 (``modes.check_as_service``, the service's pre-flight) over a scratch
   copy of the checkout with the draft laid in.
4. **Posts** each draft to the service's ``POST /glosses`` with the drafter's token, as soon as it
   is drafted, so the service files it as an ``append/`` pull request with no author and the
   drafter's block (F20-T10's route rule).

The run report (JSON) is written after planning and again after every subject, so a run killed
mid-flight — a spend limit, a cancelled job — leaves what it did (engineering log, 2026-09-17).
``--dry-run`` plans and reports what would be drafted and why, and calls no model and posts
nothing: it is what the workflow does when a credential is missing (F20-Q7, the F12-Q16 shape).

Exit status: 0 when the run did what it could (a capped run is a batch, not a failure; anything
not drafted is named in the report); 1 when it was cut short by the model provider or the
service, or a draft the service was offered was refused; 2 for a usage error (a missing
credential, no graph). The token is read through ``opn_gate.config`` and never logged or reported.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from opn_gate import config, drafter, glosses, models, modes, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.models import ModelClient

log = logging.getLogger(__name__)

SUBJECT_MODES: tuple[str, ...] = ("new", "uncovered")
#: What a merge has just created: a file or artifact with no chain at all (R17).
NEW_REASONS = frozenset({glosses.NO_GLOSS, glosses.NO_EXPLAINER, glosses.ROOT_WITHOUT_INFORMAL})
GLOSS_KINDS = frozenset({*glosses.KIND_FILES, glosses.DEFINITION})
ARTIFACT_KINDS = frozenset({"proof", "alternate", "partial"})
CONTEXT_SKIP = "a Context.lean is covered by the statements it restates (R20); nothing to draft"
POST_TIMEOUT_S = 60.0
#: Service answers that say the next post would fail too: the token, the identity's limits, the
#: service itself. The run stops rather than spend tokens on drafts nothing will take.
STOPPING_STATUSES = frozenset({401, 403, 429})
GLOSSES_ROUTE = "/glosses"


class DraftRunError(ValueError):
    """The run cannot start as asked: a missing credential, a graph that is not a checkout."""


# --- the service seam ---------------------------------------------------------------------------


class PostError(RuntimeError):
    """The service could not be reached; the message carries no credential."""


@dataclass(frozen=True)
class Answer:
    status: int
    body: dict[str, Any]


class Poster(Protocol):
    def post(self, body: Mapping[str, Any]) -> Answer:
        """``POST /glosses`` with the drafter's token; raises ``PostError`` when unreachable."""


class HttpPoster:
    """The real seam: the service over the locked ``httpx``, the token in one header."""

    def __init__(
        self, base_url: str, token: str, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._url = base_url.rstrip("/") + GLOSSES_ROUTE
        self._token = token
        self._transport = transport

    def post(self, body: Mapping[str, Any]) -> Answer:
        try:
            with httpx.Client(timeout=POST_TIMEOUT_S, transport=self._transport) as http:
                response = http.post(
                    self._url, json=dict(body), headers={"Authorization": f"Bearer {self._token}"}
                )
        except httpx.HTTPError as exc:
            msg = f"the service could not be reached: {exc.__class__.__name__}"
            raise PostError(msg) from exc
        try:
            doc = response.json()
        except ValueError:
            doc = {}
        return Answer(response.status_code, doc if isinstance(doc, dict) else {})


def make_model(settings: config.Settings) -> ModelClient:
    """The model seam (R18): the one module that talks to a provider. Tests replace this."""
    if not settings.model_api_key:  # checked by ``run`` first; kept for a direct caller
        msg = "OPN_MODEL_API_KEY is not set"
        raise DraftRunError(msg)
    return models.HttpxModelClient(settings.model_api_key, settings.model)


def make_poster(base_url: str, token: str) -> Poster:
    """The service seam. Tests replace this."""
    return HttpPoster(base_url, token)


# --- planning -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Planned:
    key: str  # the graph path of the file or artifact: the coverage report's ``file``
    kind: str
    target: str
    node: str | None
    module: str | None
    reason: str  # why it is offered: the coverage report's reason

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "target": self.target,
            "node": self.node,
            "module": self.module,
            "reason": self.reason,
        }


@dataclass
class Plan:
    commit: str | None
    planned: list[Planned] = field(default_factory=list)
    passed_over: list[dict[str, str]] = field(default_factory=list)  # never offered, and why
    no_outline: list[dict[str, str]] = field(default_factory=list)
    subjects: list[drafter.Subject] = field(default_factory=list)
    keys: dict[str, str] = field(default_factory=dict)  # a subject's library key -> graph path
    problems: list[dict[str, str]] = field(default_factory=list)  # targets that do not load


def read_keys(path: Path) -> list[str]:
    """A named list: one graph path per line (``targets/<id>/nodes/<node>/Statement.lean``, as
    the coverage report's ``file`` names it); ``#`` starts a comment."""
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            out.append(entry)
    return out


def select(
    report: Mapping[str, Any], *, target: str | None, mode: str, keys: Sequence[str] | None
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """The coverage rows to offer, and the ones passed over with the reason each was."""
    rows = [r for r in report["subjects"] if target is None or r["target"] == target]
    passed: list[dict[str, str]] = []
    if keys is not None:
        by_file = {r["file"]: r for r in rows}
        chosen = []
        for key in dict.fromkeys(keys):
            row = by_file.get(key)
            if row is None:
                passed.append({"key": key, "reason": "not a Lean file or artifact on the graph"})
            elif row["covered"]:
                passed.append({"key": key, "reason": f"already covered: {row['by']}"})
            else:
                chosen.append(row)
    else:
        chosen = [
            r
            for r in rows
            if not r["covered"] and (mode == "uncovered" or r["reason"] in NEW_REASONS)
        ]
    offered = []
    for row in chosen:
        if row["kind"] == "context":
            passed.append({"key": row["file"], "reason": CONTEXT_SKIP})
        else:
            offered.append(row)
    return offered, passed


def _current_body(parent: Path, subject: glosses.Subject, file: Path) -> str | None:
    """The body of the current gloss of ``file`` that describes it as it stands, if any."""
    if not file.is_file():
        return None
    versions = [v for v in glosses.load_versions(parent) if v.subject == subject]
    found = glosses.chains(versions, glosses.withdrawn_versions(parent, glosses.GLOSS_DIR))
    text = schemas.content_hash(file.read_bytes())
    for chain in found:
        head = chain.current
        if head is not None and head.lean_hash == text:
            _, body = glosses.split_front_matter(head.path.read_text(encoding="utf-8"))
            return body.strip()
    return None


def imported_glosses(tg: graphmod.TargetGraph, lean_text: str) -> tuple[drafter.ImportedGloss, ...]:
    """The current glosses of what a file imports (R15): a definition module for ``Defs.*``, and
    for a node's own ``Context`` the statements it restates (the node's dependencies). Mathlib's
    modules carry no gloss; an import with none is simply absent."""
    out: list[drafter.ImportedGloss] = []
    for module in drafter.imports_of(lean_text):
        if module.startswith("Defs."):
            rel = module.removeprefix("Defs.").replace(".", "/") + ".lean"
            body = _current_body(
                tg.path, (glosses.DEFINITION, None, rel), tg.path / glosses.DEFS_DIR / rel
            )
            if body:
                out.append(drafter.ImportedGloss(module, body))
        elif module.startswith("Nodes.") and module.endswith(".Context"):
            node = module.removeprefix("Nodes.").removesuffix(".Context").strip("«»")
            facts = tg.nodes.get(node)
            for dep in facts.deps if facts is not None else ():
                dep_facts = tg.nodes.get(dep)
                if dep_facts is None:
                    continue
                file = dep_facts.path / glosses.KIND_FILES["statement"]
                body = _current_body(dep_facts.path, ("statement", dep, None), file)
                if body:
                    out.append(drafter.ImportedGloss(f"{dep} (statement)", body))
    return tuple(out)


def plan(
    graph: Path,
    *,
    commit: str | None,
    target: str | None,
    mode: str,
    keys: Sequence[str] | None,
) -> Plan:
    """What a run would draft, from the coverage report and the files alone (no Lean, no model)."""
    report = glosses.coverage(graph)
    offered, passed = select(report, target=target, mode=mode, keys=keys)
    result = Plan(commit=commit, passed_over=passed, problems=list(report["problems"]))
    loaded: dict[str, graphmod.TargetGraph] = {}
    for row in offered:
        tid = row["target"]
        if tid not in loaded:
            loaded[tid] = graphmod.load_target(graph, tid)
        tg = loaded[tid]
        planned = Planned(row["file"], row["kind"], tid, row["node"], row["module"], row["reason"])
        subject: drafter.Subject
        try:
            if row["kind"] in GLOSS_KINDS:
                text = (graph / row["file"]).read_text(encoding="utf-8")
                subject = drafter.gloss_subject(
                    graph,
                    tid,
                    row["kind"],
                    input_commit=commit or "",
                    node=row["node"],
                    module=row["module"],
                    root=tg.root,
                    imported=imported_glosses(tg, text),
                )
            elif row["kind"] in ARTIFACT_KINDS:
                proof = schemas.content_hash((graph / row["file"]).read_bytes())
                subject = drafter.explainer_subject(
                    graph, tid, str(row["node"]), proof, input_commit=commit or ""
                )
            else:
                result.passed_over.append({"key": row["file"], "reason": f"kind {row['kind']}"})
                continue
        except drafter.DrafterError as exc:
            if row["kind"] in ARTIFACT_KINDS:
                result.no_outline.append({"key": row["file"], "reason": f"no outline: {exc}"})
            else:
                result.passed_over.append({"key": row["file"], "reason": str(exc)})
            continue
        result.planned.append(planned)
        result.subjects.append(subject)
        result.keys[subject.key] = row["file"]
    return result


# --- the check (R16) ----------------------------------------------------------------------------


@contextmanager
def scratch_check(graph: Path, *, service_login: str) -> Iterator[drafter.Check]:
    """The gate's R1-R6 over a scratch copy of the checkout with each draft laid in, as the
    service would open it (``modes.check_as_service``); the draft is removed again after."""
    with tempfile.TemporaryDirectory(prefix="opn-draft-check-") as tmp:
        root = Path(tmp) / "graph"
        shutil.copytree(graph, root, ignore=shutil.ignore_patterns(".git"))

        def check(draft: drafter.Draft) -> list[Diagnostic]:
            try:
                return modes.check_as_service(
                    root, draft.path, draft.text.encode("utf-8"), service_login=service_login
                )
            finally:
                (root / draft.path).unlink(missing_ok=True)

        yield check


# --- posting ------------------------------------------------------------------------------------


def request_of(draft: drafter.Draft) -> dict[str, Any]:
    """The ``POST /glosses`` body for one draft: the words, the subject, and the drafter's block
    less its name (the service names the drafter from the token)."""
    subject = draft.subject
    front = draft.front_matter
    where: dict[str, Any]
    if isinstance(subject, drafter.GlossSubject):
        where = {"kind": subject.kind, "target_id": subject.target, "lean_hash": subject.lean_hash}
        if subject.kind == glosses.DEFINITION:
            where["module"] = subject.module
        else:
            where["node_id"] = subject.node
    else:
        where = {
            "kind": "proof",
            "target_id": subject.target,
            "node_id": subject.node,
            "proof": subject.proof,
        }
    block = front["drafter"]
    return {
        "subject": where,
        "text": draft.body,
        "supersedes": None,
        "licence": front["licence"],
        "drafter": {k: block[k] for k in ("model", "model_version", "input_commit")},
    }


# --- the run ------------------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunReport:
    """The run report, written to ``path`` after planning and after every subject."""

    path: Path
    head: dict[str, Any]
    plan: Plan
    drafting: drafter.Report | None = None
    posted: list[dict[str, Any]] = field(default_factory=list)
    post_failed: list[dict[str, Any]] = field(default_factory=list)
    service_stop: str | None = None
    finished: bool = False

    @property
    def cut_short(self) -> str | None:
        """Why the run was cut short by something other than its own caps, if it was."""
        if self.drafting is not None and self.drafting.stop_kind == "provider":
            return "provider"
        if self.service_stop is not None:
            return "service"
        return None

    def as_dict(self) -> dict[str, Any]:
        drafting = self.drafting.as_dict() if self.drafting is not None else None
        complete = (
            self.finished
            and self.drafting is not None
            and self.drafting.complete
            and not self.post_failed
            and not self.plan.no_outline
            and not self.plan.problems
        )
        return {
            **self.head,
            "updated": _now(),
            "finished": self.finished,
            "complete": complete,
            "cut_short": self.cut_short,
            "service_stop": self.service_stop,
            "planned": [p.as_dict() for p in self.plan.planned],
            "passed_over": self.plan.passed_over,
            "no_outline": self.plan.no_outline,
            "problems": self.plan.problems,
            "drafting": drafting,
            "posted": self.posted,
            "post_failed": self.post_failed,
        }

    def write(self) -> None:
        """Atomically: a reader (or a killed job's artifact step) never sees half a file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n", "utf-8")
        os.replace(tmp, self.path)


def run(  # noqa: PLR0913 — one keyword per choice the command takes
    graph: Path,
    settings: config.Settings,
    *,
    commit: str | None,
    target: str | None,
    mode: str,
    keys: Sequence[str] | None,
    report_path: Path,
    dry_run: bool,
    submit_url: str | None,
) -> RunReport:
    """Plan, then (unless ``dry_run``) draft, check and post; the report is on disk throughout."""
    if not dry_run:
        missing = [
            name
            for name, value in (
                ("OPN_MODEL_API_KEY", settings.model_api_key),
                ("OPN_DRAFTER_TOKEN", settings.drafter_token),
                ("--submit-url", submit_url),
            )
            if not value
        ]
        if missing:
            msg = (
                f"{', '.join(missing)} not set: a live run asks the model and posts to the service "
                "(F20-Q7). Run with --dry-run to see what would be drafted"
            )
            raise DraftRunError(msg)
        if commit is None:
            msg = f"{graph} is not a git checkout at a commit; a draft names the commit it read"
            raise DraftRunError(msg)
    head = {
        "command": "opn-gate gloss draft",
        "mode": "dry-run" if dry_run else "live",
        "graph_commit": commit,
        "target": target,
        "subjects": mode if keys is None else "list",
        "caps": {
            "max_subjects": settings.drafter_max_subjects,
            "token_budget": settings.drafter_token_budget,
        },
        "model": None if dry_run else settings.model,
        "drafter": settings.drafter_name,
        "prompt_version": drafter.PROMPT_VERSION,
        "started": _now(),
    }
    the_plan = plan(graph, commit=commit, target=target, mode=mode, keys=keys)
    report = RunReport(report_path, head, the_plan)
    report.write()
    if dry_run:
        report.finished = True
        report.write()
        return report
    assert submit_url is not None and settings.drafter_token is not None  # checked above
    model = make_model(settings)
    poster = make_poster(submit_url, settings.drafter_token)
    done: set[str] = set()

    def after_each(progress: drafter.Report) -> str | None:
        report.drafting = progress
        halt = None
        for draft in progress.drafted:
            if draft.hash in done:
                continue
            done.add(draft.hash)
            halt = _post(report, poster, draft, the_plan.keys.get(draft.subject.key, ""))
            if halt is not None:
                break
        report.write()
        return halt

    with scratch_check(graph, service_login=settings.service_login) as check:
        drafting = drafter.draft_many(
            the_plan.subjects,
            model=model,
            check=check,
            max_subjects=settings.drafter_max_subjects,
            token_budget=settings.drafter_token_budget,
            drafter_name=settings.drafter_name,
            licence=settings.drafter_licence,
            after_each=after_each,
        )
    report.drafting = drafting
    report.finished = True
    report.write()
    return report


def _post(report: RunReport, poster: Poster, draft: drafter.Draft, key: str) -> str | None:
    """Offer one draft to the service; a reason to stop the run when the next would fail too."""
    try:
        answer = poster.post(request_of(draft))
    except PostError as exc:
        report.post_failed.append({"key": key, "status": None, "error": str(exc)})
        report.service_stop = str(exc)
        return f"the service stopped the run: {exc}"
    if answer.status == 201:
        report.posted.append(
            {
                "key": key,
                "path": answer.body.get("path"),
                "hash": answer.body.get("hash"),
                "pr_url": answer.body.get("pr_url"),
            }
        )
        return None
    error = str(answer.body.get("error") or "")
    report.post_failed.append(
        {
            "key": key,
            "status": answer.status,
            "error": error,
            "message": str(answer.body.get("message") or "")[:500],
        }
    )
    if answer.status in STOPPING_STATUSES or answer.status >= 500:
        report.service_stop = f"{answer.status} {error}".strip()
        return f"the service stopped the run: {report.service_stop}"
    return None
