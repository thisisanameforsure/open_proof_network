"""F04-T50: where a part of a statement's page sits since the page reads top down.

A section (``explainer``, ``how``, ``known``, ``work``, ``record``) runs from its opening tag to the
comment closing it; a part of the record is a closed ``<details>`` named by its summary.
"""

from __future__ import annotations

import re


def node_section(page: str, name: str) -> str:
    """The section's HTML, heading included; ``AssertionError`` when the page has none."""
    m = re.search(
        rf'<section class="node-sec" data-section="{name}"[^>]*>(.*?)</section><!--/{name}-->',
        page,
        re.S,
    )
    assert m is not None, f"no {name} section"
    return m.group(1)


def record_part(page: str, summary: str) -> str:
    """The record's fold whose summary starts with ``summary``, summary included."""
    record = node_section(page, "record")
    m = re.search(
        rf'<details class="fold rec"[^>]*><summary>{re.escape(summary)}.*?</details>'
        r'(?=<details class="fold rec"|</div>$)',
        record,
        re.S,
    )
    assert m is not None, f"no record part {summary!r}"
    return m.group(0)
