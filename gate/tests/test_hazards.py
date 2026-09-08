"""F02-T3: step 6 over the fake seam (R3, R4, R5, R6; AC1-AC4)."""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, hazards_result, metaprogram_garbage
from harness import make_context, node_dir

from opn_gate import pipeline, schemas
from opn_gate.steps import default_steps
from opn_gate.steps.hazards import (
    KNOWN_CHECKERS,
    Acknowledgment,
    Finding,
    HazardsStep,
    check_config,
    evaluate,
)

NAT_SUB = {"checker": "nat-sub", "location": "n - 1", "message": "subtraction on Nat truncates"}


def with_meta_v2(ctx: object, acks: list[dict[str, str]] | None) -> None:
    """Rewrite the fixture node's META.yaml as meta/v2 with the given acknowledgments."""
    path = node_dir(ctx) / "META.yaml"  # type: ignore[arg-type]
    meta = schemas.load_yaml(path)
    meta["schema"] = "meta/v2"
    if acks is not None:
        meta["acknowledged_hazards"] = acks
    lines = [f"schema: {meta['schema']}", f"id: {meta['id']}", f"status: {meta['status']}"]
    lines.append("deps: []")
    lines.append(f"statement-hash: {meta['statement-hash']}")
    lines.append(f"origin: {meta['origin']}")
    lines.append("provenance:")
    lines.append(f"  author: {meta['provenance']['author']}")
    lines.append(f"tutorial: {'true' if meta['tutorial'] else 'false'}")
    if acks is not None:
        lines.append("acknowledged_hazards:")
        for a in acks:
            lines.append(f"  - checker: {a['checker']}")
            lines.append(f"    location: {a['location']!r}")
            lines.append(f"    justification: {a['justification']!r}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_to_six(ctx: object) -> pipeline.Verdict:
    steps = [*default_steps(), HazardsStep()]
    return pipeline.run_steps(ctx, steps=steps)  # type: ignore[arg-type]


def test_unknown_checker_id_fails_config(tmp_path: Path) -> None:
    """AC1: an unknown id in gate-spec.json fails before step 1 with a config diagnostic."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["bogus"]})
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail" and verdict.first_failing_step is None
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "config-unknown-checker"
    assert verdict.diagnostic.details["unknown"] == ["bogus"]
    assert all(s.result == "skipped" for s in verdict.steps)
    assert fake.calls == []  # nothing ran, not even step 1
    assert check_config({"hazard_checkers": list(KNOWN_CHECKERS)}) is None


def test_unacknowledged_finding_fails(tmp_path: Path) -> None:
    """AC2."""
    fake = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["nat-sub"]})
    verdict = run_to_six(ctx)
    assert verdict.first_failing_step == 6, verdict
    d = verdict.diagnostic
    assert d is not None and d.code == "hazard-unacknowledged"
    assert d.details["findings"] == [NAT_SUB]
    assert "nat-sub" in d.message and "n - 1" in d.message
    assert fake.calls[-1] == "hazards:OpnProp.and_swap:nat-sub"  # 7 and 8 never ran


def test_acknowledged_finding_passes_and_is_listed(tmp_path: Path) -> None:
    """AC3, R5: the step's record names the acknowledgment it relied on."""
    fake = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["nat-sub"]})
    ack = {"checker": "nat-sub", "location": "n - 1", "justification": "intended: n ≥ 1 by h"}
    with_meta_v2(ctx, [ack])
    verdict = run_to_six(ctx)
    assert verdict.ok, verdict
    six = next(s for s in verdict.steps if s.step == 6)
    assert six.result == "pass" and six.diagnostic is not None
    assert six.diagnostic.code == "hazards-acknowledged"
    assert six.diagnostic.details["acknowledged"] == [ack]
    assert verdict.data["hazards"]["acknowledged"] == [ack]
    doc = verdict.as_dict()
    record = next(s for s in doc["steps"] if s["step"] == 6)
    assert record["result"] == "pass"
    assert record["diagnostic"]["details"]["acknowledged"] == [ack]


def test_empty_justification_rejected(tmp_path: Path) -> None:
    """AC4: a whitespace justification passes the schema's minLength but acknowledges nothing."""
    fake = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["nat-sub"]})
    with_meta_v2(ctx, [{"checker": "nat-sub", "location": "n - 1", "justification": "   "}])
    verdict = run_to_six(ctx)
    assert verdict.first_failing_step == 6
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hazard-unacknowledged"
    # An empty string never reaches step 6: meta/v2 rejects it at step 2.
    ctx2 = make_context(tmp_path / "b", toolchain=fake, spec_overrides={"hazard_checkers": []})
    with_meta_v2(ctx2, [{"checker": "nat-sub", "location": "n - 1", "justification": ""}])
    verdict = run_to_six(ctx2)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "meta-invalid"


def test_evaluate_matches_on_checker_and_location() -> None:
    f1 = Finding("nat-sub", "n - 1", "m")
    f2 = Finding("div-zero", "a / b", "m")
    a1 = Acknowledgment("nat-sub", "n - 1", "why")
    a_wrong_loc = Acknowledgment("div-zero", "b / a", "why")
    a_blank = Acknowledgment("div-zero", "a / b", " ")
    ev = evaluate([f1, f2], [a1, a_wrong_loc, a_blank])
    assert ev.unacknowledged == (f2,)
    assert ev.used == (a1,)
    assert ev.unused == (a_wrong_loc, a_blank)
    assert evaluate([], [a1]).unused == (a1,)


def test_no_checkers_configured_skips_the_metaprogram(tmp_path: Path) -> None:
    """R3: with an empty list nothing runs, and the step passes without a record."""
    fake = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = run_to_six(ctx)
    assert verdict.ok
    assert not any(c.startswith("hazards:") for c in fake.calls)
    six = next(s for s in verdict.steps if s.step == 6)
    assert six.diagnostic is None
    assert verdict.data["hazards"] == {"checkers": [], "findings": [], "acknowledged": []}


def test_only_listed_checkers_are_requested(tmp_path: Path) -> None:
    fake = FakeToolchain(hazards_doc=hazards_result([]))
    ctx = make_context(
        tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["div-zero", "nat-sub"]}
    )
    assert run_to_six(ctx).ok
    assert "hazards:OpnProp.and_swap:div-zero,nat-sub" in fake.calls


def test_metaprogram_failure_is_step_failure(tmp_path: Path) -> None:
    fake = FakeToolchain(hazards_doc=metaprogram_garbage())
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["nat-sub"]})
    verdict = run_to_six(ctx)
    assert verdict.first_failing_step == 6
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "metaprogram-failed"


def test_meta_v1_node_has_no_acknowledgments(tmp_path: Path) -> None:
    """R6: meta/v1 reads as an empty acknowledgment list — a finding stands."""
    fake = FakeToolchain(hazards_doc=hazards_result([NAT_SUB]))
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides={"hazard_checkers": ["nat-sub"]})
    verdict = run_to_six(ctx)
    assert verdict.first_failing_step == 6
    assert verdict.diagnostic is not None and verdict.diagnostic.details["acknowledged"] == []
