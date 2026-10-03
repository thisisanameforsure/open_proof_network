"""F08-T26 (R21; Q39, decided 2026-10-03: option (a)): the service takes a use line.

A proof, an alternate or a partial's assembly may carry *use lines* directly after its
statement's imports (F08-R16, R18): ``import Defs.<Name>`` or ``import Nodes.«<id>».Proof``. The
gate reads them from the pinned commit on (T23, T24). The service learns whether a target's pin
understands them by comparing the target's ``gate-spec.json`` ``network_commit`` with the commit
its configuration names (``OPN_API_USES_FROM``): the pin is that commit or a descendant of it.

What is asserted here, each through the route:

* on a target whose pin understands uses, ``POST /check`` reads a valid use line as the gate does
  (no ``imports-differ``), inlines the used node's statement as a ``sorry``-bodied signature and
  drops the use import, so the hosted checker can elaborate the proof;
* on a target whose pin predates uses, the same text is ``imports-differ`` exactly as before;
* a bad use is named by the gate's own code (``uses.check``: ``use-duplicate``,
  ``use-unknown-defs``, ``use-self``, ``use-unknown-node``, ``use-superseded``, ``use-unproved``,
  ``use-redundant``, ``use-ancestor``), read from the committed products, and verify mode answers
  false on it;
* ``POST /precheck`` and ``POST /submissions`` (a proof, an alternate, a partial) refuse a bad
  use by that code before any branch is pushed, job dispatched or pull request opened; a valid
  use passes their pre-flight.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import samples
from api_fakes import Harness, PrecheckKey, make_harness, make_precheck_key, result_zip
from mcp_client import NODE, NODE_DIR, TARGET, seed_node

from opn_gate import schemas

PIN = "0df444a360eaa60ab8c11dca51a86af692955474"  # a Mathlib pin the hosted mapping serves
USES_FROM = "c0ffee" + "0" * 34
NEW_PIN = samples.SHA1  # what samples.gate_spec pins: a descendant of USES_FROM below
OLD_PIN = "badc0de" + "0" * 33
ENV = {"OPN_API_USES_FROM": USES_FROM}

NODES = f"targets/{TARGET}/nodes/"
GRAPH_JSON = f"targets/{TARGET}/graph.json"
STATEMENT = "import Init\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
BODY = "\ntheorem OpnProp.and_reassoc : True := by\n  exact OpnProp.lemma_a\n"
LEMMA_A = "import Init\n\ntheorem OpnProp.lemma_a : True := by\n  sorry\n"
FACT = "def Opn.fact : Nat := 1\n"


def statement_of(name: str) -> str:
    return f"import Init\n\ntheorem OpnProp.{name.replace('-', '_')} : True := by\n  sorry\n"


def proof_of(name: str) -> str:
    return f"import Init\n\ntheorem OpnProp.{name.replace('-', '_')} : True := by\n  trivial\n"


def row(node_id: str, status: str, *, deps: tuple[str, ...] = (), proved: bool = False) -> Any:
    return {
        "deps": list(deps),
        "node_id": node_id,
        "origin": "authored",
        "proof_commit": "7" * 40 if proved else None,
        "relation": None,
        "statement_hash": "1" * 64,
        "status": status,
        "trust_base": "kernel" if proved else None,
        "tutorial": False,
    }


def proof(*uses: str, body: str = BODY) -> str:
    return "import Init\n" + "".join(f"import {m}\n" for m in uses) + body


def world(h: Harness, *, pin: str = NEW_PIN, understands: bool | None = True) -> None:
    """The fixture target pinned to ``pin``, its graph holding one node of each kind a use can
    name. ``understands`` is the host's answer to "does ``pin`` descend from USES_FROM";
    ``None`` makes the host fail the question."""
    seed_node(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN, network_commit=pin)
    )
    files[NODE_DIR + "Statement.lean"] = STATEMENT.encode()
    files[f"targets/{TARGET}/defs/Fact.lean"] = FACT.encode()
    and_reassoc = row(NODE, "ready", deps=("dep-b",))
    rows = [
        and_reassoc,
        row("lemma-a", "proved", proved=True),
        row("dep-b", "proved", proved=True),
        row("open-c", "ready"),
        row("old-d", "superseded"),
        row("above-e", "blocked", deps=(NODE,)),
        {**row("above-f", "proved", proved=True), "uses": [NODE]},
        row("refuted-g", "refuted", proved=True),
    ]
    for r in rows[1:]:
        node_id = str(r["node_id"])
        files[f"{NODES}{node_id}/Statement.lean"] = statement_of(node_id).encode()
        if node_id in ("lemma-a", "dep-b", "old-d", "above-e", "above-f"):
            files[f"{NODES}{node_id}/Proof.lean"] = proof_of(node_id).encode()
    files[f"{NODES}lemma-a/Statement.lean"] = LEMMA_A.encode()
    # a counterexample, not a proof: what step 2's declared_kind reads off the file
    files[f"{NODES}refuted-g/Proof.lean"] = (
        b"import Init\n\ntheorem OpnProp.refuted_g.counterexample : \xc2\xac True := by\n  simp\n"
    )
    doc = json.loads((h.githost.files[GRAPH_JSON]).decode())
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != NODE] + rows
    files[GRAPH_JSON] = json.dumps(doc).encode()
    if understands is not None:
        h.githost.ancestry[(USES_FROM, pin)] = understands
    h.context.files.clear()


def harness() -> Harness:
    return make_harness(ENV)


def check(h: Harness, content: str, mode: str = "check") -> dict[str, Any]:
    r = h.client.post(
        "/check", json={"target_id": TARGET, "node_id": NODE, "content": content, "mode": mode}
    )
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def codes(doc: dict[str, Any]) -> list[str]:
    return [str(w["code"]) for w in doc["lint"]]


# --- POST /check: a pin that understands uses ----------------------------------------------------


def test_a_valid_node_use_is_not_imports_differ_and_is_composed() -> None:
    h = harness()
    world(h)
    doc = check(h, proof("Nodes.«lemma-a».Proof"))
    assert "imports-differ" not in codes(doc), doc["lint"]
    assert not [c for c in codes(doc) if c.startswith("use-")], doc["lint"]
    sent = h.axle.calls[-1].content
    assert "import Nodes.«lemma-a».Proof" not in sent, sent
    assert "theorem OpnProp.lemma_a : True := by\n  sorry" in sent, sent
    # the signature sits before the proof that uses it
    assert sent.index("OpnProp.lemma_a : True") < sent.index("exact OpnProp.lemma_a"), sent
    assert "Nodes.«lemma-a».Proof" in doc["inlined_defs"], doc


def test_a_valid_defs_use_is_not_imports_differ_and_is_inlined() -> None:
    h = harness()
    world(h)
    trivial = "\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
    doc = check(h, proof("Defs.Fact", body=trivial))
    assert "imports-differ" not in codes(doc), doc["lint"]
    sent = h.axle.calls[-1].content
    assert "import Defs.Fact" not in sent and "def Opn.fact : Nat := 1" in sent, sent


def test_verify_mode_answers_the_checker_on_a_valid_use() -> None:
    h = harness()
    world(h)
    doc = check(h, proof("Nodes.«lemma-a».Proof"), mode="verify")
    assert doc["okay"] is True, doc


def test_the_ancestry_answer_is_asked_once_per_pin() -> None:
    h = harness()
    world(h)
    check(h, proof("Nodes.«lemma-a».Proof"))
    check(h, proof("Nodes.«lemma-a».Proof"))
    asked = [c for c in h.githost.ancestry_calls if c[1:] == (USES_FROM, NEW_PIN)]
    assert len(asked) == 1, h.githost.ancestry_calls
    assert asked[0][0] == h.settings.network_repo


# --- POST /check: a pin that predates uses -------------------------------------------------------


@pytest.mark.parametrize("understands", [False, None])
def test_an_older_pin_keeps_imports_differ(understands: bool | None) -> None:
    """Unchanged from before T26, and when the host cannot say (``None``) the service takes the
    side that opens nothing the gate might refuse."""
    h = harness()
    world(h, pin=OLD_PIN, understands=understands)
    doc = check(h, proof("Nodes.«lemma-a».Proof"))
    assert "imports-differ" in codes(doc), doc["lint"]
    assert not [c for c in codes(doc) if c.startswith("use-")], doc["lint"]


def test_no_configured_commit_keeps_imports_differ_and_asks_nothing() -> None:
    h = make_harness()
    world(h)
    doc = check(h, proof("Nodes.«lemma-a».Proof"))
    assert "imports-differ" in codes(doc), doc["lint"]
    assert h.githost.ancestry_calls == []


# --- POST /check: each bad use, by the gate's code -----------------------------------------------

BAD_USES: list[tuple[str, tuple[str, ...]]] = [
    ("use-duplicate", ("Defs.Fact", "Defs.Fact")),
    ("use-duplicate", ("Nodes.«lemma-a».Proof", "Nodes.«lemma-a».Proof")),
    ("use-unknown-defs", ("Defs.Missing",)),
    ("use-self", (f"Nodes.«{NODE}».Proof",)),
    ("use-unknown-node", ("Nodes.«nope».Proof",)),
    ("use-superseded", ("Nodes.«old-d».Proof",)),
    ("use-unproved", ("Nodes.«open-c».Proof",)),
    ("use-unproved", ("Nodes.«refuted-g».Proof",)),
    ("use-redundant", ("Nodes.«dep-b».Proof",)),
    ("use-ancestor", ("Nodes.«above-e».Proof",)),
    ("use-ancestor", ("Nodes.«above-f».Proof",)),
]

IDS = [f"{code}-{i}" for i, (code, _) in enumerate(BAD_USES)]


@pytest.mark.parametrize(("code", "uses"), BAD_USES, ids=IDS)
def test_a_bad_use_is_named_by_the_gates_code(code: str, uses: tuple[str, ...]) -> None:
    h = harness()
    world(h)
    doc = check(h, proof(*uses))
    found = codes(doc)
    assert code in found, doc["lint"]
    assert "imports-differ" not in found, doc["lint"]
    verified = check(h, proof(*uses), mode="verify")
    assert verified["okay"] is False, verified


# --- the routes: refused before anything opens ---------------------------------------------------


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def precheck(h: Harness, token: str, node: str, bundle: dict[str, str]) -> Any:
    return h.client.post(
        "/precheck", json={"node_id": node, "bundle": bundle}, headers=h.auth(token)
    )


def passing_job(h: Harness, key: PrecheckKey, token: str, node: str, bundle: dict[str, str]) -> str:
    h.commit_precheck_key(key.public)
    created = precheck(h, token, node, bundle)
    assert created.status_code == 202, created.text  # guard: the precheck takes this bundle
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=node,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
    )
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    return str(doc["id"])


def submit(
    h: Harness, token: str, node: str, bundle: dict[str, str], job: str, *, kind: str = "proof"
) -> Any:
    body = {"node_id": node, "artifact_type": kind, "bundle": bundle, "precheck_job_id": job}
    return h.client.post("/submissions", json=body, headers=h.auth(token))


PROOF_PATH = NODE_DIR + "Proof.lean"
PARTIAL_PATH = NODE_DIR + "attempts/20261003T120000Z-alice-partial.lean"
ALTERNATE_PATH = f"{NODES}lemma-a/attempts/20261003T120000Z-alice-alternate.lean"
LEMMA_A_ALTERNATE = (
    "import Init\nimport Nodes.«lemma-a».Proof\n\n"
    "theorem OpnProp.lemma_a : True := by\n  exact OpnProp.lemma_a\n"
)


@pytest.mark.parametrize(("code", "uses"), BAD_USES, ids=IDS)
def test_precheck_refuses_a_bad_use_before_any_job(code: str, uses: tuple[str, ...]) -> None:
    h = harness()
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = precheck(h, token, NODE, {PROOF_PATH: proof(*uses)})
        assert r.status_code == 400, r.text
        assert r.json()["error"] == code, r.text
        assert h.githost.pushes == [] and h.githost.dispatches == []


def test_precheck_takes_a_valid_use() -> None:
    h = harness()
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = precheck(h, token, NODE, {PROOF_PATH: proof("Nodes.«lemma-a».Proof")})
        assert r.status_code == 202, r.text
        assert len(h.githost.dispatches) == 1


def test_precheck_on_an_older_pin_dispatches_as_before() -> None:
    """Before the re-pin the gate itself answers (``proof-not-statement``); the service adds no
    refusal of its own on a target whose pin predates uses."""
    h = harness()
    with h.client:
        world(h, pin=OLD_PIN, understands=False)
        token = h.token_for("code_alice", "alice")
        r = precheck(h, token, NODE, {PROOF_PATH: proof("Nodes.«nope».Proof")})
        assert r.status_code == 202, r.text


@pytest.mark.parametrize(
    "case",
    [
        (NODE, PROOF_PATH, "proof", proof("Nodes.«open-c».Proof"), "use-unproved"),
        (NODE, PARTIAL_PATH, "partial", proof("Nodes.«above-e».Proof"), "use-ancestor"),
        ("lemma-a", ALTERNATE_PATH, "proof", LEMMA_A_ALTERNATE, "use-self"),
    ],
    ids=["proof", "partial", "alternate"],
)
def test_submissions_refuse_a_bad_use_before_any_pull_request(
    key: PrecheckKey, case: tuple[str, str, str, str, str]
) -> None:
    """A job prechecked while the host could not say whether the pin understands uses (so no
    pre-flight ran) still cannot carry a bad use into a pull request: the submission asks too."""
    node, path, kind, text, code = case
    h = harness()
    with h.client:
        world(h, understands=None)
        token = h.token_for("code_alice", "alice")
        bundle = {path: text}
        job = passing_job(h, key, token, node, bundle)
        h.githost.ancestry[(USES_FROM, NEW_PIN)] = True
        pushed = len(h.githost.pushes)
        r = submit(h, token, node, bundle, job, kind=kind)
        assert r.status_code == 400, r.text
        assert r.json()["error"] == code, r.text
        assert h.githost.pulls == [] and len(h.githost.pushes) == pushed


def test_submissions_take_a_valid_use(key: PrecheckKey) -> None:
    h = harness()
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        bundle = {PROOF_PATH: proof("Nodes.«lemma-a».Proof")}
        job = passing_job(h, key, token, NODE, bundle)
        r = submit(h, token, NODE, bundle, job)
        assert r.status_code == 201, r.text
        assert len(h.githost.pulls) == 1


# --- the composer: a used node's own Context comes with it ---------------------------------------


def test_a_used_nodes_own_context_is_inlined_before_its_signature() -> None:
    """Every statement written since F08-T13 imports its own Context, so a used node's signature
    can name its dependencies' theorems; they are inlined first, under that node's module."""
    h = harness()
    world(h)
    own = "import Nodes.«lemma-a».Context"
    h.githost.files[f"{NODES}lemma-a/Statement.lean"] = (
        f"import Init\n{own}\n\ntheorem OpnProp.lemma_a : True := by\n  sorry\n".encode()
    )
    h.githost.files[f"{NODES}lemma-a/Context.lean"] = (
        b"/-! Declared dependencies (D-4 step 8): `dep-b`. -/\n\n"
        b"theorem OpnProp.dep_b : True := by\n  sorry\n"
    )
    h.context.files.clear()
    doc = check(h, proof("Nodes.«lemma-a».Proof"))
    assert doc["inlined_defs"][-2:] == ["Nodes.«lemma-a».Context", "Nodes.«lemma-a».Proof"], doc
    sent = h.axle.calls[-1].content
    assert sent.index("OpnProp.dep_b") < sent.index("OpnProp.lemma_a : True") and own not in sent


# --- configuration and the host seam -------------------------------------------------------------


def test_uses_from_defaults_empty_and_refuses_a_short_id() -> None:
    from opn_api import config  # noqa: PLC0415

    assert config.load({}).uses_from == ""
    assert config.load({"OPN_API_USES_FROM": USES_FROM.upper()}).uses_from == USES_FROM
    with pytest.raises(config.ConfigError, match="OPN_API_USES_FROM"):
        config.load({"OPN_API_USES_FROM": USES_FROM[:12]})


class _Httpx:
    """``opn_api.githost.httpx`` for one test: the real module with ``Client`` scripted, so the
    real ``httpx`` is never touched (as in ``test_githost_seam``)."""

    def __init__(self, client: type) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        import httpx  # noqa: PLC0415

        return self._client if name == "Client" else getattr(httpx, name)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (200, {"status": "ahead"}, True),
        (200, {"status": "identical"}, True),
        (200, {"status": "behind"}, False),
        (200, {"status": "diverged"}, False),
        (404, {"message": "Not Found"}, False),
    ],
)
def test_the_seam_reads_the_compare_status(
    monkeypatch: pytest.MonkeyPatch, status: int, body: dict[str, Any], expected: bool
) -> None:
    """``HttpxGitHost.is_ancestor``: one compare call, ``ahead`` or ``identical`` meaning the
    commit contains the ancestor; anonymous when the App is not installed on the repository."""
    import httpx  # noqa: PLC0415

    from opn_api import githost  # noqa: PLC0415

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body)

    class Scripted(httpx.Client):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(githost, "httpx", _Httpx(Scripted))
    host = githost.HttpxGitHost(client_id="", client_secret="", app_id="", private_key="")
    assert host.is_ancestor("owner/network", USES_FROM, NEW_PIN) is expected
    (call,) = seen
    assert call.url.path == f"/repos/owner/network/compare/{USES_FROM}...{NEW_PIN}"
    assert "Authorization" not in call.headers


def test_the_seam_names_a_failed_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx  # noqa: PLC0415

    from opn_api import githost  # noqa: PLC0415

    class Scripted(httpx.Client):
        def __init__(self, **kwargs: Any) -> None:
            transport = httpx.MockTransport(lambda _r: httpx.Response(502, text="bad gateway"))
            super().__init__(transport=transport, **kwargs)

    monkeypatch.setattr(githost, "httpx", _Httpx(Scripted))
    host = githost.HttpxGitHost(client_id="", client_secret="", app_id="", private_key="")
    with pytest.raises(githost.GitHostError, match=r"compare.*502"):
        host.is_ancestor("owner/network", USES_FROM, NEW_PIN)
