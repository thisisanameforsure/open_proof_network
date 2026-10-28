"""postmortem/v2 at the service (D-13, D-23): ``POST /postmortems`` and ``submit_postmortem``
write the version the target's pinned gate reads, with the model the record declares.

The record carries its own ``model_and_tooling``, as an approach record does
(``appends.post_approach_records``): the service takes the declaration as sent, defaults an
absent one to ``null`` and verifies nothing. A target whose pinned gate predates ``postmortem/v2``
would refuse a v2 file at classify, so a pull request opened there could never merge; for such a
target the service writes ``postmortem/v1`` exactly as before, and a declared model, which v1
cannot carry, is refused before anything opens. Whether the pin reads v2 is asked of the pin
itself (its ``gate/schemas/postmortem/v2.json``), and a host that cannot say answers v1 (C7).
"""

from __future__ import annotations

from typing import Any

import pytest
import samples
import yaml
from api_fakes import Harness, make_harness
from mcp_client import NODE, NODE_DIR, TARGET, McpClient, seed_node

from opn_api.githost import GitHostError
from opn_gate import modes, paths, schemas
from opn_gate.paths import Change

PIN = samples.SHA1  # what samples.gate_spec pins
MODEL = "claude-opus-5-5 via opn-mcp"
V2_PATH = "gate/schemas/postmortem/v2.json"


def world(h: Harness, *, reads_v2: bool) -> None:
    seed_node(h)
    h.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(network_commit=PIN)
    )
    if reads_v2:
        # the network repository's tree at the pin: the schema file the pinned gate validates by
        h.githost.files_at.setdefault(PIN, {})[V2_PATH] = schemas.schema_path(
            "postmortem/v2"
        ).read_bytes()
    h.context.files.clear()


def record(**overrides: Any) -> dict[str, Any]:
    doc = samples.postmortem(**overrides)
    del doc["schema"]
    del doc["node"]
    return doc


def post(h: Harness, token: str, doc: dict[str, Any]) -> Any:
    return h.client.post("/postmortems", json={"node_id": NODE, "yaml": doc}, headers=h.auth(token))


def landed(h: Harness) -> tuple[str, dict[str, Any]]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    path, content = next(iter(push.files.items()))
    return path, yaml.safe_load(content)


def test_the_service_writes_v2_with_the_declared_model() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        token = h.token_for("code_alice", "alice")
        r = post(h, token, record(model_and_tooling=MODEL))
        assert r.status_code == 201, r.text
        path, doc = landed(h)
        assert doc["schema"] == "postmortem/v2"
        assert doc["model_and_tooling"] == MODEL
        assert doc["contributor"] == "alice"
        assert schemas.violations(doc) == []
        # the file the gate meets: a postmortem, appended, at a path the gate accepts
        assert path.startswith(NODE_DIR + "attempts/")
        located = paths.locate(path)
        assert located is not None and located.role == "postmortem"
        assert modes.classify([Change("A", path)]).mode == "append"


def test_an_undeclared_model_is_written_as_null() -> None:
    """v2 requires the field, so a record that says nothing states ``null``: no model declared."""
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        token = h.token_for("code_alice", "alice")
        assert post(h, token, record()).status_code == 201
        _, doc = landed(h)
        assert doc["schema"] == "postmortem/v2"
        assert doc["model_and_tooling"] is None


def test_an_overlong_model_is_refused_naming_the_cap() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        token = h.token_for("code_alice", "alice")
        r = post(h, token, record(model_and_tooling="x" * 201))
        assert r.status_code == 400, r.text
        assert "model_and_tooling" in r.json()["message"] and "200" in r.json()["message"]
        assert h.githost.pushes == []


def test_a_target_whose_gate_predates_v2_gets_v1_as_before() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=False)
        token = h.token_for("code_alice", "alice")
        assert post(h, token, record()).status_code == 201
        _, doc = landed(h)
        assert doc["schema"] == "postmortem/v1"
        assert "model_and_tooling" not in doc
        assert schemas.violations(doc) == []
        # an explicit null says nothing v1 cannot, so it is taken too
        h.clock.advance(seconds=2)
        assert post(h, token, record(model_and_tooling=None)).status_code == 201
        assert "model_and_tooling" not in landed(h)[1]


def test_a_declared_model_on_an_older_pin_is_refused_before_anything_opens() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=False)
        token = h.token_for("code_alice", "alice")
        r = post(h, token, record(model_and_tooling=MODEL))
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "record-invalid"
        assert "postmortem/v2" in r.json()["message"]
        assert h.githost.pushes == [] and h.githost.pulls == []


def test_a_host_that_cannot_say_answers_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        real = h.githost.fetch_raw

        def flaky(repo: str, ref: str, path: str, *, etag: str | None) -> Any:
            if path == V2_PATH:
                msg = "fetching the schema failed: ConnectError"
                raise GitHostError(msg)
            return real(repo, ref, path, etag=etag)

        monkeypatch.setattr(h.githost, "fetch_raw", flaky)
        token = h.token_for("code_alice", "alice")
        assert post(h, token, record()).status_code == 201
        assert landed(h)[1]["schema"] == "postmortem/v1"


def test_the_answer_for_a_pin_is_asked_once() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        token = h.token_for("code_alice", "alice")
        assert post(h, token, record()).status_code == 201
        h.clock.advance(seconds=2)
        assert post(h, token, record(route="another route")).status_code == 201
        asked = [p for p, _ in h.githost.fetches if p == V2_PATH]
        assert len(asked) == 1


def test_submit_postmortem_writes_v2_with_the_declared_model() -> None:
    h = make_harness()
    with h.client:
        world(h, reads_v2=True)
        token = h.token_for("code_alice", "alice")
        result = McpClient(h).call(
            "submit_postmortem",
            {"node_id": NODE, "yaml": record(model_and_tooling=MODEL)},
            token=token,
        )
        assert not result.isError, result.content
        _, doc = landed(h)
        assert doc["schema"] == "postmortem/v2" and doc["model_and_tooling"] == MODEL


def test_get_schema_serves_v2_once_the_graph_publishes_it(harness: Harness) -> None:
    harness.githost.files["schemas/postmortem/v2.json"] = schemas.schema_path(
        "postmortem/v2"
    ).read_bytes()
    harness.context.files.clear()
    served = McpClient(harness).ok("get_schema", {"name": "postmortem/v2"})
    assert served == schemas.load_schema("postmortem/v2")
    assert "model_and_tooling" in served["required"]


# --- opn-prove's draft ----------------------------------------------------------------------------


def test_opn_prove_drafts_v2_naming_the_prover_and_the_harness() -> None:
    """The client knows what ran (D-23): the run's program and the backend that drove it."""
    from test_prove_export import GRAPHS, prove  # noqa: PLC0415 — loads the client by path

    found = prove.find_node(GRAPHS / "propositional", "tutorial-and-swap", TARGET)
    run = {"program": "deepseek-prover-v2", "backend": "whole-file", "answered": False,
           "elapsed_s": 3.0, "timeout_s": 1800}  # fmt: skip
    draft = prove.postmortem(found, run, "alice", "computational")
    assert draft.get("schema") == "postmortem/v2"
    assert draft.get("model_and_tooling") == "deepseek-prover-v2 (opn-prove/whole-file)"
    assert schemas.violations(draft) == []
