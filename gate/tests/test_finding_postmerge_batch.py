"""F07-T45: one post-merge run records every merge that has no ``gate:`` commit yet.

The merge actor now merges a batch of appends in one run (``test_finding_merge_actor_batch.py``).
Each merge is a push to ``main`` and starts a post-merge run, and as the job stood each run
recorded its own merge alone, from a checkout of its own merge commit: the first run's push would
be refused because the later merges moved ``main`` under it, and it would dispatch a replay (F07-
T33), so a batch of eight would cost eight replays in sequence — the rounds the batch exists to
save. Now:

- a run whose merge already has a later merge after it on ``main`` records nothing and says which
  run will: the later merge is a push, so it has a post-merge run of its own (``later-merge``);
- the run at the head walks ``main``'s first-parent line back to the last gate commit that is not
  a replay, and records every merge in between (``plan``): appends only, each classified with the
  pinned gate over ``merge^1..merge``, one ledger call per merge in order, the products once, and
  one commit ``gate: #A #B #C pass``;
- anything it cannot record in a batch (a building merge, a different pin, a diff the gate
  refuses) is dispatched to a replay of its own, never dropped;
- the replay's idempotence check reads a number inside a multi-number subject.

The program is the heredoc the workflow writes to ``postmerge_batch.py``, run here as it stands
over real git histories (the subjects are the host's: ``Merge pull request #N from owner/branch``,
read from the live graph's first-parent log). It was seen red against the job as it stood, with the
same program at the old behaviour (``engineering/evidence/F07/task-45-red.txt``).
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc

from opn_gate import config

PIN_A, PIN_B = "a" * 40, "b" * 40
REPO = "owner/graph"
FAKE = "fake"  # the host is a fake, and so is its token


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def steps(gate_doc: dict[Any, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = gate_doc["jobs"]["postmerge"]["steps"]
    return found


def step_run(gate_doc: dict[Any, Any], *, id_: str | None = None, name: str = "") -> str:
    (step,) = [
        s
        for s in steps(gate_doc)
        if (id_ is not None and s.get("id") == id_)
        or (name and str(s.get("name", "")).startswith(name))
    ]
    return str(step["run"])


def helper_source(gate_doc: dict[Any, Any]) -> str:
    run = step_run(gate_doc, id_="pr")
    body = run.split("cat > \"$helper\" <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    return textwrap.dedent(body)


@pytest.fixture(scope="module")
def helper(gate_doc: dict[Any, Any]) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__name__": "postmerge_batch"}
    exec(compile(helper_source(gate_doc), "postmerge_batch.py", "exec"), namespace)  # noqa: S102
    return namespace


@pytest.fixture(scope="module")
def helper_file(gate_doc: dict[Any, Any], tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("helper") / "postmerge_batch.py"
    path.write_text(helper_source(gate_doc), encoding="utf-8")
    return path


# --- a real history ------------------------------------------------------------------------------


def git_env() -> dict[str, str]:
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)  # the hook exports GIT_DIR
    env.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
    )  # fmt: skip
    return env


class Graph:
    """A graph repository whose ``main`` is built the way the host builds it: merge commits with
    the host's subject, first parent the old ``main``, and direct pushes of gate commits."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        self.write("targets/t1/gate-spec.json", json.dumps({"network_commit": PIN_A}))
        self.write("targets/t2/gate-spec.json", json.dumps({"network_commit": PIN_A}))
        for product in ("attestations/.keep", "info.json"):  # what the bot commit adds by name
            self.write(product, "")
        self.commit("seed")
        self.bot(1)

    def git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True, text=True, check=True, env=git_env(),
        )  # fmt: skip
        return proc.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, subject: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", subject)
        return self.git("rev-parse", "HEAD")

    def bot(self, *numbers: int, replayed: bool = False) -> str:
        self.write("frontier.json", json.dumps({"after": list(numbers)}))
        credits = " ".join(f"#{n}" for n in numbers)
        return self.commit(f"gate: {credits} pass" + (" (replayed)" if replayed else ""))

    def branch(self, name: str, files: dict[str, str], *, base: str = "main") -> None:
        self.git("checkout", "-q", "-b", name, base)
        for rel, text in files.items():
            self.write(rel, text)
        self.commit(f"add {', '.join(files)}")
        self.git("checkout", "-q", "main")

    def merge(self, number: int, name: str, files: dict[str, str] | None = None) -> str:
        if files is not None:
            self.branch(name, files)
        self.git(
            "merge", "--no-ff", "-q", "-m", f"Merge pull request #{number} from owner/{name}", name
        )
        return self.git("rev-parse", "HEAD")

    def append(self, number: int, target: str = "t1") -> str:
        rel = f"targets/{target}/nodes/n/attempts/2026092{number:04d}-p.yaml"
        return self.merge(number, f"append/a{number}", {rel: f"postmortem {number}\n"})


def run_helper(helper_file: Path, graph: Graph, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(helper_file), *args],
        capture_output=True, text=True, check=False, cwd=graph.root, env=git_env(),
    )  # fmt: skip


def plan_of(helper_file: Path, graph: Graph, merge: str, own: int) -> dict[str, str]:
    proc = run_helper(helper_file, graph, "plan", merge, str(own))
    assert proc.returncode == 0, proc.stderr
    return dict(line.split("=", 1) for line in proc.stdout.splitlines())


def uncredited(helper: dict[str, Any], graph: Graph) -> list[int]:
    found = helper["uncredited"](log(graph))
    return [number for number, _sha, _branch in found or []]


def log(graph: Graph) -> list[tuple[str, int, str]]:
    rows = []
    for line in graph.git("log", "--first-parent", "--format=%H%x09%P%x09%s", "HEAD").splitlines():
        sha, parents, subject = line.split("\t", 2)
        rows.append((sha, len(parents.split()), subject))
    return rows


# --- which merges a run records --------------------------------------------------------------


def test_the_run_at_the_head_records_every_merge_since_the_last_gate_commit(
    helper: dict[str, Any], tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.append(2)
    graph.append(3)
    assert uncredited(helper, graph) == [2, 3]
    found = helper["uncredited"](log(graph))
    assert [branch for _n, _s, branch in found] == ["append/a2", "append/a3"]


def test_a_replay_between_is_walked_past_and_what_it_credits_left_out(
    helper: dict[str, Any], tmp_path: Path
) -> None:
    """A replay's commit credits one old merge and says nothing of the merges before it."""
    graph = Graph(tmp_path / "g")
    graph.append(2)
    graph.bot(9, replayed=True)  # a lost merge from long ago, replayed now
    graph.append(3)
    graph.bot(3, replayed=True)
    graph.append(4)
    assert uncredited(helper, graph) == [2, 4]


def test_the_matcher_reads_a_number_inside_a_multi_number_subject(helper: dict[str, Any]) -> None:
    credited = helper["credited"]
    assert helper["credits"]("gate: #2 #3 pass") == [2, 3]
    assert credited(["gate: #2 #3 pass"], 3) and credited(["gate: #2 #3 pass"], 2)
    assert credited(["gate: #2 pass (replayed) · cc @alice"], 2)
    assert credited(["gate: #7 pass"], 7)  # the single subject, as before
    assert not credited(["gate: #23 pass"], 2) and not credited(["gate: #23 pass"], 3)
    assert not credited(["gate: #2 #3 pass"], 23) and not credited(["gate: #12 pass"], 1)
    assert not credited(["Merge pull request #2 from owner/append/x"], 2)


def test_the_replay_check_uses_the_matcher_on_mains_first_parent_line(
    helper_file: Path, tmp_path: Path, gate_doc: dict[Any, Any]
) -> None:
    graph = Graph(tmp_path / "g")
    graph.append(2)
    graph.append(3)
    graph.bot(2, 3)
    assert run_helper(helper_file, graph, "credited", "HEAD", "3").returncode == 0
    assert run_helper(helper_file, graph, "credited", "HEAD", "2").returncode == 0
    assert run_helper(helper_file, graph, "credited", "HEAD", "4").returncode == 1
    run = step_run(gate_doc, id_="pr")
    assert 'python3 "$helper" credited HEAD "$number"' in run


def test_a_later_merge_on_main_is_seen_and_a_bot_commit_is_not(
    helper_file: Path, tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    three = graph.append(3)
    assert run_helper(helper_file, graph, "later-merge", two, "HEAD").returncode == 0
    assert run_helper(helper_file, graph, "later-merge", three, "HEAD").returncode == 1
    graph.bot(2, 3)
    assert run_helper(helper_file, graph, "later-merge", three, "HEAD").returncode == 1


# --- the plan ----------------------------------------------------------------------------------


def test_a_batch_of_appends_is_one_run(helper_file: Path, tmp_path: Path) -> None:
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    three = graph.append(3, "t2")
    four = graph.append(4)
    got = plan_of(helper_file, graph, four, 4)
    assert got == {
        "batch": "true",
        "numbers": "2 3 4",
        "merges": f"{two} {three} {four}",
        "targets": "t1 t2",
        "target": "t1",
        "pin": PIN_A,
        "replay": "",
    }


def test_a_merge_alone_is_recorded_as_before(helper_file: Path, tmp_path: Path) -> None:
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    assert plan_of(helper_file, graph, two, 2) == {"batch": "false", "replay": ""}
    graph.bot(2)
    proof = graph.merge(
        5, "submit/p", {"targets/t1/nodes/n/Proof.lean": "theorem x : True := trivial\n"}
    )
    assert plan_of(helper_file, graph, proof, 5) == {"batch": "false", "replay": ""}


def test_a_building_merge_is_never_batched_and_the_others_are_replayed(
    helper_file: Path, tmp_path: Path
) -> None:
    """The actor never batches a building pull request, so this is a lost run: the head records
    its own merge alone, exactly as before, and every other one gets a replay of its own."""
    graph = Graph(tmp_path / "g")
    graph.merge(2, "submit/p", {"targets/t1/nodes/n/Proof.lean": "theorem x : True := trivial\n"})
    four = graph.append(4)
    assert plan_of(helper_file, graph, four, 4) == {"batch": "false", "replay": "2"}
    graph.bot(4)  # the head's own commit; the replay of #2 records it on its own
    graph.append(5)
    six = graph.merge(6, "propose/v", {"targets/t1/nodes/v/Statement.lean": "x\n"})
    assert plan_of(helper_file, graph, six, 6) == {"batch": "false", "replay": "5"}


def test_merges_pinned_to_different_gates_are_not_batched(
    helper_file: Path, tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.append(2)
    graph.write("targets/t2/gate-spec.json", json.dumps({"network_commit": PIN_B}))
    graph.commit("re-pin t2")  # a direct push: no merge, no gate commit
    three = graph.append(3, "t2")
    assert plan_of(helper_file, graph, three, 3) == {"batch": "false", "replay": "2"}


def test_a_merge_the_batch_cannot_hold_is_replayed_not_dropped(
    helper_file: Path, tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.merge(2, "append/two", {"targets/t1/a.yaml": "a\n", "targets/t2/b.yaml": "b\n"})
    graph.append(3)
    four = graph.append(4)
    got = plan_of(helper_file, graph, four, 4)
    assert (got["batch"], got["numbers"], got["replay"]) == ("true", "3 4", "2")


def test_a_run_whose_walk_disagrees_records_its_own_merge_alone(
    helper_file: Path, tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.append(2)
    three = graph.append(3)
    assert plan_of(helper_file, graph, three, 99) == {"batch": "false", "replay": ""}


def test_an_append_merged_behind_main_diffs_as_its_own_file_alone(tmp_path: Path) -> None:
    """The classifier runs over ``--base merge^ --head merge`` (a tree diff against the first
    parent). For an append merged behind main that is exactly the file it adds: the merge commit
    applies the branch's changes onto main as it was, and ``merge^...merge`` agrees, because the
    first parent is an ancestor of the merge."""
    graph = Graph(tmp_path / "g")
    graph.branch("append/late", {"targets/t1/nodes/n/attempts/late.yaml": "late\n"})  # cut now
    graph.append(2)
    graph.bot(2)  # main moves twice after the branch was cut
    merge = graph.merge(3, "append/late")
    two_dot = graph.git("diff", "--name-only", f"{merge}^", merge).splitlines()
    three_dot = graph.git("diff", "--name-only", f"{merge}^...{merge}").splitlines()
    assert two_dot == three_dot == ["targets/t1/nodes/n/attempts/late.yaml"]


# --- the job, run as it stands with a fake host ------------------------------------------------


FAKE_GH = """#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(" ".join(args) + "\\n")
prs = json.loads(os.environ["GH_PRS"])
path = next((a for a in args if a.startswith("repos/")), "")
found = re.match(r"repos/[^/]+/[^/]+/commits/([0-9a-f]+)/pulls$", path)
if found:
    number = prs.get(found.group(1))
    merged = [{"number": number, "merged_at": "x", "user": {"login": "bot"}}]
    print(json.dumps(merged if number else []))
elif re.match(r"repos/[^/]+/[^/]+/pulls/[0-9]+$", path):
    print("open-proof-network[bot]" if "--jq" in args else json.dumps({"user": {"login": "bot"}}))
sys.exit(0)
"""


def run_find_step(
    gate_doc: dict[Any, Any], graph: Graph, tmp_path: Path, sha: str, prs: dict[str, int]
) -> tuple[int, dict[str, str], str, list[str]]:
    """The ``pr`` step on a push event, from a clone of ``graph`` checked out at ``sha``."""
    clone = tmp_path / f"clone-{sha[:7]}"
    subprocess.run(
        ["git", "clone", "-q", str(graph.root), str(clone)], check=True, env=git_env()
    )  # fmt: skip
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", sha], check=True, env=git_env())
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    runner_temp = tmp_path / f"temp-{sha[:7]}"
    runner_temp.mkdir()
    output = runner_temp / "output"
    output.write_text("", encoding="utf-8")
    gh_log = runner_temp / "gh.log"
    env = git_env()
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", GH_LOG=str(gh_log), GH_PRS=json.dumps(prs),
        GH_TOKEN=FAKE, GITHUB_EVENT_NAME="push", GITHUB_SHA=sha, GITHUB_REPOSITORY=REPO,
        GITHUB_OUTPUT=str(output), RUNNER_TEMP=str(runner_temp), REPLAY_PR="",
    )  # fmt: skip
    proc = subprocess.run(
        ["bash", "-c", step_run(gate_doc, id_="pr")],
        capture_output=True, text=True, check=False, cwd=clone, env=env,
    )  # fmt: skip
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    calls = gh_log.read_text().splitlines() if gh_log.exists() else []
    return proc.returncode, outputs, proc.stdout + proc.stderr, calls


def test_the_runs_of_a_batch_leave_their_merges_to_the_last_and_it_records_them_all(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    two, three, four = graph.append(2), graph.append(3), graph.append(4)
    prs = {two: 2, three: 3, four: 4}
    for sha, number in ((two, 2), (three, 3)):
        code, out, said, _calls = run_find_step(gate_doc, graph, tmp_path, sha, prs)
        assert code == 0 and out.get("run") == "false", (number, out, said)
        assert f"records #{number}" in said, said
    code, out, said, _calls = run_find_step(gate_doc, graph, tmp_path, four, prs)
    assert code == 0, said
    assert out["run"] == "true" and out["batch"] == "true", (out, said)
    assert (out["numbers"], out["merges"]) == ("2 3 4", f"{two} {three} {four}")
    assert out["number"] == "4" and out["merge"] == four and out["pin"] == PIN_A
    assert out["authors"] == " ".join(["open-proof-network[bot]"] * 3)
    assert out["render_pin"] == PIN_A and out["targets"] == "t1"


def test_a_merge_with_no_later_merge_is_recorded_as_before(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A later *bot* commit is not a later merge: its run records nothing, so this one must."""
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    graph.write("README.md", "owner push\n")
    graph.commit("an owner's direct push")
    code, out, said, _calls = run_find_step(gate_doc, graph, tmp_path, two, {two: 2})
    assert code == 0, said
    assert out["run"] == "true" and out.get("batch", "false") == "false", (out, said)
    assert (out["number"], out["target"], out["merge"]) == ("2", "t1", two)


# --- static: the rest of the job ------------------------------------------------------------------


def test_a_run_checks_main_for_a_later_merge_before_it_plans(gate_doc: dict[Any, Any]) -> None:
    run = step_run(gate_doc, id_="pr")
    assert "git fetch --quiet origin main" in run
    assert run.index('later-merge "$merge" origin/main') < run.index('plan "$merge" "$number"')
    assert 'git merge-base --is-ancestor "$merge" origin/main' in run


def test_a_batch_is_classified_merge_by_merge_with_the_pinned_gate(
    gate_doc: dict[Any, Any],
) -> None:
    run = step_run(gate_doc, id_="classify")
    assert "--project network " in run and "network-render" not in run
    assert '--base "${m}^" --head "$m"' in run  # the first parent: what the merge added
    assert '--base "${MERGE}^" --head "$MERGE"' in run  # a single merge, exactly as before
    assert "needs_gate" in run and "needs_review" in run and "replay" in run


def test_the_ledger_credits_each_merge_in_order_and_the_products_render_once(
    gate_doc: dict[Any, Any],
) -> None:
    ledger = step_run(gate_doc, name="Write what the merge earned")
    assert re.search(r"for merge in \$MERGES; do\s+uv run", ledger), ledger
    assert '--commit "$merge"' in ledger
    products = step_run(gate_doc, name="Regenerate the merge products")
    assert products.count("cli products") == 1 and "for " not in products


def test_one_commit_credits_the_batch_and_a_moved_main_is_caught_up(
    gate_doc: dict[Any, Any],
) -> None:
    """Restated by F07-T55: a moved main was left to the later run (T45) or replayed (T33); the
    run now catches up itself (``publish``, tested in ``test_finding_postmerge_catch_up.py``),
    and what main already credits is still never credited twice."""
    run = step_run(gate_doc, name="Commit the attestation")
    assert 'git commit -m "gate: ${credits} ' in run
    assert 'python3 "$helper" publish' in run
    assert 'replay_owed FETCH_HEAD "$REPLAY"' in run
    assert "replay_pr=" in run


def test_every_secret_is_still_named_by_one_step_only(gate_doc: dict[Any, Any]) -> None:
    """C8: the batch added no secret, and each one stays in the step that needs it."""
    named: dict[str, list[str]] = {}
    for job in gate_doc["jobs"].values():
        for step in job["steps"]:
            for secret in re.findall(r"secrets\.([A-Z_]+)", str(step)):
                named.setdefault(secret, []).append(str(step.get("name")))
    assert set(named) == {"OPN_GATE_SIGNING_KEY", "OPN_GRAPH_DEPLOY_KEY", "OPN_SITE_DEPLOY_TOKEN"}
    assert all(len(steps_) == 1 for steps_ in named.values()), named
    assert named["OPN_GRAPH_DEPLOY_KEY"][0].startswith("Commit the attestation")


# --- the commit step, rehearsed against a local bare repository -------------------------------


#: The stewards call (a pin without it says nothing); since F07-T55 a catch-up also runs the
#: ledger and the products, which here only stamp the tree they were rendered from.
FAKE_UV = """#!/usr/bin/env bash
case " $* " in
  *" ledger "*) exit 0 ;;
  *" products "*)
    commit="$(git rev-parse "$(printf '%s\\n' "$@" | sed -n '/^--commit$/{n;p;}')")"
    printf '{"rendered_from": "%s"}\\n' "$commit" > frontier.json; exit 0 ;;
esac
exit 2
"""


def rehearse_commit(
    gate_doc: dict[Any, Any],
    graph: Graph,
    tmp_path: Path,
    at: str,
    numbers: str,
    *,
    replay: str = "",
    event: str = "push",
) -> tuple[int, str, list[str], Path]:
    """The commit step as it stands, from a checkout of ``at`` with its products re-rendered,
    pushing to a bare copy of ``graph`` whose ``main`` is wherever the graph's is now."""
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(graph.root), str(bare)], check=True, env=git_env()
    )
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True, env=git_env())
    subprocess.run(["git", "-C", str(work), "checkout", "-q", at], check=True, env=git_env())
    (work / "frontier.json").write_text(json.dumps({"rendered": numbers}), encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, text in (("gh", FAKE_GH), ("uv", FAKE_UV)):
        tool = bin_dir / name
        tool.write_text(text, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    runner_temp = tmp_path / "temp"
    runner_temp.mkdir()
    (runner_temp / "postmerge_batch.py").write_text(helper_source(gate_doc), encoding="utf-8")
    gh_log = runner_temp / "gh.log"
    env = git_env()
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", GH_LOG=str(gh_log), GH_PRS="{}",
        GH_TOKEN=FAKE, GITHUB_EVENT_NAME=event, GITHUB_REPOSITORY=REPO,
        RUNNER_TEMP=str(runner_temp), OPN_GRAPH_DEPLOY_KEY="not a key", NUMBERS=numbers,
        REPLAY=replay, TARGETS="t1", VERDICT="pass", RENDER_PIN=PIN_A, PUBLISH_WAIT_S="0",
        MERGES=" ".join(merge_of_number(graph, int(n)) for n in numbers.split()),
    )  # fmt: skip
    (step,) = [
        s for s in steps(gate_doc) if str(s.get("name", "")).startswith("Commit the attestation")
    ]
    env.update(
        {k: str(v) for k, v in (step.get("env") or {}).items() if "${{" not in str(v)}
    )  # the step's own literal environment, as Actions sets it
    run = str(step["run"]).replace("${{ steps.products.outputs.verdict }}", "pass")
    run = run.replace("git@github.com:${GITHUB_REPOSITORY}.git", str(bare))
    assert "${{" not in run, "an expression this rehearsal does not supply"
    proc = subprocess.run(
        ["bash", "-c", run], capture_output=True, text=True, check=False, cwd=work, env=env
    )  # fmt: skip
    calls = gh_log.read_text().splitlines() if gh_log.exists() else []
    return proc.returncode, proc.stdout + proc.stderr, calls, bare


def merge_of_number(graph: Graph, number: int) -> str:
    """The merge commit of pull request ``number`` on the graph's first-parent line."""
    for sha, _parents, subject in log(graph):
        if subject.startswith(f"Merge pull request #{number} "):
            return sha
    raise AssertionError(f"no merge of #{number}")


def main_subject(bare: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(bare), "log", "-1", "--format=%s", "main"],
        capture_output=True, text=True, check=True, env=git_env(),
    )  # fmt: skip
    return proc.stdout.strip()


def test_the_head_run_commits_one_gate_commit_for_the_batch(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.append(2)
    three = graph.append(3)
    code, said, calls, bare = rehearse_commit(gate_doc, graph, tmp_path, three, "2 3", replay="")
    assert code == 0, said
    assert main_subject(bare) == "gate: #2 #3 pass" and calls == []


def test_a_run_whose_main_moved_by_a_later_merge_catches_up_and_records_its_own(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Restated by F07-T55. T45 left this run's merges to the later merge's run, which recorded
    them only if its own plan had not already run; now the run catches up and records #2 itself,
    and whichever run pushes second drops what the first credited. A replay does the same."""
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    graph.append(3)
    code, said, calls, bare = rehearse_commit(gate_doc, graph, tmp_path / "push", two, "2")
    assert code == 0 and calls == [], (said, calls)
    assert "caught up on" in said and main_subject(bare) == "gate: #2 pass", said
    code, said, calls, bare = rehearse_commit(
        gate_doc, graph, tmp_path / "replay", two, "2", event="workflow_dispatch"
    )
    assert code == 0 and calls == [], (said, calls)
    assert main_subject(bare) == "gate: #2 pass (replayed)", said


def test_a_run_whose_main_moved_by_an_owner_push_catches_up(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Restated by F07-T55: an owner's push that touches a target used to replay the run's own
    merges; the record is laid on main as it is instead, and only the merges this run was
    handed to replay are replayed."""
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    graph.write("targets/t1/nodes/n/META.yaml", "status: owner\n")
    graph.commit("an owner's push that touches a target")
    code, said, calls, bare = rehearse_commit(gate_doc, graph, tmp_path, two, "2", replay="5")
    assert code == 0, said
    assert main_subject(bare) == "gate: #2 pass", said
    assert [c.split("replay_pr=")[1] for c in calls if "replay_pr=" in c] == ["5"], calls


def test_a_run_whose_merges_are_already_credited_dispatches_only_what_is_owed(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    two = graph.append(2)
    graph.append(3)
    graph.bot(2, 3)
    code, said, calls, _ = rehearse_commit(gate_doc, graph, tmp_path, two, "2", replay="3 5")
    assert code == 0, said
    assert [c.split("replay_pr=")[1] for c in calls if "replay_pr=" in c] == ["5"], calls
