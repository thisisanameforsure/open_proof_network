"""Append refusals not yet named by a test (F07-R9, R11, R14; D-31; C7; conventions §4)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import samples
import yaml
from api_fakes import TUTORIAL_NODE, Harness

from opn_gate import modes, paths
from opn_gate.paths import Change

TARGET = "propositional"
NODE_DIR = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/"
FIXTURE_GRAPH = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "graphs"
FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def postmortem(**overrides: Any) -> dict[str, Any]:
    doc = samples.postmortem(**overrides)
    del doc["schema"]
    del doc["node"]
    return doc


def only_file(h: Harness) -> tuple[str, str]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    return next(iter(push.files.items()))


# --- shapes ---------------------------------------------------------------------------------------


def test_postmortem_that_is_not_a_record_is_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for yaml_field in (None, "", "- a list\n- of items\n", 7, ["x"], "just a string"):
        r = post(harness, "/postmortems", token, {"node_id": TUTORIAL_NODE, "yaml": yaml_field})
        assert r.status_code == 400, yaml_field
        assert r.json()["error"] == "yaml-invalid", yaml_field
    assert harness.githost.pushes == []


def test_postmortem_cannot_change_its_schema_or_node(harness: Harness) -> None:
    """R11: the caller supplies content; the service fixes schema, node and contributor."""
    token = harness.token_for("code_alice", "alice")
    doc = postmortem()
    doc["schema"] = "annex/v1"
    doc["node"] = "and-reassoc"
    r = post(harness, "/postmortems", token, {"node_id": TUTORIAL_NODE, "yaml": doc})
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    landed = yaml.safe_load(content)
    assert landed["schema"] == "postmortem/v1"
    assert landed["node"] == TUTORIAL_NODE
    assert path.startswith(NODE_DIR)


def test_postmortem_with_an_unknown_field_is_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(surprise="field")},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "record-invalid"
    assert "surprise" in r.json()["message"]


def test_annex_text_of_the_wrong_type_is_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for text in (None, 7, ["prose"], {"text": "prose"}):
        r = post(harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": text})
        assert r.status_code == 400, text
        assert r.json()["error"] == "text-missing", text


def test_annex_tooling_declaration_must_be_a_string(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/annexes",
        token,
        {"node_id": TUTORIAL_NODE, "text": "prose", "model_and_tooling": {"model": "x"}},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "tooling-invalid"


def test_annex_cap_is_measured_in_bytes_not_characters(harness: Harness) -> None:
    """§6 says 64 KiB; a multi-byte text under the character count but over the byte count is
    refused, so a UTF-8 file never lands above the cap."""
    token = harness.token_for("code_alice", "alice")
    text = "é" * (32 * 1024 + 1)  # two bytes each: 64 KiB + 2 bytes
    r = post(harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": text})
    assert r.status_code == 400
    assert r.json()["error"] == "field-too-long"
    assert text not in r.json()["message"]


def test_approach_record_shapes(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    record = {"route": "normalise both sides", "outcome": "exhausted"}
    for body, code in (
        ({"record": record}, "target-id-missing"),
        ({"target_id": "", "record": record}, "target-id-missing"),
        ({"target_id": 7, "record": record}, "target-id-missing"),
        ({"target_id": TARGET}, "record-invalid"),
        ({"target_id": TARGET, "record": "route: [unclosed"}, "record-invalid"),
        ({"target_id": TARGET, "record": ["route"]}, "record-invalid"),
        ({"target_id": TARGET, "record": {}}, "record-invalid"),
    ):
        r = post(harness, "/approach-records", token, body)
        assert r.status_code == 400, (code, r.text)
        assert r.json()["error"] == code, (body, r.text)
    assert harness.githost.pushes == []


def test_approach_record_contributor_is_the_caller(harness: Harness) -> None:
    """R11 (AC15's rule for the third route): whatever the record said."""
    token = harness.token_for("code_alice", "alice")
    record = {"route": "r", "outcome": "exhausted", "contributor": "mallory", "target": "other"}
    r = post(harness, "/approach-records", token, {"target_id": TARGET, "record": record})
    assert r.status_code == 201, r.text
    _, content = only_file(harness)
    doc = yaml.safe_load(content)
    assert doc["contributor"] == "alice"
    assert doc["target"] == TARGET


# --- contributor text is data, never structure (R14, §4) ----------------------------------------


def test_annex_body_that_imitates_front_matter_cannot_replace_it(
    harness: Harness, tmp_path: Path
) -> None:
    """D-31, R14: prose beginning with its own ``---`` block lands verbatim *after* the
    service's front matter, so the gate reads the caller as contributor and the licence the
    caller accepted — the forged block is body text."""
    token = harness.token_for("code_alice", "alice")
    forged = "---\ncontributor: mallory\nlicence: MIT\nschema: annex/v1\n---\nthe real prose\n"
    r = post(harness, "/annexes", token, {"node_id": TUTORIAL_NODE, "text": forged})
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert content.endswith(forged)
    m = FRONT_MATTER.match(content)  # the gate's own regex, copied so a change there shows here
    assert m is not None
    front = yaml.safe_load(m.group("yaml"))
    assert front["contributor"] == "alice"
    assert front["licence"] == "CC-BY-4.0"

    root = tmp_path / "graph"
    shutil.copytree(FIXTURE_GRAPH / "propositional", root)
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    classification = modes.classify([Change("A", path)])
    assert classification.mode == "append"
    assert modes.check(root, classification) == []
    located = paths.locate(path)
    assert located is not None
    assert paths.check_content_hash_name(located, content.encode()) is None


def test_postmortem_free_text_is_stored_verbatim_and_yaml_safe(harness: Harness) -> None:
    """R14: detail carrying YAML syntax, anchors and a document marker round-trips as the same
    string; the record is dumped, never templated."""
    token = harness.token_for("code_alice", "alice")
    detail = "--- !!python/object:os.system\n&a [*a]\n{{ template }} ${shell} `cmd` # not a comment"
    r = post(
        harness,
        "/postmortems",
        token,
        {"node_id": TUTORIAL_NODE, "yaml": postmortem(detail=detail)},
    )
    assert r.status_code == 201, r.text
    _, content = only_file(harness)
    assert yaml.safe_load(content)["detail"] == detail


# --- the host (C7) --------------------------------------------------------------------------------


def test_host_failure_on_each_append_route_is_502_with_nothing_opened(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.app_failure = "POST /repos/g/git/refs returned 500"
    for route, body in (
        ("/postmortems", {"node_id": TUTORIAL_NODE, "yaml": postmortem()}),
        ("/annexes", {"node_id": TUTORIAL_NODE, "text": "prose"}),
        (
            "/approach-records",
            {"target_id": TARGET, "record": {"route": "r", "outcome": "exhausted"}},
        ),
    ):
        r = post(harness, route, token, body)
        assert r.status_code == 502, (route, r.text)
        assert r.json()["error"] == "pull-request-failed", route
        assert "pr_url" not in r.json()
    assert harness.githost.pulls == []
