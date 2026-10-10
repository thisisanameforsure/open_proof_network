"""F25-T1 / AC1: every product version the gate emits is accepted by every reader of it.

The 2026-09-11 lesson: a one-field schema bump reaches consumers nobody would look at — the
api's field filters, both smokes, the deploy package check, the site's accepted-versions map.
This test makes the sweep permanent for the products the site and the api read by version
string, so a bump that forgets a reader is red here rather than on the first deploy.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_gate import attestation, bounce, intake, ledger, products, submission

ROOT = Path(__file__).resolve().parents[2]


def test_the_site_accepts_what_the_gate_emits() -> None:
    from opn_site import model  # noqa: PLC0415 — the site package, on the path in tests

    accepted = model.PRODUCT_SCHEMAS
    assert products.INDEX_SCHEMA in accepted["targets/index.json"]
    assert products.GRAPH_SCHEMA in accepted["graph.json"]
    assert products.FRONTIER_SCHEMA in accepted["frontier.json"]


def test_the_gate_reads_every_version_it_writes() -> None:
    assert attestation.SCHEMA in bounce.ACCEPTED_SCHEMAS
    assert submission.SCHEMA in submission.ACCEPTED_SCHEMAS
    assert ledger.SCHEMA in ledger.ACCEPTED_SCHEMAS
    assert intake.SCHEMA in intake.READABLE_SCHEMAS


def test_no_reader_outside_tests_pins_a_superseded_products_version_alone() -> None:
    """A source file that names an *older* targets-index or graph version as a constant it
    emits is a reader that will drift; naming it in an accepted set or a comment is fine."""
    pattern = re.compile(r'(INDEX_SCHEMA|GRAPH_SCHEMA)\s*=\s*"([a-z-]+/v\d+)"')
    for path in (ROOT / "gate" / "opn_gate").rglob("*.py"):
        for m in pattern.finditer(path.read_text(encoding="utf-8")):
            assert m.group(2) in (products.INDEX_SCHEMA, products.GRAPH_SCHEMA), (path, m.group(0))
