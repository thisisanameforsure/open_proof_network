"""Finding "a hole may restate an ancestor", docker tier: the cycle check in the step-3 sandbox
(F07-T34).

The lean tier proves the extractor names the ancestor when it can read the probes; this proves it
can read them where the gate runs. The sandbox holds the node under check and the work directory
and nothing else, and the ancestors live elsewhere in the graph, so their probes are staged under
the work directory — and only a run through the container shows the staging reaches it (the Log's
three sandbox-only failures).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import node_dir
from test_finding_hole_restates_ancestor import ROOT
from test_finding_hole_restates_ancestor_lean import (
    ASSEMBLE,
    FRESH,
    ROOT_SOURCE,
    leaf_partial,
)

from opn_gate import pipeline
from opn_gate.sandbox import Caps, SandboxToolchain

pytestmark = pytest.mark.docker


def test_the_sandboxed_gate_refuses_a_grandchild_hole_that_restates_the_root(
    sandbox_image: str, tmp_path: Path
) -> None:
    body = f"  have up : {ROOT_SOURCE} := sorry\n" + FRESH + ASSEMBLE
    ctx = leaf_partial(tmp_path, None, body)
    ctx.toolchain = SandboxToolchain(
        sandbox_image,
        Caps.from_spec(ctx.spec),
        read_only=[node_dir(ctx)],
        read_write=[ctx.workdir],
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "offload-restates-ancestor", verdict.as_dict()
    assert verdict.diagnostic.details["restated"] == [{"hole": "up", "ancestor": ROOT}]
