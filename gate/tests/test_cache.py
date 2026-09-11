"""F10-T4 / AC6, AC7, AC8: the olean cache (R7, R8) over the fake toolchain and the memory store."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
from fakes import FAKE_RESOLVED, FakeToolchain
from harness import GRAPH, TARGET, TUTORIAL, copy_graph

from opn_gate import cache, cli, objectstore, schemas, toolchain
from opn_gate.objectstore import MemoryStore, ObjectStoreError

ROOT_NODE = "and-swap-reassoc"
INTERIOR = "and-reassoc"
CACHE_URL = "https://cache.example.test/oleans"
NODES = f"targets/{TARGET}/nodes"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeToolchain:
    tc = FakeToolchain()
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: tc))
    return tc


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MemoryStore:
    """Every https store the code opens is this memory store."""
    memory = MemoryStore()
    monkeypatch.setattr(cache, "open_store", lambda url: memory)
    return memory


def attest(root: Path, node_id: str, n: int) -> None:
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=schemas.content_hash(
            (root / NODES / node_id / "Statement.lean").read_bytes()
        ),
        merge_commit="4" * 40,
        graph_commit="4" * 40,
        runner="hosted",
        review={"kind": "tutorial", "reviewer": None, "reference": None},
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def git_env(home: Path) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
    }


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        env=git_env(root.parent),
        capture_output=True,
        text=True,
    ).stdout.strip()


def cached_repo(tmp_path: Path, *, url: str | None = CACHE_URL) -> Path:
    """The fixture with both interior nodes proved, the root ready, an olean cache named in the
    spec, committed as a git repo."""
    root = copy_graph(tmp_path)
    attest(root, TUTORIAL, 1)
    attest(root, INTERIOR, 2)
    spec_path = root / "targets" / TARGET / "gate-spec.json"
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    spec["olean_cache_url"] = url
    spec_path.write_bytes(schemas.canonical_json(spec))
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "seed")
    return root


def publish(
    root: Path, store: MemoryStore, fake: FakeToolchain, commit: str
) -> tuple[bytes, bytes]:
    spec = schemas.load_json(root / "targets" / TARGET / "gate-spec.json", "gate-spec/v1")
    built = cache.build(root, TARGET, fake, root.parent / f"build-{commit[:8]}", spec=spec)
    manifest, archive = cache.pack(built, graph_commit=commit, target_id=TARGET, spec=spec)
    cache.upload(store, TARGET, commit, manifest, archive)
    return manifest, archive


def run_pregate(capsys: pytest.CaptureFixture[str], root: Path, out: Path) -> dict[str, Any]:
    code = cli.main(["pregate", "--graph", str(root), "--node", ROOT_NODE, "--out", str(out)])
    captured = capsys.readouterr()
    doc: dict[str, Any] = json.loads(captured.out)
    assert code == cli.EXIT_PASS, captured.err
    assert doc["verdict"] == "pass"
    return doc


DEP_MODULES = sorted(
    f"Nodes.«{n}».{stem}" for n in (TUTORIAL, INTERIOR) for stem in ("Context", "Proof")
)


def test_manifest_verification(
    tmp_path: Path, fake: FakeToolchain, store: MemoryStore, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC6: unaltered, the cache is used and the build step reports every dependency module as
    a hit; one altered byte, and the fetch discards it and rebuilds."""
    root = cached_repo(tmp_path)
    commit = git(root, "rev-parse", "HEAD")
    manifest, archive = publish(root, store, fake, commit)
    doc = json.loads(manifest)
    assert doc["graph_commit"] == commit and doc["target_id"] == TARGET
    assert sorted(doc["modules"]) == DEP_MODULES  # the proved nodes; the ready root is not built
    assert doc["archive"] == {
        "name": "oleans.tar.gz",
        "sha256": cache.sha256(archive),
        "bytes": len(archive),
    }
    assert cache.candidates(store, TARGET) == [commit]

    fake.calls.clear()
    summary = run_pregate(capsys, root, tmp_path / "hit")
    assert summary["olean_cache"]["status"] == "hit" and summary["olean_cache"]["commit"] == commit
    assert sorted(summary["olean_cache"]["hits"]) == DEP_MODULES
    assert summary["olean_cache"]["misses"] == []
    elaborated = [c for c in fake.calls if c.startswith("elaborate:")]
    assert elaborated == [
        f"elaborate:Nodes.«{ROOT_NODE}».Context",
        f"elaborate:Nodes.«{ROOT_NODE}».Proof",
    ]
    assert json.loads((tmp_path / "hit" / "cache.json").read_text())["status"] == "hit"
    for rel in doc["modules"][DEP_MODULES[0]]["files"]:
        assert (tmp_path / "hit" / "work" / "build" / rel).is_file()  # copied in for the build
    # D-5: the attestation says nothing about the cache.
    assert "olean" not in (tmp_path / "hit" / "attestation.json").read_text()

    key = cache.archive_key(TARGET, commit)
    altered = bytearray(store.objects[key])
    altered[len(altered) // 2] ^= 0x01
    store.objects[key] = bytes(altered)
    fake.calls.clear()
    summary = run_pregate(capsys, root, tmp_path / "corrupt")
    assert summary["olean_cache"]["status"] == "corrupt"
    assert "discarded" in summary["olean_cache"]["reason"]
    assert summary["olean_cache"]["hits"] == []
    assert not (tmp_path / "corrupt" / "olean-cache").exists()
    elaborated = [c for c in fake.calls if c.startswith("elaborate:")]
    assert len(elaborated) == 6  # every dependency rebuilt, then the root

    # A manifest whose member hashes do not match the archive is discarded the same way.
    store.objects[key] = archive
    tampered = json.loads(manifest)
    module = next(iter(tampered["modules"]))
    rel = next(iter(tampered["modules"][module]["files"]))
    tampered["modules"][module]["files"][rel] = "0" * 64
    store.objects[cache.manifest_key(TARGET, commit)] = schemas.canonical_json(tampered)
    result = cache.fetch(store, TARGET, commit, tmp_path / "t", distance=cache.git_distance(root))
    assert result.status == "corrupt" and "does not hash" in result.reason
    assert not (tmp_path / "t").exists()


def make_cache(tmp_path: Path, name: str, commit: str) -> tuple[bytes, bytes]:
    """A minimal cache whose one olean carries ``name``, packed the way the job packs."""
    build_dir = tmp_path / f"build-{name}"
    rel = "Nodes/x/Proof.olean"
    (build_dir / "Nodes" / "x").mkdir(parents=True)
    (build_dir / rel).write_bytes(name.encode())
    built = cache.Built(
        build_dir,
        {
            "Nodes.«x».Proof": {
                "source_sha256": "a" * 64,
                "files": {rel: cache.sha256(name.encode())},
            }
        },
        FAKE_RESOLVED,
    )
    return cache.pack(built, graph_commit=commit, target_id=TARGET, spec=samples.gate_spec())


def test_newest_at_or_before(tmp_path: Path) -> None:
    """AC7: with caches at A and C and a fetch for B (A < B < C), A's cache is chosen; a cache on
    a branch that is not B's history is never chosen, and an exact match beats an ancestor."""
    root = copy_graph(tmp_path)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "A")
    a = git(root, "rev-parse", "HEAD")
    (root / "b.txt").write_text("b")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "B")
    b = git(root, "rev-parse", "HEAD")
    (root / "c.txt").write_text("c")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "C")
    c = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "-b", "side", a)
    (root / "d.txt").write_text("d")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "D")
    d = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")

    store = MemoryStore()
    for name, commit in (("a", a), ("c", c), ("d", d)):
        manifest, archive = make_cache(tmp_path, name, commit)
        cache.upload(store, TARGET, commit, manifest, archive)
    assert cache.candidates(store, TARGET) == [d, c, a]  # newest upload first
    distance = cache.git_distance(root)
    assert cache.choose([d, c, a], b, distance) == a
    result = cache.fetch(store, TARGET, b, tmp_path / "b", distance=distance)
    assert result.status == "hit" and result.commit == a
    assert (tmp_path / "b" / "Nodes" / "x" / "Proof.olean").read_bytes() == b"a"
    assert cache.choose([d, c, a], c, distance) == c  # exact beats ancestor
    assert cache.choose([d], b, distance) is None  # the side branch is not b's history
    assert (
        cache.fetch(store, TARGET, b, tmp_path / "n", distance=lambda x, y: None).status == "miss"
    )
    # Without git, only the exact commit matches (a bare tree, F00-R15's export).
    bare = cache.git_distance(tmp_path / "not-a-repo")
    assert bare(a, b) is None and bare(b, b) == 0


def test_miss_falls_back(
    tmp_path: Path,
    fake: FakeToolchain,
    store: MemoryStore,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC8: no cache in the store — pregate.sh builds and passes, logging the miss; an unreachable
    store and a graph that names no cache degrade the same way (C7)."""
    caplog.set_level(logging.INFO, logger="opn_gate.cache")
    root = cached_repo(tmp_path)
    summary = run_pregate(capsys, root, tmp_path / "miss")
    assert summary["olean_cache"]["status"] == "miss" and summary["olean_cache"]["hits"] == []
    assert len([c for c in fake.calls if c.startswith("elaborate:")]) == 6
    assert any("olean cache miss" in r.getMessage() for r in caplog.records)

    store.unreachable = True
    summary = run_pregate(capsys, root, tmp_path / "down")
    assert summary["olean_cache"]["status"] == "unreachable"
    assert "simulated outage" in summary["olean_cache"]["reason"]

    none = cached_repo(tmp_path / "none", url=None)
    summary = run_pregate(capsys, none, tmp_path / "none-out")
    assert summary["olean_cache"] == {
        "status": "none",
        "commit": None,
        "reason": "the graph names no olean cache",
        "hits": [],
        "misses": [],
    }


def test_take_requires_the_same_source_and_toolchain(tmp_path: Path) -> None:
    manifest, archive = make_cache(tmp_path, "z", "9" * 40)
    fetched = cache.Fetched(
        "9" * 40, tmp_path / "f", cache.verify_and_extract(manifest, archive, tmp_path / "f")
    )
    source = tmp_path / "Proof.lean"
    source.write_bytes(b"not what it was built from")
    build = tmp_path / "build"
    assert cache.take(fetched, source, "Nodes.«x».Proof", build, FAKE_RESOLVED.name) is False
    assert cache.take(fetched, source, "Nodes.«y».Proof", build, FAKE_RESOLVED.name) is False
    fetched.manifest["modules"]["Nodes.«x».Proof"]["source_sha256"] = cache.sha256(
        source.read_bytes()
    )
    assert (
        cache.take(fetched, source, "Nodes.«x».Proof", build, "leanprover/lean4:v4.99.0") is False
    )
    assert cache.take(fetched, source, "Nodes.«x».Proof", build, FAKE_RESOLVED.name) is True
    assert (build / "Nodes" / "x" / "Proof.olean").read_bytes() == b"z"


def test_pack_is_deterministic_and_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    one = make_cache(tmp_path / "1", "same", "1" * 40)
    two = make_cache(tmp_path / "2", "same", "1" * 40)
    assert one == two
    monkeypatch.setattr(cache, "MAX_ARCHIVE_BYTES", 10)
    with pytest.raises(cache.CacheError, match="the cap is 10"):
        make_cache(tmp_path / "3", "same", "1" * 40)


def test_extract_refuses_extra_members_and_bad_manifests(tmp_path: Path) -> None:
    manifest, archive = make_cache(tmp_path, "m", "2" * 40)
    with pytest.raises(cache.CacheError, match="not JSON"):
        cache.verify_and_extract(b"{", archive, tmp_path / "a")
    with pytest.raises(cache.CacheError, match="version"):
        cache.verify_and_extract(b'{"version": 0}', archive, tmp_path / "b")
    doc = json.loads(manifest)
    del doc["modules"]["Nodes.«x».Proof"]["files"]["Nodes/x/Proof.olean"]
    doc["modules"]["Nodes.«x».Proof"]["files"]["Nodes/x/Other.olean"] = "0" * 64
    with pytest.raises(cache.CacheError, match="missing from the archive"):
        cache.verify_and_extract(schemas.canonical_json(doc), archive, tmp_path / "c")
    assert not (tmp_path / "c").exists()


def test_cache_commands(
    tmp_path: Path,
    fake: FakeToolchain,
    store: MemoryStore,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``cache publish`` builds, packs and uploads what the post-merge job uploads; ``cache
    fetch`` answers hit or miss for the devcontainer's post-create."""
    root = cached_repo(tmp_path)
    commit = git(root, "rev-parse", "HEAD")
    assert cli.main(["cache", "fetch", "--graph", str(root), "--out", str(tmp_path / "f0")]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "miss"

    code = cli.main(["cache", "publish", "--graph", str(root), "--out", str(tmp_path / "p")])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["ok"] and out["uploaded"] is False
    assert sorted(out["modules"]) == DEP_MODULES and (tmp_path / "p" / "manifest.json").is_file()
    assert store.objects == {}

    uploads = MemoryStore()
    monkeypatch.setattr(objectstore, "S3Store", lambda bucket, prefix="": uploads)
    code = cli.main(
        ["cache", "publish", "--graph", str(root), "--bucket", "b", "--out", str(tmp_path / "q")]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["uploaded"] is True
    assert sorted(uploads.objects) == sorted(
        [
            cache.archive_key(TARGET, commit),
            cache.manifest_key(TARGET, commit),
            cache.index_key(TARGET),
        ]
    )
    store.objects.update(uploads.objects)
    assert cli.main(["cache", "fetch", "--graph", str(root), "--out", str(tmp_path / "f1")]) == 0
    fetched = json.loads(capsys.readouterr().out)
    assert fetched["status"] == "hit" and fetched["commit"] == commit
    assert Path(fetched["directory"]).is_dir()

    uploads.unreachable = True
    code = cli.main(
        ["cache", "publish", "--graph", str(root), "--bucket", "b", "--out", str(tmp_path / "r")]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["ok"] is False and "simulated outage" in out["error"]


def test_http_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """The https view: a 403 or 404 is 'no such object', any other failure names the key, and
    it cannot write."""
    import urllib.error  # noqa: PLC0415

    class Response:
        def __init__(self, body: bytes) -> None:
            self.body = body
            self.headers = {"Content-Length": str(len(body))}

        def read(self, n: int = -1) -> bytes:
            return self.body

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def opener(request: Any, timeout: float) -> Response:
        url = request.full_url
        if url.endswith("/missing"):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]
        if url.endswith("/broken"):
            raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)  # type: ignore[arg-type]
        return Response(b"payload")

    http = objectstore.HttpStore("https://cache.example.test/oleans/", opener=opener)
    assert http.get("t/x/manifest.json") == b"payload"
    assert http.get("missing") is None
    with pytest.raises(ObjectStoreError, match="HTTP 500"):
        http.get("broken")
    with pytest.raises(ObjectStoreError, match="read-only"):
        http.put("k", b"", content_type="text/plain")
    with pytest.raises(ObjectStoreError, match="https only"):
        objectstore.HttpStore("http://cache.example.test")
    assert not (GRAPH / "targets" / TARGET / ".olean-cache").exists()
