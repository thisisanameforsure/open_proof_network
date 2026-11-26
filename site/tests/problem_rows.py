"""F34-T5: a problem's row on the Problems page, wherever it sits.

A problem with work on the record is an ``<article class="prow">`` in "With work on the record";
a waiting one is a ``<tr>`` in "Waiting for a first steward". Each carries ``data-id``.
"""

from __future__ import annotations

import re


def problem_row(page: str, target_id: str) -> str:
    """The row's HTML, from its opening tag to its close (one row per problem, F34-AC7)."""
    m = re.search(rf'<(article|tr)\b[^>]*\bdata-id="{re.escape(target_id)}"', page)
    assert m is not None, f"no row for {target_id}"
    tag = m.group(1)
    end = page.index(f"</{tag}>", m.start())
    return page[m.start() : end + len(tag) + 3]


def row_ids(page: str) -> list[str]:
    return re.findall(r'<(?:article|tr)\b[^>]*\bdata-id="([^"]+)"', page)
