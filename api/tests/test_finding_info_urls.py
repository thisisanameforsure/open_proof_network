"""F05-T25 (audit 2026-10-04): ``info.json`` names the guide and the errors catalog (``info/v2``).

An agent that arrives with nothing but the service's ``/info.json`` (D-28 ``server_info``) learned
the protocol version, the schemas and the rate limits, and not where the contributor guide is or
where an error code is explained. ``info/v2`` adds ``guide_url`` and ``errors_url``. The committed
product is the graph's and carries ``null`` for both — the gate does not know where the service
or the guide is deployed, and the products must regenerate byte for byte from the tree (F03-R11)
— and the service fills them from its own configuration on every read, as it already fills
``rate_limit_policy`` (R6): ``OPN_API_GUIDE_URL`` (default the graph's ``AGENTS.md``) and
``OPN_API_PUBLIC_URL`` plus ``/errors.json``. No hostname is written into code that serves a page.

The live graph's products stay ``info/v1`` until its re-pin, so the service serves both.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api_fakes import Harness, make_harness
from harness import copy_graph

from opn_gate import products, schemas

PUBLIC = "https://api.example.test"
GUIDE = "https://docs.example.test/guide"


def committed_info(tmp_path: Path) -> bytes:
    """The info.json the gate renders today for the propositional fixture — a golden by
    construction (F05-Q5), so this test cannot pass against a shape the gate does not produce."""
    root = copy_graph(tmp_path, publish=True)
    built = products.generate(root, rendered_from="5" * 40, commit_time="2026-09-09T12:00:00Z")
    return built.files[Path("info.json")]


def serve(h: Harness, body: bytes) -> dict[str, Any]:
    h.githost.files["info.json"] = body
    h.context.files.clear()
    r = h.client.get("/info.json")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def test_the_service_names_the_guide_and_the_errors_catalog(tmp_path: Path) -> None:
    h = make_harness({"OPN_API_PUBLIC_URL": PUBLIC, "OPN_API_GUIDE_URL": GUIDE})
    body = committed_info(tmp_path)
    committed = json.loads(body)
    doc = serve(h, body)
    assert doc.get("guide_url") == GUIDE, "info.json does not name the contributor guide"
    assert doc.get("errors_url") == f"{PUBLIC}/errors.json"
    assert doc["schema"] == "info/v2" == products.INFO_SCHEMA
    assert schemas.violations(doc) == []
    # The committed product names neither: where things are deployed is the service's to say.
    assert (committed["guide_url"], committed["errors_url"]) == (None, None)
    filled = ("guide_url", "errors_url", "rate_limit_policy")
    assert {k: v for k, v in doc.items() if k not in filled} == {
        k: v for k, v in committed.items() if k not in filled
    }


def test_the_guide_defaults_to_the_graphs_agents_md(tmp_path: Path) -> None:
    """With no guide configured, the guide is the one ``GET /`` already names: the graph
    repository's ``AGENTS.md`` at the graph branch (D-35: contributors clone the graph only)."""
    h = make_harness({"OPN_API_GRAPH_REPO": "someone/graph", "OPN_API_GRAPH_BRANCH": "trunk"})
    doc = serve(h, committed_info(tmp_path))
    assert doc["guide_url"] == h.settings.guide_url
    assert doc["guide_url"].endswith("/someone/graph/blob/trunk/AGENTS.md")
    assert h.client.get("/").json()["guide"] == doc["guide_url"]


def test_an_info_v1_document_is_still_served(harness: Harness) -> None:
    """D-34: a consumer parses by version. The fixture is the v1 document; it is served as v1,
    with the policy filled and nothing a v1 document may not carry."""
    doc = harness.client.get("/info.json").json()
    assert doc["schema"] == "info/v1"
    assert schemas.violations(doc) == []
    assert "guide_url" not in doc and "errors_url" not in doc
