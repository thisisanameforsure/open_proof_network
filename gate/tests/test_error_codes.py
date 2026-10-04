"""F13-T29: one catalog of every error code, each with a remedy (``opn_gate.codes``).

The gate names a refusal by a ``Diagnostic``'s code and the service by an ``ApiError``'s, and
before this catalog neither said what to do about one. The test walks the source of both
packages and collects every code the code can emit: the literal code argument of every
``Diagnostic(`` and ``ApiError(`` call and of the helpers that forward one (``StepResult.failed``
and ``passed_with``, ``QaError``, ``api_error``, ``bundles.Rejection``, the MCP adapter's
``error``), module-level string constants and local variables resolved, plus every literal
``"error": "<code>"`` the service builds by hand. A code that is not a literal is one of two
kinds, and each is listed here by its file and its expression so a new one cannot slip by:

* a *relay* passes on the code of a diagnostic or refusal built elsewhere, whose own
  construction the walk already collects (``first.code``, ``rejection.code``);
* a *family* builds the code from a small set the source also names (``f"{field}-invalid"`` over
  the call sites that pass ``field``); each has a resolver below that reads that set.

The collected set must equal the catalog's keys exactly, and every row must say what to do.
"""

from __future__ import annotations

import ast
import json
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from opn_gate import codes
from opn_gate.steps import artifact

REPO = Path(__file__).resolve().parents[2]
TREES: dict[str, Path] = {"gate": REPO / "gate" / "opn_gate", "api": REPO / "api" / "opn_api"}

#: Callee name -> (positional index of the code or None, keyword names that carry a code).
EMITTERS: dict[str, dict[str, tuple[int | None, tuple[str, ...]]]] = {
    "gate": {
        "Diagnostic": (0, ("code",)),
        "failed": (0, ("code",)),  # StepResult.failed
        "passed_with": (0, ("code",)),  # StepResult.passed_with: a pass that leaves a record
        "QaError": (0, ("code",)),
        "_check_schema": (None, ("code",)),
    },
    "api": {
        "ApiError": (1, ("code",)),
        "api_error": (1, ("code",)),
        "Rejection": (0, ("code",)),
        "error": (0, ("code",)),  # opn_api.mcp.calls.error, called by bare name only
        "refuse_axioms": (None, ("sorry_code", "axiom_code")),
    },
}
#: Emitters recognised only as a bare name: ``log.error(...)`` is not one.
NAME_ONLY = frozenset({"error"})
#: The helpers whose code *parameter* is forwarded to an emitter; their call sites are walked.
FORWARDERS = frozenset(
    {"failed", "passed_with", "_check_schema", "api_error", "error", "refuse_axioms"}
)

#: (file, expression) -> what is relayed. Each object's own construction is collected.
RELAYS: dict[tuple[str, str], str] = {
    ("gate/opn_gate/qa.py", "problem.code"): "a Diagnostic from check_exhibit",
    ("gate/opn_gate/qa.py", "shape.code"): "a Diagnostic from signature_of",
    ("gate/opn_gate/qa.py", "state.refused[0].code"): "a refused row's Diagnostic",
    ("gate/opn_gate/steps/artifact.py", "first.code"): "the artifact check's first Diagnostic",
    ("gate/opn_gate/steps/hazards.py", "first.code"): "layout.load_node's first Diagnostic",
    ("gate/opn_gate/steps/paths_step.py", "first.code"): "layout.load_node's first Diagnostic",
    ("gate/opn_gate/steps/replay.py", "first.code"): "the replay's first Diagnostic",
    ("gate/opn_gate/steps/witness.py", "found.code"): "a carried witness's Diagnostic",
    ("api/opn_api/checks.py", "problem.code"): "a gate Diagnostic, refused before a PR opens",
    ("api/opn_api/mcp/reads.py", "exc.code"): "an ApiError a read tool reused",
    ("api/opn_api/mcp/reads.py", "body.get('error')"): "the service route's own error body",
    ("api/opn_api/mcp/server.py", "body['error']"): "auth.unauthorized's body",
    ("api/opn_api/precheck.py", "rejection.code"): "a bundles.Rejection",
    ("api/opn_api/submissions.py", "problem.code"): "a gate Diagnostic (carried, annex)",
    ("api/opn_api/submissions.py", "refusal.code"): "a gate Diagnostic (carried.read)",
    ("api/opn_api/submissions.py", "rejection.code"): "a bundles.Rejection",
    ("api/opn_api/uses.py", "bad.code"): "a gate Diagnostic (uses.problem)",
}


def _module(rel: str) -> ast.Module:
    return ast.parse((REPO / rel).read_text(encoding="utf-8"))


def _literal_args(rel: str, callee: str, index: int) -> Iterator[tuple[str, ast.Call]]:
    """The literal string passed at ``index`` to every call of ``callee`` in its package."""
    tree = TREES["api" if rel.startswith("api/") else "gate"]
    for path in sorted(tree.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (
                f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            )
            if name != callee or len(node.args) <= index:
                continue
            arg = node.args[index]
            assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
                f"{path}:{node.lineno}: {callee} called with a non-literal {ast.unparse(arg)}"
            )
            yield arg.value, node


def _problem_prefixes() -> set[str]:
    """``problem.split(':', 1)[0]``: the steward and explainer checks name each problem
    ``"<code>: <message>"`` in their ``problems_of``."""
    out: set[str] = set()
    for rel in ("gate/opn_gate/steward.py", "gate/opn_gate/explainers.py"):
        for node in ast.walk(_module(rel)):
            if not (isinstance(node, ast.FunctionDef) and node.name == "problems_of"):
                continue
            for call in ast.walk(node):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "append"
                ):
                    arg = call.args[0]
                    head = arg.values[0] if isinstance(arg, ast.JoinedStr) else arg
                    value = head.value if isinstance(head, ast.Constant) else None
                    assert isinstance(value, str) and ":" in value, ast.unparse(arg)
                    out.add(value.split(":", 1)[0])
    assert out, "no problems_of found"
    return out


def _as_mapping_fields() -> set[str]:
    """``f'{field}-invalid'`` in ``appends.as_mapping``: the field names its callers pass."""
    return {f"{v}-invalid" for v, _ in _literal_args("api/", "as_mapping", 1)}


def _lean_text(suffix: str) -> Callable[[], set[str]]:
    """``f'{name}-missing'`` / ``f'{name}-invalid'`` in ``proposals.lean_text``. ``-missing``
    only where the field is required (the default)."""

    def resolve() -> set[str]:
        out: set[str] = set()
        for value, call in _literal_args("api/", "lean_text", 1):
            optional = any(
                k.arg == "required" and isinstance(k.value, ast.Constant) and k.value.value is False
                for k in call.keywords
            )
            if suffix == "missing" and optional:
                continue
            out.add(f"{value}-{suffix}")
        return out

    return resolve


#: (file, expression) -> the codes the expression can take.
FAMILIES: dict[tuple[str, str], Callable[[], set[str]]] = {
    ("gate/opn_gate/modes.py", "problem.split(':', 1)[0]"): _problem_prefixes,
    (
        "gate/opn_gate/steps/artifact.py",
        "'artifact-' + ('reduction' if artifact.is_reduction else artifact.kind)",
    ): lambda: {f"artifact-{k}" for k in typing.get_args(artifact.Kind)},
    ("gate/opn_gate/steps/paths_step.py", "f'{kind}-submission'"): lambda: {
        f"{k}-submission" for k in artifact.PROOF_FILE_KINDS if k != "proof"
    },
    ("api/opn_api/appends.py", "f'{field}-invalid'"): _as_mapping_fields,
    ("api/opn_api/proposals.py", "f'{name}-missing'"): _lean_text("missing"),
    ("api/opn_api/proposals.py", "f'{name}-invalid'"): _lean_text("invalid"),
}


@dataclass
class Walk:
    #: code -> source -> the emit sites (file:line), and the step class each sits in, if any.
    sites: dict[str, dict[str, list[tuple[str, int | None]]]] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    relays_seen: set[tuple[str, str]] = field(default_factory=set)
    families_seen: set[tuple[str, str]] = field(default_factory=set)

    def add(self, code: str, source: str, where: str, step: int | None) -> None:
        self.sites.setdefault(code, {}).setdefault(source, []).append((where, step))


def _module_constants(paths: list[Path]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in paths:
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            target = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
            elif isinstance(node, ast.AnnAssign):
                target = node.target
            value = getattr(node, "value", None)
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                out.setdefault(target.id, set()).add(value.value)
    return out


class _Collector(ast.NodeVisitor):
    def __init__(self, walk: Walk, source: str, rel: str, constants: dict[str, set[str]]) -> None:
        self.walk = walk
        self.source = source
        self.rel = rel
        self.constants = constants
        self.emitters = EMITTERS[source]
        self.functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self.steps: list[int | None] = []

    # -- scope -------------------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        number = None
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "number" for t in stmt.targets)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, int)
            ):
                number = stmt.value.value
        self.steps.append(number)
        self.generic_visit(node)
        self.steps.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(node)
        self.generic_visit(node)
        self.functions.pop()

    visit_FunctionDef = _visit_function  # noqa: N815 — the NodeVisitor's own method names
    visit_AsyncFunctionDef = _visit_function  # noqa: N815

    # -- emitters ----------------------------------------------------------------------------

    def visit_Dict(self, node: ast.Dict) -> None:
        if self.source == "api":
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "error"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    self._resolve(value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        if name in self.emitters and not (name in NAME_ONLY and not isinstance(f, ast.Name)):
            index, keywords = self.emitters[name]
            if index is not None and len(node.args) > index:
                self._resolve(node.args[index])
            for k in node.keywords:
                if k.arg in keywords:
                    self._resolve(k.value)
        self.generic_visit(node)

    # -- resolution --------------------------------------------------------------------------

    def _resolve(self, expr: ast.expr, depth: int = 0) -> None:  # noqa: PLR0911, PLR0912
        text = ast.unparse(expr)
        key = (self.rel, text)
        step = self.steps[-1] if self.steps else None
        where = f"{self.rel}:{expr.lineno}"
        if key in FAMILIES:
            self.walk.families_seen.add(key)
            for code in FAMILIES[key]():
                self.walk.add(code, self.source, where, step)
            return
        if key in RELAYS:
            self.walk.relays_seen.add(key)
            return
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            self.walk.add(expr.value, self.source, where, step)
            return
        if isinstance(expr, ast.IfExp):
            self._resolve(expr.body, depth)
            self._resolve(expr.orelse, depth)
            return
        if isinstance(expr, ast.BoolOp):
            for value in expr.values:
                self._resolve(value, depth)
            return
        if (
            isinstance(expr, ast.Call)
            and isinstance(expr.func, ast.Name)
            and expr.func.id == "str"
            and len(expr.args) == 1
        ):
            self._resolve(expr.args[0], depth)
            return
        if isinstance(expr, ast.Name) and depth < 4:
            fn = self.functions[-1] if self.functions else None
            if fn is not None:
                params = {a.arg for a in (*fn.args.args, *fn.args.kwonlyargs, *fn.args.posonlyargs)}
                if expr.id in params:
                    if fn.name in FORWARDERS:
                        # Forwarded: the helper's call sites are walked as emitters, and a
                        # literal default is what a call that names no code emits.
                        default = _default_of(fn, expr.id)
                        if default is not None:
                            self._resolve(default, depth + 1)
                        return
                    self.walk.unresolved.append(f"{where}: parameter {text} of {fn.name}")
                    return
                assigned = [
                    s.value
                    for s in ast.walk(fn)
                    if isinstance(s, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == expr.id for t in s.targets)
                ]
                if assigned:
                    for value in assigned:
                        self._resolve(value, depth + 1)
                    return
            values = self.constants.get(expr.id, set())
            if len(values) == 1:
                self.walk.add(next(iter(values)), self.source, where, step)
                return
        if isinstance(expr, ast.Attribute):
            values = self.constants.get(expr.attr, set())
            if expr.attr.isupper() and len(values) == 1:
                self.walk.add(next(iter(values)), self.source, where, step)
                return
        self.walk.unresolved.append(f"{where}: {text}")


def _default_of(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.expr | None:
    """The default value of parameter ``name``, or ``None`` when it has none."""
    positional = [*fn.args.posonlyargs, *fn.args.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(fn.args.defaults))
    defaults += fn.args.defaults
    pairs = [*zip(positional, defaults, strict=True)]
    pairs += [*zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=True)]
    return next((d for a, d in pairs if a.arg == name), None)


def walk_sources() -> Walk:
    walk = Walk()
    for source, tree in TREES.items():
        paths = sorted(tree.rglob("*.py"))
        constants = _module_constants(paths)
        for path in paths:
            rel = path.relative_to(REPO).as_posix()
            _Collector(walk, source, rel, constants).visit(
                ast.parse(path.read_text(encoding="utf-8"))
            )
    return walk


@pytest.fixture(scope="module")
def walked() -> Walk:
    return walk_sources()


def test_every_code_site_is_resolved(walked: Walk) -> None:
    """A code built at runtime is either a relay or a family listed above; anything else is a
    new kind of site, and the catalog cannot know what it emits."""
    assert walked.unresolved == []
    assert set(RELAYS) - walked.relays_seen == set(), "a listed relay no longer exists"
    assert set(FAMILIES) - walked.families_seen == set(), "a listed family no longer exists"


def test_the_walk_finds_both_packages(walked: Walk) -> None:
    """The accessor is proved before the count is believed: codes known to be emitted by each
    package are found, so an empty catalog cannot match an empty walk."""
    for code, source in (
        ("path-forbidden", "gate"),
        ("hazard-unacknowledged", "gate"),
        ("witness-sorry", "gate"),
        ("unauthenticated", "api"),
        ("not-found", "api"),
        ("arguments-invalid", "api"),
    ):
        assert source in walked.sites.get(code, {}), code
    assert len(walked.sites) > 250


def test_catalog_keys_equal_the_emitted_codes(walked: Walk) -> None:
    """F13-T29: every code the gate and the service can emit has a row, and no row outlives
    its code."""
    emitted = set(walked.sites)
    catalogued = set(codes.CATALOG)
    assert sorted(emitted - catalogued) == [], "codes with no catalog row"
    assert sorted(catalogued - emitted) == [], "catalog rows no code emits"


def test_every_row_says_what_to_do() -> None:
    for code, row in codes.CATALOG.items():
        assert row.meaning.strip(), code
        assert row.remedy.strip(), code
        assert row.source in codes.SOURCES, code
        assert row.step is None or 1 <= row.step <= 9, code


def test_source_matches_where_the_code_is_emitted(walked: Walk) -> None:
    for code, row in codes.CATALOG.items():
        where = set(walked.sites.get(code, {}))
        expected = "both" if where == {"gate", "api"} else next(iter(where), None)
        assert row.source == expected, (code, row.source, sorted(where))


def test_step_matches_the_step_class_that_emits_it(walked: Walk) -> None:
    """A gate code emitted only inside one D-4 step's class names that step."""
    for code, row in codes.CATALOG.items():
        gate_sites = walked.sites.get(code, {}).get("gate", [])
        steps = {step for _, step in gate_sites}
        if gate_sites and len(steps) == 1 and None not in steps:
            assert row.step == next(iter(steps)), (code, row.step, steps)


def test_document_renders_every_row_and_filters_by_prefix() -> None:
    doc = json.loads(codes.render_json())
    assert doc["count"] == len(codes.CATALOG) == len(doc["codes"])
    assert [r["code"] for r in doc["codes"]] == sorted(codes.CATALOG)
    first = doc["codes"][0]
    assert set(first) == {"code", "source", "step", "meaning", "remedy"}
    witness = codes.document("witness-")
    assert witness["prefix"] == "witness-"
    assert witness["codes"]
    assert all(r["code"].startswith("witness-") for r in witness["codes"])
    assert codes.document("no-such-prefix-")["codes"] == []
