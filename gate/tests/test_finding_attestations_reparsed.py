"""Finding attestations-reparsed (2026-11-24, after the bulk load): a render took 18 minutes.

Profiled on 40 of the live graph's 443 targets (network 90807562, graph 6d6ee88b): 236 of 244
seconds were ``graph.load_attestations``, which read and schema-validated every one of the graph's
295 attestation files on every call, and ``load_target`` (which calls it) ran nine times a target,
through ``qa.root_node`` and the fidelity grades. The cost grew as targets x attestations x 9, so
a render outran the gap between merges, every publish retry re-rendered, and the products never
landed (render 45420442037: refused at 15:19, 15:36 and 15:54, then the 60-minute timeout).

Each file is parsed once per process now, and again only when it changes: the cache is keyed by
the file's path, size and modification time, so a file the post-merge job writes mid-run is read,
a changed one is read again and a deleted one is gone. Counted at ``schemas.load_json``, the seam
that does the parse and the validation, never by the clock.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from opn_gate import graph, schemas


class Reads:
    """``schemas.load_json`` as a counter: the attestation files read, in order."""

    def __init__(self) -> None:
        self.paths: list[str] = []

    def __call__(self, path: Path, schema_id: str | None = None) -> dict[str, Any]:
        self.paths.append(Path(path).name)
        doc: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return doc


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> Reads:
    r = Reads()
    monkeypatch.setattr(schemas, "load_json", r)
    return r


def write(root: Path, name: str, doc: dict[str, Any]) -> Path:
    path = root / "attestations" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def graph_with(tmp_path: Path, n: int) -> Path:
    for i in range(n):
        write(tmp_path, f"a{i:03d}.json", {"n": i})
    return tmp_path


def test_each_attestation_is_parsed_once_across_calls(tmp_path: Path, reads: Reads) -> None:
    root = graph_with(tmp_path, 12)
    first = graph.load_attestations(root)
    for _ in range(8):  # load_target ran nine times a target
        assert graph.load_attestations(root) == first
    assert len(reads.paths) == 12, f"{len(reads.paths)} parses for 12 files over 9 calls"


def test_a_new_file_is_read_and_a_deleted_one_is_gone(tmp_path: Path, reads: Reads) -> None:
    root = graph_with(tmp_path, 3)
    graph.load_attestations(root)
    write(root, "a100.json", {"n": 100})
    (root / "attestations" / "a000.json").unlink()
    names = [name for name, _ in graph.load_attestations(root)]
    assert names == ["a001.json", "a002.json", "a100.json"]
    assert reads.paths.count("a100.json") == 1


def test_a_changed_file_is_read_again(tmp_path: Path, reads: Reads) -> None:
    root = graph_with(tmp_path, 2)
    graph.load_attestations(root)
    path = write(root, "a001.json", {"n": 1, "changed": True})  # a different size
    assert dict(graph.load_attestations(root))["a001.json"] == {"n": 1, "changed": True}
    # The same size, a later modification time: still read again.
    path.write_text(json.dumps({"n": 7, "changed": True}), encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert dict(graph.load_attestations(root))["a001.json"] == {"n": 7, "changed": True}


def test_two_graphs_do_not_share_entries(tmp_path: Path, reads: Reads) -> None:
    one = graph_with(tmp_path / "one", 1)
    two = tmp_path / "two"
    write(two, "a000.json", {"n": "other"})
    assert dict(graph.load_attestations(one))["a000.json"] == {"n": 0}
    assert dict(graph.load_attestations(two))["a000.json"] == {"n": "other"}


def test_a_malformed_attestation_is_still_a_graph_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = graph_with(tmp_path, 1)

    def refuse(path: Path, schema_id: str | None = None) -> dict[str, Any]:
        msg = "not an attestation"
        raise schemas.SchemaError(msg)

    monkeypatch.setattr(schemas, "load_json", refuse)
    with pytest.raises(graph.GraphError, match="malformed"):
        graph.load_attestations(root)
