"""Finding protocol-version (testers 2026-10-09, B4): ``PROTOCOL_VERSION`` said 3.28 while the
decisions document stood at v3.35.

Every application from v3.21 to v3.28 bumped the constant by hand and v3.29 to v3.35 did not, so
``info.json`` and the MCP server's ``serverInfo.version`` published a protocol seven amendments
old. The constant is held to the version the document's own header names, so an amendment that
is applied without the bump fails here rather than on the record.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_gate.products import PROTOCOL_VERSION

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "architecture_decisions.html"
#: The document's header line: ``<p class="meta"><b>v3.35</b> · 2026-10-08 · ...``.
HEADER = re.compile(r'<p class="meta"><b>v(\d+\.\d+)</b>')


def test_protocol_version_is_the_decisions_documents() -> None:
    found = HEADER.search(DECISIONS.read_text(encoding="utf-8"))
    assert found, "the decisions document's header names no version"
    assert found.group(1) == PROTOCOL_VERSION
