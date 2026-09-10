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
``OPN_API_FRONTIER_MAX_STALE_S``
    How long a fetched ``frontier.json`` is reused before its ETag is rechecked (R9).
    Default ``60``.
``OPN_API_WRITES_PER_HOUR`` / ``OPN_API_ACTIVE_CLAIMS`` / ``OPN_API_TOKENS_PER_LOGIN``
    Per-identity limits (R6). Defaults ``120`` / ``20`` / ``1`` (Q2).
``OPN_API_TOKEN_STARTS_PER_DAY``
    Per-source limit on ``GET /auth/github/start`` (R6). Default ``10``.
``OPN_API_PRECHECKS_PER_HOUR`` / ``OPN_API_ANONYMOUS_PRECHECKS_PER_DAY``
    Precheck limits per identity and per source address (F06-R8, R2). Defaults ``40`` / ``20``.
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
``OPN_API_LOG_LEVEL``
    Python logging level name. Default ``INFO``.
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
from typing import Any, Literal

StoreKind = Literal["memory", "dynamodb"]

DEFAULT_PARAMETER_PREFIX = "/opn/api/"
DEFAULT_PUBLIC_URL = "http://127.0.0.1:8000"
DEFAULT_GRAPH_REPO = "thisisanameforsure/open_proof_network_graph"
DEFAULT_GRAPH_BRANCH = "main"
DEFAULT_FRONTIER_MAX_STALE_S = 60
DEFAULT_WRITES_PER_HOUR = 120
DEFAULT_ACTIVE_CLAIMS = 20
DEFAULT_TOKENS_PER_LOGIN = 1
DEFAULT_TOKEN_STARTS_PER_DAY = 10
DEFAULT_PRECHECKS_PER_HOUR = 40
DEFAULT_ANONYMOUS_PRECHECKS_PER_DAY = 20
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
DEFAULT_LOG_LEVEL = "INFO"

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
    frontier_max_stale_s: int = DEFAULT_FRONTIER_MAX_STALE_S
    writes_per_hour: int = DEFAULT_WRITES_PER_HOUR
    active_claims: int = DEFAULT_ACTIVE_CLAIMS
    tokens_per_login: int = DEFAULT_TOKENS_PER_LOGIN
    token_starts_per_day: int = DEFAULT_TOKEN_STARTS_PER_DAY
    prechecks_per_hour: int = DEFAULT_PRECHECKS_PER_HOUR
    anonymous_prechecks_per_day: int = DEFAULT_ANONYMOUS_PRECHECKS_PER_DAY
    precheck_repo: str = DEFAULT_PRECHECK_REPO
    precheck_branch: str = DEFAULT_PRECHECK_BRANCH
    precheck_workflow: str = DEFAULT_PRECHECK_WORKFLOW
    precheck_key_path: str = DEFAULT_PRECHECK_KEY_PATH
    committer_name: str = DEFAULT_COMMITTER_NAME
    committer_email: str = DEFAULT_COMMITTER_EMAIL
    claim_ttl_min_h: int = DEFAULT_CLAIM_TTL_MIN_H
    claim_ttl_max_h: int = DEFAULT_CLAIM_TTL_MAX_H
    state_ttl_s: int = DEFAULT_STATE_TTL_S
    log_level: str = DEFAULT_LOG_LEVEL
    github_app_id: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = field(default=None, repr=False)
    github_private_key: str | None = field(default=None, repr=False)
    token_secret: str | None = field(default=None, repr=False)

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
        precheck_repo=env.get("OPN_API_PRECHECK_REPO", DEFAULT_PRECHECK_REPO),
        precheck_branch=env.get("OPN_API_PRECHECK_BRANCH", DEFAULT_PRECHECK_BRANCH),
        precheck_workflow=env.get("OPN_API_PRECHECK_WORKFLOW", DEFAULT_PRECHECK_WORKFLOW),
        precheck_key_path=env.get("OPN_API_PRECHECK_KEY_PATH", DEFAULT_PRECHECK_KEY_PATH),
        committer_name=env.get("OPN_API_COMMITTER_NAME", DEFAULT_COMMITTER_NAME),
        committer_email=env.get("OPN_API_COMMITTER_EMAIL", DEFAULT_COMMITTER_EMAIL),
        claim_ttl_min_h=ttl_min,
        claim_ttl_max_h=ttl_max,
        state_ttl_s=_int(env, "OPN_API_STATE_TTL_S", DEFAULT_STATE_TTL_S),
        log_level=env.get("OPN_API_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        github_app_id=env.get("OPN_API_GITHUB_APP_ID") or None,
        github_client_id=env.get("OPN_API_GITHUB_CLIENT_ID") or None,
        github_client_secret=env.get("OPN_API_GITHUB_CLIENT_SECRET") or None,
        github_private_key=env.get("OPN_API_GITHUB_PRIVATE_KEY") or None,
        token_secret=env.get("OPN_API_TOKEN_SECRET") or None,
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
