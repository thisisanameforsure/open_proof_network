"""postmortem/v2 (D-13, D-23): a postmortem says what drafted it.

``annex/v2``, ``literature/v2`` and ``approach-record/v1`` each carry ``model_and_tooling``, the
operator's own declaration of what drafted the record, never verified; ``postmortem/v1`` had no
such field, so a postmortem an agent wrote could not say so. ``postmortem/v2`` is v1 plus that
field, shaped as ``approach-record/v1`` shapes it (null, or a string of 1 to 200 characters) and
required as the newest of the three (``literature/v2``) requires it: a record states its model,
or states ``null``. D-34 versions, never edits, so every reader keeps a *set*: the v1 records
already on the graph are read as they always were.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml

from opn_gate import context, curator, demarcate, paths, records, schemas

V2 = "postmortem/v2"
MODEL = "claude-opus-5-5 via opn-mcp"


def v2(**overrides: Any) -> dict[str, Any]:
    doc = samples.postmortem(schema=V2, model_and_tooling=MODEL)
    doc.update(overrides)
    return doc


def write_yaml(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True, allow_unicode=True), encoding="utf-8")


# --- the schema -----------------------------------------------------------------------------------


def test_a_v2_record_validates_with_a_model_or_null() -> None:
    assert schemas.violations(v2()) == []
    assert schemas.violations(v2(model_and_tooling=None)) == []


def test_v2_requires_the_field_as_literature_v2_does() -> None:
    doc = v2()
    del doc["model_and_tooling"]
    assert schemas.violations(doc)


@pytest.mark.parametrize("bad", ["", "x" * 201, 7, ["a"]])
def test_v2_model_and_tooling_is_shaped_as_approach_record_v1s(bad: object) -> None:
    assert schemas.violations(v2(model_and_tooling=bad))
    assert schemas.violations(v2(model_and_tooling="x" * 200)) == []


def test_v2_field_is_approach_record_v1s_field_exactly() -> None:
    mine = schemas.load_schema(V2)["properties"]["model_and_tooling"]
    theirs = schemas.load_schema("approach-record/v1")["properties"]["model_and_tooling"]
    assert mine == theirs


def test_v2_is_v1_plus_the_one_field() -> None:
    """Nothing else changed: same properties, same required list, bar the new field."""
    one, two = schemas.load_schema("postmortem/v1"), schemas.load_schema(V2)
    assert two["$id"].endswith("/postmortem/v2.json") and two["title"] == V2
    assert two["properties"]["schema"] == {"const": V2}
    assert set(two["properties"]) - set(one["properties"]) == {"model_and_tooling"}
    for key, value in one["properties"].items():
        if key != "schema":
            assert two["properties"][key] == value, key
    assert two["required"] == [*one["required"], "model_and_tooling"]


def test_v1_records_still_validate_and_v1_still_refuses_the_field() -> None:
    """D-34: v1 is untouched, so the graph's v1 records read forever and v1 stays closed."""
    assert schemas.violations(samples.postmortem()) == []
    assert schemas.violations(samples.postmortem(model_and_tooling=MODEL))


def test_v2_is_pinned_and_published() -> None:
    assert schemas.verify_pins() == []
    assert V2 in schemas.known_schemas()


def test_the_graph_publishes_v2(tmp_path: Path) -> None:
    """``get_schema`` serves the graph's ``schemas/``; a re-pin's publish puts v2 there."""
    added = schemas.publish(tmp_path)
    assert V2 in added and "postmortem/v1" in added
    published = (tmp_path / "schemas" / "postmortem" / "v2.json").read_bytes()
    assert published == schemas.schema_path(V2).read_bytes()


# --- the readers keep a set -----------------------------------------------------------------------


def test_the_append_path_takes_both_versions() -> None:
    assert paths.SCHEMAS_FOR_ROLE["postmortem"] == ("postmortem/v1", V2)
    assert records.POSTMORTEM_SCHEMAS == ("postmortem/v1", V2)


def test_a_writer_writes_v2() -> None:
    assert records.POSTMORTEM_SCHEMA == V2


def test_load_attempts_reads_v1_and_v2_alike(tmp_path: Path) -> None:
    att = tmp_path / "attempts"
    write_yaml(att / "2026-10-27-a.yaml", samples.postmortem(failure_class="missing-library"))
    write_yaml(att / "2026-10-28-b.yaml", v2(outcome="refuted-route", route_class="computational"))
    summary = records.load_attempts(tmp_path)
    assert summary.invalid_files == ()
    assert summary.count == 2
    assert summary.refuted_route_classes == ("computational", "induction")
    assert summary.failure_class_histogram == {"missing-library": 1, "route-dead-ends": 1}


def test_a_record_declaring_another_schema_is_not_a_postmortem(tmp_path: Path) -> None:
    """The set is what is pinned: a valid document of another kind still counts as invalid."""
    att = tmp_path / "attempts"
    write_yaml(att / "2026-10-28-x.yaml", samples.node_status())
    write_yaml(att / "2026-10-28-y.yaml", {**v2(), "schema": "postmortem/v3"})
    summary = records.load_attempts(tmp_path)
    assert summary.invalid_files == ("2026-10-28-x.yaml", "2026-10-28-y.yaml")


def test_the_context_bundle_carries_a_v2_record_with_its_model_demarcated(tmp_path: Path) -> None:
    node = "targets/t/nodes/n"
    write_yaml(tmp_path / node / "attempts" / "2026-10-28-b.yaml", v2())
    write_yaml(tmp_path / node / "attempts" / "2026-10-27-a.yaml", samples.postmortem())
    got = context._attempts(context.DiskReader(tmp_path), node)
    assert not any(r.get("invalid") for r in got["records"]), got["records"]
    newest = got["records"][-1]["record"]
    assert newest["schema"] == V2
    assert newest["model_and_tooling"] == demarcate.wrap(
        MODEL, f"{node}/attempts/2026-10-28-b.yaml"
    )


def test_demarcate_wraps_a_postmortems_declared_model() -> None:
    """The declaration is contributor text (D-28), as it is on an approach record or an annex."""
    assert "model_and_tooling" in demarcate.FREE_TEXT["postmortem"]
    assert demarcate.record({**v2(), "model_and_tooling": None}, "p")["model_and_tooling"] is None


def test_the_missing_library_report_counts_v2_records(tmp_path: Path) -> None:
    att = tmp_path / "targets" / "t" / "nodes" / "n" / "attempts"
    lemma = {"missing_lemmas": ["a uniform bound"]}
    write_yaml(att / "1.yaml", samples.postmortem(failure_class="missing-library", artifacts=lemma))
    write_yaml(att / "2.yaml", v2(failure_class="missing-library", artifacts=lemma))
    [found] = curator.missing_library_report(tmp_path, "t", threshold=2)
    assert found.count == 2
