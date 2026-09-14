"""Finding 3 (the 2026-09-13 live contribution): the guide's skeleton shape is refused by the gate.

``gate/agents/AGENTS.md`` ("Skeletonization") shows the ``-- annex: <sha256>`` citation between
the imports and the theorem. A partial's header and signature must be the statement's, textually,
like a proof's (F00-R19; ``steps/paths_step.py`` applies ``check_proof_is_statement`` to the
assembly at step 2), so a file in the guide's shape diverges from ``Statement.lean`` at line 2 and
answers ``proof-not-statement`` — which is what the tester got, and what cost it a precheck. The
citation belongs inside the body, after ``by``, where ``annex_citation`` still finds it.

Two tests: the guide's block, header substituted for a real statement's, passes step 2's textual
check (red until F10-T6 moves the citation into the body); and the same skeleton with the
citation on the first line after ``by`` passes today, so the shape the fix must document is
pinned before the guide changes. Docs are tests (F10-Q3): the first test reads the guide, so
the fix is the guide's own edit, not a change to what the gate accepts.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from harness import GRAPH, TARGET

from opn_gate import layout, paths, postmerge

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"
NODE = "and-swap-reassoc"  # a statement with an import line, like the guide's example
DIGEST = "d0c8e2f9" * 8  # a 64-hex hash, the shape the citation must carry (D-31 v3.12)
CITATION = "-- annex:"

REASON = (
    "finding 3 (F10-R2, F00-R19, D-31): the guide's skeleton block puts `-- annex:` between the "
    "imports and the theorem, so step 2's textual check answers proof-not-statement at line 2; "
    "fix: F10-T6 moves the citation into the body after `by` (Mike, 2026-09-13)"
)


def _load_walkthrough() -> ModuleType:
    """``gate/tools/walkthrough.py`` is a script beside the other tools, not a package member;
    its block parser is the one the guide's executed blocks already go through."""
    path = ROOT / "gate" / "tools" / "walkthrough.py"
    spec = importlib.util.spec_from_file_location("walkthrough", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def guide_skeleton_block() -> str:
    """The one fenced block under "Skeletonization" that shows a cited skeleton."""
    walkthrough = _load_walkthrough()
    markdown = GUIDE.read_text(encoding="utf-8")
    start = markdown.index("## Skeletonization")
    end = markdown.index("\n## ", start + 1)
    section = markdown[start:end]
    found = [b for b in walkthrough.blocks(section) if CITATION in b.text and "sorry" in b.text]
    assert len(found) == 1, [b.line for b in found]
    return str(found[0].text)


def statement() -> layout.Statement:
    loaded = layout.load_node(layout.graph_nodes_dir(GRAPH, TARGET) / NODE, TARGET)
    assert isinstance(loaded, layout.Node)
    return loaded.statement


def split_guide_block(block: str) -> tuple[str, list[str]]:
    """The citation line the guide shows (its placeholder replaced by a real hash) and the
    body lines after the theorem's signature; imports and signature are the statement's."""
    lines = block.splitlines()
    theorem_at = next(i for i, line in enumerate(lines) if line.startswith("theorem "))
    citation = next(line for line in lines[:theorem_at] if line.startswith(CITATION))
    citation = f"{CITATION} {DIGEST}"  # the placeholder is `<sha256 of …>`, not a hash
    body = lines[theorem_at + 1 :]
    assert any("sorry" in line for line in body) and not any(
        line.startswith(CITATION) for line in body
    ), "the guide's citation sits outside the body today"
    return citation, body


def as_guide_shape(stmt: layout.Statement, citation: str, body: list[str]) -> str:
    """The guide's layout over a real statement: imports, the citation, a blank line, then the
    theorem's own signature and the guide's body."""
    header, _, signature = stmt.prefix.rpartition("theorem ")
    return (
        header.rstrip("\n")
        + "\n"
        + citation
        + "\n\n"
        + "theorem "
        + signature
        + " by\n"
        + "\n".join(body)
        + "\n"
    )


def as_fixed_shape(stmt: layout.Statement, citation: str, body: list[str]) -> str:
    """The same skeleton with the citation as the first line after ``by``."""
    return stmt.prefix + " by\n  " + citation + "\n" + "\n".join(body) + "\n"


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_guides_skeleton_shape_passes_step_2() -> None:
    stmt = statement()
    citation, body = split_guide_block(guide_skeleton_block())
    text = as_guide_shape(stmt, citation, body)
    problem = paths.check_proof_is_statement(stmt, text)
    assert problem is None, problem.as_dict()
    assert postmerge.annex_citation(text) == DIGEST


def test_the_citation_after_by_passes_step_2_today() -> None:
    """The target shape for F10-T6, pinned: header and signature are the statement's byte for
    byte, the citation is the body's first line, and the gate still re-derives it."""
    stmt = statement()
    citation, body = split_guide_block(guide_skeleton_block())
    text = as_fixed_shape(stmt, citation, body)
    assert text.startswith(stmt.prefix)
    assert paths.check_proof_is_statement(stmt, text) is None
    assert postmerge.annex_citation(text) == DIGEST
    assert postmerge.child_origin(text) == postmerge.ORIGIN_SKELETON
