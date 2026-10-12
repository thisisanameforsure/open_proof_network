"""The App's notice of review questions, and the ``/me/`` listing (F26-R15; D-9 v3.39).

When a review has questions waiting that no notice has named, the GitHub App posts **one**
comment for the batch on the review's tracking issue or pull request in the graph repository
(``review.yaml``'s ``tracking``: ``issue:<n>`` or ``pr:<n>``), @-mentioning the intent signer,
listing the new questions in words and linking the review page. GitHub then notifies the signer
by their own settings, so the network never holds an email address.

Which questions a notice has named is the service's own fact about what it said on the host, so
it is kept in the service's store (``reviewnotice#<target>``, a string set), never written to the
graph: the graph's history is the review's record, not the network's correspondence. An id is
remembered only once its comment was posted, so a refused post is tried again by the next run.

The intent signer (F26-R9, as ``reviews.intent_signer_holds`` decides it for the answer route):
the proposer the opening names, for a review a proposer opened; otherwise every active steward of
the target, one mention each. With none, nothing is posted (F26-Q5: "needs an intent signer" is
the review page's to say, not the notice's), and the ``/me/`` listing is empty for everyone.

Entry point: ``run(ctx, target_ids=None)``, also ``python -m opn_api.review_notice [target ...]``
with the service's configuration in the environment. The service has no periodic job and no
internal route a scheduler could call, so what calls it on a schedule is the owner's to wire
(F26-T11's report).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import TYPE_CHECKING, Any

from opn_api import reviews, session
from opn_api.githost import GitHostError

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger("opn_api")

#: ``review.yaml``'s ``tracking`` (review/v1): where the notices go.
TRACKING_RE = re.compile(r"^(?P<kind>issue|pr):(?P<n>[1-9][0-9]{0,9})$")
#: A GitHub login (review/v1's ``login``); a proposer named by anything else cannot be mentioned.
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}$")
#: What stops an ``@`` inside a question's words from mentioning anyone.
ZWSP = "\u200b"

POSTED = "posted"
NOTHING_NEW = "nothing-new"
NO_TRACKING = "no-tracking"
TRACKING_UNREADABLE = "tracking-unreadable"
NO_SIGNER = "no-intent-signer"
HOST_REFUSED = "host-refused"


def page_path(target_id: str) -> str:
    return f"/problems/{target_id}/review/"


def page_url(ctx: Context, target_id: str) -> str:
    """The review page on the site, from the configured origin (no hostname is written here,
    log 2026-09-09); the bare path when the service knows no site origin."""
    origin = ctx.settings.site_origin
    return f"{origin}{page_path(target_id)}" if origin else page_path(target_id)


def intent_signers(ctx: Context, target_id: str, head: dict[str, Any]) -> list[str]:
    """The logins ``reviews.intent_signer_holds`` accepts for this review, as a list: the
    proposer the opening names, or the target's active stewards in the order they became so."""
    opened_by = head.get("opened_by") or {}
    if opened_by.get("role") == "proposer":
        who = str(opened_by.get("identity") or "")
        return [who] if LOGIN_RE.match(who) else []
    return session.active_stewards(session.steward_records(ctx, target_id))


def reviewed_targets(ctx: Context, target_ids: list[str] | None) -> list[str]:
    """The targets (all of the index's, or those named) whose review directory holds an
    opening at ``main``; one listing per target, kept per head."""
    ids = session.target_ids(ctx) if target_ids is None else target_ids
    return [t for t in ids if "review.yaml" in session.listing(ctx, reviews.review_dir(t))]


def waiting(ctx: Context, target_id: str) -> list[tuple[str, str]]:
    """``(id, words)`` of every question no answer names, in record order (as
    ``opn_gate.review.questions_waiting`` reads them)."""
    answered = reviews.answered_questions(ctx, target_id)
    return [
        (qid, str(doc.get("question") or ""))
        for qid, doc in reviews.questions(ctx, target_id).items()
        if qid not in answered
    ]


def comment_body(
    ctx: Context, target_id: str, signers: list[str], questions: list[tuple[str, str]]
) -> str:
    mentions = " ".join(f"@{login}" for login in signers)
    n = len(questions)
    lines = [
        f"{mentions}: the formalization review of `{target_id}` has "
        f"{n} new question{'s' if n != 1 else ''} for its intent signer.",
        "",
    ]
    for i, (qid, text) in enumerate(questions, 1):
        words = " ".join(text.split()).replace("@", "@" + ZWSP)
        lines.append(f"{i}. {words} ({qid})")
    lines += [
        "",
        f"Answer on the review page, signed in with GitHub: {page_url(ctx, target_id)}",
    ]
    return "\n".join(lines) + "\n"


def outcome(target_id: str, reason: str, questions: list[str]) -> dict[str, Any]:
    return {
        "target": target_id,
        "posted": reason == POSTED,
        "reason": reason,
        "questions": questions,
    }


def notify(ctx: Context, target_id: str) -> dict[str, Any]:  # noqa: PLR0911 — one return per reason
    """One target: post one comment for the questions waiting that no notice has named."""
    head = reviews.opening(ctx, target_id)
    if head is None:
        return outcome(target_id, NOTHING_NEW, [])
    named = ctx.store.review_notified(target_id)
    new = [(qid, text) for qid, text in waiting(ctx, target_id) if qid not in named]
    ids = [qid for qid, _ in new]
    if not new:
        return outcome(target_id, NOTHING_NEW, [])
    tracking = head.get("tracking")
    if tracking is None:
        log.info(
            "review notice: %s has %d questions waiting and no tracking issue; none posted",
            target_id,
            len(ids),
        )
        return outcome(target_id, NO_TRACKING, ids)
    m = TRACKING_RE.match(str(tracking))
    if m is None:
        log.warning(
            "review notice: %s's tracking %r names no issue or pull request", target_id, tracking
        )
        return outcome(target_id, TRACKING_UNREADABLE, ids)
    signers = intent_signers(ctx, target_id, head)
    if not signers:
        log.info("review notice: %s's review has no intent signer to mention", target_id)
        return outcome(target_id, NO_SIGNER, ids)
    body = comment_body(ctx, target_id, signers, new)
    try:
        post = (
            ctx.githost.comment_on_issue  # F26-Q17: a plain issue needs Issues: write
            if m.group("kind") == "issue"
            else ctx.githost.comment_on_pull_request
        )
        post(ctx.settings.graph_repo, int(m.group("n")), body)
    except GitHostError as exc:
        log.warning("review notice: %s: no comment posted on %s: %s", target_id, tracking, exc)
        return outcome(target_id, HOST_REFUSED, ids)
    ctx.store.add_review_notified(target_id, set(ids))
    log.info("review notice: %s: %d questions named on %s", target_id, len(ids), tracking)
    return outcome(target_id, POSTED, ids)


def run(ctx: Context, target_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """R15: one notice per target with new questions; what happened, per reviewed target."""
    return [notify(ctx, t) for t in reviewed_targets(ctx, target_ids)]


def waiting_for(ctx: Context, login: str | None) -> list[dict[str, str]]:
    """``GET /session``'s ``reviews``: every question waiting on a review whose intent signer
    ``login`` is, whether or not a notice has named it yet (the page shows what is open)."""
    if not login:
        return []
    out: list[dict[str, str]] = []
    for target_id in reviewed_targets(ctx, None):
        head = reviews.opening(ctx, target_id)
        if head is None or login.casefold() not in {
            s.casefold() for s in intent_signers(ctx, target_id, head)
        }:
            continue
        out.extend(
            {"target": target_id, "question": qid, "text": text, "page": page_path(target_id)}
            for qid, text in waiting(ctx, target_id)
        )
    return out


def main(argv: list[str] | None = None, ctx: Context | None = None) -> int:
    """``python -m opn_api.review_notice [target ...]``: one run, its outcomes as JSON."""
    if ctx is None:
        from opn_api import app as appmod  # noqa: PLC0415 — the app imports the routes
        from opn_api import config  # noqa: PLC0415

        ctx = appmod.create_app(config.load()).state.context
        if ctx.missing:
            print(f"not configured: {', '.join(ctx.missing)}", file=sys.stderr)
            return 2
    targets = list(sys.argv[1:] if argv is None else argv) or None
    print(json.dumps(run(ctx, targets), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
