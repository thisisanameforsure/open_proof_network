"""F07-T55: the post-merge job catches up instead of holding the queue (the owner, 2026-10-02).

Since F07-T33 nothing merged while a post-merge job had not committed, because that job's push
used to be refused when ``main`` moved under it and the record was lost (#125, #132, #133, #145).
Read from the record (``engineering/evidence/F07/task-55.txt``): fifteen post-merge runs took five
to eight and a half minutes each, so every merge waited that long for the one before it.

The products are derived: a deterministic function of the tree they are rendered from (F03-R11).
So a refused push loses nothing that cannot be made again. The job now keeps what is *its own* —
the attestation it signed, the hole children a partial wrote (``record.patch``, taken before any
product is rendered) — and when ``main`` has moved it fetches, lays that record on ``main`` as it
now is, writes its ledger lines again on the ledger as ``main`` now has it, renders the products
of that tree and pushes again. One commit then carries the products of every merge so far. What
``main`` already credits is dropped first, so no merge is ever credited twice; a record that does
not apply (a real conflict) or a re-pin of the rendering gate is replayed on its own, as before.

And a building merge records itself: its run no longer leaves it to a later merge (T45's rule
stays for appends, which earn no attestation), and a later run's plan leaves a building merge
whose own run is still going to that run instead of replaying it.

Everything below runs the workflow's own step scripts — the record step, the ledger and products
steps, the commit step — against a bare remote, with a ``uv`` that stands in for the pinned gate's
three commands and renders products as a deterministic function of the tree. It was seen red
against the job as it stood (``engineering/evidence/F07/task-55-red.txt``).
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_postmerge_batch import (
    FAKE,
    PIN_A,
    PIN_B,
    REPO,
    Graph,
    git_env,
    helper_source,
    run_find_step,
    step_run,
)

RECORD_STEP = "Keep this merge's own record"
COMMIT_STEP = "Commit the attestation"

#: The pinned gate's ledger, products and stewards commands, as ``uv run ... opn_gate.cli <cmd>``.
#: Deterministic functions of the tree, as the real ones are; every call is logged.
FAKE_UV = r"""#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys
args = sys.argv[1:]
root = pathlib.Path.cwd()
with open(os.environ["UV_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
def arg(flag):
    return args[args.index(flag) + 1]
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()
def dump(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
if args[:1] == ["sync"]:
    sys.exit(0)
if "stewards" in args:
    sys.exit(2)  # a pin without the command says nothing
if "ledger" in args:
    merge = git("rev-parse", arg("--commit"))
    path = root / "ledger" / "p.json"  # one identity, so two merges write one file
    doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"entries": []}
    doc["entries"].append({"merge": merge, "subject": git("log", "-1", "--format=%s", merge)})
    dump(path, doc)
    sys.exit(0)
if "products" in args:
    commit = git("rev-parse", arg("--commit"))
    attested = sorted(p.name for p in (root / "attestations").glob("*.json"))
    for target in sorted(p for p in (root / "targets").iterdir() if p.is_dir()):
        nodes_dir = target / "nodes"
        nodes = sorted(p.name for p in nodes_dir.iterdir()) if nodes_dir.is_dir() else []
        dump(target / "graph.json", {"rendered_from": commit, "nodes": nodes})
        cache_path = target / ".tags-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
        dirty = False
        for node in nodes:
            statement = nodes_dir / node / "Statement.lean"
            if statement.is_file():
                key = hashlib.sha256(statement.read_bytes()).hexdigest()
                if key not in cache:
                    with open(os.environ["UV_LOG"], "a", encoding="utf-8") as log:
                        log.write(f"scanned {target.name}/{node}\n")
                    cache[key] = [f"tag-{node}"]
                    dirty = True
        if dirty:
            dump(cache_path, cache)
    dump(root / "frontier.json", {"rendered_from": commit, "attested": attested})
    sys.exit(0)
sys.exit(2)
"""

#: The host: logs every call; a dispatch is all the commit step asks of it.
FAKE_GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_LOG"
exit 0
"""

STATEMENT = "theorem n : True := trivial\n"
CONTEXT = "-- generated\nimport Defs\n"


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=git_env()
    )
    return proc.stdout.strip()


def tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    if not bin_dir.is_dir():
        bin_dir.mkdir()
        for name, text in (("uv", FAKE_UV), ("gh", FAKE_GH)):
            tool = bin_dir / name
            tool.write_text(text, encoding="utf-8")
            tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return bin_dir


class Origin:
    """The graph on the host: a bare repository, and a working clone that moves its ``main`` the
    way the host and the other post-merge runs do (merges, then their bot commits)."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.graph = Graph(tmp_path / "seed")
        for target in ("t1", "t2"):
            self.graph.write(f"targets/{target}/nodes/n/Statement.lean", STATEMENT)
            self.graph.write(f"targets/{target}/nodes/n/Context.lean", CONTEXT)
            self.graph.write(f"targets/{target}/nodes/n/META.yaml", "status: ready\n")
        self.graph.commit("seed the nodes")
        self.bare = tmp_path / "origin.git"
        subprocess.run(
            ["git", "clone", "-q", "--bare", str(self.graph.root), str(self.bare)],
            check=True, env=git_env(),
        )  # fmt: skip
        self.mover = Graph.__new__(Graph)
        self.mover.root = tmp_path / "mover"
        subprocess.run(
            ["git", "clone", "-q", str(self.bare), str(self.mover.root)], check=True, env=git_env()
        )

    def sync(self) -> None:
        git(self.mover.root, "fetch", "-q", "origin")
        git(self.mover.root, "reset", "-q", "--hard", "origin/main")

    def push(self) -> str:
        git(self.mover.root, "push", "-q", "origin", "HEAD:main")
        return git(self.mover.root, "rev-parse", "HEAD")

    def merge(self, number: int, branch: str, files: dict[str, str]) -> str:
        """A pull request merged by the host on main as it is now."""
        self.sync()
        sha = self.mover.merge(number, branch, files)
        self.push()
        return sha

    def append(self, number: int, target: str = "t1") -> str:
        rel = f"targets/{target}/nodes/n/attempts/2026100{number:04d}-p.yaml"
        return self.merge(number, f"append/a{number}", {rel: f"postmortem {number}\n"})

    def proof(self, number: int, target: str = "t1") -> str:
        rel = f"targets/{target}/nodes/n/Proof.lean"
        return self.merge(number, f"submit/p{number}", {rel: f"-- proof {number}\n{STATEMENT}"})

    def bot(
        self, *numbers: int, files: dict[str, str] | None = None, ledger: tuple[str, ...] = ()
    ) -> str:
        """Another run's gate commit: its ledger lines and products, by the same commands."""
        self.sync()
        for rel, text in (files or {}).items():
            self.mover.write(rel, text)
        for merge in ledger:
            command(self.mover.root, self.tmp, "ledger", merge)
        command(self.mover.root, self.tmp, "products", "HEAD")
        credits = " ".join(f"#{n}" for n in numbers)
        self.mover.commit(f"gate: {credits} pass")
        return self.push()

    def owner(self, files: dict[str, str], subject: str = "an owner's direct push") -> str:
        self.sync()
        for rel, text in files.items():
            self.mover.write(rel, text)
        self.mover.commit(subject)
        return self.push()

    def main(self) -> str:
        return git(self.bare, "rev-parse", "main")

    def subjects(self, count: int = 8) -> list[str]:
        return git(self.bare, "log", "--first-parent", f"-n{count}", "--format=%s", "main").split(
            "\n"
        )

    def show(self, path: str, ref: str = "main") -> str:
        return git(self.bare, "show", f"{ref}:{path}")


def env_for(tmp_path: Path, runner_temp: Path, **extra: str) -> dict[str, str]:
    env = git_env()
    env.update(
        PATH=f"{tools(tmp_path)}{os.pathsep}{env['PATH']}",
        UV_LOG=str(tmp_path / "uv.log"), GH_LOG=str(runner_temp / "gh.log"),
        GH_TOKEN=FAKE, GITHUB_REPOSITORY=REPO, RUNNER_TEMP=str(runner_temp),
        GITHUB_OUTPUT=str(runner_temp / "output"), PUBLISH_WAIT_S="0",
    )  # fmt: skip
    env.update(extra)
    return env


def command(root: Path, tmp_path: Path, name: str, commit: str) -> None:
    """One of the gate's commands, through the same stand-in the steps call."""
    runner = tmp_path / "render-temp"
    runner.mkdir(exist_ok=True)
    env = env_for(tmp_path, runner)
    sha = git(root, "rev-parse", commit)
    subprocess.run(
        ["uv", "run", "python", "-m", "opn_gate.cli", name, "--graph", ".", "--commit", sha],
        cwd=root, check=True, env=env,
    )  # fmt: skip


class Job:
    """One post-merge run of ``merge``, from a clone of the host checked out at that merge, through
    the record, ledger, products and commit steps exactly as the workflow writes them."""

    def __init__(
        self,
        gate_doc: dict[Any, Any],
        origin: Origin,
        name: str,
        merge: str,
        numbers: str,
        *,
        merges: str | None = None,
        target: str = "t1",
        event: str = "push",
    ) -> None:
        self.doc, self.origin = gate_doc, origin
        self.tmp = origin.tmp
        self.work = origin.tmp / f"job-{name}"
        self.temp = origin.tmp / f"temp-{name}"
        self.temp.mkdir()
        (self.temp / "output").write_text("", encoding="utf-8")
        (self.temp / "postmerge_batch.py").write_text(helper_source(gate_doc), encoding="utf-8")
        subprocess.run(
            ["git", "clone", "-q", str(origin.bare), str(self.work)], check=True, env=git_env()
        )
        git(self.work, "checkout", "-q", merge)
        self.merge, self.numbers = merge, numbers
        self.merges = merges if merges is not None else merge
        self.target, self.event = target, event
        self.needs_gate = False

    def env(self, **extra: str) -> dict[str, str]:
        return env_for(
            self.tmp, self.temp,
            GITHUB_EVENT_NAME=self.event, NUMBERS=self.numbers, MERGES=self.merges,
            TARGETS=self.target, RENDER_PIN=PIN_A, REPLAY="", VERDICT="pass",
            NEEDS_GATE="true" if self.needs_gate else "false", OPN_GRAPH_DEPLOY_KEY="not a key",
            OPN_API_CLAIMS_URL="",
            **extra,
        )  # fmt: skip

    def step(self, name: str, **extra: str) -> subprocess.CompletedProcess[str]:
        (found,) = [
            s for s in self.doc["jobs"]["postmerge"]["steps"]
            if str(s.get("name", "")).startswith(name)
        ]  # fmt: skip
        run = str(found["run"]).replace(
            "git@github.com:${GITHUB_REPOSITORY}.git", str(self.origin.bare)
        )
        assert "${{" not in run, f"{name}: an expression this rehearsal does not supply"
        # the step's own literal environment, as Actions sets it; expressions are this harness's
        literal = {
            key: str(value)
            for key, value in (found.get("env") or {}).items()
            if "${{" not in str(value)
        }
        return subprocess.run(
            ["bash", "-c", run],
            capture_output=True, text=True, check=False, cwd=self.work,
            env={**self.env(**extra), **literal},
        )  # fmt: skip

    def attest(self) -> None:
        """What the re-derive and sign steps leave: the signed attestation in the tree."""
        self.needs_gate = True
        out = self.temp / "postmerge-out"
        out.mkdir()
        (out / "attestation.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
        number = int(self.numbers.split()[0])
        (self.work / "attestations" / f"{number:06d}.json").write_text(
            json.dumps({"pr": number, "merge": self.merge}, indent=2) + "\n", encoding="utf-8"
        )

    def write(self, rel: str, text: str) -> None:
        path = self.work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def render(self) -> None:
        """The record, products and ledger steps, in the workflow's order."""
        for name in (RECORD_STEP, "Regenerate the merge products", "Write what the merge earned"):
            proc = self.step(name)
            assert proc.returncode == 0, (name, proc.stdout, proc.stderr)

    def publish(self, **extra: str) -> tuple[int, str]:
        proc = self.step(COMMIT_STEP, **extra)
        return proc.returncode, proc.stdout + proc.stderr

    def dispatched(self) -> list[str]:
        log = self.temp / "gh.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        return [line.split("replay_pr=")[1] for line in lines if "replay_pr=" in line]


def fresh_render_agrees(origin: Origin) -> None:
    """The products on main are what the commands render from main's tree at its parent: the
    catch-up published a render of a tree that exists, not one that no longer does."""
    check = origin.tmp / "check"
    subprocess.run(["git", "clone", "-q", str(origin.bare), str(check)], check=True, env=git_env())
    command(check, origin.tmp, "products", "HEAD^")
    assert git(check, "status", "--porcelain") == "", git(check, "diff")


def ledger_merges(origin: Origin) -> list[str]:
    return [entry["merge"] for entry in json.loads(origin.show("ledger/p.json"))["entries"]]


# --- the catch-up -------------------------------------------------------------------------------


def test_a_push_refused_by_a_merge_on_another_target_is_caught_up(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """#2's run renders while #3 merges on another target and its own run commits first. As the
    job stood it dispatched a replay of #2 (a second three-minute re-derive) or left it to a
    later run; now it publishes its own record on main as main is."""
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    three = origin.append(3, "t2")
    origin.bot(3, ledger=(three,))
    code, said = job.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    assert origin.subjects(4)[:2] == ["gate: #2 pass", "gate: #3 pass"], origin.subjects()
    assert json.loads(origin.show("attestations/000002.json"))["merge"] == two
    assert job.dispatched() == [], said
    assert ledger_merges(origin) == [three, two]  # each merge once, in the order credited
    fresh_render_agrees(origin)


def test_a_push_refused_by_a_merge_on_the_same_target_is_caught_up(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    origin.append(3, "t1")  # merged, its own run not committed yet
    code, said = job.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    assert origin.subjects(1) == ["gate: #2 pass"]
    assert job.dispatched() == []
    fresh_render_agrees(origin)


def test_a_partials_hole_children_ride_the_catch_up(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """What a partial's run writes into the tree is its record, not a product: the hole's node
    and the parent's regenerated Context reach main exactly as written."""
    origin = Origin(tmp_path)
    two = origin.merge(2, "submit/partial", {"targets/t1/nodes/n/attempts/x.lean": "-- partial\n"})
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.write("targets/t1/nodes/n--h1/Statement.lean", "theorem h1 : True := trivial\n")
    job.write("targets/t1/nodes/n--h1/META.yaml", "origin: skeleton-hole\nstatus: blocked\n")
    job.write("targets/t1/nodes/n/Context.lean", CONTEXT + "import Nodes.n__h1\n")
    job.render()
    origin.append(3, "t2")
    origin.bot(3)
    code, said = job.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    assert origin.show("targets/t1/nodes/n--h1/Statement.lean") == "theorem h1 : True := trivial"
    assert origin.show("targets/t1/nodes/n/Context.lean").endswith("import Nodes.n__h1")
    assert "n--h1" in json.loads(origin.show("targets/t1/graph.json"))["nodes"]
    fresh_render_agrees(origin)


def test_a_record_that_conflicts_with_main_is_replayed(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The one case the catch-up cannot settle: main changed a line this merge's record also
    changed. Nothing is pushed, and the merge is replayed on its own from main as it is."""
    origin = Origin(tmp_path)
    two = origin.merge(2, "submit/partial", {"targets/t1/nodes/n/attempts/x.lean": "-- partial\n"})
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.write("targets/t1/nodes/n/Context.lean", CONTEXT + "import Nodes.n__h1\n")
    job.render()
    before = origin.owner({"targets/t1/nodes/n/Context.lean": CONTEXT + "import Nodes.other\n"})
    code, said = job.publish()
    assert code == 0, said
    assert origin.main() == before, "nothing was pushed"
    assert job.dispatched() == ["2"], said
    assert git(job.work, "rev-parse", "HEAD") == before, "HEAD is main as the host has it"


def test_a_re_pin_of_the_rendering_gate_is_replayed(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The products describe main, so they are rendered by the gate main pins (F07-T33); a run
    whose rendering gate was re-pinned under it cannot render them, and replays."""
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    repin = json.dumps({"network_commit": PIN_B})
    before = origin.owner({"targets/t1/gate-spec.json": repin, "targets/t2/gate-spec.json": repin})
    code, said = job.publish()
    assert code == 0, said
    assert origin.main() == before
    assert job.dispatched() == ["2"], said


def test_a_merge_main_already_credits_is_not_credited_twice(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    before = origin.bot(2, files={"attestations/000002.json": "{}\n"})  # a replay got there first
    code, said = job.publish()
    assert code == 0, said
    assert origin.main() == before and job.dispatched() == [], said
    # the site step reads HEAD: it is main as the host has it, not the commit this run never pushed
    assert git(job.work, "rev-parse", "HEAD") == before


def test_a_batch_drops_what_another_run_credited_and_credits_the_rest(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Two runs may both cover an append: #2's own run, and #3's, which batched it while #2's
    was still going. Whichever pushes second drops #2 and records only #3, ledger line and all."""
    origin = Origin(tmp_path)
    two = origin.append(2)
    three = origin.append(3)
    job = Job(gate_doc, origin, "three", three, "2 3", merges=f"{two} {three}")
    job.render()
    origin.bot(2, ledger=(two,))
    code, said = job.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    assert origin.subjects(2) == ["gate: #3 pass", "gate: #2 pass"]
    assert ledger_merges(origin) == [two, three]
    fresh_render_agrees(origin)


def test_the_tag_cache_of_both_renders_is_kept_and_nothing_is_scanned_twice(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A tag scan elaborates a statement in the Mathlib image; the catch-up must not pay for one
    the run already made, nor drop one another run made."""
    origin = Origin(tmp_path)
    two = origin.merge(
        2, "propose/v", {"targets/t1/nodes/v/Statement.lean": "theorem v : 1 = 1 := rfl\n"}
    )
    job = Job(gate_doc, origin, "two", two, "2")
    job.render()
    origin.merge(
        3, "propose/w", {"targets/t2/nodes/w/Statement.lean": "theorem w : 2 = 2 := rfl\n"}
    )
    origin.bot(3)
    log = tmp_path / "uv.log"
    scans_before = log.read_text(encoding="utf-8").count("scanned t1/v")
    code, said = job.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    assert log.read_text(encoding="utf-8").count("scanned t1/v") == scans_before, said
    cache = json.loads(origin.show("targets/t1/.tags-cache.json"))
    assert ["tag-v"] in cache.values()
    assert ["tag-w"] in json.loads(origin.show("targets/t2/.tags-cache.json")).values()
    fresh_render_agrees(origin)


def test_a_push_refused_every_time_gives_up_loudly_and_replays(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    origin.append(3, "t2")
    hook = origin.bare / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho refused >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    code, said = job.publish(PUBLISH_ATTEMPTS="2")
    assert code != 0 and "::error::" in said, said
    assert job.dispatched() == ["2"], said


def test_two_runs_racing_on_two_targets_both_land_once(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The case the queue's per-target lanes make common: two proofs merged a minute apart,
    their runs overlapping. Each records its own merge, once."""
    origin = Origin(tmp_path)
    two = origin.proof(2, "t1")
    three = origin.proof(3, "t2")
    first = Job(gate_doc, origin, "two", two, "2")
    second = Job(gate_doc, origin, "three", three, "3", target="t2")
    for job in (first, second):
        job.attest()
        job.render()
    code, said = second.publish()
    assert code == 0, said
    code, said = first.publish()
    assert code == 0, said
    assert "caught up on" in said, said
    subjects = origin.subjects(2)
    assert sorted(subjects) == ["gate: #2 pass", "gate: #3 pass"], subjects
    assert sorted(ledger_merges(origin)) == sorted([two, three])
    assert {"000002.json", "000003.json"} <= set(
        json.loads(origin.show("frontier.json"))["attested"]
    )
    fresh_render_agrees(origin)


def test_the_first_push_lands_as_before_when_main_has_not_moved(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    code, said = job.publish()
    assert code == 0, said
    assert "caught up" not in said and "publish pushed" in said, said
    assert origin.subjects(1) == ["gate: #2 pass"]
    assert git(origin.bare, "rev-parse", "main^") == two  # rendered from the merge, nothing else
    fresh_render_agrees(origin)


# --- the record ---------------------------------------------------------------------------------


def test_the_record_is_taken_after_signing_and_before_any_product(gate_doc: dict[Any, Any]) -> None:
    names = [str(s.get("name", "")) for s in gate_doc["jobs"]["postmerge"]["steps"]]
    record = next(i for i, n in enumerate(names) if n.startswith(RECORD_STEP))
    assert names.index(next(n for n in names if n.startswith("Sign with the gate key"))) < record
    for later in ("Regenerate the merge products", "Write what the merge earned"):
        assert record < names.index(next(n for n in names if n.startswith(later))), later
    run = step_run(gate_doc, name=RECORD_STEP)
    assert "git diff --cached --binary" in run and "record.patch" in run


def test_the_catch_up_renders_with_the_gate_main_pins(gate_doc: dict[Any, Any]) -> None:
    """F07-T33's split stands: the products and the ledger are rendered by network-render."""
    (step,) = [
        s for s in gate_doc["jobs"]["postmerge"]["steps"]
        if str(s.get("name", "")).startswith(COMMIT_STEP)
    ]  # fmt: skip
    env = step["env"]
    for key in ("LEDGER_CMD", "PRODUCTS_CMD"):
        assert "--project network-render" in env[key], key
        assert "--project network " not in env[key], key
    assert "cli ledger" in env["LEDGER_CMD"] and '"$MERGE"' in env["LEDGER_CMD"]
    assert "cli products" in env["PRODUCTS_CMD"] and '"$COMMIT"' in env["PRODUCTS_CMD"]
    assert "git rebase" not in str(step["run"]), "a rebase over moved inputs is what this replaces"


# --- who records a building merge ---------------------------------------------------------------


def test_a_building_merge_records_itself_even_with_a_later_merge_on_main(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Its record needs its own re-derive and signature; leaving it to a later run only costs a
    replay once that run has committed. An append still leaves itself to the later run (T45)."""
    graph = Graph(tmp_path / "g")
    two = graph.merge(
        2, "submit/p", {"targets/t1/nodes/n/Proof.lean": "theorem x : True := trivial\n"}
    )
    three = graph.append(3)
    prs = {two: 2, three: 3}
    code, out, said, _calls = run_find_step(gate_doc, graph, tmp_path / "proof", two, prs)
    assert code == 0 and out.get("run") == "true", (out, said)
    graph2 = Graph(tmp_path / "g2")
    four = graph2.append(4)
    graph2.append(5)
    code, out, said, _calls = run_find_step(gate_doc, graph2, tmp_path / "append", four, {four: 4})
    assert code == 0 and out.get("run") == "false", (out, said)


def test_a_plan_leaves_a_building_merge_to_its_own_run_while_that_run_is_going(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    helper: dict[str, Any] = {"__name__": "postmerge_batch"}
    exec(compile(helper_source(gate_doc), "postmerge_batch.py", "exec"), helper)  # noqa: S102
    graph = Graph(tmp_path / "g")
    two = graph.merge(
        2, "submit/p", {"targets/t1/nodes/n/Proof.lean": "theorem x : True := trivial\n"}
    )
    four = graph.append(4)
    log = []
    for line in graph.git("log", "--first-parent", "--format=%H%x09%P%x09%s", "HEAD").splitlines():
        sha, parents, subject = line.split("\t", 2)
        log.append((sha, len(parents.split()), subject))

    def targets_of(_sha: str) -> list[str]:
        return ["t1"]

    def pin_of(_sha: str, _target: str) -> str:
        return PIN_A

    plan = helper["plan"]
    going = plan(
        four, 4, log=log, targets_of=targets_of, pin_of=pin_of, in_flight=lambda s: s == two
    )
    assert going == {"batch": "false", "replay": ""}, going
    lost = plan(four, 4, log=log, targets_of=targets_of, pin_of=pin_of, in_flight=lambda _s: False)
    assert lost == {"batch": "false", "replay": "2"}, lost
    # and the workflow's plan asks the host, through the helper, with no flag to forget
    run = step_run(gate_doc, id_="pr")
    assert 'plan "$merge" "$number"' in run
    assert "actions/runs?head_sha=" in helper_source(gate_doc)


def test_a_merge_that_touched_no_target_is_not_replayed(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Found live on 2026-10-03: #361's run replayed #321, a workflow change that touched no
    target, and the replay said "touched no target; nothing to record". Such a merge never gets a
    gate commit, so every later plan found it unrecorded and spent a run on it."""
    helper: dict[str, Any] = {"__name__": "postmerge_batch"}
    exec(compile(helper_source(gate_doc), "postmerge_batch.py", "exec"), helper)  # noqa: S102
    graph = Graph(tmp_path / "g")
    graph.merge(2, "f07-workflow", {".github/workflows/merge.yml": "on: {}\n"})
    four = graph.append(4)
    log = []
    for line in graph.git("log", "--first-parent", "--format=%H%x09%P%x09%s", "HEAD").splitlines():
        sha, parents, subject = line.split("\t", 2)
        log.append((sha, len(parents.split()), subject))

    def targets_of(sha: str) -> list[str]:
        names = graph.git("diff", "--name-only", f"{sha}^", sha).splitlines()
        return sorted({n.split("/")[1] for n in names if n.startswith("targets/")})

    got = helper["plan"](
        four, 4, log=log, targets_of=targets_of, pin_of=lambda _s, _t: PIN_A,
        in_flight=lambda _s: False,
    )  # fmt: skip
    assert got == {"batch": "false", "replay": ""}, got
