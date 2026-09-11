"""F10-T1 / AC1, AC2: AGENTS.md executes, and says what R1 requires in R1's order (F10-Q3).

The document is driven the way a person would drive it: a git checkout of the fixture graph
with its products committed, the api served on a real port over the local runner's server with
the fake host and a memory store, and every ``sh`` block run in order by the walkthrough runner.
Only blocks that need the pinned toolchain (``lean``) and the two that push to a remote
(``manual``) are skipped in the fast tier; the lean tier runs the toolchain ones too.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import queue
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from api_fakes import FakeGitHost, PrecheckKey, make_harness, make_precheck_key, result_zip
from harness import GRAPH, TARGET, TUTORIAL

from opn_api import local
from opn_api.githost import WorkflowRun
from opn_gate import config, products, schemas

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "gate" / "agents" / "AGENTS.md"


def _load_runner() -> Any:
    """``gate/tools/walkthrough.py`` is a script beside the other tools, not a package member."""
    path = ROOT / "gate" / "tools" / "walkthrough.py"
    spec = importlib.util.spec_from_file_location("walkthrough", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


walkthrough = _load_runner()
GRAPH_COPY = ROOT.parent / "open_proof_network_graph" / "AGENTS.md"
DECISIONS = ROOT / "docs" / "architecture_decisions_v_3_12.html"
COMMIT = "6" * 40
MERGE = "4" * 40

#: R1's topics, as heading fragments, in R1's order (AC2).
REQUIRED_HEADINGS: tuple[str, ...] = (
    "What this is",
    "The tutorial node",
    "Claiming",
    "Permitted paths",
    "The gate contract",
    "Getting a token",
    "Precheck and submit",
    "The postmortem",
    "Skeletonization",
    "Artifact types",
    "Proposals",
    "Rate limits",
)
#: The blocks the runner cannot execute against a fixture: a push and a pull request, and the
#: MCP registration. Anything else tagged ``manual`` is a command hiding from the test.
MANUAL_FIRST_LINES: tuple[str, ...] = (
    'git -C "$GRAPH" push -u origin "$BRANCH"',
    "claude mcp add --transport http open-proof-network",
)
MIN_EXECUTED = 20  # a document that lost most of its commands is not the document


# --- the fixture graph as a clone -----------------------------------------------------------------


def git_env(home: Path) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "seed",
        "GIT_AUTHOR_EMAIL": "seed@x",
        "GIT_COMMITTER_NAME": "seed",
        "GIT_COMMITTER_EMAIL": "seed@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
    }


def build_graph_repo(tmp: Path, key: PrecheckKey) -> Path:
    """The propositional fixture as the live graph would be: the tutorial node proved and
    attested, the target claimable, the products rendered, the precheck key committed."""
    root = tmp / "graph"
    shutil.copytree(GRAPH, root)
    nodes = root / "targets" / TARGET / "nodes"
    attestation = samples.attestation(
        node_id=TUTORIAL,
        statement_hash=schemas.content_hash((nodes / TUTORIAL / "Statement.lean").read_bytes()),
        merge_commit=MERGE,
        graph_commit=MERGE,
        runner="hosted",
        review={"kind": "tutorial", "reviewer": None, "reference": None},
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / "000001.json").write_bytes(schemas.canonical_json(attestation))
    status = root / "targets" / TARGET / "status"
    status.mkdir()
    (status / "2026-09-01-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(date="2026-09-01")), encoding="utf-8"
    )
    (root / "keys").mkdir()
    (root / "keys" / "precheck.pub").write_text(key.public + "\n", encoding="utf-8")
    products.generate(root, rendered_from=COMMIT, commit_time="2026-09-09T12:00:00Z").write(root)
    env = git_env(tmp)

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    return root


def tree_files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


# --- a fake host whose precheck runs finish by themselves ----------------------------------------


class AutoRunGitHost(FakeGitHost):
    """The fake host, plus a scratch repository that runs every dispatched job at once: the first
    poll finds the run complete with a result signed by the fixture precheck key, so the
    document's polling loops terminate the way they do on the live service, only faster."""

    def __init__(self, files: dict[str, bytes], key: PrecheckKey) -> None:
        super().__init__(files=files)
        self.key = key

    def find_run(self, repo: str, workflow: str, *, branch: str) -> WorkflowRun | None:
        if branch not in self.runs:
            push = next((p for p in self.pushes if p.branch == branch), None)
            if push is None:
                return None
            job = json.loads(push.files["job.json"])
            artifact = result_zip(
                job_id=job["id"],
                node_id=job["node_id"],
                graph_commit=job["graph_commit"],
                bundle_digest=job["bundle_digest"],
                key=self.key,
            )
            self.finish_run(branch, artifact=(f"result-{job['id']}", artifact))
        return super().find_run(repo, workflow, branch=branch)


def serve_in_thread(app: Any) -> tuple[str, Any]:
    """The api on a real loopback port, over the local runner's own server (F05-T1)."""
    ready: queue.Queue[int] = queue.Queue()
    loop = asyncio.new_event_loop()

    async def main() -> None:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await local.serve_connection(app, reader, writer)

        server = await asyncio.start_server(handle, "127.0.0.1", 0, limit=local.MAX_HEADER_BYTES)
        ready.put(server.sockets[0].getsockname()[1])
        async with server:
            await server.serve_forever()

    def run() -> None:
        try:
            loop.run_until_complete(main())
        except RuntimeError:  # loop.stop() from the fixture teardown
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=run, daemon=True, name="opn-walkthrough-api")
    thread.start()
    port = ready.get(timeout=30)
    return f"http://127.0.0.1:{port}", loop


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


@pytest.fixture
def stage(tmp_path: Path, key: PrecheckKey) -> Iterator[dict[str, str]]:
    """A graph clone, a served api and the environment the document assumes."""
    graph = build_graph_repo(tmp_path, key)
    harness = make_harness(githost=AutoRunGitHost(tree_files(graph), key))
    base, loop = serve_in_thread(harness.app)
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    env.update({"GRAPH": str(graph), "NETWORK": str(ROOT), "OPN_API": base})
    yield env
    loop.call_soon_threadsafe(loop.stop)


# --- AC2 -----------------------------------------------------------------------------------------


def test_required_sections() -> None:
    """AC2: every R1 topic is a heading, in R1's order, and every decision cited exists."""
    markdown = DOC.read_text(encoding="utf-8")
    found = walkthrough.headings(markdown)
    position = 0
    for fragment in REQUIRED_HEADINGS:
        later = [i for i in range(position, len(found)) if fragment in found[i]]
        assert later, f"no heading for {fragment!r} after heading {position}: {found}"
        position = later[0] + 1
    doc = DECISIONS.read_text(encoding="utf-8")
    anchors = {f"D-{m}" for m in re.findall(r'<h3 id="d-([0-9]+)">', doc)}
    cited = walkthrough.decisions(markdown)
    assert cited, "the document cites no decision"
    assert cited <= anchors, f"cited decisions with no section in the protocol: {cited - anchors}"


def test_graph_copy_is_identical() -> None:
    """D-35: the graph carries a copy of the tested document, byte for byte (skipped when the
    sibling checkout is not present, as in CI)."""
    if not GRAPH_COPY.is_file():
        pytest.skip(f"{GRAPH_COPY} is not checked out beside this repo")
    assert GRAPH_COPY.read_bytes() == DOC.read_bytes(), "the graph's AGENTS.md drifted; recopy it"


def test_manual_blocks_are_the_known_two() -> None:
    """A ``manual`` tag is how a command escapes the test, so the set is frozen."""
    plan = walkthrough.steps(walkthrough.blocks(DOC.read_text(encoding="utf-8")))
    manual = [s.command.text.strip().splitlines()[0] for s in plan if "manual" in s.command.tags]
    assert len(manual) == len(MANUAL_FIRST_LINES)
    for first, expected in zip(manual, MANUAL_FIRST_LINES, strict=True):
        assert first.startswith(expected), first
    assert all(s.command.tags <= {"lean", "manual"} for s in plan), "unknown block tag"


# --- AC1 -----------------------------------------------------------------------------------------


def _drive(stage: dict[str, str], tmp_path: Path, skip: frozenset[str]) -> list[Any]:
    plan = walkthrough.steps(walkthrough.blocks(DOC.read_text(encoding="utf-8")))
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    outcomes: list[Any] = walkthrough.run(plan, stage, cwd=cwd, skip=skip)
    report = walkthrough.summary(outcomes)
    print(report)  # the per-block record, kept in the evidence (C1)
    assert all(o.ok for o in outcomes), report
    executed = [o for o in outcomes if o.status == "passed"]
    assert len(executed) >= MIN_EXECUTED, report
    assert all(o.step.command.tags & skip for o in outcomes if o.status == "skipped"), report
    return outcomes


def test_agents_md_executes(stage: dict[str, str], tmp_path: Path) -> None:
    """AC1 (fast tier): every block but the toolchain and remote ones runs and prints what it
    says it prints, against the fixture clone and the fake service."""
    outcomes = _drive(stage, tmp_path, frozenset({"lean", "manual"}))
    assert any("lean" in o.step.command.tags for o in outcomes)  # the git path is documented


@pytest.mark.lean
def test_agents_md_executes_with_toolchain(
    stage: dict[str, str], tmp_path: Path, lean_pkg: Path
) -> None:
    """AC1 (lean tier): the same, with pregate.sh really running on the tutorial node."""
    assert lean_pkg.is_dir()
    outcomes = _drive(stage, tmp_path, frozenset({"manual"}))
    pregate = next(o for o in outcomes if "lean" in o.step.command.tags)
    assert pregate.status == "passed" and '"verdict": "pass"' in pregate.stdout
