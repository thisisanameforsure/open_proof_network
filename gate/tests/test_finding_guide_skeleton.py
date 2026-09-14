"""Finding 3 (the 2026-09-13 live contribution): the guide's skeleton shape is refused by the gate.

``gate/agents/AGENTS.md`` ("Skeletonization") shows the ``-- annex: <sha256>`` citation between
the imports and the theorem. A partial's header and signature must be the statement's, textually,
like a proof's (F00-R19; ``steps/paths_step.py`` applies ``check_proof_is_statement`` to the
assembly at step 2), so a file in the guide's shape diverges from ``Statement.lean`` at line 2 and
answers ``proof-not-statement`` — which is what the tester got, and what cost it a precheck. The
citation belongs inside the body, after ``by``, where ``annex_citation`` still finds it.

Two tests: the guide's block, laid over a real statement exactly as the guide lays it out
(anything it puts between the imports and the theorem kept there), passes step 2's textual check
— red until F10-T6 moved the citation into the body; and the guide's holes with the citation on
the first line after ``by`` pass, pinning the shape the guide documents. Docs are tests (F10-Q3):
the first test reads the guide, so the fix is the guide's own edit, not a change to what the
gate accepts.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from harness import GRAPH, TARGET

from opn_gate import layout, paths, postmerge

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"
NODE = "and-swap-reassoc"  # a statement with an import line, like the guide's example
DIGEST = "d0c8e2f9" * 8  # a 64-hex hash, the shape the citation must carry (D-31 v3.12)
CITATION = "-- annex:"


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


def with_real_hash(line: str) -> str:
    """The citation's placeholder is `<sha256 of …>`, not a hash; keep the line's indentation."""
    stripped = line.lstrip()
    if not stripped.startswith(CITATION):
        return line
    return line[: len(line) - len(stripped)] + f"{CITATION} {DIGEST}"


def split_guide_block(block: str) -> tuple[list[str], list[str]]:
    """What the guide puts between its imports and the theorem (anything but an import or a
    blank line), and the body lines after the theorem's signature — the citation's placeholder
    replaced by a real hash wherever the guide puts it. Imports and signature are the
    statement's."""
    lines = [with_real_hash(line) for line in block.splitlines()]
    theorem_at = next(i for i, line in enumerate(lines) if line.startswith("theorem "))
    between = [
        line for line in lines[:theorem_at] if line.strip() and not line.startswith("import ")
    ]
    body = lines[theorem_at + 1 :]
    assert any("sorry" in line for line in body), "the guide's skeleton has no hole"
    assert sum(CITATION in line for line in lines) == 1, "the guide shows one citation"
    return between, body


def as_guide_shape(stmt: layout.Statement, between: list[str], body: list[str]) -> str:
    """The guide's layout over a real statement: imports, whatever the guide puts before the
    theorem followed by a blank line, then the theorem's own signature and the guide's body."""
    header, _, signature = stmt.prefix.rpartition("theorem ")
    if between:
        header = header.rstrip("\n") + "\n" + "\n".join(between) + "\n\n"
    return header + "theorem " + signature + " by\n" + "\n".join(body) + "\n"


def as_fixed_shape(stmt: layout.Statement, body: list[str]) -> str:
    """The guide's holes with the citation as the first line after ``by``."""
    holes = [line for line in body if CITATION not in line]
    return stmt.prefix + " by\n  " + f"{CITATION} {DIGEST}" + "\n" + "\n".join(holes) + "\n"


def test_the_guides_skeleton_shape_passes_step_2() -> None:
    stmt = statement()
    between, body = split_guide_block(guide_skeleton_block())
    text = as_guide_shape(stmt, between, body)
    problem = paths.check_proof_is_statement(stmt, text)
    assert problem is None, problem.as_dict()
    assert postmerge.annex_citation(text) == DIGEST


def test_the_citation_after_by_passes_step_2_today() -> None:
    """The target shape for F10-T6, pinned: header and signature are the statement's byte for
    byte, the citation is the body's first line, and the gate still re-derives it."""
    stmt = statement()
    _, body = split_guide_block(guide_skeleton_block())
    text = as_fixed_shape(stmt, body)
    assert text.startswith(stmt.prefix)
    assert paths.check_proof_is_statement(stmt, text) is None
    assert postmerge.annex_citation(text) == DIGEST
    assert postmerge.child_origin(text) == postmerge.ORIGIN_SKELETON
