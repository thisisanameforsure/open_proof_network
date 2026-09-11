"""The olean cache (F10-T4; R7, R8; D-27's required infrastructure; C7).

What is cached: the ``.olean``/``.ilean`` files the gate's build layout produces for every
*proved* node of a target — ``Nodes.«id».Context`` (generated) and ``Nodes.«id».Proof``
(merged) — which are exactly the modules the kernel-replay step compiles *before* the node
under check (F01-Q4). The post-merge job builds them inside the step-3 image and uploads an
archive keyed by the graph commit; ``pregate.sh``, the devcontainer and CI fetch the newest
archive at or before their own commit and skip compiling any dependency whose staged source
hashes to what the manifest says it was built from.

What the cache can never do: change a verdict. The node under check is always compiled, and
``leanchecker --fresh`` replays every imported declaration, so a poisoned olean fails step 4
(D-4, D-5). It can waste time, which is why every archive carries a SHA-256 manifest and a
fetch that does not verify is discarded and the build proceeds as on a miss (R8).

Layout in the store (``objectstore``): ``<target>/<commit>/manifest.json``,
``<target>/<commit>/oleans.tar.gz`` and ``<target>/index.json`` listing the commits that have
one, newest first.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import shutil
import subprocess
import tarfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from opn_gate import config, layout, schemas
from opn_gate import graph as graphmod
from opn_gate.objectstore import HttpStore, ObjectStore, ObjectStoreError
from opn_gate.steps import stage as staging
from opn_gate.toolchain import ResolvedToolchain, Toolchain

log = logging.getLogger(__name__)

MANIFEST = "manifest.json"
ARCHIVE = "oleans.tar.gz"
INDEX = "index.json"
MANIFEST_VERSION = 1
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024  # §6
CONTEXT_MODULE = "Context"
PROOF_MODULE = "Proof"
STEMS: tuple[str, ...] = (CONTEXT_MODULE, PROOF_MODULE)
OLEAN_SUFFIXES: tuple[str, ...] = (".olean", ".ilean")
Status = Literal["hit", "miss", "corrupt", "unreachable", "none"]


class CacheError(RuntimeError):
    """The cache could not be built or packed; nothing was uploaded."""


def manifest_key(target_id: str, commit: str) -> str:
    return f"{target_id}/{commit}/{MANIFEST}"


def archive_key(target_id: str, commit: str) -> str:
    return f"{target_id}/{commit}/{ARCHIVE}"


def index_key(target_id: str) -> str:
    return f"{target_id}/{INDEX}"


def open_store(url: str) -> ObjectStore:
    """Every consumer reads the cache over https; tests replace this with a memory store."""
    return HttpStore(url)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- building (the post-merge job; R7) -----------------------------------------------------------


@dataclass(frozen=True)
class Built:
    """A compiled tree: where the oleans are and which modules, from which sources."""

    build_dir: Path
    modules: dict[str, dict[str, Any]]  # module -> {"source_sha256", "files": {rel: sha256}}
    toolchain: ResolvedToolchain


def proved_order(tg: graphmod.TargetGraph) -> list[str]:
    """Every proved node whose deps are all proved, deps before dependents."""
    proved = {n for n, s in tg.statuses.items() if s == "proved"}
    order: list[str] = []
    seen: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in seen or node_id not in proved:
            return
        node = tg.nodes[node_id]
        if any(d not in proved for d in node.deps):
            return
        for dep in node.deps:
            visit(dep)
        seen.add(node_id)
        order.append(node_id)

    for node_id in tg.order:
        visit(node_id)
    return order


def build(  # noqa: PLR0913 — one argument per fact the build needs
    graph_root: Path,
    target_id: str,
    toolchain: Toolchain,
    workdir: Path,
    *,
    spec: dict[str, Any],
    install: bool = False,
) -> Built:
    """Compile every proved node's ``Context`` and ``Proof`` modules in the gate's own layout
    (``steps.stage``), deps first, and record each module's source hash and output hashes."""
    tg = graphmod.load_target(graph_root, target_id)
    tc = toolchain.resolve(str(spec["lean_toolchain"]), install=install)
    src = workdir / "src"
    build_dir = workdir / "build"
    modules: dict[str, dict[str, Any]] = {}
    for node_id in proved_order(tg):
        node = tg.nodes[node_id]
        dest = src / "Nodes" / node_id
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(node.path / "Proof.lean", dest / "Proof.lean")
        (dest / "Context.lean").write_text(
            staging.generated_context(list(node.deps)), encoding="utf-8"
        )
        (build_dir / "Nodes" / node_id).mkdir(parents=True, exist_ok=True)
        for stem in STEMS:
            module = layout.node_module(node_id, stem)
            source = dest / f"{stem}.lean"
            elab = toolchain.elaborate(
                tc,
                source,
                module,
                build_dir,
                root=src,
                timeout_s=float(spec["step3_caps"]["wallclock_s"]),
            )
            if not elab.ok:
                msg = f"{module} does not elaborate from the merged tree; the cache is not built"
                raise CacheError(msg)
            modules[module] = {
                "source_sha256": sha256(source.read_bytes()),
                "files": _outputs(build_dir, module),
            }
    return Built(build_dir, modules, tc)


def _outputs(build_dir: Path, module: str) -> dict[str, str]:
    from opn_gate.toolchain import module_output_path  # noqa: PLC0415

    out: dict[str, str] = {}
    for suffix in OLEAN_SUFFIXES:
        rel = module_output_path(module, suffix)
        path = build_dir / rel
        if path.is_file():
            out[rel.as_posix()] = sha256(path.read_bytes())
    return out


def pack(
    built: Built, *, graph_commit: str, target_id: str, spec: dict[str, Any]
) -> tuple[bytes, bytes]:
    """The manifest and the archive, both deterministic in their inputs (no clock, fixed tar
    metadata), so two post-merge runs over one commit upload identical bytes."""
    names = sorted(rel for entry in built.modules.values() for rel in entry["files"])
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel in names:
            path = built.build_dir / rel
            info = tarfile.TarInfo(rel)
            info.size = path.stat().st_size
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with path.open("rb") as fh:
                tar.addfile(info, fh)
    archive = gzip.compress(raw.getvalue(), compresslevel=6, mtime=0)
    if len(archive) > MAX_ARCHIVE_BYTES:
        msg = f"the cache archive is {len(archive)} bytes; the cap is {MAX_ARCHIVE_BYTES} (§6)"
        raise CacheError(msg)
    manifest = {
        "version": MANIFEST_VERSION,
        "target_id": target_id,
        "graph_commit": graph_commit,
        "lean_toolchain": str(spec["lean_toolchain"]),
        "toolchain_hash": built.toolchain.toolchain_hash,
        "network_commit": str(spec["network_commit"]),
        "archive": {"name": ARCHIVE, "sha256": sha256(archive), "bytes": len(archive)},
        "modules": dict(sorted(built.modules.items())),
    }
    return schemas.canonical_json(manifest), archive


def upload(
    store: ObjectStore, target_id: str, commit: str, manifest: bytes, archive: bytes
) -> None:
    """Archive first, manifest second, index last: a reader that sees the manifest can fetch the
    archive, and one that sees the index entry can fetch the manifest (R8's verification does
    the rest)."""
    store.put(archive_key(target_id, commit), archive, content_type="application/gzip")
    store.put(manifest_key(target_id, commit), manifest, content_type="application/json")
    commits = candidates(store, target_id)
    if commit not in commits:
        commits.insert(0, commit)
    store.put(
        index_key(target_id),
        schemas.canonical_json({"commits": commits}),
        content_type="application/json",
    )


# --- fetching (pregate.sh, the devcontainer, CI; R7, R8) ------------------------------------------


@dataclass(frozen=True)
class Fetched:
    """A verified cache on disk: the extracted tree and the manifest it verified against."""

    commit: str
    directory: Path
    manifest: dict[str, Any]

    @property
    def toolchain(self) -> str:
        return str(self.manifest.get("lean_toolchain", ""))


@dataclass
class FetchResult:
    status: Status
    commit: str | None = None
    reason: str = ""
    fetched: Fetched | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "commit": self.commit, "reason": self.reason}


def candidates(store: ObjectStore, target_id: str) -> list[str]:
    raw = store.get(index_key(target_id))
    if raw is None:
        return []
    try:
        doc = json.loads(raw)
    except ValueError:
        return []
    commits = doc.get("commits") if isinstance(doc, dict) else None
    return [str(c) for c in commits if isinstance(c, str)] if isinstance(commits, list) else []


Distance = Callable[[str, str], int | None]


def git_distance(graph_root: Path) -> Distance:
    """``distance(ancestor, commit)``: how many commits ``commit`` is past ``ancestor`` on its
    own history, ``None`` when ``ancestor`` is not an ancestor (or the same). No git, no
    ancestry: only the exact commit matches then."""

    def distance(ancestor: str, commit: str) -> int | None:
        if ancestor == commit:
            return 0
        env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
        is_ancestor = subprocess.run(
            ["git", "-C", str(graph_root), "merge-base", "--is-ancestor", ancestor, commit],
            capture_output=True,
            check=False,
            env=env,
        )
        if is_ancestor.returncode != 0:
            return None
        count = subprocess.run(
            ["git", "-C", str(graph_root), "rev-list", "--count", f"{ancestor}..{commit}"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip() else None

    return distance


def choose(commits: list[str], commit: str, distance: Distance) -> str | None:
    """R7: the newest cache at or before ``commit`` — the candidate with the smallest distance
    behind it; a cache from a commit not on this history is never used."""
    best: tuple[int, str] | None = None
    for candidate in commits:
        d = distance(candidate, commit)
        if d is None:
            continue
        if best is None or d < best[0]:
            best = (d, candidate)
    return best[1] if best is not None else None


def verify_and_extract(manifest_raw: bytes, archive: bytes, dest: Path) -> dict[str, Any]:
    """R8: the archive's hash against the manifest, then every member's hash after extraction.
    Any mismatch raises ``CacheError`` after removing ``dest``, so nothing half-verified stays."""
    try:
        manifest = json.loads(manifest_raw)
    except ValueError as exc:
        msg = f"the manifest is not JSON: {exc}"
        raise CacheError(msg) from exc
    if not isinstance(manifest, dict) or manifest.get("version") != MANIFEST_VERSION:
        msg = f"the manifest is not version {MANIFEST_VERSION}"
        raise CacheError(msg)
    expected = (manifest.get("archive") or {}).get("sha256")
    if sha256(archive) != expected:
        msg = "the archive does not hash to what its manifest says"
        raise CacheError(msg)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            tar.extractall(dest, filter="data")
        wanted: dict[str, str] = {}
        for entry in (manifest.get("modules") or {}).values():
            wanted.update(entry.get("files") or {})
        for rel, digest in wanted.items():
            path = dest / rel
            if not path.is_file() or sha256(path.read_bytes()) != digest:
                msg = f"{rel} is missing from the archive or does not hash to the manifest"
                raise CacheError(msg)
        extra = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
        if set(extra) - set(wanted):
            unnamed = sorted(set(extra) - set(wanted))[:3]
            msg = f"the archive carries files the manifest does not name: {unnamed}"
            raise CacheError(msg)
    except (tarfile.TarError, OSError, CacheError) as exc:
        shutil.rmtree(dest, ignore_errors=True)
        if isinstance(exc, CacheError):
            raise
        msg = f"the archive cannot be extracted: {exc}"
        raise CacheError(msg) from exc
    return manifest


def fetch(
    store: ObjectStore, target_id: str, commit: str, dest: Path, *, distance: Distance
) -> FetchResult:
    """The newest verified cache at or before ``commit`` on disk under ``dest``, or why not.
    Never raises: every failure is a miss the caller builds through (C7)."""
    try:
        chosen = choose(candidates(store, target_id), commit, distance)
        if chosen is None:
            return FetchResult("miss", reason="no cache at or before this commit")
        manifest_raw = store.get(manifest_key(target_id, chosen))
        archive = store.get(archive_key(target_id, chosen))
    except ObjectStoreError as exc:
        return FetchResult("unreachable", reason=str(exc))
    if manifest_raw is None or archive is None:
        return FetchResult("miss", chosen, reason="the index names a cache the store lacks")
    try:
        manifest = verify_and_extract(manifest_raw, archive, dest)
    except CacheError as exc:
        log.warning("olean cache %s discarded: %s", chosen[:12], exc)
        return FetchResult("corrupt", chosen, reason=f"discarded: {exc}")
    return FetchResult("hit", chosen, fetched=Fetched(chosen, dest, manifest))


def prepare(spec: dict[str, Any], graph_root: Path, commit: str | None, dest: Path) -> FetchResult:
    """What a run does before building: fetch when the graph names a cache, else nothing."""
    url = spec.get("olean_cache_url")
    if not isinstance(url, str) or not url:
        return FetchResult("none", reason="the graph names no olean cache")
    if commit is None:
        return FetchResult("none", reason="no graph commit to key the cache on")
    try:
        store = open_store(url)
    except ObjectStoreError as exc:
        return FetchResult("unreachable", reason=str(exc))
    result = fetch(store, str(spec["graph_id"]), commit, dest, distance=git_distance(graph_root))
    if result.status != "hit":
        log.info("olean cache %s: %s", result.status, result.reason)
    else:
        log.info("olean cache hit: %s", str(result.commit)[:12])
    return result


# --- using a fetched cache in the build (R7) ------------------------------------------------------


@dataclass
class Usage:
    """What the build step took from the cache and what it compiled itself."""

    commit: str | None = None
    hits: list[str] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"commit": self.commit, "hits": list(self.hits), "misses": list(self.misses)}


def take(fetched: Fetched, source: Path, module: str, build_dir: Path, toolchain_name: str) -> bool:
    """Copy the module's cached outputs into ``build_dir`` when the staged source hashes to what
    the cache was built from under the same toolchain; ``False`` means compile it."""
    if fetched.toolchain != toolchain_name:
        return False
    entry = (fetched.manifest.get("modules") or {}).get(module)
    if not isinstance(entry, dict) or entry.get("source_sha256") != sha256(source.read_bytes()):
        return False
    files = entry.get("files") or {}
    if not files:
        return False
    for rel in files:
        src = fetched.directory / rel
        if not src.is_file():
            return False
        dst = build_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    return True
