"""F07-T3: the three append routes (R11, R14; AC14, AC15, AC19).

An append claims nothing, so the whole of its checking is its schema and its path. What the
service adds is the identity: the contributor on the record is the caller, whatever the caller
wrote, and the free text is capped before it is stored verbatim.
"""

from __future__ import annotations

from typing import Any

import samples
import yaml
from api_fakes import TUTORIAL_NODE, Harness

from opn_api import appends
from opn_gate import modes, paths, schemas
from opn_gate.paths import Change

NODE_DIR = f"targets/propositional/nodes/{TUTORIAL_NODE}/"
TARGET = "propositional"


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def only_file(h: Harness) -> tuple[str, str]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    return next(iter(push.files.items()))


def postmortem(**overrides: Any) -> dict[str, Any]:
    doc = samples.postmortem(**overrides)
    del doc["schema"]
    del doc["node"]
    return doc


# --- POST /postmortems (D-13) ---------------------------------------------------------------------


def test_contributor_is_caller(harness: Harness) -> None:
    """AC15: a record naming someone else is stored under the caller's identity."""
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(contributor="somebody-else")},
    )
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    doc = yaml.safe_load(content)
    assert doc["contributor"] == "alice"
    assert doc["node"] == TUTORIAL_NODE
    assert doc["schema"] == "postmortem/v1"
    assert path.startswith(NODE_DIR + "attempts/")
    assert path.endswith("-alice.yaml")
    assert r.json()["path"] == path
    assert r.json()["pr_url"].endswith("/pull/1")

    # The commit is the contributor's, signed off, as a submission's is (R11 -> R2).
    push = harness.githost.pushes[-1]
    assert push.author is not None and push.author.name == "alice"
    assert push.message.endswith("Signed-off-by: alice <alice@anon.opn.invalid>\n")


def test_postmortem_accepts_yaml_text_and_rejects_bad_records(harness: Harness) -> None:
    """R11: the record may arrive as YAML or as an object; either way it must validate."""
    token = harness.token_for("code_alice", "alice")
    as_text = yaml.safe_dump(postmortem(), sort_keys=True)
    sent = post(harness, "/postmortems", token, {"node_id": TUTORIAL_NODE, "yaml": as_text})
    assert sent.status_code == 201

    bad = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(outcome="gave-up")},
    )
    assert bad.status_code == 400
    assert bad.json()["error"] == "record-invalid"
    assert "outcome" in bad.json()["message"]

    unparseable = post(
        harness, "/postmortems", token, {"node_id": TUTORIAL_NODE, "yaml": "route: [unclosed"}
    )
    assert unparseable.status_code == 400
    missing_node = post(harness, "/postmortems", token, {"yaml": postmortem()})
    assert missing_node.status_code == 400
    unknown_node = post(
        harness, "/postmortems", token, {"node_id": "no-such-node", "yaml": postmortem()}
    )
    assert unknown_node.status_code == 404


def test_free_text_caps(harness: Harness) -> None:
    """AC19, R14: a 5,000-character detail is refused, naming the field and the cap — and the
    text is not echoed back."""
    token = harness.token_for("code_alice", "alice")
    long_detail = "x" * 5000
    r = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(detail=long_detail)},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "field-too-long"
    message = r.json()["message"]
    assert "detail" in message and "4000" in message
    assert long_detail not in message
    assert harness.githost.pushes == []

    # The cap is the schema's, so a record one character under it is accepted.
    cap = schemas.load_schema("postmortem/v1")["properties"]["detail"]["maxLength"]
    ok = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(detail="x" * cap)},
    )
    assert ok.status_code == 201


# --- POST /annexes (D-31) -------------------------------------------------------------------------


def test_annex_hash(harness: Harness) -> None:
    """AC14: the returned hash is the file's, is its name, and the gate accepts what lands."""
    token = harness.token_for("code_alice", "alice")
    text = "The route is symmetry: both conjuncts are already in hand.\n"
    r = post(harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": text})
    assert r.status_code == 201, r.text
    digest = r.json()["hash"]
    path, content = only_file(harness)
    assert path == f"{NODE_DIR}annex/{digest}.md"
    assert digest == schemas.content_hash(content.encode())
    assert content.endswith(text)  # the prose is stored verbatim (R14)

    front = yaml.safe_load(content.split("---\n")[1])
    assert front == {
        "schema": "annex/v1",
        "node": TUTORIAL_NODE,
        "contributor": "alice",
        "licence": "CC-BY-4.0",
        "date": "2026-09-09T12:00:00Z",
        "model_and_tooling": None,
    }

    # What the service writes is what the gate accepts: the same file through the same checks.
    located = paths.locate(path)
    assert located is not None and located.role == "annex"
    assert paths.check_content_hash_name(located, content.encode()) is None
    assert modes.classify([Change("A", path)]).mode == "append"


def test_annex_licence_and_caps(harness: Harness) -> None:
    """D-23: annex prose is licensed by its author or is not accepted; §6 caps the file."""
    token = harness.token_for("code_alice", "alice")
    chosen = post(
        harness,
        "/annexes",
        token,
        {"node_id": TUTORIAL_NODE, "text": "prose", "licence": "Apache-2.0"},
    )
    assert chosen.status_code == 201
    _, content = only_file(harness)
    assert "licence: Apache-2.0" in content

    refused = post(
        harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": "prose", "licence": "MIT"}
    )
    assert refused.status_code == 400
    assert refused.json()["error"] == "licence-invalid"

    empty = post(harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": "   "})
    assert empty.status_code == 400

    huge = post(
        harness,
        "/annexes",
        token,
        {"node_id": TUTORIAL_NODE, "text": "x" * (appends.ANNEX_MAX_BYTES + 1)},
    )
    assert huge.status_code == 400
    assert huge.json()["error"] == "field-too-long"


# --- POST /approach-records (D-14) ----------------------------------------------------------------


def test_approach_record(harness: Harness) -> None:
    """R11: a target-scoped strategy record, contributed under the caller's identity."""
    token = harness.token_for("code_alice", "alice")
    record = {"route": "normalise both sides and compare", "outcome": "exhausted"}
    r = post(harness, "/approach-records", token, {"target_id": TARGET, "record": record})
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path.startswith(f"targets/{TARGET}/approaches/")
    assert path.endswith("-alice.yaml")
    doc = yaml.safe_load(content)
    assert doc["contributor"] == "alice"
    assert doc["target"] == TARGET
    assert doc["schema"] == "approach-record/v1"
    assert doc["pinned_mathlib_sha"] is None
    assert schemas.violations(doc, "approach-record/v1") == []
    located = paths.locate(path)
    assert located is not None and located.role == "approach-record"

    unknown = post(harness, "/approach-records", token, {"target_id": "nowhere", "record": record})
    assert unknown.status_code == 404
    bad = post(
        harness,
        "/approach-records",
        token,
        {"target_id": TARGET, "record": {**record, "outcome": "ran-out"}},
    )
    assert bad.status_code == 400
    long_route = post(
        harness,
        "/approach-records",
        token,
        {"target_id": TARGET, "record": {**record, "route": "x" * 501}},
    )
    assert long_route.status_code == 400
    assert long_route.json()["error"] == "field-too-long"


def test_appends_need_a_token(harness: Harness) -> None:
    for route, body in (
        ("/postmortems", {"node_id": TUTORIAL_NODE, "yaml": postmortem()}),
        ("/annexes", {"node_id": TUTORIAL_NODE, "text": "prose"}),
        ("/approach-records", {"target_id": TARGET, "record": {}}),
    ):
        assert harness.client.post(route, json=body).status_code == 401
    assert harness.githost.pushes == []
