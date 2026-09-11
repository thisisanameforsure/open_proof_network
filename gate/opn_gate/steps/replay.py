"""D-4 step 4: build the node in the gate's layout, then replay it through the kernel from clean
(F00-R5; F01-Q4).

The node and its dependency closure are staged as ``Nodes.«id».*`` modules with generated
Contexts, compiled deps-first, and the node's ``Proof`` module is replayed with
``leanchecker --fresh``, which re-checks every imported declaration too.
"""

from __future__ import annotations

import subprocess

from opn_gate import cache, layout
from opn_gate.steps import stage as staging
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ElabResult, ResolvedToolchain

PROOF_MODULE = "Proof"
CONTEXT_MODULE = "Context"


class KernelReplayStep:
    number = 4
    name = "kernel-replay"

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 4 needs steps 1 and 2 to have passed")
        staged = staging.stage(node, ctx.workdir)
        ctx.data["staged"] = staged
        if staged.problems:
            first = staged.problems[0]
            return StepResult.failed(
                first.code,
                first.message,
                **first.details,
                problems=[p.message for p in staged.problems],
            )
        try:
            for node_id in staged.order:
                for stem in (CONTEXT_MODULE, PROOF_MODULE):
                    failure = self._compile(ctx, tc, staged, node_id, stem)
                    if failure is not None:
                        return failure
            replay = ctx.toolchain.kernel_replay(
                tc,
                layout.node_module(node.node_id, PROOF_MODULE),
                [staged.build],
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired as exc:
            return StepResult.failed(
                "timeout",
                f"step 4 exceeded the {ctx.wallclock_s:g}s wall-clock cap",
                cmd=str(exc.cmd),
            )
        if not replay.ok:
            return StepResult.failed(
                "kernel-replay-failed",
                "leanchecker --fresh rejected the module",
                output=replay.output,
            )
        return StepResult.passed()

    def _compile(
        self,
        ctx: RunContext,
        tc: ResolvedToolchain,
        staged: staging.Staged,
        node_id: str,
        stem: str,
    ) -> StepResult | None:
        module = layout.node_module(node_id, stem)
        source = staged.root / staged.rel(node_id, stem)
        # F10-R7: a dependency whose staged source the cache was built from is taken as built;
        # the node under check is always compiled, and the replay re-checks every import anyway.
        fetched: cache.Fetched | None = ctx.data.get("olean_cache")
        usage: cache.Usage | None = ctx.data.get("olean_cache_usage")
        if fetched is not None and ctx.node is not None and node_id != ctx.node.node_id:
            if cache.take(fetched, source, module, staged.build, tc.name):
                if usage is not None:
                    usage.hits.append(module)
                return None
            if usage is not None:
                usage.misses.append(module)
        elab: ElabResult = ctx.toolchain.elaborate(
            tc,
            source,
            module,
            staged.build,
            root=staged.root,
            timeout_s=ctx.wallclock_s,
        )
        if elab.ok:
            return None
        return StepResult.failed(
            "elaboration-failed",
            f"{module} does not elaborate",
            module=module,
            node=node_id,
            messages=[m.as_dict() for m in elab.errors or elab.messages],
            stderr=elab.stderr,
        )
