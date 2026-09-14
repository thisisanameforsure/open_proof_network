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

Strict xfails until the task lands (conventions §2); both names are looked up with ``getattr``
so a missing one is a failed test, never a collection error. The last test is a guard on the
record model as it stands: a skipped step is never READY.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
FINDING = "finding 11 (F05-R10, F11-R11, C8): "
FIX = "; fix: F11-T12 (Mike, 2026-09-13)"

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


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "rehearsal.py keeps no list of the repository variables the workflows read and has no "
    + "variable_names(text) reader, so a variable the graph's gate.yml references can be "
    + "unset for months without any tool noticing"
    + FIX,
)
def test_variable_names_are_read_from_the_workflow_text() -> None:
    """Both spellings a workflow uses count; a secret is not a variable; a text with no
    reference answers the empty set."""
    variable_names = getattr(rehearsal, "variable_names", None)
    assert variable_names is not None, "rehearsal.py has no variable_names(text) reader"
    assert variable_names(GATE_YML) == NAMES
    assert variable_names("run: echo ${{ secrets.OPN_GATE_SIGNING_KEY }}\n") == frozenset()


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "rehearsal.py has no repository_variables check, so the readiness record has no step "
    + "for the repository's variables and a run without gh cannot say it did not look"
    + FIX,
)
def test_the_check_is_not_attempted_without_gh_and_says_so() -> None:
    """No listing (``gh`` unavailable) is the record's not-attempted state — ``skipped``, the
    status ``Record.exit_code`` turns into PENDING — and the detail names ``gh``."""
    status, detail = _check()(NAMES, None)
    assert status == "skipped", (status, detail)
    assert "gh" in detail, detail


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "rehearsal.py has no repository_variables check, so OPN_API_CLAIMS_URL unset on the "
    + "graph repository (the live state on 2026-09-13) is reported by nothing"
    + FIX,
)
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


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "rehearsal.py has no repository_variables check to pass when every referenced variable "
    + "is defined"
    + FIX,
)
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
