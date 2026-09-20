"""F07-T25 (D-4, F07-Q16, C8): the graph's merge actor, read statically and run as it stands.

D-4 has said since v3.11 that "the merge happens with no person pressing a button"; nothing did
it, and in the 2026-09-19 primes run four outside agents each lost half a session behind a
gate-green proposal nobody merged. ``.github/workflows/merge.yml`` on the graph is that actor.

Two kinds of test, both without running the workflow. The static ones pin what makes it safe to
hold a write token: it is woken by the gate's completion in the base repository's context, never
by a pull request; it checks nothing out; its job's own token can only read; and exactly one step
names the secret. The others take the decision program out of the YAML and run it over fake host
data, so the file that ships is the file that is tested.

Read from the sibling graph's ``origin/main``, or from the local branch the task was built on
until that is pushed; skipped where neither carries the file.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import config

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
PATH = ".github/workflows/merge.yml"
REFS = ("origin/main", "f07-t25-merge-actor")
SECRET = "OPN_GRAPH_MERGE_TOKEN"  # noqa: S105 — the secret's name, not a secret
GATE_JOB = "gate (steps 1, 2 and 4-8 in the sandbox)"
STEP9_JOB = "step 9 (a non-author approving review)"
REPO = "owner/graph"


def _text() -> str:
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)  # the hook exports GIT_DIR
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_REPO), "show", f"{ref}:{PATH}"],
            capture_output=True, text=True, check=False, env=env,
        )  # fmt: skip
        if proc.returncode == 0:
            return proc.stdout
    pytest.skip(f"no {PATH} on {' or '.join(REFS)} of the graph")


@pytest.fixture(scope="module")
def text() -> str:
    return _text()


@pytest.fixture(scope="module")
def doc(text: str) -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(text)
    return loaded


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    """The decision program, exactly as the workflow writes it to ``pick.py``."""
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    script = step["run"]
    body = script.split("cat > pick.py <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    namespace: dict[str, Any] = {"__name__": "pick"}
    exec(compile(textwrap.dedent(body), "pick.py", "exec"), namespace)  # noqa: S102
    return namespace


# --- static: what makes it safe to hold a write token -------------------------------------------


def test_it_is_woken_in_the_base_context_and_never_by_a_pull_request(doc: dict[Any, Any]) -> None:
    triggers = doc[True]  # YAML reads the key `on` as a boolean
    assert set(triggers) == {"workflow_run", "schedule", "workflow_dispatch"}
    assert triggers["workflow_run"] == {"workflows": ["gate"], "types": ["completed"]}
    assert "pull_request" not in str(triggers)


def test_it_checks_nothing_out_and_runs_no_gate_code(text: str, doc: dict[Any, Any]) -> None:
    steps = doc["jobs"]["merge"]["steps"]
    assert all("uses" not in step for step in steps), "no action, so no checkout"
    live = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("actions/checkout", "git clone", "git fetch", "opn_gate", "uv run"):
        assert forbidden not in live, forbidden


def test_the_jobs_own_token_can_only_read(doc: dict[Any, Any]) -> None:
    assert doc["permissions"] == {}
    granted = doc["jobs"]["merge"]["permissions"]
    assert granted and all(level == "read" for level in granted.values()), granted


def test_exactly_one_step_names_the_secret_and_it_dry_runs_without_it(doc: dict[Any, Any]) -> None:
    steps = doc["jobs"]["merge"]["steps"]
    naming = [s for s in steps if SECRET in str(s)]
    assert len(naming) == 1 and naming[0]["name"].startswith("Act")
    act = naming[0]["run"]
    assert 'if [ -z "${GH_TOKEN:-}" ]' in act and "dry run" in act and "exit 0" in act
    # the merge names the commit it saw, so a push in between refuses rather than lands unchecked
    assert '-f sha="$SHA"' in act and 'expected_head_sha="$SHA"' in act
    assert doc["concurrency"] == {"group": "merge", "cancel-in-progress": False}


# --- the decision program, as shipped -----------------------------------------------------------


def pull(number: int, ref: str, *, draft: bool = False, fork: bool = False) -> dict[str, Any]:
    return {
        "number": number,
        "draft": draft,
        "head": {
            "ref": ref,
            "sha": f"{number:040d}",
            "repo": {"full_name": "x/fork" if fork else REPO},
        },
        "base": {"ref": "main", "repo": {"full_name": REPO}},
    }


def check(name: str, conclusion: str | None, *, id_: int = 1) -> dict[str, Any]:
    status = "completed" if conclusion else "in_progress"
    return {"id": id_, "name": name, "status": status, "conclusion": conclusion}


GREEN = [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]
REQUIRED = [GATE_JOB, STEP9_JOB]
RULES = [
    {"type": "deletion"},
    {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [{"context": GATE_JOB}, {"context": STEP9_JOB}],
        },
    },
]


def test_only_branches_the_service_opened_are_candidates(pick: dict[str, Any]) -> None:
    pulls = [
        pull(9, "submit/x"),
        pull(3, "propose/x"),
        pull(4, "repin-c7faed3"),  # a curator's own branch: a person presses that button
        pull(5, "append/x", draft=True),
        pull(6, "submit/x", fork=True),
    ]
    assert [n for n, _ in pick["candidates"](pulls)] == [3, 9]  # oldest first


@pytest.mark.parametrize(
    ("runs", "expected"),
    [
        (GREEN, "green"),
        ([check(GATE_JOB, "success"), check(STEP9_JOB, "success", id_=2)], "green"),
        ([check(GATE_JOB, "success"), check(STEP9_JOB, "failure", id_=2)], "red"),  # awaits review
        ([check(GATE_JOB, "failure"), check(STEP9_JOB, "skipped", id_=2)], "red"),
        ([check(GATE_JOB, "skipped"), check(STEP9_JOB, "skipped", id_=2)], "red"),  # never ran
        ([check(GATE_JOB, None), check(STEP9_JOB, "skipped", id_=2)], "pending"),
        ([check(GATE_JOB, "success")], "pending"),  # step 9 has not reported
        ([], "pending"),
        # a review re-runs step 9 in place: the later attempt is the one that counts
        (
            [
                check(GATE_JOB, "success"),
                check(STEP9_JOB, "failure", id_=2),
                check(STEP9_JOB, "success", id_=3),
            ],
            "green",
        ),
    ],
)
def test_green_is_both_required_checks_finished_and_passed(
    pick: dict[str, Any], runs: list[dict[str, Any]], expected: str
) -> None:
    assert pick["verdict"](runs, REQUIRED) == expected


def test_the_required_checks_come_from_the_ruleset_by_exact_name(pick: dict[str, Any]) -> None:
    """The file names no check of its own, so it cannot drift from what GitHub enforces. A job
    renamed in gate.yml without the ruleset following reads as pending here — nothing merges —
    which is the loud version of the silent failure of 2026-09-10."""
    assert pick["required_checks"](RULES) == (sorted(REQUIRED), True)
    assert pick["required_checks"]([{"type": "deletion"}]) == ([], False)
    renamed = [check("gate (steps 1 to 8)", "success"), check(STEP9_JOB, "skipped", id_=2)]
    assert pick["verdict"](renamed, REQUIRED) == "pending"


def test_a_ruleset_that_requires_no_gate_merges_nothing(pick: dict[str, Any]) -> None:
    """C7: with the rule deleted or emptied, "every required check passed" is vacuously true."""
    assert pick["verdict"](GREEN, []) == "red"
    assert pick["verdict"](GREEN, [STEP9_JOB]) == "red"
    pulls = [pull(5, "propose/x")]
    assert pick["decide"](pulls, [{"type": "deletion"}], lambda _s: GREEN, lambda _s: 0) == (
        "",
        "",
        "",
    )


def test_it_takes_the_oldest_green_one_and_updates_before_it_merges(pick: dict[str, Any]) -> None:
    pulls = [pull(7, "submit/x"), pull(5, "propose/x"), pull(6, "append/x")]
    red = [check(GATE_JOB, "failure"), check(STEP9_JOB, "skipped", id_=2)]
    checks = {f"{5:040d}": red, f"{6:040d}": GREEN, f"{7:040d}": GREEN}
    decide = pick["decide"]
    assert decide(pulls, RULES, checks.__getitem__, lambda _sha: 2) == (6, f"{6:040d}", "update")
    assert decide(pulls, RULES, checks.__getitem__, lambda _sha: 0) == (6, f"{6:040d}", "merge")
    assert decide(pulls, RULES, lambda _sha: red, lambda _sha: 0) == ("", "", "")
    assert decide([], RULES, checks.__getitem__, lambda _sha: 0) == ("", "", "")


def test_a_green_pull_request_that_conflicts_with_main_is_passed_over(pick: dict[str, Any]) -> None:
    """Without this the oldest green pull request with a conflict fails the acting step on every
    run and holds everything behind it; the next one is taken and the conflicted one waits for a
    person, which it needed anyway."""
    pulls = [pull(5, "propose/x"), pull(6, "append/x")]
    decide = pick["decide"]
    took = decide(pulls, RULES, lambda _s: GREEN, lambda _s: 0, lambda number: number == 5)
    assert took == (6, f"{6:040d}", "merge")
    none = decide(pulls, RULES, lambda _s: GREEN, lambda _s: 0, lambda _number: True)
    assert none == ("", "", "")
