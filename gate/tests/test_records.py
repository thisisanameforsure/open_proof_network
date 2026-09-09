"""F03-T1: loaders for attempts and status records (R7; Q3, Q5)."""

from __future__ import annotations

from pathlib import Path

import pytest
import samples
import yaml

from opn_gate import records, schemas


def write_yaml(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True, allow_unicode=True), encoding="utf-8")


def test_no_attempts_dir_is_empty(tmp_path: Path) -> None:
    summary = records.load_attempts(tmp_path)
    assert summary == records.AttemptSummary()
    assert summary.as_dict() == {
        "attempts": 0,
        "refuted_route_classes": [],
        "failure_class_histogram": {},
    }


def test_attempt_aggregation_counts_invalid(tmp_path: Path) -> None:
    """R7 at the loader: three postmortems and one invalid file; nothing dropped silently."""
    att = tmp_path / "attempts"
    write_yaml(att / "2026-09-01-a.yaml", samples.postmortem(route_class="induction"))
    write_yaml(
        att / "2026-09-02-b.yaml",
        samples.postmortem(route_class="case-split", failure_class="missing-library"),
    )
    write_yaml(
        att / "2026-09-03-c.yaml",
        samples.postmortem(
            route_class="induction", outcome="exhausted", failure_class="timeout-blowup"
        ),
    )
    (att / "2026-09-04-d.yaml").write_text("outcome: [unclosed\n", encoding="utf-8")
    (att / ".gitkeep").write_text("")
    (att / "notes.txt").write_text("not an attempt")
    summary = records.load_attempts(tmp_path)
    assert summary.count == 4
    assert summary.refuted_route_classes == ("case-split", "induction")
    assert summary.failure_class_histogram == {
        "route-dead-ends": 1,
        "missing-library": 1,
        "timeout-blowup": 1,
        "invalid": 1,
    }
    assert summary.invalid_files == ("2026-09-04-d.yaml",)
    assert list(summary.as_dict()["failure_class_histogram"]) == [
        "invalid",
        "missing-library",
        "route-dead-ends",
        "timeout-blowup",
    ]


def test_schema_invalid_attempt_is_invalid(tmp_path: Path) -> None:
    write_yaml(tmp_path / "attempts" / "x.yaml", samples.postmortem(outcome="gave-up"))
    summary = records.load_attempts(tmp_path)
    assert summary.count == 1 and summary.failure_class_histogram == {"invalid": 1}


def test_node_status_latest_wins(tmp_path: Path) -> None:
    assert records.load_node_status(tmp_path) is None
    st = tmp_path / "status"
    write_yaml(st / "2026-09-01-1.yaml", samples.node_status(status="disputed", date="2026-09-01"))
    write_yaml(st / "2026-09-03-1.yaml", samples.node_status(status="abandoned", date="2026-09-03"))
    write_yaml(st / "2026-09-02-9.yaml", samples.node_status(status="stale", date="2026-09-02"))
    rec = records.load_node_status(tmp_path)
    assert rec is not None and rec.status == "abandoned" and rec.date == "2026-09-03"
    # Same date: file name order decides.
    write_yaml(st / "2026-09-03-2.yaml", samples.node_status(status="stale", date="2026-09-03"))
    rec = records.load_node_status(tmp_path)
    assert rec is not None and rec.status == "stale" and rec.path.name == "2026-09-03-2.yaml"


def test_bad_status_record_raises(tmp_path: Path) -> None:
    """A malformed status record is a graph defect, never a silent default (C7)."""
    write_yaml(tmp_path / "status" / "x.yaml", samples.node_status(status="ready"))
    with pytest.raises(schemas.SchemaError):
        records.load_node_status(tmp_path)
    write_yaml(tmp_path / "t" / "status" / "x.yaml", samples.node_status())  # wrong schema
    with pytest.raises(schemas.SchemaError):
        records.load_target_status(tmp_path / "t")


def test_target_status(tmp_path: Path) -> None:
    assert records.load_target_status(tmp_path) is None
    write_yaml(
        tmp_path / "status" / "2026-09-09-1.yaml",
        samples.target_status(status="dormant", root="and-swap-reassoc"),
    )
    rec = records.load_target_status(tmp_path)
    assert rec is not None and rec.status == "dormant"
    assert rec.doc["root"] == "and-swap-reassoc" and rec.doc["claimable"] is True
