"""F04-T56: the site reads a literature record by the schema it declares (D-25 v3.45).

Found 2026-10-21 rendering the live erdos-257 for F30-T11's evidence: since F08-T43 the gate writes
``literature/v2``, while the site's reader validated every record against ``literature/v1``, so a v2
record (erdos-257's, written 2026-10-19) was carried as unreadable and its page said "Its record
could not be read at this commit". A record is read by its own declared schema, among those the
gate accepts (``literature.SCHEMAS``); a record declaring none of them is still unreadable.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from opn_gate import literature, schemas
from opn_site import model

RECORD = "literature/20261019T205105Z-fable-1019-e257.yaml"


def _record(schema: str, **extra: object) -> dict[str, object]:
    return {
        "schema": schema,
        "node": "n",
        "contributor": "fable-1019-e257",
        "date": "2026-10-19T20:51:05Z",
        "status": "open",
        "references": [
            {"title": "T. F. Bloom, Erdős Problem #257", "url": "https://example.org", "note": None}
        ],
        "summary": "Open in general.",
        "model_and_tooling": "a model",
        "confirms": None,
        "via": None,
        "key": None,
        "signature": None,
        # the shape of the live erdos-257 record (graph 8fcb13861); v1 has no `disputes`
        **({"disputes": None} if schema == "literature/v2" else {}),
        **extra,
    }


def _view(tmp_path: Path, doc: dict[str, object]) -> model.LiteratureView | None:
    node_dir = tmp_path / "targets" / "t" / "nodes" / "n"
    (node_dir / "literature").mkdir(parents=True)
    (node_dir / RECORD).write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    raw = {"status": "open", "record": RECORD, "contributor": "fable-1019-e257"}
    return model._literature_for(tmp_path, node_dir, raw)


def test_the_fixtures_are_valid_records() -> None:
    """The red runs below must fail on the reader, never on a malformed fixture."""
    for schema in literature.SCHEMAS:
        assert schemas.violations(_record(schema), schema) == [], schema


def test_a_v2_record_is_read(tmp_path: Path) -> None:
    assert literature.SCHEMA == "literature/v2"
    view = _view(tmp_path, _record("literature/v2"))
    assert view is not None
    assert view.readable, "a literature/v2 record was carried as unreadable"
    assert [r.title for r in view.references] == ["T. F. Bloom, Erdős Problem #257"]


def test_a_v1_record_is_still_read(tmp_path: Path) -> None:
    view = _view(tmp_path, _record("literature/v1"))
    assert view is not None and view.readable


def test_a_record_declaring_no_known_schema_is_unreadable(tmp_path: Path) -> None:
    view = _view(tmp_path, _record("literature/v9"))
    assert view is not None and not view.readable
