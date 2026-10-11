"""F07-T50 (R23), docker tier: a partial's carried witnesses in the step-3 sandbox.

The lean tier proves step 7 holds a carried witness to its hole's statement when the toolchain
can read the staged child; this proves it can read it where the gate runs. The sandbox holds
the node under check and the work directory and nothing else, the carried files are under the
node's ``attempts/`` and the would-be children exist nowhere, so both are staged under the work
directory — and only a run through the container shows the staging reaches it (the Log's three
sandbox-only failures).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import node_dir
from test_finding_partial_carries_witnesses_lean import (
    BODY,
    INHERITS,
    NAMES,
    OWN,
    PROOF_OWN,
    PROOFS,
    prepare,
    witness_file,
)

from opn_gate import carried, pipeline
from opn_gate.sandbox import Caps, SandboxToolchain
from opn_gate.steps.base import RunContext

pytestmark = pytest.mark.docker

TYPES = {"first": OWN, "second": INHERITS, "third": OWN, "fourth": OWN}


def sandboxed(ctx: RunContext, image: str) -> RunContext:
    ctx.toolchain = SandboxToolchain(
        image, Caps.from_spec(ctx.spec), read_only=[node_dir(ctx)], read_write=[ctx.workdir]
    )
    return ctx


def test_the_sandboxed_gate_checks_every_carried_witness(
    sandbox_image: str, tmp_path: Path
) -> None:
    witnesses = {name: witness_file(name, TYPES[name], PROOFS[name]) for name in NAMES}
    ctx, _text = prepare(tmp_path, None, BODY, witnesses)
    verdict = pipeline.run_submission(sandboxed(ctx, sandbox_image))
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [w["hole"] for w in verdict.data[carried.DATA_KEY]] == list(NAMES)
    step7 = next(s for s in verdict.steps if s.step == 7)
    assert step7.diagnostic is not None and step7.diagnostic.code == "hole-witnesses"


def test_the_sandboxed_gate_refuses_a_carried_witness_of_the_wrong_type(
    sandbox_image: str, tmp_path: Path
) -> None:
    ctx, _text = prepare(tmp_path, None, BODY, {"second": witness_file("second", OWN, PROOF_OWN)})
    verdict = pipeline.run_submission(sandboxed(ctx, sandbox_image))
    assert verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "witness-type-mismatch", verdict.as_dict()
    assert verdict.diagnostic.details["hole"] == "second"
