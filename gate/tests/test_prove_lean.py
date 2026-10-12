"""F17-T6 / AC3, AC5 (lean tier): what ``opn-prove`` writes, checked by the real toolchain.

AC3: the exported problem file of every fixture node elaborates on its own, with its definitions
and Context inlined and nothing else to import beyond its library, and its only complaint is the
one ``sorry``. The on-ramp nodes are elaborated against the pinned Mathlib checkout, as the gate
does. AC5: every complete proof ``import`` accepts from the corpus is byte-identical to a fixture
``Proof.lean`` (the fast tier asserts that), so the gate's own lean-tier suite already runs it
through steps 1 to 8; here each is also elaborated inside the exported file, which is what a
prover's answer was checked against.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import ONRAMP_MATHLIB, PINNED_TOOLCHAIN, ROOT

from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean
CLIENT = ROOT / "gate" / "clients" / "prove" / "opn_prove.py"
GRAPHS = ROOT / "gate" / "tests" / "fixtures" / "graphs"
CORPUS = ROOT / "api" / "tests" / "fixtures" / "prover-answers"


def _client() -> Any:
    spec = importlib.util.spec_from_file_location("opn_prove_lean", CLIENT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prove = _client()


#: The graphs whose statements are meant to elaborate. The adversarial graph's nodes are wrong on
#: purpose (each is some step's refusal), so they are held to parity in the fast tier only.
REAL_GRAPHS = ("propositional", "onramp")


def nodes() -> list[tuple[str, str, str]]:
    return [
        (graph, s.parts[-4], s.parts[-2])
        for graph in REAL_GRAPHS
        for s in sorted((GRAPHS / graph).glob("targets/*/nodes/*/Statement.lean"))
    ]


class Toolchains:
    """The resolved toolchain for a graph's Mathlib pin, resolved on first use: a node that needs
    no Mathlib must not need the Mathlib checkout to exist (an eager fixture made it)."""

    def __init__(self, real: LocalToolchain) -> None:
        self.real = real
        self.cache: dict[str | None, ResolvedToolchain] = {}

    def __getitem__(self, mathlib_sha: str | None) -> ResolvedToolchain:
        if mathlib_sha not in self.cache:
            assert mathlib_sha in (None, ONRAMP_MATHLIB), mathlib_sha
            self.cache[mathlib_sha] = self.real.resolve(
                PINNED_TOOLCHAIN, install=False, mathlib_sha=mathlib_sha
            )
        return self.cache[mathlib_sha]


@pytest.fixture(scope="module")
def toolchains(real_toolchain: LocalToolchain) -> Toolchains:
    return Toolchains(real_toolchain)


def elaborate(
    real: LocalToolchain, tc: ResolvedToolchain, text: str, tmp: Path
) -> tuple[bool, list[str], list[str]]:
    src = tmp / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "Problem.lean").write_text(text, encoding="utf-8")
    result = real.elaborate(tc, src / "Problem.lean", "Problem", tmp / "out", root=src,
                            timeout_s=600)  # fmt: skip
    errors = [m.text for m in result.errors]
    warnings = [m.text for m in result.messages if m.severity == "warning"]
    return result.ok, errors, warnings


def sorry_bodies(text: str) -> int:
    """The statement's own ``sorry``, plus one per dependency the inlined Context restates."""
    return len(list(prove.SORRY_BODY_RE.finditer(text)))


@pytest.mark.parametrize("where", [f"{g}/{t}/{n}" for g, t, n in nodes()])
def test_elaborates(
    where: str,
    real_toolchain: LocalToolchain,
    toolchains: Toolchains,
    tmp_path: Path,
) -> None:
    graph, target, node = where.split("/")
    found = prove.find_node(GRAPHS / graph, node, target)
    tc = toolchains[found.gate_spec().get("mathlib_sha")]
    problem = prove.export(found)
    ok, errors, warnings = elaborate(real_toolchain, tc, problem, tmp_path)
    assert ok and not errors, errors
    assert sum("sorry" in w for w in warnings) == sorry_bodies(problem), warnings


@pytest.mark.parametrize(
    "case",
    sorted(
        c
        for c, row in json.loads((CORPUS / "index.json").read_text()).items()
        if row["expect"] == "proof"
    ),
)
def test_accepted_answers_elaborate(
    case: str,
    real_toolchain: LocalToolchain,
    toolchains: Toolchains,
    tmp_path: Path,
) -> None:
    """The proof ``import`` produced, placed back into the exported problem file, elaborates with
    no error and no ``sorry``: what the prover was asked is what the gate will be shown."""
    row = json.loads((CORPUS / "index.json").read_text())[case]
    graph, target, node = {
        "tutorial": ("propositional", "propositional", "tutorial-and-swap"),
        "fact-pos": ("onramp", "euclid-primes", "fact-pos"),
    }[row["node"]]
    found = prove.find_node(GRAPHS / graph, node, target)
    imported = prove.import_answer(found, (CORPUS / f"{case}.txt").read_bytes().decode("utf-8"))
    statement = prove.parse_statement(found.read("Statement.lean"))
    body = imported.text[len(statement.prefix) :]
    problem = prove.export(found)
    last = list(prove.SORRY_BODY_RE.finditer(problem))[-1]  # the statement closes the file
    filled = problem[: last.start() + 2] + body
    assert filled.endswith(imported.text[len(statement.prefix) :])
    tc = toolchains[found.gate_spec().get("mathlib_sha")]
    ok, errors, warnings = elaborate(real_toolchain, tc, filled, tmp_path)
    assert ok and not errors, errors
    assert sum("sorry" in w for w in warnings) == sorry_bodies(filled), warnings
