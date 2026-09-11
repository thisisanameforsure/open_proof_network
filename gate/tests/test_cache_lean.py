"""F10-T4 with the real toolchain (lean tier): the cache the post-merge job builds is what
pregate.sh takes, the run passes on it, and the attestation is the same with or without it (D-5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness import TARGET
from test_cache import DEP_MODULES, ROOT_NODE, cached_repo, git

from opn_gate import attestation, cache, cli, config, schemas
from opn_gate.objectstore import MemoryStore
from opn_gate.toolchain import LocalToolchain

pytestmark = pytest.mark.lean


def test_real_cache_round_trip(
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    lean_pkg: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("OPN_LEAN_PKG_BIN", str(lean_pkg))
    store = MemoryStore()
    monkeypatch.setattr(cache, "open_store", lambda url: store)
    root = cached_repo(tmp_path)
    commit = git(root, "rev-parse", "HEAD")
    spec = schemas.load_json(root / "targets" / TARGET / "gate-spec.json", "gate-spec/v1")

    # The post-merge job's half, over the real toolchain: real oleans, hashed and packed.
    built = cache.build(root, TARGET, real_toolchain, tmp_path / "build", spec=spec)
    assert sorted(built.modules) == DEP_MODULES
    for entry in built.modules.values():
        assert any(rel.endswith(".olean") for rel in entry["files"])
    manifest, archive = cache.pack(built, graph_commit=commit, target_id=TARGET, spec=spec)
    assert len(archive) < cache.MAX_ARCHIVE_BYTES
    cache.upload(store, TARGET, commit, manifest, archive)

    def pregate(out: Path) -> dict[str, object]:
        code = cli.main(["pregate", "--graph", str(root), "--node", ROOT_NODE, "--out", str(out)])
        captured = capsys.readouterr()
        assert code == cli.EXIT_PASS, captured.err + captured.out[-2000:]
        doc: dict[str, object] = json.loads(captured.out)
        return doc

    with_cache = pregate(tmp_path / "with")
    report = with_cache["olean_cache"]
    assert isinstance(report, dict)
    assert report["status"] == "hit" and sorted(report["hits"]) == DEP_MODULES
    assert report["misses"] == []

    store.objects.clear()
    without = pregate(tmp_path / "without")
    report = without["olean_cache"]
    assert isinstance(report, dict) and report["status"] == "miss"

    # D-5: the attestation is a function of the tree and the pinned tooling, not of the cache.
    a = schemas.load_json(tmp_path / "with" / "attestation.json")
    b = schemas.load_json(tmp_path / "without" / "attestation.json")
    assert attestation.compare(a, b) == []
    assert a["verdict"] == "pass"
    assert config.load().runner == "local"
