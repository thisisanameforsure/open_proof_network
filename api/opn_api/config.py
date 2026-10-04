"""The one config module for the api (conventions §1; constitution C6, C8; F05-R2).

Every environment variable and secret the api reads is read here and nowhere else. Non-secret
values have documented defaults; secrets default to ``None``, are never logged, and are listed
by ``Settings.missing()`` so the health check can refuse to serve a partial service (R13, C7).

Two doors (C8 item 3 and 5): locally the git-ignored ``.env`` populates the environment; on
Lambda the handler reads the SecureString parameters under ``OPN_API_PARAMETER_PREFIX`` through
``load_parameters`` and merges them over the function's environment before ``load``.

Variables (prefix ``OPN_API_``):

``OPN_API_STORE``
    ``memory`` (the in-process store; the local runner's default) or ``dynamodb``.
``OPN_API_TABLE_IDENTITIES`` / ``OPN_API_TABLE_TOKENS`` / ``OPN_API_TABLE_CLAIMS``
    The three DynamoDB tables (R12). Required when the store is ``dynamodb``; default ``None``.
``OPN_API_PARAMETER_PREFIX``
    Parameter Store path the secrets live under. Default ``/opn/api/``.
``OPN_API_PUBLIC_URL``
    The service's own origin, used for the OAuth redirect URI (R3).
    Default ``http://127.0.0.1:8000`` (the local runner).
``OPN_API_GRAPH_REPO`` / ``OPN_API_GRAPH_BRANCH``
    Where the committed ``frontier.json`` is read from (R7, R9). Defaults: the Stage 0 graph
    under the founder's account, ``main``.
``OPN_API_GUIDE_URL``
    The contributor guide's URL, as ``GET /`` and ``info.json`` (``info/v2``'s ``guide_url``,
    F05-T25) name it. Default: ``AGENTS.md`` in the graph repository at the graph branch, on the
    graph's host (D-35: contributors clone the graph only).
``OPN_API_FRONTIER_MAX_STALE_S``
    How long a fetched ``frontier.json`` is reused before its ETag is rechecked (R9).
    Default ``60``.
``OPN_API_WRITES_PER_HOUR`` / ``OPN_API_ACTIVE_CLAIMS`` / ``OPN_API_TOKENS_PER_LOGIN``
    Per-identity limits (R6). Defaults ``120`` / ``20`` / ``1`` (Q2).
``OPN_API_TOKEN_DAYS`` / ``OPN_API_TOKEN_CUTOVER``
    How long a write token is valid from its issue or its last renewal (D-19 v3.28, F05-T27),
    default ``90``; and the date (``YYYY-MM-DD``) a token issued before tokens carried an expiry
    is read as issued on, default ``2026-10-04`` — set it to the deploy day if that is later, so
    every such token gets a full window from the deploy (Q27).
``OPN_API_TOKEN_STARTS_PER_DAY``
    Per-source limit on ``GET /auth/github/start`` (R6). Default ``10``.
``OPN_API_PRECHECKS_PER_HOUR`` / ``OPN_API_ANONYMOUS_PRECHECKS_PER_DAY``
    Precheck limits per identity and per source address (F06-R8, R2). Defaults ``40`` / ``20``.
``OPN_API_PROPOSALS_PER_DAY``
    Node proposals per identity per day (F08 §6; D-29's identity-layer bound). Default ``40``.
``OPN_API_OPEN_PRS_PER_IDENTITY`` / ``OPN_API_OPEN_PRS_GLOBAL``
    Pull requests the service may hold open on the graph per pseudonym, and in all (F07-T67).
    Defaults ``10`` / ``150``, not yet signed off by the owner.
``OPN_API_PRECHECK_REPO`` / ``OPN_API_PRECHECK_BRANCH`` / ``OPN_API_PRECHECK_WORKFLOW``
    The scratch repository job branches are pushed to, the branch they are based on, and the
    workflow file dispatched there (F06-R3; D-35). Defaults: the Stage 0 scratch repo under the
    founder's account, ``main``, ``precheck.yml``.
``OPN_API_PRECHECK_KEY_PATH``
    Where the precheck public key is committed in the graph, against which a downloaded
    attestation's signature is verified (F06-R5; C8 item 2). Default ``keys/precheck.pub``.
``OPN_API_COMMITTER_NAME`` / ``OPN_API_COMMITTER_EMAIL``
    How the App signs a submission commit as committer (F07-R2). Defaults name the Stage 0 App.
``OPN_API_CLAIM_TTL_MIN_H`` / ``OPN_API_CLAIM_TTL_MAX_H``
    The D-25 flat caps (R7). Defaults ``1`` / ``168``.
``OPN_API_STATE_TTL_S``
    Lifetime of an OAuth state nonce and of the identity proof it yields (§7). Default ``600``.
``OPN_API_MAX_BODY_BYTES``
    The largest request body the api accepts, in bytes; anything larger is refused with a 413
    ``body-too-large`` before any parsing (F05 §6, Q7). Default ``1048576`` (1 MiB), above
    the 512 KiB precheck bundle (F06 §6) with room for its JSON envelope.
``OPN_API_LOG_LEVEL``
    Python logging level name. Default ``INFO``.
``OPN_API_AXLE_URL``
    The hosted fast checker's origin (F13-R3; D-4 v3.14). Default
    ``https://axle.axiommath.ai``. Keyless at Stage 0 (F13-Q5): no secret is read for it.
``OPN_API_CHECK_TIMEOUT_S``
    The per-call budget handed to the checker, in seconds (F13 §6). Default ``60``.
``OPN_API_CHECKS_PER_HOUR`` / ``OPN_API_ANONYMOUS_CHECKS_PER_DAY``
    Fast-check limits per identity and per source address (F13-R8). Defaults ``600`` / ``200``.
``OPN_API_CHECK_MAX_BYTES``
    The largest Lean text ``POST /check`` forwards (F13-R7). Default ``200000``.
``OPN_API_CHECK_CONCURRENCY``
    Checks in flight to the hosted service per process (F13-R8, Q8). Default ``8``, under
    AXLE's ten concurrent keyless requests.
``OPN_API_PULL_MAX_STALE_S``
    How long a pull request's live state (``GET /submissions/<id>``) is reused before the host
    is asked again (F07-T47). Default ``180``: a read is three or four API calls, the queue moves
    at about three minutes a merge, and at 60 s twenty open pull requests polled by a few agents
    spent the App's whole hourly budget.
``OPN_API_PULL_LISTING_MAX_STALE_S``
    How long the open pull-request listing ``GET /submissions.json`` reconciles the queue against
    is reused (F07-T47). Default ``60``: it is one call for the whole queue.
``OPN_API_HOST_BUDGET_RESERVE``
    The App's remaining hourly calls at or below which the service stops spending the host on
    unauthenticated reads and serves their cached state as stale (F07-T47), so pollers cannot
    starve the writes that open and close pull requests. Default ``200``; ``0`` keeps no reserve.
``OPN_API_RECONCILE_CONCURRENCY``
    Pull-request lookups ``GET /submissions.json`` makes at once while it reconciles the open
    records against the host (F07-T39, Q47). Default ``8``; each lookup is three or four GitHub API
    calls, and the App's rate budget is per hour, not per second.
``OPN_API_NETWORK_REPO``
    Where this repository lives on the host, so a target's pinned ``network_commit`` can be
    compared with ``OPN_API_USES_FROM`` (F08-T26). Default the Stage 0 network repository.
``OPN_API_USES_FROM``
    The network commit from which the gate understands use lines (F08-R21, Q39 option (a)): a
    target whose ``gate-spec.json`` pins this commit or a descendant of it takes a proof with
    use lines, and the service then reads them as the gate does. Default empty: no target
    understands uses, and a use line is ``imports-differ`` everywhere, as before T26.
``OPN_API_ANNEX_STEPS_FROM``
    The network commit from which the gate takes a stepped annex (F18-R6, D-31 v3.26:
    ``annex/v2``'s ``steps``), compared as ``OPN_API_USES_FROM`` is. ``POST /annexes`` writes
    ``steps`` only for a target whose pin is this commit or a descendant of it, since an older
    gate refuses an ``annex/v2`` append. Default empty: no target takes steps, and an annex
    without them is written as ``annex/v1``, as before F18-T5.
``OPN_API_DRAFTER_PSEUDONYM``
    The pseudonym of the network's drafter identity (F20-Q6, T10): the one identity whose
    ``POST /glosses`` files a *draft* — no ``author``, and a ``drafter`` block naming it, its
    model and the graph commit its input was read at. Default empty: no identity is the drafter,
    and a ``drafter`` block is refused for everyone. Set it only after the owner has created that
    identity himself, so nobody else can hold the name first (pseudonyms are unique).
``OPN_API_GITHUB_APP_ID`` / ``OPN_API_GITHUB_CLIENT_ID``
    The GitHub App's ids (not secret, but issued with the App, so they travel with its secrets).
``OPN_API_GITHUB_CLIENT_SECRET`` / ``OPN_API_GITHUB_PRIVATE_KEY``
    **Secret.** The App's OAuth client secret and private key (C8 item 3).
``OPN_API_TOKEN_SECRET``
    **Secret.** The salt every stored token hash uses (R4).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import date
from typing import Any, Literal

StoreKind = Literal["memory", "dynamodb"]

DEFAULT_PARAMETER_PREFIX = "/opn/api/"
DEFAULT_PUBLIC_URL = "http://127.0.0.1:8000"
DEFAULT_GRAPH_REPO = "thisisanameforsure/open_proof_network_graph"
DEFAULT_GRAPH_BRANCH = "main"
#: The web host of the graph repository (the host the ``GitHost`` seam talks to, not this
#: deployment's own hostname, which only configuration names).
GRAPH_HOST_WEB = "https://github.com"
GUIDE_FILE = "AGENTS.md"


def default_guide_url(graph_repo: str, graph_branch: str) -> str:
    """The guide in the graph repository, the one place every contributor reads (D-35)."""
    return f"{GRAPH_HOST_WEB}/{graph_repo}/blob/{graph_branch}/{GUIDE_FILE}"


DEFAULT_NETWORK_REPO = "thisisanameforsure/open_proof_network"  # F08-T26
DEFAULT_USES_FROM = ""  # F08-T26: no target understands uses until a commit is named
DEFAULT_ANNEX_STEPS_FROM = ""  # F18-T5: no target takes a stepped annex until a commit is named
DEFAULT_FRONTIER_MAX_STALE_S = 60
DEFAULT_WRITES_PER_HOUR = 120
DEFAULT_ACTIVE_CLAIMS = 20
DEFAULT_TOKENS_PER_LOGIN = 1
DEFAULT_TOKEN_STARTS_PER_DAY = 10
DEFAULT_PRECHECKS_PER_HOUR = 40
DEFAULT_ANONYMOUS_PRECHECKS_PER_DAY = 20
DEFAULT_PROPOSALS_PER_DAY = 40  # F08 §6
DEFAULT_OPEN_PRS_PER_IDENTITY = 10  # F07-T67; awaiting the owner's sign-off
DEFAULT_OPEN_PRS_GLOBAL = 150  # F07-T67; awaiting the owner's sign-off
DEFAULT_PRECHECK_REPO = "thisisanameforsure/open_proof_network_precheck"
DEFAULT_PRECHECK_BRANCH = "main"
DEFAULT_PRECHECK_WORKFLOW = "precheck.yml"
DEFAULT_PRECHECK_KEY_PATH = "keys/precheck.pub"
# The App as git sees it (F07-R2). GitHub does *not* fill the committer in when the Git Data
# API is given an author and no committer — it copies the author — so the App names itself.
DEFAULT_COMMITTER_NAME = "open-proof-network[bot]"
DEFAULT_COMMITTER_EMAIL = "327070898+open-proof-network[bot]@users.noreply.github.com"
DEFAULT_CLAIM_TTL_MIN_H = 1
DEFAULT_CLAIM_TTL_MAX_H = 168
DEFAULT_STATE_TTL_S = 600
DEFAULT_MAX_BODY_BYTES = 1024 * 1024  # F05 §6: above bundles.MAX_BUNDLE_BYTES (512 KiB)
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_AXLE_URL = "https://axle.axiommath.ai"  # F13-R3
DEFAULT_CHECK_TIMEOUT_S = 20  # F13 §6, T13: inside the function's 29 s, never above it
DEFAULT_CHECKS_PER_HOUR = 600  # F13-R8
DEFAULT_ANONYMOUS_CHECKS_PER_DAY = 200  # F13-R8
DEFAULT_CHECK_MAX_BYTES = 200_000  # F13-R7
DEFAULT_CHECK_CONCURRENCY = 8  # F13-R8, Q8
DEFAULT_RECONCILE_CONCURRENCY = 8  # F07-T39, Q47
DEFAULT_PULL_MAX_STALE_S = 180  # F07-T47
DEFAULT_PULL_LISTING_MAX_STALE_S = 60  # F07-T47
DEFAULT_HOST_BUDGET_RESERVE = 200  # F07-T47

# --- audit 2026-10-04: reads that spend the host or the store (F07-T68, F05-T20) ---------------
#: OPN_API_PRECHECK_POLL_MIN_S: the least time between two host reads made by polls of one
#: running precheck job (``GET /precheck/<id>``); a poll inside it answers the record as it is.
DEFAULT_PRECHECK_POLL_MIN_S = 10  # F07-T68
#: OPN_API_VERDICT_RETRY_S: how long a failed read of a refused pull request's gate verdict is
#: remembered before the host is asked again (F07-T68).
DEFAULT_VERDICT_RETRY_S = 60  # F07-T68
#: OPN_API_CLAIMS_MAX_STALE_S: how long the claims registry (``/frontier.json``,
#: ``/claims.json``) is reused before the claims table is scanned again; a claim or a release
#: through this process invalidates it at once (F05-T20).
DEFAULT_CLAIMS_MAX_STALE_S = 30  # F05-T20

# --- audit 2026-10-04: write tokens lapse unless renewed (F05-T27; D-19 v3.28, Q27) ------------
#: OPN_API_TOKEN_DAYS: how long a write token is valid from its issue or its last renewal.
DEFAULT_TOKEN_DAYS = 90
#: OPN_API_TOKEN_CUTOVER: the date (YYYY-MM-DD, UTC midnight) a token issued before tokens carried
#: an expiry is read as issued on, so it gets a full window from the deploy that introduced
#: expiry rather than lapsing at once. Set it to the deploy day if that is later than this.
DEFAULT_TOKEN_CUTOVER = "2026-10-04"  # noqa: S105 — a date, not a secret

# Parameter Store name (under the prefix) -> the variable it populates (C8 item 3).
PARAMETERS: dict[str, str] = {
    "github-app-id": "OPN_API_GITHUB_APP_ID",
    "github-client-id": "OPN_API_GITHUB_CLIENT_ID",
    "github-client-secret": "OPN_API_GITHUB_CLIENT_SECRET",
    "github-private-key": "OPN_API_GITHUB_PRIVATE_KEY",
    "token-secret": "OPN_API_TOKEN_SECRET",
}
SECRET_FIELDS: tuple[str, ...] = ("github_client_secret", "github_private_key", "token_secret")
TABLE_FIELDS: tuple[str, ...] = ("table_identities", "table_tokens", "table_claims")


class ConfigError(ValueError):
    """A configured value is not acceptable. Raised at load time, never later (C7)."""


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the api's configuration."""

    store: StoreKind = "memory"
    table_identities: str | None = None
    table_tokens: str | None = None
    table_claims: str | None = None
    parameter_prefix: str = DEFAULT_PARAMETER_PREFIX
    public_url: str = DEFAULT_PUBLIC_URL
    graph_repo: str = DEFAULT_GRAPH_REPO
    graph_branch: str = DEFAULT_GRAPH_BRANCH
    network_repo: str = DEFAULT_NETWORK_REPO
    uses_from: str = DEFAULT_USES_FROM
    annex_steps_from: str = DEFAULT_ANNEX_STEPS_FROM
    frontier_max_stale_s: int = DEFAULT_FRONTIER_MAX_STALE_S
    writes_per_hour: int = DEFAULT_WRITES_PER_HOUR
    active_claims: int = DEFAULT_ACTIVE_CLAIMS
    tokens_per_login: int = DEFAULT_TOKENS_PER_LOGIN
    token_starts_per_day: int = DEFAULT_TOKEN_STARTS_PER_DAY
    prechecks_per_hour: int = DEFAULT_PRECHECKS_PER_HOUR
    anonymous_prechecks_per_day: int = DEFAULT_ANONYMOUS_PRECHECKS_PER_DAY
    proposals_per_day: int = DEFAULT_PROPOSALS_PER_DAY
    open_prs_per_identity: int = DEFAULT_OPEN_PRS_PER_IDENTITY
    open_prs_global: int = DEFAULT_OPEN_PRS_GLOBAL
    precheck_repo: str = DEFAULT_PRECHECK_REPO
    precheck_branch: str = DEFAULT_PRECHECK_BRANCH
    precheck_workflow: str = DEFAULT_PRECHECK_WORKFLOW
    precheck_key_path: str = DEFAULT_PRECHECK_KEY_PATH
    committer_name: str = DEFAULT_COMMITTER_NAME
    committer_email: str = DEFAULT_COMMITTER_EMAIL
    claim_ttl_min_h: int = DEFAULT_CLAIM_TTL_MIN_H
    claim_ttl_max_h: int = DEFAULT_CLAIM_TTL_MAX_H
    state_ttl_s: int = DEFAULT_STATE_TTL_S
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    log_level: str = DEFAULT_LOG_LEVEL
    axle_url: str = DEFAULT_AXLE_URL
    check_timeout_s: int = DEFAULT_CHECK_TIMEOUT_S
    checks_per_hour: int = DEFAULT_CHECKS_PER_HOUR
    anonymous_checks_per_day: int = DEFAULT_ANONYMOUS_CHECKS_PER_DAY
    check_max_bytes: int = DEFAULT_CHECK_MAX_BYTES
    check_concurrency: int = DEFAULT_CHECK_CONCURRENCY
    reconcile_concurrency: int = DEFAULT_RECONCILE_CONCURRENCY
    pull_max_stale_s: int = DEFAULT_PULL_MAX_STALE_S
    pull_listing_max_stale_s: int = DEFAULT_PULL_LISTING_MAX_STALE_S
    host_budget_reserve: int = DEFAULT_HOST_BUDGET_RESERVE
    github_app_id: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = field(default=None, repr=False)
    github_private_key: str | None = field(default=None, repr=False)
    token_secret: str | None = field(default=None, repr=False)
    # --- audit 2026-10-04 (F07-T68, F05-T20) ---
    precheck_poll_min_s: int = DEFAULT_PRECHECK_POLL_MIN_S
    verdict_retry_s: int = DEFAULT_VERDICT_RETRY_S
    claims_max_stale_s: int = DEFAULT_CLAIMS_MAX_STALE_S
    # --- audit 2026-10-04 (F05-T25) ---
    guide_url: str = default_guide_url(DEFAULT_GRAPH_REPO, DEFAULT_GRAPH_BRANCH)
    # --- audit 2026-10-04 (F05-T27) ---
    token_days: int = DEFAULT_TOKEN_DAYS
    token_cutover: str = DEFAULT_TOKEN_CUTOVER
    # --- F20-T10: the drafter's identity (Q6) ---
    drafter_pseudonym: str = ""

    def __repr__(self) -> str:  # secrets never appear in a repr or a log (C8)
        parts = []
        for f in fields(self):
            value = getattr(self, f.name)
            shown = ("<set>" if value else None) if f.name in SECRET_FIELDS else repr(value)
            parts.append(f"{f.name}={shown}")
        return "Settings(" + ", ".join(parts) + ")"

    def missing(self) -> list[str]:
        """Every table name or parameter the service cannot run without (R13), by variable."""
        out: list[str] = []
        if self.store == "dynamodb":
            out.extend(_var(f) for f in TABLE_FIELDS if getattr(self, f) is None)
        out.extend(
            _var(f)
            for f in ("github_app_id", "github_client_id", *SECRET_FIELDS)
            if not getattr(self, f)
        )
        return out

    def rate_limit_policy(self) -> dict[str, Any]:
        """The policy in force, as ``info.json`` publishes it (R6; D-28 ``server_info``)."""
        return {
            "writes_per_hour": self.writes_per_hour,
            "active_claims": self.active_claims,
            "tokens_per_github_login": self.tokens_per_login,
            "token_starts_per_address_per_day": self.token_starts_per_day,
            "prechecks_per_hour": self.prechecks_per_hour,
            "anonymous_prechecks_per_address_per_day": self.anonymous_prechecks_per_day,
            "proposals_per_day": self.proposals_per_day,
            "open_pull_requests_per_identity": self.open_prs_per_identity,
            "open_pull_requests_global": self.open_prs_global,
            "claim_ttl_hours": {"min": self.claim_ttl_min_h, "max": self.claim_ttl_max_h},
        }


def _var(field_name: str) -> str:
    return "OPN_API_" + field_name.upper()


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"{name} must be an integer, got {raw!r}"
        raise ConfigError(msg) from exc
    if value <= 0:
        msg = f"{name} must be positive, got {value}"
        raise ConfigError(msg)
    return value


def _date(env: Mapping[str, str], name: str, default: str) -> str:
    """A calendar date, ``YYYY-MM-DD``, refused at load time if it is not one (C7)."""
    raw = env.get(name, default).strip()
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        msg = f"{name} must be a date YYYY-MM-DD, got {raw!r}"
        raise ConfigError(msg) from exc
    if len(raw) != len("2026-10-04"):
        msg = f"{name} must be a date YYYY-MM-DD, got {raw!r}"
        raise ConfigError(msg)
    return raw


def _count(env: Mapping[str, str], name: str, default: int) -> int:
    """``_int`` for a value that may be zero (a reserve of none)."""
    raw = env.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"{name} must be an integer, got {raw!r}"
        raise ConfigError(msg) from exc
    if value < 0:
        msg = f"{name} must not be negative, got {value}"
        raise ConfigError(msg)
    return value


def _commit(env: Mapping[str, str], name: str) -> str:
    """A full commit id, or empty when unset (F08-T26). A short or malformed id is refused at
    load time: compared by ancestry, it would silently match nothing (C7)."""
    raw = env.get(name, "").strip().lower()
    if raw and (len(raw) != 40 or any(c not in "0123456789abcdef" for c in raw)):
        msg = f"{name} must be a full 40-character commit id, got {raw!r}"
        raise ConfigError(msg)
    return raw


def load(environ: Mapping[str, str] | None = None) -> Settings:
    """Build ``Settings`` from ``environ`` (default: the real process environment).

    Tests pass an explicit mapping; production code calls ``load()`` or passes the merged
    environment-plus-parameters mapping the Lambda handler builds. This is the only function in
    the api that touches ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    raw_store = env.get("OPN_API_STORE", "memory")
    store: StoreKind
    if raw_store == "memory":
        store = "memory"
    elif raw_store == "dynamodb":
        store = "dynamodb"
    else:
        msg = f"OPN_API_STORE must be 'memory' or 'dynamodb', got {raw_store!r}"
        raise ConfigError(msg)
    ttl_min = _int(env, "OPN_API_CLAIM_TTL_MIN_H", DEFAULT_CLAIM_TTL_MIN_H)
    ttl_max = _int(env, "OPN_API_CLAIM_TTL_MAX_H", DEFAULT_CLAIM_TTL_MAX_H)
    if ttl_min > ttl_max:
        msg = f"OPN_API_CLAIM_TTL_MIN_H ({ttl_min}) exceeds OPN_API_CLAIM_TTL_MAX_H ({ttl_max})"
        raise ConfigError(msg)
    return Settings(
        store=store,
        table_identities=env.get("OPN_API_TABLE_IDENTITIES") or None,
        table_tokens=env.get("OPN_API_TABLE_TOKENS") or None,
        table_claims=env.get("OPN_API_TABLE_CLAIMS") or None,
        parameter_prefix=env.get("OPN_API_PARAMETER_PREFIX", DEFAULT_PARAMETER_PREFIX),
        public_url=env.get("OPN_API_PUBLIC_URL", DEFAULT_PUBLIC_URL).rstrip("/"),
        graph_repo=env.get("OPN_API_GRAPH_REPO", DEFAULT_GRAPH_REPO),
        graph_branch=env.get("OPN_API_GRAPH_BRANCH", DEFAULT_GRAPH_BRANCH),
        network_repo=env.get("OPN_API_NETWORK_REPO", DEFAULT_NETWORK_REPO),
        uses_from=_commit(env, "OPN_API_USES_FROM"),
        annex_steps_from=_commit(env, "OPN_API_ANNEX_STEPS_FROM"),
        frontier_max_stale_s=_int(
            env, "OPN_API_FRONTIER_MAX_STALE_S", DEFAULT_FRONTIER_MAX_STALE_S
        ),
        writes_per_hour=_int(env, "OPN_API_WRITES_PER_HOUR", DEFAULT_WRITES_PER_HOUR),
        active_claims=_int(env, "OPN_API_ACTIVE_CLAIMS", DEFAULT_ACTIVE_CLAIMS),
        tokens_per_login=_int(env, "OPN_API_TOKENS_PER_LOGIN", DEFAULT_TOKENS_PER_LOGIN),
        token_starts_per_day=_int(
            env, "OPN_API_TOKEN_STARTS_PER_DAY", DEFAULT_TOKEN_STARTS_PER_DAY
        ),
        prechecks_per_hour=_int(env, "OPN_API_PRECHECKS_PER_HOUR", DEFAULT_PRECHECKS_PER_HOUR),
        anonymous_prechecks_per_day=_int(
            env, "OPN_API_ANONYMOUS_PRECHECKS_PER_DAY", DEFAULT_ANONYMOUS_PRECHECKS_PER_DAY
        ),
        proposals_per_day=_int(env, "OPN_API_PROPOSALS_PER_DAY", DEFAULT_PROPOSALS_PER_DAY),
        open_prs_per_identity=_int(
            env, "OPN_API_OPEN_PRS_PER_IDENTITY", DEFAULT_OPEN_PRS_PER_IDENTITY
        ),
        open_prs_global=_int(env, "OPN_API_OPEN_PRS_GLOBAL", DEFAULT_OPEN_PRS_GLOBAL),
        precheck_repo=env.get("OPN_API_PRECHECK_REPO", DEFAULT_PRECHECK_REPO),
        precheck_branch=env.get("OPN_API_PRECHECK_BRANCH", DEFAULT_PRECHECK_BRANCH),
        precheck_workflow=env.get("OPN_API_PRECHECK_WORKFLOW", DEFAULT_PRECHECK_WORKFLOW),
        precheck_key_path=env.get("OPN_API_PRECHECK_KEY_PATH", DEFAULT_PRECHECK_KEY_PATH),
        committer_name=env.get("OPN_API_COMMITTER_NAME", DEFAULT_COMMITTER_NAME),
        committer_email=env.get("OPN_API_COMMITTER_EMAIL", DEFAULT_COMMITTER_EMAIL),
        claim_ttl_min_h=ttl_min,
        claim_ttl_max_h=ttl_max,
        state_ttl_s=_int(env, "OPN_API_STATE_TTL_S", DEFAULT_STATE_TTL_S),
        max_body_bytes=_int(env, "OPN_API_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES),
        log_level=env.get("OPN_API_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        axle_url=env.get("OPN_API_AXLE_URL", DEFAULT_AXLE_URL).rstrip("/"),
        check_timeout_s=_int(env, "OPN_API_CHECK_TIMEOUT_S", DEFAULT_CHECK_TIMEOUT_S),
        checks_per_hour=_int(env, "OPN_API_CHECKS_PER_HOUR", DEFAULT_CHECKS_PER_HOUR),
        anonymous_checks_per_day=_int(
            env, "OPN_API_ANONYMOUS_CHECKS_PER_DAY", DEFAULT_ANONYMOUS_CHECKS_PER_DAY
        ),
        check_max_bytes=_int(env, "OPN_API_CHECK_MAX_BYTES", DEFAULT_CHECK_MAX_BYTES),
        check_concurrency=_int(env, "OPN_API_CHECK_CONCURRENCY", DEFAULT_CHECK_CONCURRENCY),
        reconcile_concurrency=_int(
            env, "OPN_API_RECONCILE_CONCURRENCY", DEFAULT_RECONCILE_CONCURRENCY
        ),
        pull_max_stale_s=_int(env, "OPN_API_PULL_MAX_STALE_S", DEFAULT_PULL_MAX_STALE_S),
        pull_listing_max_stale_s=_int(
            env, "OPN_API_PULL_LISTING_MAX_STALE_S", DEFAULT_PULL_LISTING_MAX_STALE_S
        ),
        host_budget_reserve=_count(env, "OPN_API_HOST_BUDGET_RESERVE", DEFAULT_HOST_BUDGET_RESERVE),
        github_app_id=env.get("OPN_API_GITHUB_APP_ID") or None,
        github_client_id=env.get("OPN_API_GITHUB_CLIENT_ID") or None,
        github_client_secret=env.get("OPN_API_GITHUB_CLIENT_SECRET") or None,
        github_private_key=env.get("OPN_API_GITHUB_PRIVATE_KEY") or None,
        token_secret=env.get("OPN_API_TOKEN_SECRET") or None,
        # --- audit 2026-10-04 (F07-T68, F05-T20) ---
        precheck_poll_min_s=_count(env, "OPN_API_PRECHECK_POLL_MIN_S", DEFAULT_PRECHECK_POLL_MIN_S),
        verdict_retry_s=_count(env, "OPN_API_VERDICT_RETRY_S", DEFAULT_VERDICT_RETRY_S),
        claims_max_stale_s=_count(env, "OPN_API_CLAIMS_MAX_STALE_S", DEFAULT_CLAIMS_MAX_STALE_S),
        # --- audit 2026-10-04 (F05-T27) ---
        token_days=_int(env, "OPN_API_TOKEN_DAYS", DEFAULT_TOKEN_DAYS),
        token_cutover=_date(env, "OPN_API_TOKEN_CUTOVER", DEFAULT_TOKEN_CUTOVER),
        drafter_pseudonym=env.get("OPN_API_DRAFTER_PSEUDONYM", "").strip(),
        # --- audit 2026-10-04 (F05-T25) ---
        guide_url=(
            env.get("OPN_API_GUIDE_URL", "").strip()
            or default_guide_url(
                env.get("OPN_API_GRAPH_REPO", DEFAULT_GRAPH_REPO),
                env.get("OPN_API_GRAPH_BRANCH", DEFAULT_GRAPH_BRANCH),
            )
        ),
    )


def load_parameters(prefix: str, *, client: Any | None = None) -> dict[str, str]:
    """Read the SecureStrings under ``prefix`` from Parameter Store, keyed by variable name.

    The Lambda handler merges the result over ``os.environ`` and passes it to ``load``; a
    parameter that is absent is simply absent (``missing()`` reports it). ``client`` is a boto3
    SSM client, injectable for tests.
    """
    if client is None:
        import boto3  # noqa: PLC0415 — present in the Lambda runtime; a dev dependency here

        client = boto3.client("ssm")
    found: dict[str, str] = {}
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Path": prefix, "WithDecryption": True}
        if token:
            kwargs["NextToken"] = token
        page = client.get_parameters_by_path(**kwargs)
        for p in page.get("Parameters", []):
            name = str(p["Name"]).removeprefix(prefix)
            if name in PARAMETERS:
                found[PARAMETERS[name]] = str(p["Value"])
        token = page.get("NextToken")
        if not token:
            return found


def environment_with_parameters(prefix: str) -> dict[str, str]:
    """``os.environ`` plus the parameters: the mapping the Lambda handler feeds to ``load``."""
    merged = dict(os.environ)
    merged.update(load_parameters(prefix))
    return merged
