"""F07-T44 (D-29 v3.22), fast tier: step 7 reads which of a hole's binders the assembly proved.

The rule is Lean's to apply (``test_finding_witness_proved_haves_lean.py``); what the fast tier
owns is the record's path. The extractor reports ``proved_binders`` per hole, the post-merge job
writes them into the child's ``META.yaml`` (``meta/v5``, the first version that can carry them —
``meta/v4`` is closed and pinned, D-34), and step 7 hands them to ``opn-witness-type``. A node
without the record — every hole written before the rule, and every node that is not a hole — is
asked exactly what it was asked before.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import samples
import yaml
from fakes import FakeToolchain, witness_result
from harness import make_context, node_dir

from opn_gate import layout, pipeline, schemas
from opn_gate.steps import default_steps
from opn_gate.steps.artifact import Hole, proved_indices
from opn_gate.steps.witness import WitnessStep
from opn_gate.toolchain import WitnessRequest


def run_to_seven(ctx: object) -> pipeline.Verdict:
    """Steps 1 to 8 as the gate runs them; step 7 is among them (``default_steps``)."""
    assert any(isinstance(s, WitnessStep) for s in default_steps())
    return pipeline.run_steps(ctx)  # type: ignore[arg-type]


def record(path: Path, proved: list[int] | None) -> None:
    """Rewrite a node's META.yaml with (or without) the record, at the version that carries it."""
    meta = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta.pop("proved_binders", None)
    if proved is not None:
        meta["schema"] = "meta/v5"
        meta["proved_binders"] = proved
    path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_step_7_passes_the_record_to_the_witness_metaprogram(tmp_path: Path) -> None:
    fake = FakeToolchain(witness=witness_result(expected="True", witness="True"))
    ctx = make_context(tmp_path, toolchain=fake)
    record(node_dir(ctx) / "META.yaml", [0, 2])
    verdict = run_to_seven(ctx)
    assert verdict.ok, verdict.as_dict()
    (req,) = fake.witness_requests
    assert req.proved == (0, 2)
    assert req.args()[-2:] == ["--proved", "0,2"]


def test_without_the_record_step_7_asks_what_it_always_asked(tmp_path: Path) -> None:
    fake = FakeToolchain(witness=witness_result(expected="True", witness="True"))
    verdict = run_to_seven(make_context(tmp_path, toolchain=fake))
    assert verdict.ok, verdict.as_dict()
    (req,) = fake.witness_requests
    assert req.proved == ()
    assert "--proved" not in req.args()


def test_meta_v5_carries_the_record_and_v4_does_not() -> None:
    doc = samples.meta(schema="meta/v5", origin="skeleton-hole", proved_binders=[3, 4])
    schemas.validate(doc)
    assert schemas.violations({**doc, "schema": "meta/v4"})
    for bad in ([], [-1], ["hp"], [1, 1]):
        assert schemas.violations({**doc, "proved_binders": bad}), bad
    assert "meta/v5" in layout.META_SCHEMAS


def test_a_hole_reads_the_extractors_marks() -> None:
    doc = {"name": "h", "type": "q", "closed_type": "∀ p q, p → q", "defeq_goal": False}
    assert Hole.of(doc).proved_binders == ()  # an older pin reports no field
    marked = Hole.of({**doc, "proved_binders": [2, 1]})
    assert marked.proved_binders == (1, 2)
    assert marked.as_dict()["proved_binders"] == [1, 2]


@pytest.mark.parametrize("raw", [None, "1,2", [1, "2"], [True], [-1], {"a": 1}])
def test_anything_but_a_list_of_indices_reads_as_no_record(raw: object) -> None:
    assert proved_indices(raw) == ()


def test_the_request_is_unchanged_without_the_record(tmp_path: Path) -> None:
    """The metaprogram's argument list is byte for byte what an older pin was handed."""
    statement = tmp_path / "S.lean"
    statement.write_text("theorem s : True := by\n  sorry\n")
    req = WitnessRequest(statement=statement, statement_module="S", decl="s")
    assert req.args() == ["--statement", str(statement.resolve()), "--module", "S", "--decl", "s"]
