"""F14-T6: second formalizations and the equivalence against one (R7, R8; AC7, AC8).

A formalization is evidence about the root, held outside ``nodes/``: the gate admits it as a
curator's addition when the pair is sound, the products never make it a node or a frontier entry,
and ``qa equivalence`` runs both implications against it and records what it compared against.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import copy_graph
from scripted import ScriptedToolchain
from test_qa import WHEN, equivalence_context

from opn_gate import cli, formalizations, layout, modes, products, qa, schemas
from opn_gate.paths import Change, Status
from opn_gate.qa import QaError

TARGET = "propositional"
NAME = "alt"
CURATORS = modes.Curators((("curator", "curator"),))


def write_formalization(
    root: Path,
    name: str = NAME,
    *,
    text: str | None = None,
    **record: Any,
) -> tuple[str, str]:
    """A formalization of the propositional root: ``and-reassoc``'s statement under its own
    theorem name, with a record that agrees with it unless ``record`` says otherwise. Returns the
    two paths as a diff would list them."""
    base = (root / "targets" / TARGET / "nodes" / "and-reassoc" / "Statement.lean").read_text()
    body = (
        text
        if text is not None
        else re.sub(r"theorem\s+\S+", "theorem Opn.alt_formal", base, count=1)
    )
    parsed = layout.parse_statement(body)
    declaration = parsed.decl_name if isinstance(parsed, layout.Statement) else "Opn.alt_formal"
    doc = samples.formalization(
        name=name,
        declaration=declaration,
        statement_hash=schemas.content_hash(body.encode("utf-8")),
    )
    doc.update(record)
    directory = root / "targets" / TARGET / formalizations.FORMALIZATIONS_DIR / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / formalizations.STATEMENT_FILE).write_text(body, encoding="utf-8")
    (directory / formalizations.RECORD_FILE).write_text(yaml.safe_dump(doc), encoding="utf-8")
    prefix = f"targets/{TARGET}/formalizations/{name}"
    return f"{prefix}/formalization.yaml", f"{prefix}/Statement.lean"


def classify(paths_: tuple[str, ...], status: Status = "A") -> modes.Classification:
    return modes.classify([Change(status, p) for p in paths_], author="curator", curators=CURATORS)


def codes(root: Path, c: modes.Classification) -> list[str]:
    return [d.code for d in (c.problems or ())] + [d.code for d in modes.check(root, c)]


# --- AC7: the gate admits a sound pair as a curator's addition ------------------------------------


def test_a_curator_adds_a_formalization(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    pair = write_formalization(root)
    c = classify(pair)
    assert c.mode == "curator", c.as_dict()
    assert {loc.role for loc in c.located} == {"formalization", "formalization-statement"}
    assert modes.check(root, c) == []


def test_a_formalization_is_never_a_node(tmp_path: Path) -> None:
    """R7: the products carry no node, no frontier entry and no claim for it; the index lists it
    with no equivalence yet."""
    root = copy_graph(tmp_path, publish=True)
    before = products.generate(root, rendered_from="5" * 40, commit_time=WHEN)
    write_formalization(root)
    after = products.generate(root, rendered_from="5" * 40, commit_time=WHEN)
    graph_path = Path(f"targets/{TARGET}/graph.json")
    assert after.files[graph_path] == before.files[graph_path]
    assert after.files[Path("frontier.json")] == before.files[Path("frontier.json")]
    index = json.loads(after.files[Path("targets/index.json")])
    row = next(t for t in index["targets"] if t["target_id"] == TARGET)
    [listed] = row["formalizations"]
    assert listed["name"] == NAME and listed["equivalence"] is None and listed["exhibit"] is None
    assert schemas.violations(index, products.INDEX_SCHEMA) == []


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param(
            {"text": "theorem Opn.a : True := by\n  sorry\ntheorem Opn.b : True := by\n  sorry\n"},
            "formalization-shape",
            id="two-theorems",
        ),
        pytest.param({"statement_hash": "0" * 64}, "formalization-hash", id="hash"),
        pytest.param(
            {"declaration": "Opn.somethingElse"}, "formalization-declaration", id="declaration"
        ),
        pytest.param(
            {"text": "import Nodes.«and-reassoc».Context\ntheorem Opn.x : True := by\n  sorry\n"},
            "import-forbidden",
            id="import",
        ),
    ],
)
def test_an_unsound_pair_is_refused_by_name(
    tmp_path: Path, kwargs: dict[str, Any], expected: str
) -> None:
    root = copy_graph(tmp_path, publish=True)
    pair = write_formalization(root, **kwargs)
    assert expected in codes(root, classify(pair))


def test_a_formalization_named_like_a_node_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    pair = write_formalization(root, "and-reassoc")
    assert "formalization-name" in codes(root, classify(pair))


def test_a_statement_without_its_record_is_incomplete(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    record, statement = write_formalization(root)
    (root / record).unlink()
    assert codes(root, classify((statement,))) == ["formalization-incomplete"]


def test_a_formalization_is_not_modified(tmp_path: Path) -> None:
    """R7: added once; a pull request that modifies one is refused before any check runs — a
    formalization is not a modifiable path (``path-forbidden``)."""
    root = copy_graph(tmp_path, publish=True)
    pair = write_formalization(root)
    c = classify(pair, status="M")
    assert c.mode is None, c.as_dict()
    assert {d.code for d in c.problems} <= {"path-forbidden", "mode-mixed"} and c.problems


# --- AC8: the equivalence against a formalization ---------------------------------------------


def test_equivalence_against_a_formalization(tmp_path: Path) -> None:
    fake = ScriptedToolchain()
    target, ctx = equivalence_context(tmp_path, fake)
    write_formalization(ctx.graph_root)
    found = formalizations.get(target, NAME)
    assert found is not None
    run = qa.equivalence(ctx, NAME, date=WHEN, attempt_budget_s=30, formalization=True)
    assert run.ok and run.row.verdict == "pass" and run.row.exhibit is not None
    assert run.row.against == {
        "kind": "formalization",
        "ref": NAME,
        "statement_hash": found.statement_hash,
    }
    record = run.record
    assert record is not None
    doc = yaml.safe_load((target.parents[1] / record).read_text(encoding="utf-8"))
    assert doc["schema"] == "qa/v2" and doc["checks"][0]["against"]["ref"] == NAME
    assert formalizations.summary(target) == [
        {
            "name": NAME,
            "statement_hash": found.statement_hash,
            "equivalence": "pass",
            "exhibit": run.row.exhibit,
        }
    ]


def test_a_failed_equivalence_against_a_formalization_is_inconclusive(tmp_path: Path) -> None:
    target, ctx = equivalence_context(
        tmp_path, ScriptedToolchain(failing_modules={"OpnQa.EquivBackward"})
    )
    write_formalization(ctx.graph_root)
    run = qa.equivalence(ctx, NAME, date=WHEN, attempt_budget_s=30)  # found without the flag
    assert run.row.verdict == "inconclusive" and run.row.exhibit is None
    assert run.row.against is not None and run.row.against["kind"] == "formalization"
    assert formalizations.summary(target)[0]["equivalence"] == "inconclusive"


def test_a_node_comparison_names_the_node(tmp_path: Path) -> None:
    _target, ctx = equivalence_context(tmp_path, ScriptedToolchain())
    run = qa.equivalence(ctx, "and-reassoc", date=WHEN, attempt_budget_s=30)
    assert run.row.against is not None and run.row.against["kind"] == "node"
    assert run.row.against["ref"] == "and-reassoc"


def test_the_flag_refuses_a_node_name_and_an_unsound_formalization(tmp_path: Path) -> None:
    _target, ctx = equivalence_context(tmp_path, ScriptedToolchain())
    with pytest.raises(QaError, match="not a formalization"):
        qa.equivalence(ctx, "and-reassoc", date=WHEN, attempt_budget_s=30, formalization=True)
    write_formalization(ctx.graph_root, statement_hash="0" * 64)
    with pytest.raises(QaError, match="not a sound formalization"):
        qa.equivalence(ctx, NAME, date=WHEN, attempt_budget_s=30)


def test_the_command_takes_the_flag() -> None:
    args = cli.build_parser().parse_args(
        ["qa", "equivalence", TARGET, "root", NAME, "--graph", ".", "--formalization"]
    )
    assert args.formalization is True and args.other == NAME
