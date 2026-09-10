"""The DynamoDB store, ``DynamoStore``, against a scripted boto3 resource (F05-R4, R6, R12, R13;
C7, C9).

``MemoryStore`` is the seam's fake and every route test runs on it; nothing exercised the
DynamoDB half without a real table until now. The fake resource here implements only the
handful of calls the store makes, but it is honest where DynamoDB bites: items pass through
boto3's own ``TypeSerializer``/``TypeDeserializer`` (so numbers come back as ``Decimal`` and a
``float`` is refused, exactly as the live service does), a transaction cancels with the
``CancellationReasons`` shape the store parses, and every error is a real
``botocore.exceptions.ClientError``. No moto (C5).

Where the interface allows, a behaviour is asserted over both stores so the fake the routes
run on and the store production runs on cannot drift apart.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from boto3.dynamodb.types import (  # type: ignore[import-untyped]  # pyproject ignores boto3, not boto3.*
    TypeDeserializer,
    TypeSerializer,
)
from botocore.exceptions import ClientError

from opn_api import store as storemod
from opn_api.store import (
    KEY_JOB,
    KEY_PROOF_REF,
    KEY_PSEUDONYM,
    KEY_TOKEN,
    Claim,
    ConflictError,
    DynamoStore,
    Identity,
    MemoryStore,
    Store,
    TokenRecord,
)

NOW = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=10)
TABLES = {"identities": "opn-identities", "tokens": "opn-tokens", "claims": "opn-claims"}


class TransactionCanceledException(ClientError):  # type: ignore[misc]  # noqa: N818 — boto3's name; untyped base
    """What ``client.exceptions.TransactionCanceledException`` is on a real client."""


def client_error(code: str, operation: str, message: str = "", **extra: Any) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}, **extra}, operation)


def cancelled(reasons: list[dict[str, str]]) -> TransactionCanceledException:
    return TransactionCanceledException(
        {
            "Error": {
                "Code": "TransactionCanceledException",
                "Message": "Transaction cancelled, please refer cancellation reasons",
            },
            "CancellationReasons": reasons,
        },
        "TransactWriteItems",
    )


_serializer = TypeSerializer()
_deserializer = TypeDeserializer()


def through_dynamo(item: dict[str, Any]) -> dict[str, Any]:
    """An item as boto3 would hand it back: numbers are ``Decimal``, floats are refused."""
    wire = {k: _serializer.serialize(v) for k, v in item.items()}
    return {k: _deserializer.deserialize(v) for k, v in wire.items()}


@dataclass
class FakeTable:
    name: str
    key: str
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    page_size: int = 2
    failure: ClientError | None = None
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def _fail(self, op: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((op, copy.deepcopy(kwargs)))
        if self.failure is not None:
            raise self.failure

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        self._fail("put_item", kwargs)
        item = through_dynamo(kwargs["Item"])
        self.items[str(item[self.key])] = item
        return {}

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self._fail("get_item", kwargs)
        item = self.items.get(str(kwargs["Key"][self.key]))
        return {"Item": copy.deepcopy(item)} if item is not None else {}

    def delete_item(self, **kwargs: Any) -> dict[str, Any]:
        self._fail("delete_item", kwargs)
        old = self.items.pop(str(kwargs["Key"][self.key]), None)
        if old is not None and kwargs.get("ReturnValues") == "ALL_OLD":
            return {"Attributes": old}
        return {}

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self._fail("update_item", kwargs)
        # The one expression the store uses (bump_counter); anything else is a test error.
        assert kwargs["UpdateExpression"] == (
            "ADD #c :one SET expires_at = if_not_exists(expires_at, :exp)"
        )
        counter = kwargs["ExpressionAttributeNames"]["#c"]
        values = through_dynamo(kwargs["ExpressionAttributeValues"])
        key = str(kwargs["Key"][self.key])
        item = self.items.setdefault(key, {self.key: key})
        item[counter] = Decimal(item.get(counter, 0)) + values[":one"]
        item.setdefault("expires_at", values[":exp"])
        assert kwargs["ReturnValues"] == "UPDATED_NEW"
        return {"Attributes": {counter: item[counter]}}

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        self._fail("scan", kwargs)
        keys = list(self.items)
        start = keys.index(kwargs["ExclusiveStartKey"][self.key]) + 1 if kwargs else 0
        page = keys[start : start + self.page_size]
        out: dict[str, Any] = {"Items": [copy.deepcopy(self.items[k]) for k in page]}
        if start + self.page_size < len(keys):
            out["LastEvaluatedKey"] = {self.key: page[-1]}
        return out


@dataclass
class FakeClient:
    tables: dict[str, FakeTable]
    missing: set[str] = field(default_factory=set)  # never provisioned (R13)
    unreachable: set[str] = field(default_factory=set)
    transact_failure: Exception | None = None
    transactions: list[list[dict[str, Any]]] = field(default_factory=list)
    exceptions: Any = field(
        default_factory=lambda: SimpleNamespace(
            TransactionCanceledException=TransactionCanceledException
        )
    )

    def describe_table(self, **kwargs: Any) -> dict[str, Any]:
        name = kwargs["TableName"]
        if name in self.missing:
            raise client_error("ResourceNotFoundException", "DescribeTable", "Requested resource")
        if name in self.unreachable:
            msg = "Could not connect to the endpoint URL"
            raise ConnectionError(msg)  # botocore's EndpointConnectionError is not a ClientError
        return {"Table": {"TableName": name, "TableStatus": "ACTIVE"}}

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
        items = kwargs["TransactItems"]
        self.transactions.append(copy.deepcopy(items))
        if self.transact_failure is not None:
            raise self.transact_failure
        reasons: list[dict[str, str]] = []
        for entry in items:
            put = entry["Put"]
            table = self.tables[put["TableName"]]
            key = str(put["Item"][table.key])
            condition = put.get("ConditionExpression")
            assert condition in (None, f"attribute_not_exists({table.key})")
            if condition and key in table.items:
                reasons.append(
                    {"Code": "ConditionalCheckFailed", "Message": "The conditional request failed"}
                )
            else:
                reasons.append({"Code": "None"})
        if any(r["Code"] != "None" for r in reasons):
            raise cancelled(reasons)
        for entry in items:
            put = entry["Put"]
            self.tables[put["TableName"]].put_item(Item=put["Item"])
        return {}


@dataclass
class FakeResource:
    client: FakeClient

    @property
    def meta(self) -> Any:
        return SimpleNamespace(client=self.client)

    def Table(self, name: str) -> FakeTable:  # noqa: N802 — boto3's own spelling
        """Lazy, like boto3's: a handle to a table nobody has checked exists."""
        return self.client.tables[name]


def fake_resource(**overrides: Any) -> FakeResource:
    tables = {
        TABLES["identities"]: FakeTable(TABLES["identities"], "id"),
        TABLES["tokens"]: FakeTable(TABLES["tokens"], "key"),
        TABLES["claims"]: FakeTable(TABLES["claims"], "id"),
    }
    return FakeResource(FakeClient(tables, **overrides))


def dynamo(resource: FakeResource | None = None) -> DynamoStore:
    return DynamoStore(**TABLES, resource=resource or fake_resource())


@pytest.fixture(params=["memory", "dynamodb"])
def both(request: pytest.FixtureRequest) -> Store:
    """The route tests' fake and the production store, one behaviour at a time."""
    if request.param == "memory":
        return MemoryStore()
    return dynamo()


def identity(pseudonym: str = "Alice", reference: str = "alice", id_: str = "01H") -> Identity:
    return Identity(id_, pseudonym, "github", reference, "2026-09-10T12:00:00Z")


def claim(id_: str, released: str | None = None) -> Claim:
    return Claim(id_, "node", "target", "01H", "2026-09-10T12:00:00Z", "2026-09-11", released)


# --- check (R13) -------------------------------------------------------------------------------


def test_check_names_the_missing_table_by_role_and_name() -> None:
    resource = fake_resource(missing={TABLES["tokens"]})
    assert DynamoStore(**TABLES, resource=resource).check() == ["tokens table 'opn-tokens'"]


def test_check_names_every_missing_table_in_role_order() -> None:
    resource = fake_resource(missing=set(TABLES.values()))
    assert DynamoStore(**TABLES, resource=resource).check() == [
        "identities table 'opn-identities'",
        "tokens table 'opn-tokens'",
        "claims table 'opn-claims'",
    ]


def test_check_reports_an_unreachable_endpoint_as_missing() -> None:
    """An outage is not a ClientError; the health check must still name the table (C7)."""
    resource = fake_resource(unreachable={TABLES["claims"]})
    assert DynamoStore(**TABLES, resource=resource).check() == ["claims table 'opn-claims'"]


def test_check_healthy_is_empty_for_both_stores(both: Store) -> None:
    assert both.check() == []


# --- put_identity: the uniqueness transaction (R4, R6) -----------------------------------------


def test_identity_transaction_writes_the_row_and_two_conditional_markers() -> None:
    resource = fake_resource()
    dynamo(resource).put_identity(identity("Alice", "alice"))
    (items,) = resource.client.transactions
    assert [i["Put"]["TableName"] for i in items] == [TABLES["identities"]] * 3
    assert "ConditionExpression" not in items[0]["Put"]
    assert items[0]["Put"]["Item"]["id"] == "01H"
    assert items[1]["Put"] == {
        "TableName": TABLES["identities"],
        "Item": {"id": KEY_PSEUDONYM + "alice", "what": "pseudonym", "identity_id": "01H"},
        "ConditionExpression": "attribute_not_exists(id)",
    }
    assert items[2]["Put"]["Item"]["id"] == KEY_PROOF_REF + "github#alice"
    assert items[2]["Put"]["ConditionExpression"] == "attribute_not_exists(id)"


def test_pseudonym_conflict_is_case_insensitive_in_both_stores(both: Store) -> None:
    both.put_identity(identity("Alice", "alice", "01H"))
    with pytest.raises(ConflictError) as raised:
        both.put_identity(identity("ALICE", "someone-else", "01J"))
    assert raised.value.what == "pseudonym"
    assert both.get_identity("01J") is None


def test_proof_reference_conflict_names_the_rule_in_both_stores(both: Store) -> None:
    both.put_identity(identity("Alice", "alice", "01H"))
    with pytest.raises(ConflictError) as raised:
        both.put_identity(identity("Alice2", "alice", "01J"))
    assert raised.value.what == "proof-reference"
    assert both.get_identity("01J") is None
    assert both.count_identities_by_proof("github", "alice") == 1


def test_both_rules_violated_names_the_pseudonym_first_in_both_stores(both: Store) -> None:
    both.put_identity(identity("Alice", "alice", "01H"))
    with pytest.raises(ConflictError) as raised:
        both.put_identity(identity("alice", "alice", "01J"))
    assert raised.value.what == "pseudonym"


def test_conflict_on_the_identity_row_itself_is_not_a_uniqueness_conflict() -> None:
    """Index 0 is the identity row; a failure there is not one of the two rules, so it is
    re-raised as the transaction error rather than misreported as a pseudonym clash."""
    resource = fake_resource(
        transact_failure=cancelled(
            [{"Code": "ConditionalCheckFailed"}, {"Code": "None"}, {"Code": "None"}]
        )
    )
    with pytest.raises(TransactionCanceledException):
        dynamo(resource).put_identity(identity())


@pytest.mark.parametrize(
    "reasons",
    [
        [{"Code": "None"}, {"Code": "TransactionConflict"}, {"Code": "None"}],
        [{"Code": "None"}, {"Code": "ProvisionedThroughputExceeded"}, {"Code": "None"}],
        [
            {"Code": "None"},
            {"Code": "ValidationError", "Message": "item too large"},
            {"Code": "None"},
        ],
        [],
    ],
    ids=["transaction-conflict", "throughput", "validation", "no-reasons"],
)
def test_cancellation_for_another_reason_is_re_raised_not_swallowed(
    reasons: list[dict[str, str]],
) -> None:
    resource = fake_resource(transact_failure=cancelled(reasons))
    with pytest.raises(TransactionCanceledException) as raised:
        dynamo(resource).put_identity(identity())
    assert not isinstance(raised.value, ConflictError)
    assert raised.value.response.get("CancellationReasons") == reasons


def test_a_client_error_that_is_not_a_cancellation_propagates() -> None:
    failure = client_error("ProvisionedThroughputExceededException", "TransactWriteItems")
    resource = fake_resource(transact_failure=failure)
    with pytest.raises(ClientError) as raised:
        dynamo(resource).put_identity(identity())
    assert raised.value is failure


# --- reads (R4) --------------------------------------------------------------------------------


def test_get_identity_absent_is_none_in_both_stores(both: Store) -> None:
    assert both.get_identity("nobody") is None


def test_get_identity_of_a_marker_row_is_none() -> None:
    """The uniqueness markers share the table; asking for one by id must not yield an identity
    made of the marker's fields."""
    store = dynamo()
    store.put_identity(identity("Alice", "alice"))
    assert store.get_identity(KEY_PSEUDONYM + "alice") is None
    assert store.get_identity(KEY_PROOF_REF + "github#alice") is None
    assert store.get_identity("01H") == identity("Alice", "alice")


def test_count_identities_by_proof_in_both_stores(both: Store) -> None:
    assert both.count_identities_by_proof("github", "alice") == 0
    both.put_identity(identity("Alice", "alice"))
    assert both.count_identities_by_proof("github", "alice") == 1
    assert both.count_identities_by_proof("tutorial", "alice") == 0


def test_get_token_absent_is_none_in_both_stores(both: Store) -> None:
    assert both.get_token("deadbeef") is None


def test_token_row_carries_the_hash_only_under_the_token_prefix() -> None:
    resource = fake_resource()
    store = dynamo(resource)
    store.put_token(TokenRecord("hash-1", "01H", "2026-09-10T12:00:00Z"))
    item = resource.client.tables[TABLES["tokens"]].items[KEY_TOKEN + "hash-1"]
    assert item == {
        "key": KEY_TOKEN + "hash-1",
        "token_hash": "hash-1",
        "identity_id": "01H",
        "created": "2026-09-10T12:00:00Z",
        "revoked": False,
    }
    assert store.get_token("hash-1") == TokenRecord("hash-1", "01H", "2026-09-10T12:00:00Z")


def test_revoked_token_round_trips_in_both_stores(both: Store) -> None:
    both.put_token(TokenRecord("hash-1", "01H", "2026-09-10T12:00:00Z", revoked=True))
    found = both.get_token("hash-1")
    assert found is not None
    assert found.revoked is True


def test_token_row_without_the_revoked_field_reads_as_live() -> None:
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].put_item(
        Item={
            "key": KEY_TOKEN + "old",
            "token_hash": "old",
            "identity_id": "01H",
            "created": "2026-09-10T12:00:00Z",
        }
    )
    found = dynamo(resource).get_token("old")
    assert found is not None
    assert found.revoked is False


# --- jobs (F06-R3): the Decimal round trip ---------------------------------------------------


JOB = {
    "id": "job-1",
    "attempt": 1,
    "steps": [{"step": 1, "ms": 1200}, {"step": 2, "ms": 0}],
    "nested": {"depth": {"n": 3}},
    "label": "x",
    "flag": True,
    "none": None,
}


def test_job_record_reads_back_with_plain_ints_not_decimals_in_both_stores(both: Store) -> None:
    """The live-found defect: a DynamoDB Decimal reaching ``json.dumps`` in a pull-request
    body. The store converts on read, so the seam's contract holds on both sides."""
    both.put_job("job-1", JOB, LATER)
    found = both.get_job("job-1")
    assert found == JOB
    assert found is not None
    assert type(found["attempt"]) is int
    assert type(found["steps"][0]["ms"]) is int
    assert type(found["nested"]["depth"]["n"]) is int
    assert found["flag"] is True


def test_job_item_stores_dynamo_decimals_and_a_ttl_epoch() -> None:
    resource = fake_resource()
    dynamo(resource).put_job("job-1", JOB, LATER)
    item = resource.client.tables[TABLES["tokens"]].items[KEY_JOB + "job-1"]
    assert item["expires_at"] == Decimal(int(LATER.timestamp()))
    assert isinstance(item["job"]["attempt"], Decimal)


def test_get_job_absent_is_none_in_both_stores(both: Store) -> None:
    assert both.get_job("nothing") is None


def test_get_job_returns_a_copy_in_both_stores(both: Store) -> None:
    both.put_job("job-1", JOB, LATER)
    first = both.get_job("job-1")
    assert first is not None
    first["attempt"] = 99
    second = both.get_job("job-1")
    assert second is not None
    assert second["attempt"] == 1


def test_job_item_whose_record_is_not_an_object_is_none() -> None:
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].put_item(
        Item={"key": KEY_JOB + "job-1", "job": "corrupt", "expires_at": 1}
    )
    assert dynamo(resource).get_job("job-1") is None


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="boto3 refuses float attributes ('Float types are not supported'), so a job record "
    "carrying one fails put_job on DynamoDB while MemoryStore accepts it; store.plain's "
    "docstring promises floats come back as floats, but they never go in (seam parity, C7). "
    "No record carries a float today.",
)
def test_a_float_in_a_job_record_is_stored_by_dynamodb_like_memory() -> None:
    store = dynamo()
    store.put_job("job-1", {"ratio": 0.5}, LATER)
    assert store.get_job("job-1") == {"ratio": 0.5}


def test_plain_converts_decimals_by_integrality() -> None:
    assert storemod.plain(Decimal("2")) == 2
    assert type(storemod.plain(Decimal("2"))) is int
    assert storemod.plain(Decimal("2.5")) == 2.5
    assert storemod.plain({"a": [Decimal("1"), (Decimal("0.25"),)], "s": {Decimal("3")}}) == {
        "a": [1, [0.25]],
        "s": {3},
    }


# --- claims (F05-R7) ---------------------------------------------------------------------------


def test_get_claim_absent_is_none_in_both_stores(both: Store) -> None:
    assert both.get_claim("nothing") is None


def test_claim_round_trips_with_and_without_release_in_both_stores(both: Store) -> None:
    both.put_claim(claim("c1"))
    both.put_claim(claim("c2", "2026-09-10T13:00:00Z"))
    assert both.get_claim("c1") == claim("c1")
    assert both.get_claim("c2") == claim("c2", "2026-09-10T13:00:00Z")


def test_claim_row_with_an_empty_released_string_reads_as_unreleased() -> None:
    resource = fake_resource()
    resource.client.tables[TABLES["claims"]].put_item(Item={**asdict(claim("c1")), "released": ""})
    assert dynamo(resource).get_claim("c1") == claim("c1")


def test_list_claims_pages_through_last_evaluated_key_and_sorts_by_id() -> None:
    resource = fake_resource()
    store = dynamo(resource)
    for id_ in ("c3", "c1", "c5", "c2", "c4"):
        store.put_claim(claim(id_))
    assert [c.id for c in store.list_claims()] == ["c1", "c2", "c3", "c4", "c5"]
    scans = [k for op, k in resource.client.tables[TABLES["claims"]].calls if op == "scan"]
    assert len(scans) == 3
    assert scans[0] == {}
    assert [s["ExclusiveStartKey"]["id"] for s in scans[1:]] == ["c1", "c2"]


def test_list_claims_empty_in_both_stores(both: Store) -> None:
    assert both.list_claims() == []


def test_list_claims_sorted_by_id_in_both_stores(both: Store) -> None:
    for id_ in ("b", "a", "c"):
        both.put_claim(claim(id_))
    assert [c.id for c in both.list_claims()] == ["a", "b", "c"]


# --- ephemeral items (R3 state nonces, F06-R7 nonces; C7) ---------------------------------------


def test_take_ephemeral_is_single_use_in_both_stores(both: Store) -> None:
    both.put_ephemeral("state#n1", {"redirect": "/x"}, LATER)
    assert both.take_ephemeral("state#n1", NOW) == {"redirect": "/x"}
    assert both.take_ephemeral("state#n1", NOW) is None


def test_take_ephemeral_absent_is_none_in_both_stores(both: Store) -> None:
    assert both.take_ephemeral("state#none", NOW) is None


@pytest.mark.parametrize("late_by", [timedelta(0), timedelta(seconds=1), timedelta(days=1)])
def test_expired_ephemeral_is_none_and_consumed_in_both_stores(
    both: Store, late_by: timedelta
) -> None:
    """At or after expiry the item is gone: DynamoDB's TTL sweep lags by up to 48 hours, so
    the store must not trust the row's presence."""
    both.put_ephemeral("state#n1", {"x": 1}, LATER)
    assert both.take_ephemeral("state#n1", LATER + late_by) is None
    assert both.take_ephemeral("state#n1", NOW) is None


def test_ephemeral_item_carries_the_ttl_attribute_as_an_epoch() -> None:
    resource = fake_resource()
    dynamo(resource).put_ephemeral("state#n1", {"x": 1}, LATER)
    item = resource.client.tables[TABLES["tokens"]].items["state#n1"]
    assert item["expires_at"] == Decimal(int(LATER.timestamp()))
    assert item["data"] == {"x": Decimal(1)}


def test_take_ephemeral_returns_plain_ints_like_memory(both: Store) -> None:
    both.put_ephemeral("proof#n1", {"job": "j", "attempt": 2}, LATER)
    taken = both.take_ephemeral("proof#n1", NOW)
    assert taken == {"job": "j", "attempt": 2}
    assert taken is not None
    assert isinstance(taken["attempt"], int | Decimal)


@pytest.mark.xfail(
    strict=True,
    reason="store.py:322-331 take_ephemeral returns the raw DynamoDB attributes: a Decimal "
    "reaches the caller where MemoryStore hands back the int that went in. Harmless today: "
    "the one numeric field, the proof record's github_id (identity.py:218), is never read "
    "(github_reference uses login only) and undo re-stores it, which boto3 accepts. But the "
    "seam's contract is 'what goes in comes out' and get_job already converts (seam parity).",
)
def test_take_ephemeral_returns_exact_ints_on_dynamodb() -> None:
    store = dynamo()
    store.put_ephemeral("proof#n1", {"attempt": 2}, LATER)
    taken = store.take_ephemeral("proof#n1", NOW)
    assert taken is not None
    assert type(taken["attempt"]) is int


def test_take_ephemeral_deletes_with_return_all_old_in_one_call() -> None:
    """Read-and-delete in one step (single use): a race between two callbacks with the same
    state cannot both win."""
    resource = fake_resource()
    store = dynamo(resource)
    store.put_ephemeral("state#n1", {"x": "y"}, LATER)
    store.take_ephemeral("state#n1", NOW)
    ops = [op for op, _ in resource.client.tables[TABLES["tokens"]].calls]
    assert ops == ["put_item", "delete_item"]
    (delete,) = [
        k for op, k in resource.client.tables[TABLES["tokens"]].calls if op == "delete_item"
    ]
    assert delete == {"Key": {"key": "state#n1"}, "ReturnValues": "ALL_OLD"}


def test_ephemeral_data_that_is_not_an_object_is_none() -> None:
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].put_item(
        Item={"key": "state#n1", "data": "corrupt", "expires_at": int(LATER.timestamp())}
    )
    assert dynamo(resource).take_ephemeral("state#n1", NOW) is None


def test_ephemeral_row_without_a_ttl_reads_as_expired() -> None:
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].put_item(Item={"key": "state#n1", "data": {"x": 1}})
    assert dynamo(resource).take_ephemeral("state#n1", NOW) is None


def test_take_ephemeral_swallows_a_store_outage_into_none() -> None:
    """Documented behaviour: a throttled or unreachable table reads as 'no such state', so the
    caller answers 400 state-invalid rather than 503. The first is what the code does."""
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].failure = client_error(
        "ProvisionedThroughputExceededException", "DeleteItem"
    )
    assert dynamo(resource).take_ephemeral("state#n1", NOW) is None


@pytest.mark.xfail(
    strict=True,
    reason="store.py:323-326 take_ephemeral catches bare Exception, so a programming error "
    "(here a TypeError from the client) is swallowed into None and reported to the caller as an "
    "expired nonce instead of failing loudly (C7: no silent swallowing)",
)
def test_take_ephemeral_does_not_swallow_a_programming_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = fake_resource()

    def broken(**kwargs: Any) -> dict[str, Any]:
        msg = "delete_item() got an unexpected keyword"
        raise TypeError(msg)

    monkeypatch.setattr(resource.client.tables[TABLES["tokens"]], "delete_item", broken)
    with pytest.raises(TypeError):
        dynamo(resource).take_ephemeral("state#n1", NOW)


# --- counters (R6, F06-R2) ---------------------------------------------------------------------


def test_bump_counter_counts_from_one_in_both_stores(both: Store) -> None:
    assert [both.bump_counter("rate#w#s#0", LATER) for _ in range(3)] == [1, 2, 3]
    assert both.bump_counter("rate#w#other#0", LATER) == 1


def test_bump_counter_returns_an_int_not_a_decimal() -> None:
    count = dynamo().bump_counter("rate#w#s#0", LATER)
    assert type(count) is int


def test_bump_counter_sets_the_ttl_once_and_adds_atomically() -> None:
    resource = fake_resource()
    store = dynamo(resource)
    store.bump_counter("rate#w#s#0", LATER)
    store.bump_counter("rate#w#s#0", LATER + timedelta(hours=1))
    item = resource.client.tables[TABLES["tokens"]].items["rate#w#s#0"]
    assert item["count"] == Decimal(2)
    assert item["expires_at"] == Decimal(int(LATER.timestamp()))
    calls = resource.client.tables[TABLES["tokens"]].calls
    assert all(op == "update_item" for op, _ in calls)
    assert calls[0][1]["ExpressionAttributeValues"] == {":one": 1, ":exp": int(LATER.timestamp())}


def test_bump_counter_failure_propagates() -> None:
    """A rate limit that cannot be counted is not a rate limit that passed (C7)."""
    resource = fake_resource()
    resource.client.tables[TABLES["tokens"]].failure = client_error(
        "ProvisionedThroughputExceededException", "UpdateItem"
    )
    with pytest.raises(ClientError):
        dynamo(resource).bump_counter("rate#w#s#0", LATER)


# --- build (C6) --------------------------------------------------------------------------------


def test_build_dynamodb_names_the_three_tables_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3  # noqa: PLC0415 — patched at the seam's own import

    resource = fake_resource()
    asked: list[str] = []

    def fake_boto_resource(service: str) -> FakeResource:
        asked.append(service)
        return resource

    monkeypatch.setattr(boto3, "resource", fake_boto_resource)
    settings = SimpleNamespace(store="dynamodb", **{f"table_{k}": v for k, v in TABLES.items()})
    built = storemod.build(settings)
    assert isinstance(built, DynamoStore)
    assert asked == ["dynamodb"]
    assert built.check() == []


def test_build_memory_ignores_table_names() -> None:
    settings = SimpleNamespace(store="memory", table_identities=None)
    assert isinstance(storemod.build(settings), MemoryStore)


def test_release_renders_the_time(both: Store) -> None:
    released = storemod.release(claim("c1"), NOW)
    both.put_claim(released)
    found = both.get_claim("c1")
    assert found is not None
    assert found.released == "2026-09-10T12:00:00Z"
