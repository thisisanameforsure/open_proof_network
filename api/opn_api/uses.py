"""The service's reading of a use line (F08-R21, T26; Q39, decided 2026-10-03: option (a)).

A proof, an alternate or a partial's assembly may carry *use lines* directly after its
statement's imports (F08-R16, R18; ``opn_gate.uses``): ``import Defs.<Name>`` or
``import Nodes.«<id>».Proof``. The gate reads them from T23/T24 on, and a gate is live per target
at its re-pin (D-35), so the service decides per target: **a target's pinned gate understands
uses when its ``gate-spec.json`` ``network_commit`` is ``Settings.uses_from`` or a descendant of
it.** The comparison is one host call per pin for the life of the process (a commit's ancestry
never changes), and when ``uses_from`` is unset or the host cannot say, the target is read as
not understanding uses: a use line is then ``imports-differ``, as before T26, which refuses where
the gate might have taken it rather than open what the gate would refuse (2026-09-24).

Where a target does understand uses, the lines are read by the gate's own function
(``opn_gate.uses.split``) and held to the rules of ``opn_gate.uses.check``, by the gate's codes.
The gate asks those questions of a checkout; the service holds none (D-35), so ``problem`` is a
thin equivalent over what the graph has committed, and says per rule what it reads:

* ``use-duplicate``: the texts alone, as the gate;
* ``use-unknown-defs``: whether ``targets/<t>/defs/<Name>.lean`` is committed, as the gate;
* ``use-self``, ``use-unknown-node``: the target's ``graph.json`` rows;
* ``use-superseded``: the row's status (derived from the same status record the gate reads),
  with the successor where the record names one (``precheck.replacement_of``);
* ``use-unproved``: the used node's committed ``Proof.lean``, read by the gate's own
  ``declared_kind``, so a counterexample is not a proof here either;
* ``use-redundant``: the node's ``deps`` in ``graph.json``;
* ``use-ancestor``: every node resting on this one over ``graph.json``'s ``deps`` and, where a
  row carries one, its ``uses`` (graph/v4, T27). Until T27 publishes uses, a merged use the
  products do not show is not seen here; the gate, which reads the merged proofs, still refuses
  it at step 2.

No route gains a field: the declaration is the artifact's text.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from opn_api import frontier, pending, precheck
from opn_api.githost import GitHostError
from opn_gate import layout
from opn_gate import uses as gate_uses
from opn_gate.diagnostic import Diagnostic

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_gate.paths import Claim

log = logging.getLogger("opn_api.uses")

#: Every code ``problem`` can answer: the gate's own (``opn_gate.uses``), so a refusal here and at
#: step 2 read the same. ``use-kind`` is not among them: ``uses.split`` reads no use lines off a
#: text that is not the statement's (a counterexample, a vacuity certificate), so neither the gate
#: as built nor the service has a use to refuse there.
CODES: frozenset[str] = frozenset(
    {
        "use-duplicate",
        "use-unknown-defs",
        "use-self",
        "use-unknown-node",
        "use-superseded",
        "use-unproved",
        "use-redundant",
        "use-ancestor",
    }
)
#: The bundle roles whose file declares uses at step 2: a proof, an alternate, an assembly.
ARTIFACT_ROLES: tuple[str, ...] = ("proof", "alternate", "partial")


def understood(ctx: Context, target_id: str) -> bool:
    """Whether ``target_id``'s pinned gate reads use lines (Q39 (a)): its ``network_commit`` is
    ``uses_from`` or descends from it. No host call when ``uses_from`` is unset or equal to the
    pin; one per new pin otherwise, kept on the app's own context."""
    return pinned_from(ctx, target_id, ctx.settings.uses_from, what="uses")


def pinned_from(ctx: Context, target_id: str, since: str, *, what: str) -> bool:
    """Whether ``target_id``'s pinned ``network_commit`` is ``since`` or descends from it: the
    question a per-target capability is decided by (Q39 (a); F18-T5 asks it of a stepped annex).
    ``False`` when ``since`` is unset, the pin is unreadable or the host cannot say (C7: the
    answer that opens nothing the pinned gate might refuse)."""
    uses_from = since
    if not uses_from:
        return False
    spec = json.loads(frontier.committed(ctx, f"targets/{target_id}/gate-spec.json"))
    pin = spec.get("network_commit") if isinstance(spec, dict) else None
    if not isinstance(pin, str) or not pin:
        return False
    if pin.lower() == uses_from:
        return True
    key = (uses_from, pin)
    if key not in ctx.ancestry:
        try:
            ctx.ancestry[key] = ctx.githost.is_ancestor(ctx.settings.network_repo, uses_from, pin)
        except GitHostError as exc:
            # C7: not cached, so the next call asks again; meanwhile the answer that opens nothing
            log.warning("%s: whether %s understands %s is unknown: %s", target_id, pin, what, exc)
            return False
    return ctx.ancestry[key]


def has_use_line(text: str) -> bool:
    """Whether any line of ``text`` has a use line's shape: a cheap test before anything is
    fetched (``uses.split`` decides which of them are uses)."""
    return any(layout.USE_LINE_RE.fullmatch(line) for line in text.splitlines())


def declared(statement: layout.Statement, text: str, node_id: str | None) -> gate_uses.Uses:
    """The uses ``text`` declares, read by the gate's own function (``opn_gate.uses.declared``)."""
    return gate_uses.declared(statement, text, node_id)


def without_uses(statement: layout.Statement, text: str, node_id: str | None) -> str:
    """``text`` with its use lines removed, as step 2 compares it (``opn_gate.uses.split``)."""
    return gate_uses.split(statement.prefix, text, node_id)[0]


def _rows(ctx: Context, target_id: str) -> dict[str, dict[str, Any]]:
    return {str(n.get("node_id")): n for n in precheck.graph_doc(ctx).get(target_id, [])}


def above(rows: Mapping[str, Mapping[str, Any]], node_id: str) -> set[str]:
    """Every node that rests on ``node_id`` over the products' ``deps`` and, where a row carries
    them, its ``uses``; never the node itself (``opn_gate.uses.above``, read from ``graph.json``
    rather than a checkout)."""
    rests_on = {
        nid: {str(d) for d in (row.get("deps") or [])} | {str(u) for u in (row.get("uses") or [])}
        for nid, row in rows.items()
    }
    found: set[str] = set()
    frontier_ = [node_id]
    while frontier_:
        below = frontier_.pop()
        for candidate, on in rests_on.items():
            if below in on and candidate not in found and candidate != node_id:
                found.add(candidate)
                frontier_.append(candidate)
    return found


def _committed_text(ctx: Context, path: str) -> str | None:
    raw = pending.optional_committed(ctx, path)
    return raw.decode("utf-8", "replace") if raw is not None else None


def _node_problem(  # noqa: PLR0911 — one return per rule, in the gate's order
    ctx: Context,
    target_id: str,
    node_id: str | None,
    used: str,
    rows: Mapping[str, Mapping[str, Any]],
) -> Diagnostic | None:
    """``opn_gate.uses._node_problem`` over the committed products (see the module docstring)."""
    from opn_gate.steps import artifact  # noqa: PLC0415 — only a node use reads it

    module = layout.node_module(used, layout.USED_STEM)
    details: dict[str, Any] = {"module": module, "node": used}
    if used == node_id:
        return Diagnostic("use-self", f"{module} is this node's own proof", details)
    row = rows.get(used)
    if row is None:
        return Diagnostic("use-unknown-node", f"{used} is not a node of {target_id}", details)
    if row.get("status") == "superseded":
        successor = precheck.replacement_of(ctx, target_id, used)
        return Diagnostic(
            "use-superseded",
            f"{used} has been superseded"
            + (f" by {successor}: use that node's proof" if successor else "")
            + " (D-8); a proof may not rest on a statement the graph has replaced",
            {**details, "successor": successor},
        )
    base = f"targets/{target_id}/nodes/{used}/"
    proof = _committed_text(ctx, base + "Proof.lean")
    statement_text = _committed_text(ctx, base + "Statement.lean") if proof is not None else None
    statement = layout.parse_statement(statement_text) if statement_text is not None else None
    kind = (
        artifact.declared_kind(statement.decl_name, proof)[0]
        if proof is not None and isinstance(statement, layout.Statement)
        else None
    )
    if kind != "proof":
        return Diagnostic(
            "use-unproved",
            f"{used} has no merged proof to use"
            + (f" (its merged artifact is a {kind})" if kind else "")
            + ": a proof may use a node of its target only once that node's Proof.lean has "
            "merged (D-3)",
            {**details, "artifact": kind},
        )
    own = rows.get(node_id or "") or {}
    if used in {str(d) for d in (own.get("deps") or [])}:
        return Diagnostic(
            "use-redundant",
            f"{used} is already a dependency of {node_id}: its theorem reaches the proof "
            f"through {layout.node_module(str(node_id), 'Context')}, and a node is named one way",
            details,
        )
    if node_id is not None and used in above(rows, node_id):
        return Diagnostic(
            "use-ancestor",
            f"{used} rests on {node_id} (through recorded dependencies and merged uses), so a "
            f"proof of {node_id} that uses it would make the statement graph wait on itself; a "
            "node is proved from what lies beside or below it, never from a node it was written "
            "to help prove (D-12: no cycles)",
            details,
        )
    return None


def problem(
    ctx: Context,
    target_id: str,
    node_id: str | None,
    statement: layout.Statement,
    found: gate_uses.Uses,
) -> Diagnostic | None:
    """The first rule of ``opn_gate.uses.check`` that ``found`` breaks, read from the committed
    products; ``None`` when every use is usable or there are none. Same order as the gate."""
    if not found:
        return None
    seen = set(layout.imports_of(statement.text))
    for module in found.modules:
        if module in seen:
            return Diagnostic(
                "use-duplicate",
                f"the header imports {module} twice: a use line names a module once, and never "
                "one the statement already imports",
                {"module": module},
            )
        seen.add(module)
    for module in found.defs:
        stem = module.partition(".")[2]
        if pending.optional_committed(ctx, f"targets/{target_id}/defs/{stem}.lean") is None:
            return Diagnostic(
                "use-unknown-defs",
                f"{module} is not a definition of {target_id}: a proof may use a module under "
                f"targets/{target_id}/defs/ that is already on the graph (D-3), and a definition "
                "is added by a curator's pull request (F11-R15)",
                {"module": module},
            )
    if not found.nodes:
        return None
    rows = _rows(ctx, target_id)
    for used in found.nodes:
        bad = _node_problem(ctx, target_id, node_id, used, rows)
        if bad is not None:
            return bad
    return None


def finding(diagnostic: Diagnostic) -> dict[str, Any]:
    """A use refusal as a ``POST /check`` lint finding: the gate's code and words."""
    return {
        "code": diagnostic.code,
        "message": f"{diagnostic.message}; the gate refuses this use at step 2 (F08-R16, R18)",
        **dict(diagnostic.details),
    }


def check_bundle(ctx: Context, claim: Claim, files: Mapping[str, str]) -> None:
    """F08-R21 for the write routes (``POST /precheck``, ``POST /submissions``): a proof, an
    alternate or a partial's assembly whose use lines the target's pinned gate would refuse at
    step 2 is a 400 with the gate's code, before a job is dispatched or anything is pushed. On a
    target whose pin predates uses nothing is added: that gate refuses the header itself."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this
    from opn_gate import paths as gate_paths  # noqa: PLC0415

    texts = [
        text
        for path, text in sorted(files.items())
        if (where := gate_paths.locate(path)) is not None
        and where.role in ARTIFACT_ROLES
        and has_use_line(text)
    ]
    if not texts or not understood(ctx, claim.target_id):
        return
    from opn_api import checks  # noqa: PLC0415 — checks imports this module

    statement, _ = checks.statement_of(ctx, claim.target_id, claim.node_id)
    if statement is None:
        return  # step 2 names an unparsable statement itself
    for text in texts:
        found = declared(statement, text, claim.node_id)
        bad = problem(ctx, claim.target_id, claim.node_id, statement, found)
        if bad is not None:
            raise ApiError(400, bad.code, bad.message, details=dict(bad.details))


def used_sources(
    ctx: Context, target_id: str, found: gate_uses.Uses, skip: frozenset[str] = frozenset()
) -> list[tuple[str, str, str]]:
    """What the composer inlines for each used node not in ``skip``: ``(module, statement text,
    used node)``, the statement the used node's Context-style signature is made from (D-3: a
    Context carries a dependency's statement verbatim with its ``sorry`` body)."""
    out: list[tuple[str, str, str]] = []
    for used in found.nodes:
        module = layout.node_module(used, layout.USED_STEM)
        if module in skip:
            continue
        text = _committed_text(ctx, f"targets/{target_id}/nodes/{used}/Statement.lean")
        if text is not None:
            out.append((module, text, used))
    return out
