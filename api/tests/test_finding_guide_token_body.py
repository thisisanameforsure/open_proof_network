"""F10: the guide gives ``POST /tokens``'s body, and the body it gives is accepted.

Tester finding 2026-09-27: agents needed three tries to mint a token, because the guide's
"Getting a token" section named the parts in prose (``proof``, a ``pseudonym``, "the current
``dco`` version") and never showed the body; the only literal shape sat inside a Python
heredoc in the claiming walkthrough. The working body is ``dco: {accepted: true, version}``
beside ``pseudonym`` and ``proof``.

The rule. The section carries one ```json block with the body, and that block, with its
placeholders filled from a real passing tutorial precheck, is what ``POST /tokens`` answers
``201`` to — so the example cannot drift from the route.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from api_fakes import Harness, PrecheckKey, make_precheck_key

from opn_api import identity

GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def token_section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("## Getting a token")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def documented_body() -> dict[str, object]:
    blocks = re.findall(r"```json\n(.*?)```", token_section(), re.S)
    assert len(blocks) == 1, "the token section shows POST /tokens's body as one json block"
    body: dict[str, object] = json.loads(blocks[0])
    return body


def test_the_section_shows_the_body() -> None:
    body = token_section()
    assert "```json" in body


def test_the_documented_body_is_what_the_route_takes(harness: Harness, key: PrecheckKey) -> None:
    body = documented_body()
    assert set(body) == set(identity.TOKEN_FIELDS)
    assert isinstance(body["dco"], dict)
    assert body["dco"]["accepted"] is True
    assert isinstance(body["proof"], dict)
    assert body["proof"]["kind"] == "tutorial"
    job = harness.tutorial_job(key)
    filled = {
        **body,
        "pseudonym": "guide-reader",
        "proof": {**body["proof"], "job_id": job["id"], "nonce": job["nonce"]},
        "dco": {**body["dco"], "version": identity.DCO_VERSION},
    }
    r = harness.client.post("/tokens", json=filled)
    assert r.status_code == 201, r.text
