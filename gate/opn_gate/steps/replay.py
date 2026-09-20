"""D-4 step 4: build the node in the gate's layout, then replay it through the kernel from clean
(F00-R5; F01-Q4).

The node and its dependency closure are staged as ``Nodes.«id».*`` modules with generated
Contexts, compiled deps-first, and then replayed through the kernel. Which replay runs depends on
the target's ``gate-spec.json``:

* **No Mathlib pinned** (``mathlib_sha`` null): ``leanchecker --fresh Nodes.«id».Proof``, which
  re-checks every imported declaration, Lean core's included.
* **Mathlib pinned**: ``leanchecker <module>`` without ``--fresh``, once for every module under
  the graph's own prefixes — the node, every dependency (including one taken from the olean
  cache, F10-R7) and every compiled ``Defs.*`` module — each having its own declarations
  replayed through the kernel against its imports. Fresh-replaying all of Mathlib exceeds the
  wall-clock cap, so Lean core's and the pinned image's Mathlib oleans are trusted as built, not
  re-checked. **One process per module, in sequence** (F02-T7): a single ``leanchecker Nodes
  Defs`` holds every module's Mathlib-sized environment at once, and every proof with a proved
  dependency was killed at the 4 GiB memory cap (5 of 5 on the live graph; nothing with a proved
  dependency had passed step 4 since v3.16). What is replayed is unchanged; the modules share the
  step's one wall-clock budget.

The mode that ran is recorded in ``ctx.data["replay_mode"]`` and on a failure's details.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Mapping
from pathlib import Path

from opn_gate import cache, defs, layout, sandbox
from opn_gate.steps import artifact
from opn_gate.steps import stage as staging
from opn_gate.steps.artifact import ALTERNATE_KEY, PARTIAL_KEY
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ElabResult, ReplayResult, ResolvedToolchain, Toolchain

PROOF_MODULE = "Proof"
CONTEXT_MODULE = "Context"

#: ``ctx.data`` key and the two values it takes.
REPLAY_MODE_KEY = "replay_mode"
MODE_FRESH = "fresh"
MODE_PREFIX = "prefix"


def graph_prefixes(build: Path) -> list[str]:
    """The graph's own module prefixes that have at least one olean under ``build``."""
    return [
        prefix
        for prefix in (layout.NODES_PREFIX, layout.DEFS_PREFIX)
        if (build / prefix).is_dir() and any((build / prefix).rglob("*.olean"))
    ]


def built_modules(build: Path) -> list[str]:
    """Every module under the graph's own prefixes that has an olean in ``build``, by name:
    ``Defs.*`` first, then ``Nodes.«id».*``, each sorted. A node id is always quoted, as
    ``layout.node_module`` writes it."""
    names: list[str] = []
    for prefix in (layout.DEFS_PREFIX, layout.NODES_PREFIX):
        base = build / prefix
        if not base.is_dir():
            continue
        for olean in sorted(base.rglob("*.olean")):
            parts = olean.relative_to(base).with_suffix("").parts
            if prefix == layout.NODES_PREFIX and len(parts) >= 2:
                names.append(layout.node_module(parts[0], ".".join(parts[1:])))
            else:
                names.append(".".join((prefix, *parts)))
    return names


def replay_plan(spec: Mapping[str, object], module: str, build: Path) -> tuple[str, list[str]]:
    """The replay for ``module`` under ``spec``: ``(mode, modules)``. A Mathlib-free spec replays
    ``module`` fresh; a Mathlib-pinned one replays every module the graph built (``built_modules``)
    plus ``module`` itself when it is not among them, each in a process of its own."""
    if spec.get("mathlib_sha") is None:
        return MODE_FRESH, [module]
    modules = built_modules(build)
    if module not in modules:
        modules.append(module)
    return MODE_PREFIX, modules


def replay(  # noqa: PLR0913 — the seam's inputs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    spec: Mapping[str, object],
    module: str,
    build: Path,
    *,
    timeout_s: float | None,
) -> tuple[str, list[str], ReplayResult]:
    """Run :func:`replay_plan`'s replay through the seam: one call for a fresh replay, one call
    per module otherwise (F02-T7), stopping at the first that fails. The calls share
    ``timeout_s``: each is given what is left of it, and running out is the step's timeout."""
    mode, modules = replay_plan(spec, module, build)
    if mode == MODE_FRESH:
        result = toolchain.kernel_replay(tc, modules, [build], fresh=True, timeout_s=timeout_s)
        return mode, modules, result
    started = time.monotonic()
    output: list[str] = []
    for name in modules:
        left = None if timeout_s is None else timeout_s - (time.monotonic() - started)
        if left is not None and left <= 0:
            raise subprocess.TimeoutExpired(["leanchecker", name], float(timeout_s or 0))
        result = toolchain.kernel_replay(tc, [name], [build], fresh=False, timeout_s=left)
        output.append(result.output)
        if not result.ok:
            return mode, modules, ReplayResult(ok=False, output="".join(output))
    return mode, modules, ReplayResult(ok=True, output="".join(output))


class KernelReplayStep:
    number = 4
    name = "kernel-replay"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 4 needs steps 1 and 2 to have passed")
        # A partial's assembly (F07-R5) or a proved node's alternate (D-25) is built and replayed
        # as the node's own Proof module; neither ever writes the node's Proof.lean.
        chosen = ctx.data.get(PARTIAL_KEY) or ctx.data.get(ALTERNATE_KEY)
        override = Path(str(chosen["file"])) if isinstance(chosen, dict) else None
        staged = staging.stage(node, ctx.workdir, proof_override=override)
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
            # F11-R2, F01-Q2: ``Defs.*`` first — a node's Context and Proof may import them.
            target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
            problem = defs.compile_all(
                ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=ctx.wallclock_s
            )
            if problem is not None:
                return StepResult(ok=False, diagnostic=problem)
            for node_id in staged.order:
                for stem in (CONTEXT_MODULE, PROOF_MODULE):
                    failure = self._compile(ctx, tc, staged, node_id, stem)
                    if failure is not None:
                        return failure
            proof_module = layout.node_module(node.node_id, PROOF_MODULE)
            ctx.data[REPLAY_MODE_KEY] = replay_plan(ctx.spec, proof_module, staged.build)[0]
            mode, modules, result = replay(
                ctx.toolchain, tc, ctx.spec, proof_module, staged.build, timeout_s=ctx.wallclock_s
            )
        except sandbox.MemoryExceeded as exc:
            return StepResult.failed(
                "memory-exceeded",
                f"step 4 was killed at the {exc.memory_mib} MiB memory cap, not by the clock",
                cmd=str(exc.cmd),
                replay_mode=ctx.data.get(REPLAY_MODE_KEY),
                memory_mib=exc.memory_mib,
            )
        except subprocess.TimeoutExpired as exc:
            return StepResult.failed(
                "timeout",
                f"step 4 exceeded the {ctx.wallclock_s:g}s wall-clock cap",
                cmd=str(exc.cmd),
                replay_mode=ctx.data.get(REPLAY_MODE_KEY),
            )
        if not result.ok:
            return StepResult.failed(
                "kernel-replay-failed",
                "the kernel replay rejected the build",
                output=result.output,
                replay_mode=mode,
                modules=modules,
            )
        # F07-R4, R5: which of D-12's artifacts this is, and whether it is that thing — step 4's
        # last word, because the type check needs the build that just passed (F11-T4).
        try:
            return artifact.judge(ctx, tc)
        except subprocess.TimeoutExpired:
            return StepResult.failed("timeout", "the artifact check exceeded the wall-clock cap")

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
        # the node under check is always compiled, and the replay re-checks every graph module.
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
