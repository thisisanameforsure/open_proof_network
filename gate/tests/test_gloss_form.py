"""F20-T16 (Q21): whether a gloss opens with math, and the tool that audits a target's glosses.

The gloss contract is math first (guidance, not a gate rule): a gloss opens with the statement
in LaTeX, ``$$…$$`` or ``$…$``. ``glosses.opens_with_math`` reads a gloss body that way, using
the site's dollar rule (Pandoc's: an opening ``$`` has a non-space after it, a closing one a
non-space before it), and ``gate/tools/check_gloss_form.py`` lists every current gloss version of
a target from its ``glosses.json`` and names those that do not open with math. Run here against
the propositional fixture graph with versions written as a pull request adds them.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from harness import TARGET, copy_graph
from test_gloss_chains import gloss
from test_products import generate

from opn_gate import glosses

TOOL = Path(__file__).resolve().parents[1] / "tools" / "check_gloss_form.py"
MATH = "$$\n\\forall p\\, q : \\mathrm{Prop},\\ p \\land q \\to q \\land p\n$$\n\nSwapping sides.\n"
PROSE = "For any two propositions p and q, if both hold then both hold the other way round.\n"


@pytest.mark.parametrize(
    "text",
    [
        MATH,
        "$$\\forall n,\\ n + 0 = n$$",
        "  \n\n$$\nx\n$$\nthen words",
        "$n \\ge 1 \\to n! > 0$\n\nFor every n.",
        "$a = a$ holds.",
    ],
)
def test_opens_with_math(text: str) -> None:
    assert glosses.opens_with_math(text)


@pytest.mark.parametrize(
    "text",
    [
        PROSE,
        "",
        "   \n",
        "$$ $$ nothing in it",
        "$$\\forall n, unclosed",
        "$ x$ has a space after the opening dollar",
        "Costs $5 and $6.",
        "**$x$** opens with emphasis",
        "Words first, then $$x$$.",
    ],
)
def test_does_not_open_with_math(text: str) -> None:
    assert not glosses.opens_with_math(text)


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_gloss_form", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    """The propositional fixture with three gloss chains: one whose prose version was
    superseded by a math-first one, one prose only, one math only; products regenerated so
    ``glosses.json`` carries them."""
    root = copy_graph(tmp_path, publish=True)
    old, _ = gloss(root, PROSE, node="and-reassoc")
    gloss(root, MATH, supersedes=old, node="and-reassoc")
    gloss(root, PROSE, node="tutorial-and-swap")
    gloss(root, MATH, node="and-swap-reassoc")
    generate(root).write(root)
    return root


def test_the_tool_names_each_current_gloss_that_does_not_open_with_math(
    graph: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = load_tool().main(["--graph", str(graph), "--target", TARGET])
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["target"] == TARGET
    assert out["current"] == 3, "the superseded prose version is not current"
    [bad] = out["not_math_first"]
    assert bad["node"] == "tutorial-and-swap" and bad["kind"] == "statement"
    assert bad["path"].startswith("nodes/tutorial-and-swap/gloss/") and bad["path"].endswith(".md")
    assert bad["opens"].startswith("For any two propositions")


def test_the_tool_passes_a_target_whose_glosses_all_open_with_math(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_graph(tmp_path, publish=True)
    gloss(root, MATH, node="and-reassoc")
    generate(root).write(root)
    code = load_tool().main(["--graph", str(root), "--target", TARGET])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["current"] == 1 and out["not_math_first"] == []


def test_the_tool_refuses_a_target_without_glosses_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_graph(tmp_path, publish=True)
    code = load_tool().main(["--graph", str(root), "--target", "no-such-target"])
    assert code == 2
    assert "glosses.json" in capsys.readouterr().err
