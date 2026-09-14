"""The ``Store`` seam (conventions §1): the api's operational tables (C9; D-35).

Three tables (F05-R12): identities, tokens and claims. Everything here is rebuildable from the
graph without any verdict changing. The tokens table also carries the short-lived items that
have no table of their own — OAuth state nonces, identity proofs and rate-limit counters —
under key prefixes with a TTL attribute, so the stack stays at three tables.

``MemoryStore`` is the in-process implementation: the unit tests' fake and the local runner's
default. ``DynamoStore`` talks to DynamoDB through boto3, imported lazily because boto3 is a dev
dependency here and part of the Lambda runtime there.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from opn_api import clock

KEY_TOKEN = "token#"  # noqa: S105 — a key prefix
KEY_STATE = "state#"
KEY_PROOF = "proof#"
KEY_RATE = "rate#"
KEY_JOB = "job#"
KEY_PSEUDONYM = "pseudonym#"
KEY_PROOF_REF = "proofref#"
# F07-T16: the pull requests the service opened. Three prefixes in the tokens table, no TTL, rather
# than a fourth table: a stack update adding a table would answer 503 under R13 between the deploy
# and the update.
KEY_SUBMISSION = "submission#"
KEY_SUBMISSION_PR = "submissionpr#"
KEY_SUBMISSIONS_OPEN = "submissions#open"
# F13-T4: one record per fast check, no TTL (Q3), in the tokens table like the submissions.
KEY_CHECK = "check#"


class ConflictError(Exception):
    """A uniqueness rule refused the write; ``what`` names the rule."""

    def __init__(self, what: str) -> None:
        super().__init__(what)
        self.what = what


@dataclass(frozen=True)
class Identity:
    id: str
    pseudonym: str
    proof_kind: str
    proof_reference: str
    created: str


@dataclass(frozen=True)
class TokenRecord:
    token_hash: str
    identity_id: str
    created: str
    revoked: bool = False


@dataclass(frozen=True)
class Claim:
    id: str
    node_id: str
    target_id: str
    identity_id: str
    created: str
    expires: str
    released: str | None = None


@dataclass(frozen=True)
class Submission:
    """A pull request the service opened on the graph (F07-T16): what it was, where it is, and —
    once a live read found it merged or closed — when that was seen and the state it was in, so
    a finished pull request never costs another host call.

    ``kind`` is the artifact type for ``POST /submissions`` (``proof``, ``partial``, …) and the
    record's kind for the other routes (``postmortem``, ``annex``, ``approach-record``,
    ``speculative``, ``variant``, ``witness``). ``node_id`` is ``None`` for a target-level record.
    Operational, not evidentiary (C9): the graph's attestations are the record of what merged.
    """

    id: str
    kind: str
    node_id: str | None
    target_id: str
    pr_number: int
    pr_url: str
    pseudonym: str
    precheck_job_id: str | None
    created: str
    closed: str | None = None
    final_state: dict[str, Any] | None = None


@dataclass(frozen=True)
class CheckLog:
    """One fast check (F13-R9): who asked, about what, where it went and how it ended — the
    content's hash and size, never the content (C9 v2, F13-Q3). ``caller`` is an identity id when
    ``caller_kind`` is ``identity`` and a keyed hash of the source address otherwise (Q4).
    ``outcome`` is ``answered`` or the refusal's code. Operational, never evidentiary."""

    id: str
    created: str
    caller_kind: str
    caller: str
    target_id: str
    node_id: str | None
    mode: str
    environment: str | None
    content_sha256: str
    content_bytes: int
    outcome: str
    okay: bool | None
    error_count: int | None
    lint: list[str]
    axle_request_id: str | None
    upstream_status: int | None
    latency_ms: int


class Store(Protocol):
    def check(self) -> list[str]:
        """Names of tables that cannot be reached; empty when healthy (R13)."""
        ...

    def put_identity(self, identity: Identity) -> None:
        """Atomic with the pseudonym (case-insensitive) and proof-reference uniqueness rules."""
        ...

    def get_identity(self, identity_id: str) -> Identity | None: ...

    def count_identities_by_proof(self, proof_kind: str, reference: str) -> int: ...

    def put_token(self, record: TokenRecord) -> None: ...

    def get_token(self, token_hash: str) -> TokenRecord | None: ...

    def put_job(self, job_id: str, record: dict[str, Any], expires: datetime) -> None:
        """A precheck job (F06-R3). Readable until ``expires``, unlike an ephemeral item."""
        ...

    def get_job(self, job_id: str) -> dict[str, Any] | None: ...

    def put_claim(self, claim: Claim) -> None: ...

    def get_claim(self, claim_id: str) -> Claim | None: ...

    def list_claims(self) -> list[Claim]: ...

    def put_ephemeral(self, key: str, data: dict[str, Any], expires: datetime) -> None: ...

    def take_ephemeral(self, key: str, now: datetime) -> dict[str, Any] | None:
        """Read and delete in one step (single use); ``None`` when absent or expired."""
        ...

    def bump_counter(self, key: str, expires: datetime) -> int:
        """Increment and return the counter at ``key``; it disappears after ``expires``."""
        ...

    def put_submission(self, submission: Submission) -> None:
        """Record an opened pull request, reachable by id and by number; open unless closed."""
        ...

    def get_submission(self, submission_id: str) -> Submission | None: ...

    def get_submission_by_pr(self, pr_number: int) -> Submission | None: ...

    def list_open_submissions(self) -> list[Submission]:
        """Every record no live read has found finished, by id (ULIDs sort by time)."""
        ...

    def close_submission(
        self, submission_id: str, *, closed: str, final_state: dict[str, Any]
    ) -> Submission | None:
        """Mark a record finished with the state that finished it; ``None`` when absent."""
        ...

    def put_check(self, record: CheckLog) -> None:
        """Record one fast check (F13-R9); a record is written once and never changed."""
        ...

    def get_check(self, check_id: str) -> CheckLog | None: ...


# --- memory ------------------------------------------------------------------------------------


@dataclass
class MemoryStore:
    identities: dict[str, Identity] = field(default_factory=dict)
    unique: set[str] = field(default_factory=set)
    tokens: dict[str, TokenRecord] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    ephemeral: dict[str, tuple[dict[str, Any], datetime]] = field(default_factory=dict)
    counters: dict[str, tuple[int, datetime]] = field(default_factory=dict)
    submissions: dict[str, Submission] = field(default_factory=dict)
    submissions_by_pr: dict[int, str] = field(default_factory=dict)
    open_submissions: set[str] = field(default_factory=set)
    checks: dict[str, CheckLog] = field(default_factory=dict)

    def check(self) -> list[str]:
        return []

    def put_identity(self, identity: Identity) -> None:
        keys = _unique_keys(identity)
        for key, what in keys:
            if key in self.unique:
                raise ConflictError(what)
        self.unique.update(k for k, _ in keys)
        self.identities[identity.id] = identity

    def get_identity(self, identity_id: str) -> Identity | None:
        return self.identities.get(identity_id)

    def count_identities_by_proof(self, proof_kind: str, reference: str) -> int:
        return sum(
            1
            for i in self.identities.values()
            if i.proof_kind == proof_kind and i.proof_reference == reference
        )

    def put_token(self, record: TokenRecord) -> None:
        self.tokens[record.token_hash] = record

    def get_token(self, token_hash: str) -> TokenRecord | None:
        return self.tokens.get(token_hash)

    def put_job(self, job_id: str, record: dict[str, Any], expires: datetime) -> None:
        self.jobs[job_id] = dict(record)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        found = self.jobs.get(job_id)
        return dict(found) if found is not None else None

    def put_claim(self, claim: Claim) -> None:
        self.claims[claim.id] = claim

    def get_claim(self, claim_id: str) -> Claim | None:
        return self.claims.get(claim_id)

    def list_claims(self) -> list[Claim]:
        return sorted(self.claims.values(), key=lambda c: c.id)

    def put_ephemeral(self, key: str, data: dict[str, Any], expires: datetime) -> None:
        self.ephemeral[key] = (dict(data), expires)

    def take_ephemeral(self, key: str, now: datetime) -> dict[str, Any] | None:
        item = self.ephemeral.pop(key, None)
        if item is None or item[1] <= now:
            return None
        return item[0]

    def bump_counter(self, key: str, expires: datetime) -> int:
        count, _ = self.counters.get(key, (0, expires))
        self.counters[key] = (count + 1, expires)
        return count + 1

    def put_submission(self, submission: Submission) -> None:
        self.submissions[submission.id] = submission
        self.submissions_by_pr[submission.pr_number] = submission.id
        if submission.closed is None:
            self.open_submissions.add(submission.id)
        else:
            self.open_submissions.discard(submission.id)

    def get_submission(self, submission_id: str) -> Submission | None:
        return self.submissions.get(submission_id)

    def get_submission_by_pr(self, pr_number: int) -> Submission | None:
        found = self.submissions_by_pr.get(pr_number)
        return self.submissions.get(found) if found is not None else None

    def list_open_submissions(self) -> list[Submission]:
        return [self.submissions[i] for i in sorted(self.open_submissions) if i in self.submissions]

    def close_submission(
        self, submission_id: str, *, closed: str, final_state: dict[str, Any]
    ) -> Submission | None:
        found = self.submissions.get(submission_id)
        if found is None:
            return None
        done = replace(found, closed=closed, final_state=dict(final_state))
        self.put_submission(done)
        return done

    def put_check(self, record: CheckLog) -> None:
        self.checks[record.id] = replace(record, lint=list(record.lint))

    def get_check(self, check_id: str) -> CheckLog | None:
        found = self.checks.get(check_id)
        return replace(found, lint=list(found.lint)) if found is not None else None


def _unique_keys(identity: Identity) -> list[tuple[str, str]]:
    return [
        (KEY_PSEUDONYM + identity.pseudonym.lower(), "pseudonym"),
        (KEY_PROOF_REF + identity.proof_kind + "#" + identity.proof_reference, "proof-reference"),
    ]


# --- dynamodb ----------------------------------------------------------------------------------


def _epoch(when: datetime) -> int:
    return int(when.timestamp())


def plain(value: Any) -> Any:
    """DynamoDB numbers come back as ``Decimal``; turn a read item back into plain JSON types.

    The seam's contract is that what goes in comes out (conventions §1), and the memory store
    honours it exactly — which is why nothing caught this until a job record read from DynamoDB
    was re-serialised into a pull-request body and ``json.dumps`` refused a Decimal. Integral
    values become ``int`` and the rest ``float``, which is what they were before boto3 saw them.
    """
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, set):
        return {plain(v) for v in value}
    return value


def storable(value: Any) -> Any:
    """``plain``'s inverse at the write side: turn plain JSON types into what boto3 will accept.

    boto3 refuses a ``float`` outright ("Float types are not supported"), so a record carrying one
    raised ``TypeError`` on DynamoDB while ``MemoryStore`` took it happily — the two halves of the
    seam disagreeing about what can be stored, which is the one thing a seam may not do
    (conventions §1, C7). The conversion goes through ``str`` rather than ``Decimal(value)``
    because ``Decimal(0.1)`` is the exact binary expansion, fifty-odd digits of it, while
    ``Decimal("0.1")`` is the number the caller wrote; ``plain`` then returns the same float, since
    ``str`` round-trips a Python float exactly.

    A non-finite float has no DynamoDB representation and is not valid JSON either, so it is
    refused here by name instead of reaching boto3 as a puzzle.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):  # NaN or ±inf
            msg = f"cannot store the non-finite number {value!r}"
            raise ValueError(msg)
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: storable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [storable(v) for v in value]
    if isinstance(value, set):
        return {storable(v) for v in value}
    return value


class DynamoStore:
    """The three tables (R12). Key layout:

    identities: ``id`` — an identity row, or a uniqueness marker (``pseudonym#<lower>``,
    ``proofref#<kind>#<ref>``) written in the same transaction as the identity (R4, R6).
    tokens: ``key`` — ``token#<hash>`` rows, plus ``state#``, ``proof#``, ``rate#`` and
    ``job#`` items carrying ``expires_at`` (the table's TTL attribute). A job is readable
    until it expires, unlike the single-use ephemeral items. Submissions (F07-T16) carry no
    TTL: ``submission#<ulid>`` is the record, ``submissionpr#<n>`` points a pull-request number at
    it, and ``submissions#open`` holds the open ids as a string set. Fast checks (F13-T4)
    are ``check#<ulid>`` records, also without TTL.
    claims: ``id`` — one row per claim; the registry is read by scan (Stage 0 volume).
    """

    def __init__(
        self, *, identities: str, tokens: str, claims: str, resource: Any | None = None
    ) -> None:
        if resource is None:
            import boto3  # noqa: PLC0415 — Lambda runtime / dev dependency

            resource = boto3.resource("dynamodb")
        self._client = resource.meta.client
        self._names = {"identities": identities, "tokens": tokens, "claims": claims}
        self._identities = resource.Table(identities)
        self._tokens = resource.Table(tokens)
        self._claims = resource.Table(claims)

    def check(self) -> list[str]:
        missing: list[str] = []
        for what, name in self._names.items():
            try:
                self._client.describe_table(TableName=name)
            except Exception:
                missing.append(f"{what} table {name!r}")
        return missing

    def put_identity(self, identity: Identity) -> None:
        table = self._names["identities"]
        items = [{"Put": {"TableName": table, "Item": asdict(identity)}}]
        for key, what in _unique_keys(identity):
            items.append(
                {
                    "Put": {
                        "TableName": table,
                        "Item": {"id": key, "what": what, "identity_id": identity.id},
                        "ConditionExpression": "attribute_not_exists(id)",
                    }
                }
            )
        try:
            self._client.transact_write_items(TransactItems=items)
        except self._client.exceptions.TransactionCanceledException as exc:
            reasons = exc.response.get("CancellationReasons", [])
            for index, reason in enumerate(reasons):
                if index > 0 and reason.get("Code") == "ConditionalCheckFailed":
                    raise ConflictError(_unique_keys(identity)[index - 1][1]) from exc
            raise

    def get_identity(self, identity_id: str) -> Identity | None:
        item = self._identities.get_item(Key={"id": identity_id}).get("Item")
        return _identity(item) if item and "pseudonym" in item else None

    def count_identities_by_proof(self, proof_kind: str, reference: str) -> int:
        key = KEY_PROOF_REF + proof_kind + "#" + reference
        return 1 if self._identities.get_item(Key={"id": key}).get("Item") else 0

    def put_token(self, record: TokenRecord) -> None:
        item = {"key": KEY_TOKEN + record.token_hash, **asdict(record)}
        self._tokens.put_item(Item=item)

    def get_token(self, token_hash: str) -> TokenRecord | None:
        item = self._tokens.get_item(Key={"key": KEY_TOKEN + token_hash}).get("Item")
        if not item:
            return None
        return TokenRecord(
            token_hash=str(item["token_hash"]),
            identity_id=str(item["identity_id"]),
            created=str(item["created"]),
            revoked=bool(item.get("revoked", False)),
        )

    def put_job(self, job_id: str, record: dict[str, Any], expires: datetime) -> None:
        self._tokens.put_item(
            Item={
                "key": KEY_JOB + job_id,
                "job": storable(record),
                "expires_at": _epoch(expires),
            }
        )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        item = self._tokens.get_item(Key={"key": KEY_JOB + job_id}).get("Item")
        job = item.get("job") if item else None
        # `plain`: a job record carries a whole attestation, which is re-serialised into a
        # pull-request body later (F07-R2). A Decimal in it is a 500 at that point, not here.
        return plain(dict(job)) if isinstance(job, dict) else None

    def put_claim(self, claim: Claim) -> None:
        self._claims.put_item(Item=asdict(claim))

    def get_claim(self, claim_id: str) -> Claim | None:
        item = self._claims.get_item(Key={"id": claim_id}).get("Item")
        return _claim(item) if item else None

    def list_claims(self) -> list[Claim]:
        out: list[Claim] = []
        kwargs: dict[str, Any] = {}
        while True:
            page = self._claims.scan(**kwargs)
            out.extend(_claim(i) for i in page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last:
                return sorted(out, key=lambda c: c.id)
            kwargs["ExclusiveStartKey"] = last

    def put_ephemeral(self, key: str, data: dict[str, Any], expires: datetime) -> None:
        self._tokens.put_item(
            Item={"key": key, "data": storable(data), "expires_at": _epoch(expires)}
        )

    def take_ephemeral(self, key: str, now: datetime) -> dict[str, Any] | None:
        # No guard: an unconditional DeleteItem reports an absent item as a response with no
        # ``Attributes``, never as an error, so there is no client error that means "no such
        # nonce". Anything DynamoDB raises here — throttling, a missing table, a permission —
        # is an outage and reaches the app's boundary as one (C7; F05-Q7), rather than reading
        # as an expired nonce and a 400.
        deleted = self._tokens.delete_item(Key={"key": key}, ReturnValues="ALL_OLD")
        item = deleted.get("Attributes")
        if not item or int(item.get("expires_at", 0)) <= _epoch(now):
            return None
        data = item.get("data")
        # `plain`, as in get_job: what went in comes back out, ints not Decimals.
        return plain(dict(data)) if isinstance(data, dict) else None

    def bump_counter(self, key: str, expires: datetime) -> int:
        updated = self._tokens.update_item(
            Key={"key": key},
            UpdateExpression="ADD #c :one SET expires_at = if_not_exists(expires_at, :exp)",
            ExpressionAttributeNames={"#c": "count"},
            ExpressionAttributeValues={":one": 1, ":exp": _epoch(expires)},
            ReturnValues="UPDATED_NEW",
        )
        return int(updated["Attributes"]["count"])

    # --- submissions (F07-T16): three key prefixes in the tokens table, no TTL -----------------

    def put_submission(self, submission: Submission) -> None:
        self._tokens.put_item(
            Item={"key": KEY_SUBMISSION + submission.id, "submission": storable(asdict(submission))}
        )
        self._tokens.put_item(
            Item={
                "key": KEY_SUBMISSION_PR + str(submission.pr_number),
                "submission_id": submission.id,
            }
        )
        self._open_index("DELETE" if submission.closed is not None else "ADD", submission.id)

    def _open_index(self, action: str, submission_id: str) -> None:
        """``ADD`` or ``DELETE`` one id in the open index's string set — atomic on DynamoDB's side,
        so two requests closing two records cannot lose each other's write."""
        self._tokens.update_item(
            Key={"key": KEY_SUBMISSIONS_OPEN},
            UpdateExpression=f"{action} #ids :one",
            ExpressionAttributeNames={"#ids": "ids"},
            ExpressionAttributeValues={":one": {submission_id}},
        )

    def get_submission(self, submission_id: str) -> Submission | None:
        item = self._tokens.get_item(Key={"key": KEY_SUBMISSION + submission_id}).get("Item")
        record = item.get("submission") if item else None
        return _submission(plain(dict(record))) if isinstance(record, dict) else None

    def get_submission_by_pr(self, pr_number: int) -> Submission | None:
        item = self._tokens.get_item(Key={"key": KEY_SUBMISSION_PR + str(pr_number)}).get("Item")
        found = item.get("submission_id") if item else None
        return self.get_submission(str(found)) if found else None

    def list_open_submissions(self) -> list[Submission]:
        item = self._tokens.get_item(Key={"key": KEY_SUBMISSIONS_OPEN}).get("Item") or {}
        out: list[Submission] = []
        for submission_id in sorted(str(i) for i in item.get("ids") or ()):
            found = self.get_submission(submission_id)
            if found is not None and found.closed is None:
                out.append(found)
        return out

    def close_submission(
        self, submission_id: str, *, closed: str, final_state: dict[str, Any]
    ) -> Submission | None:
        found = self.get_submission(submission_id)
        if found is None:
            return None
        done = replace(found, closed=closed, final_state=dict(final_state))
        self.put_submission(done)
        return done

    # --- fast checks (F13-T4): one key prefix in the tokens table, no TTL ---------------------

    def put_check(self, record: CheckLog) -> None:
        self._tokens.put_item(
            Item={"key": KEY_CHECK + record.id, "check": storable(asdict(record))}
        )

    def get_check(self, check_id: str) -> CheckLog | None:
        item = self._tokens.get_item(Key={"key": KEY_CHECK + check_id}).get("Item")
        record = item.get("check") if item else None
        return _check(plain(dict(record))) if isinstance(record, dict) else None


def _identity(item: dict[str, Any]) -> Identity:
    return Identity(
        id=str(item["id"]),
        pseudonym=str(item["pseudonym"]),
        proof_kind=str(item["proof_kind"]),
        proof_reference=str(item["proof_reference"]),
        created=str(item["created"]),
    )


def _claim(item: dict[str, Any]) -> Claim:
    return Claim(
        id=str(item["id"]),
        node_id=str(item["node_id"]),
        target_id=str(item["target_id"]),
        identity_id=str(item["identity_id"]),
        created=str(item["created"]),
        expires=str(item["expires"]),
        released=str(item["released"]) if item.get("released") else None,
    )


def _submission(record: dict[str, Any]) -> Submission:
    final = record.get("final_state")
    return Submission(
        id=str(record["id"]),
        kind=str(record["kind"]),
        node_id=str(record["node_id"]) if record.get("node_id") is not None else None,
        target_id=str(record["target_id"]),
        pr_number=int(record["pr_number"]),
        pr_url=str(record["pr_url"]),
        pseudonym=str(record["pseudonym"]),
        precheck_job_id=(
            str(record["precheck_job_id"]) if record.get("precheck_job_id") is not None else None
        ),
        created=str(record["created"]),
        closed=str(record["closed"]) if record.get("closed") is not None else None,
        final_state=dict(final) if isinstance(final, dict) else None,
    )


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _check(record: dict[str, Any]) -> CheckLog:
    okay = record.get("okay")
    return CheckLog(
        id=str(record["id"]),
        created=str(record["created"]),
        caller_kind=str(record["caller_kind"]),
        caller=str(record["caller"]),
        target_id=str(record["target_id"]),
        node_id=_optional_str(record.get("node_id")),
        mode=str(record["mode"]),
        environment=_optional_str(record.get("environment")),
        content_sha256=str(record["content_sha256"]),
        content_bytes=int(record["content_bytes"]),
        outcome=str(record["outcome"]),
        okay=okay if isinstance(okay, bool) else None,
        error_count=int(record["error_count"]) if record.get("error_count") is not None else None,
        lint=[str(code) for code in record.get("lint") or []],
        axle_request_id=_optional_str(record.get("axle_request_id")),
        upstream_status=(
            int(record["upstream_status"]) if record.get("upstream_status") is not None else None
        ),
        latency_ms=int(record["latency_ms"]),
    )


def release(claim: Claim, when: datetime) -> Claim:
    return replace(claim, released=clock.render(when))


def build(settings: Any) -> Store:
    """The store the configuration names (C6)."""
    if settings.store == "dynamodb":
        return DynamoStore(
            identities=settings.table_identities,
            tokens=settings.table_tokens,
            claims=settings.table_claims,
        )
    return MemoryStore()
