"""Finding 11 (2026-09-13, the live MCP contribution): every committed product says zero claims.

``OPN_API_CLAIMS_URL`` was never set on the graph repository (``gh variable list``), so
F05-R10's overlay has never run and ``frontier.json``, every ``CONTEXT.json`` and the site's
claims column carry ``claims.history_count: 0`` while the service says 6. The rehearsal
(``gate/tools/rehearsal.py``, F11-R11) is the tool that says READY, and it never asked the
repository whether the variables its workflows read exist — the log's lesson of 2026-09-12: a
rehearsal that reports READY with a step not attempted is lying by omission.

The behaviour F11-T12 lands, asserted here on pure functions (no network, no ``gh``):

- ``rehearsal.variable_names(text)`` reads the set of ``vars.<NAME>`` references out of a
  workflow's text — both ``${{ vars.X }}`` and the bare ``vars.X != ''`` form an ``if:`` uses —
  so a new variable cannot be forgotten by a hand-kept list, and ``secrets.`` is not a variable.
- ``rehearsal.repository_variables(names, listing)`` is the check: ``names`` the referenced set,
  ``listing`` the names the repository defines (what ``gh variable list`` answers) or ``None``
  when ``gh`` was unavailable. It answers ``(status, detail)`` the way ``check_site`` does:
  ``"skipped"`` (the record's not-attempted state, which ``Record.exit_code`` already counts as
  PENDING) naming ``gh`` when the listing could not be read; ``"failed"`` naming every missing
  variable; ``"ok"`` when every referenced name is defined.

The first four tests were held as strict xfails from f80151b until F11-T12 landed them
(conventions §2); both names are still looked up with ``getattr`` so a missing one is a failed
test, never a collection error. The fifth is a guard on the record model: a skipped step is never
READY. The tests after it are F11-T12's edge cases — the spellings a workflow uses, a malformed
``gh`` answer, and the step as the rehearsal records it, with ``gh`` faked.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: The shapes the graph's gate.yml uses on 2026-09-13, cut down to the lines that reference a
#: repository variable (``OPN_CACHE_UPLOAD_ROLE_ARN`` appears bare in an ``if:`` and inside
#: ``${{ }}``; the signing key is a secret, not a variable).
GATE_YML = """\
jobs:
  postmerge:
    steps:
      - name: Regenerate the merge products from the committed facts (F03; no secret)
        env:
          OPN_API_CLAIMS_URL: ${{ vars.OPN_API_CLAIMS_URL }}
        run: |
          uv run python -m opn_gate.cli products --graph . \\
            ${OPN_API_CLAIMS_URL:+--claims-url "$OPN_API_CLAIMS_URL"}
      - name: Assume the cache upload role (OIDC, no stored key)
        if: steps.products.outputs.verdict == 'pass' && vars.OPN_CACHE_UPLOAD_ROLE_ARN != ''
        with:
          role-to-assume: ${{ vars.OPN_CACHE_UPLOAD_ROLE_ARN }}
          aws-region: ${{vars.OPN_AWS_REGION}}
      - name: Publish the olean cache for this commit
        run: |
          uv run python -m opn_gate.cli cache publish \\
            --bucket "${{ vars.OPN_CACHE_BUCKET }}" --prefix "${{ vars.OPN_CACHE_PREFIX }}"
      - name: Sign with the gate key (the only step that sees it)
        env:
          OPN_GATE_SIGNING_KEY: ${{ secrets.OPN_GATE_SIGNING_KEY }}
"""
NAMES = frozenset(
    {
        "OPN_API_CLAIMS_URL",
        "OPN_CACHE_UPLOAD_ROLE_ARN",
        "OPN_AWS_REGION",
        "OPN_CACHE_BUCKET",
        "OPN_CACHE_PREFIX",
    }
)


def _load() -> Any:
    path = ROOT / "gate" / "tools" / "rehearsal.py"
    spec = importlib.util.spec_from_file_location("rehearsal", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rehearsal = _load()


def _check() -> Any:
    check = getattr(rehearsal, "repository_variables", None)
    assert check is not None, "rehearsal.py has no repository_variables(names, listing) check"
    return check


def test_variable_names_are_read_from_the_workflow_text() -> None:
    """Both spellings a workflow uses count; a secret is not a variable; a text with no
    reference answers the empty set."""
    variable_names = getattr(rehearsal, "variable_names", None)
    assert variable_names is not None, "rehearsal.py has no variable_names(text) reader"
    assert variable_names(GATE_YML) == NAMES
    assert variable_names("run: echo ${{ secrets.OPN_GATE_SIGNING_KEY }}\n") == frozenset()


def test_the_check_is_not_attempted_without_gh_and_says_so() -> None:
    """No listing (``gh`` unavailable) is the record's not-attempted state — ``skipped``, the
    status ``Record.exit_code`` turns into PENDING — and the detail names ``gh``."""
    status, detail = _check()(NAMES, None)
    assert status == "skipped", (status, detail)
    assert "gh" in detail, detail


def test_every_missing_variable_fails_the_step_by_name() -> None:
    """The live state: the cache variables are set and ``OPN_API_CLAIMS_URL`` is not. The
    step fails and names each missing variable, and none of the defined ones."""
    check = _check()
    status, detail = check(NAMES, NAMES - {"OPN_API_CLAIMS_URL"})
    assert status == "failed", (status, detail)
    assert "OPN_API_CLAIMS_URL" in detail, detail
    assert not any(name in detail for name in NAMES - {"OPN_API_CLAIMS_URL"}), detail

    status, detail = check(NAMES, NAMES - {"OPN_API_CLAIMS_URL", "OPN_CACHE_PREFIX"})
    assert status == "failed", (status, detail)
    assert "OPN_API_CLAIMS_URL" in detail and "OPN_CACHE_PREFIX" in detail, detail


def test_the_check_passes_when_every_referenced_variable_is_defined() -> None:
    """Every referenced name defined is ``ok``; variables the workflow does not read are not
    the check's business."""
    check = _check()
    status, _detail = check(NAMES, NAMES)
    assert status == "ok"
    status, _detail = check(NAMES, NAMES | {"OPN_SITE_HOSTNAME"})
    assert status == "ok"


def test_a_step_not_attempted_counts_against_the_verdict() -> None:
    """Guard on the record as it stands (the log, 2026-09-12): a skipped step is PENDING, a
    failed one NOT READY, and neither renders as READY — the new step rides on this."""
    record = rehearsal.Record("https://api.example.test")
    record.add("repository-variables", "skipped", time.monotonic(), "gh is not on PATH")
    assert record.exit_code == rehearsal.EXIT_PENDING
    assert "verdict: PENDING" in record.render()
    record.add("repository-variables", "failed", time.monotonic(), "missing: OPN_API_CLAIMS_URL")
    assert record.exit_code == rehearsal.EXIT_FAIL
    assert "verdict: NOT READY" in record.render()


# --- F11-T12 edge cases ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "x: ${{ vars.OPN_X }}\n",
        "x: ${{vars.OPN_X}}\n",
        "x: ${{   vars.OPN_X   }}\n",
        'x: "${{ vars.OPN_X }}"-suffix\n',
    ],
)
def test_an_expression_reads_with_or_without_spaces(text: str) -> None:
    assert rehearsal.variable_names(text) == frozenset({"OPN_X"})


def test_format_and_if_expressions_are_read() -> None:
    text = (
        "      - if: ${{ github.event_name == 'push' && vars.OPN_GUARD != '' }}\n"
        "        if: vars.OPN_BARE == 'true' || (vars.OPN_PAREN)\n"
        "        with:\n"
        "          url: ${{ format('https://{0}/claims.json', vars.OPN_HOST) }}\n"
        "          other: ${{ format('{0}{1}', vars.OPN_A,vars.OPN_B) }}\n"
    )
    assert rehearsal.variable_names(text) == frozenset(
        {"OPN_GUARD", "OPN_BARE", "OPN_PAREN", "OPN_HOST", "OPN_A", "OPN_B"}
    )


def test_lookalikes_are_not_variables() -> None:
    """A secret, an env value, a step whose id ends in ``vars`` and an output named ``vars``
    are not repository variables."""
    text = (
        "a: ${{ secrets.OPN_KEY }}\n"
        "b: ${{ env.OPN_ENV }}\n"
        "c: ${{ steps.vars.outputs.OPN_OUT }}\n"
        "d: ${{ steps.myvars.outputs.x }}\n"
        "e: ${{ needs.build-vars.outputs.y }}\n"
        "f: $vars.NOT_AN_EXPRESSION_BUT_STILL_READ\n"
    )
    assert rehearsal.variable_names(text) == frozenset({"NOT_AN_EXPRESSION_BUT_STILL_READ"})


def test_a_name_referenced_twice_is_one_name_and_named_once() -> None:
    text = "a: ${{ vars.OPN_API_CLAIMS_URL }}\nif: vars.OPN_API_CLAIMS_URL != ''\n"
    names = rehearsal.variable_names(text)
    assert names == frozenset({"OPN_API_CLAIMS_URL"})
    status, detail = _check()(names, frozenset())
    assert status == "failed"
    assert detail.count("OPN_API_CLAIMS_URL") == 1, detail


def test_a_workflow_with_no_variables() -> None:
    text = "on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: [{run: echo hi}]\n"
    assert rehearsal.variable_names(text) == frozenset()
    assert _check()(frozenset(), frozenset())[0] == "ok"
    assert _check()(frozenset(), None)[0] == "skipped"  # not looking is never a pass


def test_names_compare_case_insensitively_as_github_resolves_them() -> None:
    assert _check()(frozenset({"opn_api_claims_url"}), frozenset({"OPN_API_CLAIMS_URL"}))[0] == "ok"


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "not json",
        '{"name": "OPN_X"}',
        '[{"value": "x"}]',
        '["OPN_X"]',
        '[{"name": 3}]',
        '[{"name": "OPN_X"}, null]',
    ],
)
def test_a_malformed_gh_answer_is_no_listing(stdout: str) -> None:
    assert rehearsal.parse_variable_listing(stdout) is None


def test_gh_answers_are_parsed() -> None:
    assert rehearsal.parse_variable_listing("[]") == frozenset()
    assert rehearsal.parse_variable_listing(
        '[{"name":"OPN_A"},{"name":"OPN_B","updatedAt":"2026-09-14T00:00:00Z"}]'
    ) == frozenset({"OPN_A", "OPN_B"})


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _fake_gh(monkeypatch: pytest.MonkeyPatch, proc: _Proc | None) -> list[list[str]]:
    """``gh`` on PATH answering ``proc`` (or absent when ``None``); records each argv."""
    calls: list[list[str]] = []
    monkeypatch.setattr(
        rehearsal.shutil, "which", lambda name: None if proc is None else f"/fake/{name}"
    )

    def run(argv: list[str], **_kw: Any) -> _Proc:
        calls.append(argv)
        assert proc is not None
        return proc

    monkeypatch.setattr(rehearsal.subprocess, "run", run)
    return calls


def _graph(tmp_path: Path, **workflows: str) -> Path:
    directory = tmp_path / "graph" / ".github" / "workflows"
    directory.mkdir(parents=True)
    for name, text in workflows.items():
        (directory / name.replace("_", ".")).write_text(text, encoding="utf-8")
    return tmp_path / "graph"


def _step(record: Any) -> Any:
    [step] = [s for s in record.steps if s.name == "repository-variables"]
    return step


def test_the_step_reads_every_workflow_and_asks_gh_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = _graph(tmp_path, gate_yml=GATE_YML, refresh_yaml="x: ${{ vars.OPN_REFRESH }}\n")
    listing = ",".join(f'{{"name":"{n}"}}' for n in sorted(NAMES))
    calls = _fake_gh(monkeypatch, _Proc(0, f"[{listing}]"))
    record = rehearsal.Record("https://api.example.test")
    rehearsal.variables_step(record, graph, "owner/graph")
    step = _step(record)
    assert step.status == "failed", step
    assert "OPN_REFRESH" in step.detail and "OPN_API_CLAIMS_URL" not in step.detail
    assert calls == [["gh", "variable", "list", "--repo", "owner/graph", "--json", "name"]]
    assert record.exit_code == rehearsal.EXIT_FAIL


def test_the_step_passes_when_the_repository_defines_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = _graph(tmp_path, gate_yml=GATE_YML)
    listing = ",".join(f'{{"name":"{n}"}}' for n in sorted(NAMES))
    _fake_gh(monkeypatch, _Proc(0, f"[{listing}]"))
    record = rehearsal.Record("https://api.example.test")
    rehearsal.variables_step(record, graph, "owner/graph")
    assert _step(record).status == "ok"
    assert record.exit_code == rehearsal.EXIT_OK


@pytest.mark.parametrize(
    ("proc", "said"),
    [
        (None, "gh is not on PATH"),
        (_Proc(4, stderr="HTTP 403: Resource not accessible"), "exited 4: HTTP 403"),
        (_Proc(0, stdout="<html>rate limited</html>"), "answered no list of names"),
    ],
)
def test_the_step_is_not_attempted_when_gh_cannot_say(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, proc: _Proc | None, said: str
) -> None:
    graph = _graph(tmp_path, gate_yml=GATE_YML)
    _fake_gh(monkeypatch, proc)
    record = rehearsal.Record("https://api.example.test")
    rehearsal.variables_step(record, graph, "owner/graph")
    step = _step(record)
    assert step.status == "skipped", step
    assert said in step.detail and "gh" in step.detail, step.detail
    assert record.exit_code == rehearsal.EXIT_PENDING
    assert "verdict: PENDING" in record.render()


def test_the_step_without_its_inputs_or_workflows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake_gh(monkeypatch, _Proc(0, "[]"))
    record = rehearsal.Record("https://api.example.test")
    rehearsal.variables_step(record, None, None)
    assert _step(record).status == "skipped" and "--graph" in _step(record).detail
    empty = tmp_path / "not-a-graph"
    empty.mkdir()
    record = rehearsal.Record("https://api.example.test")
    rehearsal.variables_step(record, empty, "owner/graph")
    assert _step(record).status == "failed" and "no .github/workflows" in _step(record).detail
    assert calls == []  # gh is never asked when there is nothing to ask about
