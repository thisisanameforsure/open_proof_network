"""F16-T5 / AC8, R12: the gate is blind to the harness a contributor declares (D-1).

F16 gives every connector an id and asks the agent to declare it in ``tooling.harness`` (D-23),
which makes it easy for a later change to start branching on it. D-1 forbids that: a
hand-written proof and one from any harness are indistinguishable to the gate. The test runs the
gate's own command over the same node with every connector's id declared, and with none, on a
passing and on a failing toolchain, and asserts every verdict is byte-identical and every
attestation differs only in the ``tooling`` it records. A mutant gate that branches on one
harness is caught, so the test is shown to see what it is for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fakes import FakeToolchain
from harness import TUTORIAL, copy_graph

from opn_gate import attestation, cli, clients, schemas, toolchain
from opn_gate.toolchain import AxiomResult

DECLARATIONS: list[tuple[str | None, str | None]] = [
    (None, None),
    *[("some-model", e.id) for e in clients.load().entries],
    ("some-model", "hand-written"),
    ("another-model", "claude-code"),
]
TOOLING_FIELDS = ("tooling", "model_and_tooling")


def pregate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], model: str | None, harness: str | None
) -> tuple[int, dict[str, Any], dict[str, Any]]:
    graph = copy_graph(tmp_path / f"g-{model}-{harness}")
    out = tmp_path / f"out-{model}-{harness}"
    argv = ["pregate", "--graph", str(graph), "--node", TUTORIAL, "--out", str(out)]
    argv += ["--model", model] if model else []
    argv += ["--harness", harness] if harness else []
    code = cli.main(argv)
    capsys.readouterr()
    verdict = json.loads((out / "verdict.json").read_text())
    record = schemas.load_json(out / "attestation.json")
    return code, verdict, record


def masked(record: dict[str, Any]) -> dict[str, Any]:
    """The record as D-5 compares two runs (runner, merge commit and signature masked, D-34),
    less the tooling it is meant to record."""
    return {k: v for k, v in attestation.masked(record).items() if k not in TOOLING_FIELDS}


def runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    return [pregate(tmp_path, capsys, model, harness) for model, harness in DECLARATIONS]


@pytest.mark.parametrize("outcome", ["pass", "fail"])
def test_gate_never_reads_harness(
    outcome: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = (
        FakeToolchain()
        if outcome == "pass"
        else FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    )
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: fake))
    results = runs(tmp_path, capsys)
    codes = {code for code, _, _ in results}
    assert codes == {cli.EXIT_PASS if outcome == "pass" else cli.EXIT_FAIL}
    first_verdict, first_record = results[0][1], masked(results[0][2])
    for (model, harness), (_, verdict, record) in zip(DECLARATIONS, results, strict=True):
        assert verdict == first_verdict, (model, harness)
        assert masked(record) == first_record, (model, harness)
        assert record["tooling"] == {"model": model, "harness": harness}


def test_mutant_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gate that fails one harness's submissions: the same comparison sees the difference."""
    fake = FakeToolchain()
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: fake))
    real = attestation.build

    def biased(*args: Any, **kwargs: Any) -> dict[str, Any]:
        record: dict[str, Any] = real(*args, **kwargs)
        if (kwargs.get("tooling") or {}).get("harness") == "cursor":
            record["verdict"] = "fail"
        return record

    monkeypatch.setattr(attestation, "build", biased)
    results = runs(tmp_path, capsys)
    records = [masked(record) for _, _, record in results]
    assert any(r != records[0] for r in records), "the comparison missed a harness-biased gate"
