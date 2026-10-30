"""A refused push re-lays the merge's own record, and the products follow (the owner, 2026-10-30).

Measured on graph run 40902300897 (2026-10-29, #1179, a proof on erdos-849): the post-merge job's
first push was refused because main had moved since the merge. Each catch-up (F07-T55) then spent
about 76 s rendering every product on main as it now was, and pushed — and was refused within a
second, because an append's bot commit, an outline or a batch's gate commit had landed during those
76 s. Six refusals, ``publish gave-up``, a replay, and the attestation reached main at 16:01:33, 31
minutes after the merge (15:30:39). The same shape on erdos-849 on 2026-10-27 (run 40500099998).

The products are derived (F03-R11): a function of the tree, made again by anyone. What only this
run can put on main is its own record — the attestation(s) it signed, a partial's hole children and
the parent's Context and META it wrote, the attempts file, its ledger lines. So when the first push
is refused, the catch-up lays only that record on main as it now is and pushes it without rendering
(seconds, not a render), and render.yml, dispatched once the record has landed, brings the products
up to date (F07-T60's workflow, whose concurrency group coalesces the dispatches). The first push
still carries the record and the products together, exactly as before.

``test_the_live_run_lands_its_record_without_a_replay`` drives the workflow's own commit step
against a bare remote whose main moves on the live run's own clock: every first-parent commit main
took between #1179's merge and 15:50, delivered at its offset from the job's first push, with the
commands costed as the live log measured them (a product render 75 s, a ledger line 0.76 s, a fetch
0.5 s, a push 0.7 s). Against the job as it stood it gave up after six refusals, exactly as live.

The olean cache job (F32-T6's finding, carried here because it reads this step): a born-proved
hole's files exist only in the commit that lands the record, never in the merge commit, so the
cache job builds the commit the record landed in (``recorded``), falling back to the merge.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_postmerge_batch import git_env
from test_finding_postmerge_catch_up import Job, Origin, fresh_render_agrees, git, tools
from test_finding_render_without_merge import render_follows

#: graph run 40902300897: #1179 merged at 15:30:39; the job's first push was refused at 15:39:04.
MERGED_AT = "2026-10-29T15:30:39Z"
FIRST_PUSH_AT = "2026-10-29T15:39:04Z"
#: Every commit on main's first-parent line from #1179's merge to 15:50 (`git log --first-parent
#: origin/main`), as (committer time, subject). None of them credits the run's own merge.
LIVE_MAIN = (
    ("2026-10-29T15:31:57Z", "Merge pull request #1207"),
    ("2026-10-29T15:33:21Z", "gate: #1205 #1206 #1208 pass"),
    ("2026-10-29T15:35:09Z", "gate: #1175 pass"),
    ("2026-10-29T15:36:12Z", "Merge pull request #1181"),
    ("2026-10-29T15:36:15Z", "Merge pull request #1182"),
    ("2026-10-29T15:36:20Z", "Merge pull request #1183"),
    ("2026-10-29T15:36:24Z", "Merge pull request #1184"),
    ("2026-10-29T15:36:29Z", "Merge pull request #1185"),
    ("2026-10-29T15:36:33Z", "Merge pull request #1186"),
    ("2026-10-29T15:36:37Z", "Merge pull request #1187"),
    ("2026-10-29T15:36:42Z", "Merge pull request #1188"),
    ("2026-10-29T15:38:20Z", "outline: 1 for erdos-849"),
    ("2026-10-29T15:40:09Z", "gate: #1178 pass"),
    ("2026-10-29T15:41:05Z", "Merge pull request #1189"),
    ("2026-10-29T15:41:08Z", "Merge pull request #1190"),
    ("2026-10-29T15:41:12Z", "Merge pull request #1191"),
    ("2026-10-29T15:41:16Z", "Merge pull request #1192"),
    ("2026-10-29T15:41:19Z", "Merge pull request #1193"),
    ("2026-10-29T15:41:23Z", "Merge pull request #1195"),
    ("2026-10-29T15:41:26Z", "Merge pull request #1197"),
    ("2026-10-29T15:41:30Z", "Merge pull request #1198"),
    ("2026-10-29T15:42:39Z", "gate: #1207 pass"),
    ("2026-10-29T15:43:53Z", "outline: 1 for erdos-849"),
    ("2026-10-29T15:44:14Z", "Merge pull request #1209"),
    ("2026-10-29T15:44:18Z", "Merge pull request #1210"),
    ("2026-10-29T15:45:19Z", "Merge pull request #1211"),
    ("2026-10-29T15:45:23Z", "Merge pull request #1212"),
    ("2026-10-29T15:45:44Z", "outline: 1 for erdos-68"),
    ("2026-10-29T15:46:21Z", "Merge pull request #1213"),
    ("2026-10-29T15:47:20Z", "Merge pull request #1180"),
    ("2026-10-29T15:48:44Z", "gate: #1181 #1182 #1183 pass"),
    ("2026-10-29T15:48:52Z", "Merge pull request #1200"),
    ("2026-10-29T15:48:57Z", "Merge pull request #1214"),
    ("2026-10-29T15:49:48Z", "Merge pull request #1199"),
)
#: What each command cost on the live runner (the log's timestamps): `products` is the render the
#: catch-up paid on every attempt; `ledger` is one `opn-gate ledger` (15:39:02.01 to 15:39:02.77).
COST_S = {"products": 75.0, "ledger": 0.76, "fetch": 0.5, "push": 0.7}

#: `git`, as the commit step sees it: before a push or a fetch, main takes every live commit whose
#: time has come; each push and fetch costs its time; every push is logged with its answer.
CLOCK_GIT = r"""#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
real, args = os.environ["REAL_GIT"], sys.argv[1:]
state = pathlib.Path(os.environ["CLOCK_STATE"])
doc = json.loads(state.read_text(encoding="utf-8"))
cost = json.loads(os.environ["CLOCK_COST"])
rest = list(args)
while rest[:1] == ["-C"] or rest[:1] == ["-c"]:
    rest = rest[2:]
verb = rest[0] if rest else ""
if verb in ("push", "fetch"):
    mover = os.environ["CLOCK_MOVER"]
    due = [m for m in doc["moves"] if m["at"] <= doc["now"]]
    for move in due:
        g = lambda *a: subprocess.run([real, "-C", mover, *a], check=True, capture_output=True)
        g("fetch", "-q", "origin")
        g("reset", "-q", "--hard", "origin/main")
        name = f"move-{move['i']:03d}.yaml"
        rel = pathlib.Path(mover, "targets", "t2", "nodes", "n", "attempts", name)
        rel.parent.mkdir(parents=True, exist_ok=True)
        rel.write_text(f"{move['subject']}\n", encoding="utf-8")
        g("add", "-A")
        g("commit", "-q", "-m", move["subject"])
        g("push", "-q", "origin", "HEAD:main")
    doc["moves"] = [m for m in doc["moves"] if m["at"] > doc["now"]]
    doc["now"] += cost[verb]
proc = subprocess.run([real, *args], check=False)
if verb == "push":
    doc["pushes"].append({"at": doc["now"], "ok": proc.returncode == 0})
state.write_text(json.dumps(doc), encoding="utf-8")
sys.exit(proc.returncode)
"""

#: `uv`, costed: the stand-in gate's commands, each charged to the clock before it runs.
CLOCK_UV = r"""#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
state = pathlib.Path(os.environ["CLOCK_STATE"])
doc = json.loads(state.read_text(encoding="utf-8"))
cost = json.loads(os.environ["CLOCK_COST"])
for name in ("products", "ledger"):
    if name in args:
        doc["now"] += cost[name]
        doc["commands"].append({"at": doc["now"], "name": name})
state.write_text(json.dumps(doc), encoding="utf-8")
sys.exit(subprocess.run([os.environ["CLOCK_UV_REAL"], *args], check=False).returncode)
"""


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def at(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def clocked(tmp_path: Path, origin: Origin) -> tuple[dict[str, str], Path]:
    """The environment that puts the commit step on the live run's clock, and its state file."""
    bin_dir = tmp_path / "clock-bin"
    bin_dir.mkdir()
    for name, text in (("git", CLOCK_GIT), ("uv", CLOCK_UV)):
        tool = bin_dir / name
        tool.write_text(text, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    t0 = at(FIRST_PUSH_AT)
    moves = [
        {"i": i, "at": (at(stamp) - t0).total_seconds(), "subject": subject}
        for i, (stamp, subject) in enumerate(LIVE_MAIN)
    ]
    state = tmp_path / "clock.json"
    state.write_text(json.dumps({"now": 0.0, "moves": moves, "pushes": [], "commands": []}))
    real_git = shutil.which("git")
    assert real_git, "git is not on PATH"
    fake_uv = tools(tmp_path) / "uv"
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{tools(tmp_path)}{os.pathsep}{os.environ['PATH']}",
        "REAL_GIT": real_git, "CLOCK_STATE": str(state), "CLOCK_COST": json.dumps(COST_S),
        "CLOCK_MOVER": str(origin.mover.root), "CLOCK_UV_REAL": str(fake_uv),
    }  # fmt: skip
    return env, state


def renders(job: Job) -> list[str]:
    log = job.temp / "gh.log"
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return [line for line in lines if line.startswith("workflow run render.yml")]


def outputs(job: Job) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in (job.temp / "output").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            found[key] = value
    return found


PRODUCTS = ("frontier.json", "info.json", "claims.json", "graph.json")


def changed_by(origin: Origin, rev: str) -> list[str]:
    return git(origin.bare, "diff", "--name-only", f"{rev}^", rev).splitlines()


# --- the live run, replayed ---------------------------------------------------------------------


def test_the_live_run_lands_its_record_without_a_replay(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    env, state = clocked(tmp_path, origin)
    code, said = job.publish(**env)
    doc = json.loads(state.read_text(encoding="utf-8"))
    pushes = doc["pushes"]
    refused = sum(1 for p in pushes if not p["ok"])
    landed = next((p["at"] for p in pushes if p["ok"]), None)
    pre = (at(FIRST_PUSH_AT) - at(MERGED_AT)).total_seconds()
    report = {
        "exit": code, "pushes": len(pushes), "refused": refused,
        "landed_s_after_first_push": landed,
        "merge_to_record_s": None if landed is None else pre + landed,
        "renders_in_publish": sum(1 for c in doc["commands"] if c["name"] == "products"),
        "replays": job.dispatched(), "render_dispatches": len(renders(job)),
    }  # fmt: skip
    print("record-first replay of run 40902300897:", json.dumps(report, sort_keys=True))
    assert code == 0, said
    assert job.dispatched() == [], said  # no replay
    assert refused == 1, report  # the first push only: main had moved since the merge
    assert landed is not None and landed < 10, report  # seconds, not a render
    assert report["renders_in_publish"] == 0, report
    # the record is on main, credited once, and the commit carries no product
    assert origin.subjects(40).count("gate: #2 pass") == 1, origin.subjects(40)
    assert json.loads(origin.show("attestations/000002.json"))["merge"] == two
    assert not [p for p in changed_by(origin, "main") if p.endswith(PRODUCTS)], said
    assert renders(job) == ["workflow run render.yml --repo owner/graph --ref main"], said
    # and the cache job is told where the record landed
    assert outputs(job).get("recorded") == origin.main(), outputs(job)
    # render.yml, once dispatched, brings the products up to date with the record in them
    render_follows(origin)
    assert "000002.json" in json.loads(origin.show("frontier.json"))["attested"]
    fresh_render_agrees(origin)


# --- what the catch-up carries, and what it never does -----------------------------------------


def test_a_partials_record_lands_whole_without_the_products(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Everything 'Keep this merge's own record' took — the attestation, the hole's node, the
    parent's Context — and the ledger line, in one commit; the products come after, by render."""
    origin = Origin(tmp_path)
    two = origin.merge(2, "submit/partial", {"targets/t1/nodes/n/attempts/x.lean": "-- partial\n"})
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.write("targets/t1/nodes/n--h1/Statement.lean", "theorem h1 : True := trivial\n")
    job.write("targets/t1/nodes/n--h1/META.yaml", "origin: skeleton-hole\nstatus: blocked\n")
    job.write("targets/t1/nodes/n/Context.lean", "-- generated\nimport Defs\nimport Nodes.n__h1\n")
    job.render()
    three = origin.append(3, "t2")
    origin.bot(3, ledger=(three,))
    log = tmp_path / "uv.log"
    renders_before = log.read_text(encoding="utf-8").count("products")
    code, said = job.publish()
    assert code == 0, said
    assert log.read_text(encoding="utf-8").count("products") == renders_before, "no render"
    assert origin.subjects(2) == ["gate: #2 pass", "gate: #3 pass"]
    landed = set(changed_by(origin, "main"))
    assert {
        "attestations/000002.json",
        "targets/t1/nodes/n--h1/Statement.lean",
        "targets/t1/nodes/n--h1/META.yaml",
        "targets/t1/nodes/n/Context.lean",
        "ledger/p.json",
    } <= landed, landed
    assert not [p for p in landed if p.endswith(PRODUCTS)], landed
    entries = json.loads(origin.show("ledger/p.json"))["entries"]
    assert [e["merge"] for e in entries] == [three, two]
    assert renders(job), said
    render_follows(origin)
    assert "n--h1" in json.loads(origin.show("targets/t1/graph.json"))["nodes"]
    fresh_render_agrees(origin)


def test_the_first_push_still_carries_the_products_and_dispatches_no_render(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    code, said = job.publish()
    assert code == 0 and "publish pushed" in said, said
    assert "frontier.json" in changed_by(origin, "main")
    assert renders(job) == [], said
    assert outputs(job).get("recorded") == origin.main(), outputs(job)
    fresh_render_agrees(origin)


def test_a_record_already_credited_by_another_run_names_that_commit(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A replay got there first: nothing is pushed, nothing is credited twice, and the commit
    that carries the record is the one that credits it."""
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    theirs = origin.bot(2, files={"attestations/000002.json": "{}\n"})
    origin.owner({"AGENTS.md": "a guide\n"})
    code, said = job.publish()
    assert code == 0, said
    assert origin.subjects(5).count("gate: #2 pass") == 1
    assert renders(job) == [] and job.dispatched() == [], said
    assert outputs(job).get("recorded") == theirs, outputs(job)


def test_a_record_that_lands_nowhere_names_no_commit(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Refused every time: it replays and fails, as before; the cache falls back to the merge."""
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    origin.append(3, "t2")
    hook = origin.bare / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho refused >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    code, said = job.publish(PUBLISH_ATTEMPTS="3")
    assert code != 0 and "::error::" in said, said
    assert job.dispatched() == ["2"], said
    assert renders(job) == [], said
    assert "recorded" not in outputs(job), outputs(job)


def test_a_failed_render_dispatch_is_a_warning_not_a_lost_record(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """C7: the record has landed; the products follow at the next merge's run or a render."""
    origin = Origin(tmp_path)
    two = origin.proof(2)
    job = Job(gate_doc, origin, "two", two, "2")
    job.attest()
    job.render()
    origin.append(3, "t2")
    failing = tmp_path / "failing-gh"
    failing.mkdir()
    gh = failing / "gh"
    gh.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$GH_LOG"\nexit 1\n')
    gh.chmod(0o755)
    code, said = job.publish(PATH=f"{failing}{os.pathsep}{job.env()['PATH']}")
    assert code == 0, said
    assert "::warning::render.yml was not dispatched" in said, said
    assert origin.subjects(1) == ["gate: #2 pass"]


# --- the cache job builds the commit the record landed in (F32-T6's finding) --------------------


def test_the_cache_job_builds_the_commit_the_record_landed_in(gate_doc: dict[Any, Any]) -> None:
    postmerge, cache = gate_doc["jobs"]["postmerge"], gate_doc["jobs"]["cache"]
    assert postmerge["outputs"]["recorded"] == "${{ steps.record.outputs.recorded }}"
    (commit_step,) = [
        s for s in postmerge["steps"] if str(s.get("name", "")).startswith("Commit the attestation")
    ]
    assert commit_step.get("id") == "record"
    want = "${{ needs.postmerge.outputs.recorded || needs.postmerge.outputs.merge }}"
    (checkout,) = [
        s
        for s in cache["steps"]
        if s.get("uses", "").startswith("actions/checkout") and "path" not in (s.get("with") or {})
    ]
    assert checkout["with"]["ref"] == want
    (publish,) = [
        s for s in cache["steps"] if str(s.get("name", "")).startswith("Publish the olean cache")
    ]
    assert publish["env"]["COMMIT"] == want
    run = str(publish["run"])
    assert '--commit "$COMMIT"' in run and '"$MERGE"' not in run


def test_the_clock_harness_moves_main_by_itself(tmp_path: Path) -> None:
    """The replay's own instrument: a fetch at a time delivers exactly the commits due by then."""
    origin = Origin(tmp_path)
    env, state = clocked(tmp_path, origin)
    work = tmp_path / "probe"
    git(tmp_path, "clone", "-q", str(origin.bare), str(work))
    before = len(origin.subjects(60))
    subprocess.run(
        ["git", "-C", str(work), "fetch", "-q", "origin"],
        check=True, env={**git_env(), **env},
    )  # fmt: skip
    due = sum(1 for stamp, _s in LIVE_MAIN if at(stamp) <= at(FIRST_PUSH_AT))
    assert len(origin.subjects(60)) == before + due
    assert json.loads(state.read_text(encoding="utf-8"))["now"] == COST_S["fetch"]
