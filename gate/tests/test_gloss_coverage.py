"""F20-T14 / AC17: the coverage report (R20).

``opn-gate gloss coverage --graph <dir>`` lists every Lean file and every merged proof artifact of
every target, each with the gloss or explainer that covers it or the reason none does. A root's
statement is covered by its curated informal statement; a ``Context.lean`` by the statements it
restates; a gloss of text that has since changed leaves its file uncovered. The report is complete
exactly when every listed subject is covered, and the exit code says which.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import cli, glosses, products, schemas
from opn_gate import graph as graphmod
from opn_gate.signer import SshKeygenSigner

TARGET = "euclid-primes"
ROOT = "and-reassoc"  # take_in's root, with the fixture's Proof.lean
HOLE = "hole-a"
VARIANT = "variant-a"
MODULE = "Primes.lean"
ALTERNATE = "attempts/2026-10-01T00-00-00Z-bob-alternate.lean"
PARTIAL = "attempts/2026-10-01T00-00-00Z-carol.lean"


def target_dir(root: Path) -> Path:
    return root / "targets" / TARGET


def nodes(root: Path) -> Path:
    return target_dir(root) / "nodes"


def add_node(root: Path, name: str, *, origin: str, relation: str | None = None) -> None:
    shutil.copytree(nodes(root) / ROOT, nodes(root) / name)
    (nodes(root) / name / "Proof.lean").unlink()
    meta_path = nodes(root) / name / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta.update({"id": name, "origin": origin, "deps": []})
    if origin == "skeleton-hole":
        meta["schema"] = "meta/v3"
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    if relation is not None:
        (nodes(root) / name / "Relation.lean").write_text(relation, encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return curated_graph(tmp_path)


def curated_graph(tmp_path: Path) -> Path:
    """A curated target: its root (informal statement on record, a proof, an alternate and a
    partial assembly), a hole it depends on, a variant with a relation, and a definition.
    (F21-T7: the MCP's ``list_words_needed`` tests serve the same tree.)"""
    graph = copy_graph(tmp_path)
    take_in(graph, TARGET, defs={MODULE: "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"})
    shutil.rmtree(graph / "targets" / "propositional")  # one target, so complete can be reached
    add_node(graph, HOLE, origin="skeleton-hole")
    (nodes(graph) / HOLE / "Witness.lean").write_text("theorem witness : True := sorry\n")
    add_node(graph, VARIANT, origin="variant", relation="-- relation: related\n")
    meta_path = nodes(graph) / ROOT / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["deps"] = [HOLE]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    proof = (nodes(graph) / ROOT / "Proof.lean").read_text(encoding="utf-8")
    (nodes(graph) / ROOT / ALTERNATE).write_text(proof + "\n-- another\n", encoding="utf-8")
    (nodes(graph) / ROOT / PARTIAL).write_text("-- a partial assembly\n", encoding="utf-8")
    return graph


def put(directory: Path, doc: dict[str, Any], body: str) -> str:
    text = "---\n" + str(yaml.safe_dump(doc, sort_keys=False)) + "---\n" + body
    digest = schemas.content_hash(text.encode("utf-8"))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{digest}.md").write_text(text, encoding="utf-8")
    return digest


def gloss(root: Path, kind: str, node: str | None, module: str | None = None) -> str:
    parent = nodes(root) / node if node is not None else target_dir(root)
    file = (
        target_dir(root) / "defs" / str(module)
        if kind == "definition"
        else parent / glosses.KIND_FILES[kind]
    )
    doc = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {
            "kind": kind,
            "node": node,
            "module": module,
            "lean_hash": schemas.content_hash(file.read_bytes()),
        },
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    return put(parent / "gloss", doc, f"What the {kind} says.\n")


def explain(root: Path, node: str, rel: str) -> str:
    proof = schemas.content_hash((nodes(root) / node / rel).read_bytes())
    doc = {
        "schema": "explainer/v1",
        "target": TARGET,
        "node": node,
        "proof": proof,
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    return put(nodes(root) / node / "explainer", doc, "## The idea\nIt holds.\n")


def report(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any]]:
    code = cli.main(["gloss", "coverage", "--graph", str(root)])
    return code, json.loads(capsys.readouterr().out)


def rows(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in doc["subjects"]:
        out[row["file"]] = row
    return out


def test_coverage_lists_every_file_and_why(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC17: every Lean file and artifact is listed; the root's statement is covered by its
    informal statement, Context files by what they restate, a gloss of a since-changed witness
    leaves its file uncovered; incomplete until every subject is covered, then complete."""
    gloss(root, "witness", ROOT)
    gloss(root, "statement", HOLE)
    gloss(root, "witness", HOLE)  # of the stub; the witness is then filled
    (nodes(root) / HOLE / "Witness.lean").write_text("theorem witness : True := trivial\n")
    gloss(root, "relation", VARIANT)
    gloss(root, "definition", None, MODULE)
    explain(root, ROOT, "Proof.lean")
    explain(root, ROOT, PARTIAL)

    code, doc = report(root, capsys)
    assert code == 1 and doc["complete"] is False
    by_file = rows(doc)
    base = f"targets/{TARGET}"
    expected = {
        f"{base}/nodes/{n}/{f}"
        for n in (ROOT, HOLE, VARIANT)
        for f in ("Statement.lean", "Witness.lean", "Context.lean")
    } | {
        f"{base}/nodes/{VARIANT}/Relation.lean",
        f"{base}/nodes/{ROOT}/Proof.lean",
        f"{base}/nodes/{ROOT}/{ALTERNATE}",
        f"{base}/nodes/{ROOT}/{PARTIAL}",
        f"{base}/defs/{MODULE}",
    }
    assert set(by_file) == expected
    root_statement = by_file[f"{base}/nodes/{ROOT}/Statement.lean"]
    assert root_statement["covered"] is True and root_statement["by"] == {"informal": "target.yaml"}
    context = by_file[f"{base}/nodes/{ROOT}/Context.lean"]
    assert context["covered"] is True and context["by"] == {"restates": [HOLE]}
    stale = by_file[f"{base}/nodes/{HOLE}/Witness.lean"]
    assert stale["covered"] is False and stale["reason"] == "describes-earlier-text"
    assert by_file[f"{base}/nodes/{VARIANT}/Statement.lean"]["reason"] == "no-gloss"
    assert by_file[f"{base}/nodes/{ROOT}/{ALTERNATE}"]["reason"] == "no-explainer"
    assert by_file[f"{base}/nodes/{ROOT}/{PARTIAL}"]["covered"] is True
    assert by_file[f"{base}/defs/{MODULE}"]["covered"] is True
    uncovered = sorted(f for f, r in by_file.items() if not r["covered"])
    assert doc["counts"] == {"subjects": len(expected), "covered": len(expected) - len(uncovered)}

    # A Context that restates an uncovered statement is uncovered, and says which.
    meta_path = nodes(root) / VARIANT / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["deps"] = [HOLE]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    hole_statement_glosses = list((nodes(root) / HOLE / "gloss").iterdir())
    for path in hole_statement_glosses:
        if "statement" in path.read_text(encoding="utf-8").split("---")[1]:
            path.unlink()
    _, doc = report(root, capsys)
    context = rows(doc)[f"{base}/nodes/{VARIANT}/Context.lean"]
    assert context["covered"] is False and context["reason"] == "restates-uncovered"
    assert context["by"] == {"restates": [HOLE]}

    # Words for everything that lacks them: complete, exit 0.
    gloss(root, "statement", HOLE)
    gloss(root, "witness", HOLE)
    gloss(root, "statement", VARIANT)
    gloss(root, "witness", VARIANT)
    explain(root, ROOT, ALTERNATE)
    code, doc = report(root, capsys)
    assert [f for f, r in rows(doc).items() if not r["covered"]] == []
    assert code == 0 and doc["complete"] is True


def test_withdrawn_words_cover_nothing(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    digest = gloss(root, "statement", VARIANT)
    withdrawals = nodes(root) / VARIANT / "withdrawals"
    withdrawals.mkdir()
    (withdrawals / "2026-10-04T00-00-00Z-carol.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "withdrawal/v2",
                "withdraws": f"gloss/{digest}.md",
                "reason": "Wrong.",
                "author": "carol",
                "date": "2026-10-04",
            }
        ),
        encoding="utf-8",
    )
    _, doc = report(root, capsys)
    row = rows(doc)[f"targets/{TARGET}/nodes/{VARIANT}/Statement.lean"]
    assert row["covered"] is False and row["reason"] == "all-withdrawn"


def test_a_root_without_curated_words_needs_a_gloss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The propositional fixture has no target.yaml: its root's statement is covered by nothing
    until it has a gloss, and the report says why."""
    graph = copy_graph(tmp_path)
    _, doc = report(graph, capsys)
    row = rows(doc)["targets/propositional/nodes/and-swap-reassoc/Statement.lean"]
    assert row["covered"] is False and row["reason"] == "root-without-informal"


def test_a_missing_graph_is_a_usage_error(tmp_path: Path) -> None:
    assert cli.main(["gloss", "coverage", "--graph", str(tmp_path / "nope")]) == 2


# --- F21-T7 / AC7: words needed, from the product (R8; Q6) --------------------------------------


def _as_v1(doc: dict[str, Any]) -> dict[str, Any]:
    """The same product as an older gate renders it (``glosses/v1``): the live graph holds v1
    until its re-pin, so ``needed`` must read both."""
    old = json.loads(json.dumps(doc))
    old["schema"] = "glosses/v1"
    for subject in old["subjects"]:
        for chain in subject["chains"]:
            chain.pop("shown")
            chain.pop("pending")
            for version in chain["versions"]:
                version.pop("drafted_with")
                version.pop("sections")
                for sig in version["signatures"]:
                    sig.pop("sections", None)
    return schemas.validate(old, "glosses/v1")


def _needed_everywhere(graph: Path) -> list[dict[str, Any]]:
    """``glosses.needed`` over every target's rendered product, as the service and the site
    call it: the product, the root and what ``target.yaml`` says, nothing read from the tree."""
    out: list[dict[str, Any]] = []
    for target in sorted(p.name for p in (graph / "targets").iterdir() if p.is_dir()):
        tg = graphmod.load_target(graph, target)
        doc = schemas.validate(
            products.glosses_doc(tg, None, signer=SshKeygenSigner()), products.GLOSSES_SCHEMA
        )
        record = tg.path / "target.yaml"
        curated = glosses.curated_words(
            yaml.safe_load(record.read_text(encoding="utf-8")) if record.is_file() else None
        )
        rows = glosses.needed(doc, root=tg.root, curated=curated)
        assert glosses.needed(_as_v1(doc), root=tg.root, curated=curated) == rows
        out.extend(rows)
    return out


def _uncovered(graph: Path, capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    _, doc = report(graph, capsys)
    keep = ("target", "file", "kind", "node", "module", "reason")
    return [
        {k: r[k] for k in keep}
        for r in doc["subjects"]
        if not r["covered"] and r["kind"] != "context"
    ]


def _assert_parity(graph: Path, capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    rows = _needed_everywhere(graph)
    expected = _uncovered(graph, capsys)
    assert expected, "guard: the state has subjects without words"
    by_file = sorted(rows, key=lambda r: str(r["file"]))
    assert [{k: v for k, v in r.items() if k != "outline"} for r in by_file] == sorted(
        expected, key=lambda r: str(r["file"])
    )
    return rows


def test_needed_from_the_product_matches_coverage(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC7 (R8, Q6): computed from the committed ``glosses.json`` and ``target.yaml`` alone,
    the subjects lacking words are exactly ``gloss coverage``'s uncovered rows, Context files
    aside — with nothing written, part way (a gloss of since-changed text, a withdrawn one, an
    explained partial), and on a target with no curated words; a proof's row names its
    outline's path."""
    base = f"targets/{TARGET}"
    rows = _assert_parity(root, capsys)  # nothing written: everything but the root statement
    outline = {r["file"]: r["outline"] for r in rows}
    proof = schemas.content_hash((nodes(root) / ROOT / "Proof.lean").read_bytes())
    assert outline[f"{base}/nodes/{ROOT}/Proof.lean"] == f"{base}/outlines/{proof}.json"
    assert outline[f"{base}/nodes/{VARIANT}/Statement.lean"] is None

    gloss(root, "witness", ROOT)
    gloss(root, "witness", HOLE)  # of the stub; the witness is then filled
    (nodes(root) / HOLE / "Witness.lean").write_text("theorem witness : True := trivial\n")
    digest = gloss(root, "statement", VARIANT)
    withdrawals = nodes(root) / VARIANT / "withdrawals"
    withdrawals.mkdir()
    (withdrawals / "2026-10-04T00-00-00Z-carol.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "withdrawal/v2",
                "withdraws": f"gloss/{digest}.md",
                "reason": "Wrong.",
                "author": "carol",
                "date": "2026-10-04",
            }
        ),
        encoding="utf-8",
    )
    gloss(root, "definition", None, MODULE)
    explain(root, ROOT, PARTIAL)
    rows = _assert_parity(root, capsys)
    reasons = {r["file"]: r["reason"] for r in rows}
    assert reasons[f"{base}/nodes/{HOLE}/Witness.lean"] == "describes-earlier-text"
    assert reasons[f"{base}/nodes/{VARIANT}/Statement.lean"] == "all-withdrawn"
    assert reasons[f"{base}/nodes/{ROOT}/{ALTERNATE}"] == "no-explainer"
    assert f"{base}/nodes/{ROOT}/{PARTIAL}" not in reasons
    assert not any(str(r["file"]).endswith("Context.lean") for r in rows)

    # A target with no target.yaml: its root's statement needs words, and says why.
    plain = copy_graph(tmp_path / "plain")
    rows = _assert_parity(plain, capsys)
    assert "root-without-informal" in {r["reason"] for r in rows}
