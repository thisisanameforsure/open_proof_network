"""F13-T26 (testers 2026-10-01, A1): hazards mode of the fast check was dead for every statement.

``POST /check {"target_id": "erdos-69", "mode": "hazards", "node_id": "spec-2e765953"}`` answered
``okay: false, hazards: null`` with two Lean errors, both in the program the service appends:
``Unknown identifier `Lean.Elab.IO.processCommands` `` and the field access that followed it. So
every proposal's ``hazards_preflight`` read ``inconclusive``, its pull request opened anyway, and
the gate was the first hazard check (graph #337, refused three minutes later).

Root cause, measured on the hosted checker rather than reasoned about: AXLE replaces whatever
header a text carries with its own (``Imports mismatch detected. Overriding with default
header``), which is ``import Mathlib`` and nothing else. The ``import Lean`` line the composer
writes is never honoured, and ``import Mathlib`` at the pin reaches 693 of ``Lean``'s modules,
not all of them: ``Lean.Elab.Frontend``, which declares ``Lean.Elab.IO.processCommands``, is not
one (``gate/hosted-checker-modules/lean-4.33.1.txt``, the list as the checker printed it). The
lean tier compiled the same text under ``import Lean`` and was green.

Three guards, one per tier. Here, the fast tier: the composed program names nothing declared in
a module the hosted environment lacks, and a runner that fails says so as its own fault. The lean
tier compiles the composed text under exactly the hosted module list
(``gate/tests/test_hazards_through_axle_text_lean.py``). The deploy calls the deployed route
(``api/tools/smoke.py``).
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import AXLE_OKAY
from mcp_client import TARGET
from test_finding_hazards_preflight import (
    CHECKERS,
    DIV,
    STATEMENT,
    found,
    harness,
    speculative,
    variant,
)

from opn_api import checks
from opn_gate import hosted, schemas

MODULES_DIR = schemas.SCHEMAS_DIR.parent / "hosted-checker-modules"

#: Names a network-composed program might reach for, each with the module that declares it. The
#: module is absent from the hosted environment (asserted below, so this table cannot go stale
#: silently); the name must not appear in what the service sends.
DECLARED_OUTSIDE_THE_HOSTED_ENVIRONMENT = {
    "Lean.Elab.IO.processCommands": "Lean.Elab.Frontend",
    "Lean.Elab.Frontend.": "Lean.Elab.Frontend",
    "Lean.Elab.runFrontend": "Lean.Elab.Frontend",
    "Lean.Language.Lean.process": "Lean.Language.Lean",
}

#: What AXLE answered on 2026-10-01 (log 01M3WG8X7G4NC1AB75SWJES52Y), cut to what is read: the
#: statement compiles (a sorry warning on its own line), the program after it does not, and no
#: tagged line was printed.
RUNNER_FAILED: dict[str, Any] = {
    **AXLE_OKAY,
    "okay": False,
    "failed_declarations": ["Opn.erdos_1050_rem"],
    "lean_messages": {
        "errors": [
            "-:513:15-513:43: error(lean.unknownIdentifier): Unknown identifier "
            "`Lean.Elab.IO.processCommands`\n",
            "-:515:11-515:35: error(lean.invalidField): Invalid field notation: Type of\n  st\n"
            "is not known; cannot resolve field `commandState`\n",
        ],
        "infos": [],
        "warnings": ["-:3:8-3:26: warning: declaration uses `sorry`\n"],
    },
}

#: A statement that does not compile: the error is on one of the statement's own lines.
STATEMENT_FAILED: dict[str, Any] = {
    **AXLE_OKAY,
    "okay": False,
    "lean_messages": {
        "errors": ["-:4:4-4:9: error: Unknown identifier `Summble`\n"],
        "infos": [],
        "warnings": [],
    },
}


def hosted_modules(environment: str) -> set[str]:
    path = MODULES_DIR / f"{environment}.txt"
    return {
        line.strip()
        for line in path.read_text("utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


# --- the budget -----------------------------------------------------------------------------------


def test_every_hosted_environment_has_its_module_list() -> None:
    """One measured list per environment ``gate/hosted-checkers.yaml`` names, so a new
    environment cannot be mapped without asking it what it holds."""
    known = hosted.load()
    environments = {e.environment for e in known.pins.values() if e.environment}
    if known.core is not None and known.core.environment:
        environments.add(known.core.environment)
    assert environments, "the mapping names no environment"
    for environment in sorted(environments):
        modules = hosted_modules(environment)
        # The floor the composed programs stand on, present in the measured list.
        for needed in ("Lean.Elab.Command", "Lean.Parser.Module", "Lean.Language.Basic"):
            assert needed in modules, (environment, needed)
        for name, module in DECLARED_OUTSIDE_THE_HOSTED_ENVIRONMENT.items():
            assert module not in modules, f"{module} is hosted now; drop {name} from the table"


def test_the_composed_hazards_program_names_nothing_the_hosted_environment_lacks() -> None:
    text = checks.hazards_text(STATEMENT, "Opn.erdos_1050_rem", ["auto-implicit", *CHECKERS])
    outside = {
        name: module
        for name, module in DECLARED_OUTSIDE_THE_HOSTED_ENVIRONMENT.items()
        if name in text
    }
    assert not outside, f"declared in modules `import Mathlib` does not reach: {outside}"


# --- a runner that fails is the network's fault, and says so --------------------------------------


def check_hazards(h: Any) -> dict[str, Any]:
    r = h.client.post(
        "/check", json={"target_id": TARGET, "mode": "hazards", "statement": STATEMENT}
    )
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def test_a_program_that_ran_says_so() -> None:
    doc = check_hazards(harness(found(DIV)))
    assert doc["hazards_status"] == "ran"
    assert doc["service_fault"] is False
    assert doc["hazards"]["findings"] == [DIV]


def test_a_runner_that_failed_is_unavailable_not_the_callers_false() -> None:
    """The statement compiled and the network's own program did not: no verdict on the
    statement, said as ``okay: null``, ``hazards_status: "unavailable"`` and ``service_fault``,
    with the program's errors lifted where a script finds them."""
    doc = check_hazards(harness(RUNNER_FAILED))
    assert doc["hazards"] is None
    assert doc["hazards_status"] == "unavailable"
    assert doc["service_fault"] is True
    assert doc["okay"] is None, "okay: false reads as the caller's statement failing"
    assert "processCommands" in doc["hazards_error"]
    assert doc["result"]["okay"] is False  # the checker's own word stays verbatim


def test_a_statement_that_does_not_compile_is_the_callers() -> None:
    doc = check_hazards(harness(STATEMENT_FAILED))
    assert doc["hazards"] is None
    assert doc["hazards_status"] == "statement-failed"
    assert doc["service_fault"] is False
    assert doc["okay"] is False


def test_the_runner_fault_is_logged_under_its_own_outcome() -> None:
    """An operator reading the call log finds the fault without the text (R9 keeps none)."""
    h = harness(RUNNER_FAILED)
    doc = check_hazards(h)
    assert h.store.checks[doc["log_id"]].outcome == "hazards-runner-failed"


# --- the proposal's pre-flight: refused on request, opened by default -----------------------------


@pytest.mark.parametrize("propose", [speculative, variant])
def test_an_inconclusive_hazard_pre_flight_opens_by_default(propose: Any) -> None:
    """F13-Q23 as settled: step 6 is the authority, and the default is unchanged."""
    h = harness(RUNNER_FAILED)
    r = propose(h)
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == "inconclusive"
    assert len(h.githost.pulls) == 1


@pytest.mark.parametrize("propose", [speculative, variant])
def test_a_caller_may_require_the_hazard_pre_flight(propose: Any) -> None:
    """``require_hazards_preflight: true``: no pull request unless the checkers answered."""
    h = harness(RUNNER_FAILED)
    r = propose(h, require_hazards_preflight=True)
    assert r.status_code == 503, r.text
    doc = r.json()
    assert doc["error"] == "hazards-preflight-inconclusive", r.text
    assert doc["details"]["hazards_preflight"] == "inconclusive"
    assert "Nothing was opened" in doc["message"]
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_requiring_the_pre_flight_refuses_an_unavailable_checker_too() -> None:
    from opn_api.axle import AxleError  # noqa: PLC0415

    h = harness(AxleError("AXLE check returned 502", status=502))
    r = speculative(h, require_hazards_preflight=True)
    assert r.status_code == 503, r.text
    assert r.json()["error"] == "hazards-preflight-inconclusive", r.text
    assert r.json()["details"]["hazards_preflight"] == "unavailable"
    assert h.githost.pulls == []


def test_requiring_the_pre_flight_changes_nothing_when_it_answers() -> None:
    h = harness(found())
    r = speculative(h, require_hazards_preflight=True)
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == "clear"
    h = harness(found(), checkers=[])
    assert speculative(h, require_hazards_preflight=True).status_code == 201


def test_require_hazards_preflight_is_a_boolean() -> None:
    h = harness(found())
    r = speculative(h, require_hazards_preflight="yes")
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "require-hazards-preflight-invalid", r.text
    assert h.githost.pulls == []


# --- the deploy asks the deployed route -----------------------------------------------------------


def smoke_module() -> Any:
    import importlib.util  # noqa: PLC0415

    path = schemas.SCHEMAS_DIR.parents[1] / "api" / "tools" / "smoke.py"
    spec = importlib.util.spec_from_file_location("opn_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hazards_smoke(monkeypatch: pytest.MonkeyPatch, status: int, doc: Any) -> list[str]:
    smoke = smoke_module()
    asked: list[dict[str, Any]] = []

    def fake(url: str, **kwargs: Any) -> tuple[int, Any]:
        asked.append({"url": url, **kwargs})
        return status, doc

    monkeypatch.setattr(smoke, "call", fake)
    problems: list[str] = []
    smoke.hazards_mode("https://api.example", problems)
    assert asked[0]["url"].endswith("/check") and asked[0]["body"]["mode"] == "hazards"
    return problems


def test_the_deploy_smoke_fails_on_a_hazard_program_that_does_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What the deployed route answered on 2026-10-01, and what it answers now."""
    old = {"okay": False, "hazards": None, "user_error": None}
    assert run_hazards_smoke(monkeypatch, 200, old)
    now = {"okay": None, "hazards": None, "hazards_status": "unavailable", "hazards_error": "x"}
    assert run_hazards_smoke(monkeypatch, 200, now)
    ran = {"hazards": {"checkers": [], "findings": [], "capped": False}, "hazards_status": "ran"}
    assert run_hazards_smoke(monkeypatch, 200, ran) == []
    # The checker being down is said, and is not this deploy's failure.
    assert run_hazards_smoke(monkeypatch, 502, {"error": "upstream-unavailable"}) == []


def test_the_deploy_runs_the_smoke_that_asks() -> None:
    workflow = (schemas.SCHEMAS_DIR.parents[1] / ".github/workflows/api-deploy.yml").read_text(
        "utf-8"
    )
    assert "api/tools/smoke.py" in workflow
    source = (schemas.SCHEMAS_DIR.parents[1] / "api/tools/smoke.py").read_text("utf-8")
    assert "hazards_mode(base, problems)" in source.split("def read_only")[1].split("\ndef ")[0]
