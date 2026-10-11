"""A cap a schema states inside ``oneOf`` is a cap too (testers on erdos-1094, 2026-10-08).

Found while the guide was taught every approach-record cap (F10-T18): ``approach-record/v1``
states ``model_and_tooling`` as ``oneOf [null, string maxLength 200]``, and ``check_caps`` read
``maxLength`` at the top of a property only. So a 201-character declaration was refused by
validation instead, as ``400 record-invalid`` with the whole text in the message — the echo
R14's cap check exists to prevent ("a 5,000-character detail must not travel twice").
"""

from __future__ import annotations

from typing import Any

from api_fakes import Harness

TARGET = "propositional"
RECORD = {"route": "normalise both sides and compare", "outcome": "exhausted"}


def _post(h: Harness, record: dict[str, Any]) -> Any:
    token = h.token_for("code_alice", "alice")
    return h.client.post(
        "/approach-records", json={"target_id": TARGET, "record": record}, headers=h.auth(token)
    )


def test_a_cap_inside_one_of_is_refused_by_name_without_echoing_the_text(
    harness: Harness,
) -> None:
    text = "y" * 5000
    r = _post(harness, {**RECORD, "model_and_tooling": text})
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "field-too-long", body
    assert "model_and_tooling" in body["message"]
    assert "200" in body["message"]
    assert text not in r.text


def test_a_null_declaration_is_still_accepted(harness: Harness) -> None:
    r = _post(harness, {**RECORD, "model_and_tooling": None})
    assert r.status_code == 201, r.text


def test_a_declaration_at_the_cap_is_accepted(harness: Harness) -> None:
    r = _post(harness, {**RECORD, "model_and_tooling": "y" * 200})
    assert r.status_code == 201, r.text
