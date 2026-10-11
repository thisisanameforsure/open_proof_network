"""F25-T7 / AC7 (F25-R8, R9, R10; D-10 v3.37): the export of one resolved target as a wrapper
repository in Palomar's shape, on the propositional fixture.

The fixture's root ``and-swap-reassoc`` declares ``tutorial-and-swap`` and ``and-reassoc`` and
its proof names both; the tests prove the root with an attestation whose footprint is the
closure under test, write a curated ``target.yaml`` with a classification and a root ``LICENSE``,
and read the export back file by file.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph
from test_products import MERGE, ROOT_NODE, attest, nodes_dir

from opn_gate import intake, palomar, paths, schemas
from opn_gate import palomar_export as ex

A, B = "tutorial-and-swap", "and-reassoc"
GRAPH_COMMIT = "c" * 40
PKG = "OpnPropositional"


def proof_hash(root: Path, node_id: str) -> str:
    return schemas.content_hash((nodes_dir(root) / node_id / "Proof.lean").read_bytes())


def curate(
    root: Path, *, classification: dict[str, Any] | None = None, licence: bool = True
) -> None:
    doc = samples.target_record(
        schema="target/v3", id=TARGET, title="Propositional swap and reassociation"
    )
    doc["informal"] = (
        "Conjunction can be reassociated and swapped: $(p \\wedge q) \\wedge r \\to r \\wedge "
        "(q \\wedge p)$."
    )
    if classification is not None:
        doc["classification"] = classification
    intake.record_path(root / "targets" / TARGET).write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    if licence:
        (root / "LICENSE").write_text(palomar.licence_text(), encoding="utf-8")


def prove_all(root: Path, *, footprint: list[str] | None = None, **root_kw: Any) -> None:
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint={"nodes": []})
    attest(
        root,
        ROOT_NODE,
        n=3,
        artifact_hash=proof_hash(root, ROOT_NODE),
        footprint={"nodes": footprint if footprint is not None else [A, B]},
        **root_kw,
    )


def ready(tmp_path: Path, **kw: Any) -> Path:
    root = copy_graph(tmp_path, publish=True)
    curate(root, classification=samples.classification())
    prove_all(root, **kw)
    return root


def run(root: Path, **kw: Any) -> ex.Export:
    return ex.export(root, TARGET, graph_commit=GRAPH_COMMIT, **kw)


# --- names -------------------------------------------------------------------------------------


def test_names_are_lean_identifiers_and_injective() -> None:
    assert ex.package_name("erdos-1050") == "OpnErdos1050"
    assert ex.package_name("euclid-primes") == "OpnEuclidPrimes"
    ids = ["erdos-1050", "erdos-1050--h1-v2", "erdos-1050--h1-v2--h3", "euclid-primes", "a-b", "ab"]
    modules = [ex.node_module(PKG, i) for i in ids]
    assert len(set(modules)) == len(ids)
    assert ex.node_module(PKG, "erdos-1050--h1-v2") == f"{PKG}.Nodes.erdos_1050__h1_v2"
    assert ex.node_file(PKG, "erdos-1050--h1-v2") == f"{PKG}/Nodes/erdos_1050__h1_v2.lean"


# --- the export of the fixture ---------------------------------------------------------------


def test_the_export_writes_the_registrys_shape(tmp_path: Path) -> None:
    root = ready(tmp_path)
    out = run(root)
    files = out.files
    expected = {
        "LICENSE", "README.md", "lakefile.toml", "lake-manifest.json", "lean-toolchain",
        "Challenge.lean", "Solution.lean", f"{PKG}.lean", f"{PKG}/Nodes/tutorial_and_swap.lean",
        f"{PKG}/Nodes/and_reassoc.lean", "comparator.json", "formalization.yaml",
        ex.PREFLIGHT_PATH, ex.EXPORT_RECORD,
    }  # fmt: skip
    assert set(files) == expected
    assert out.closure.order in {(B, A, ROOT_NODE), (A, B, ROOT_NODE)}
    assert out.closure.pruned == {} and out.closure.kept_by_text == {}
    assert files["lean-toolchain"] == b"leanprover/lean4:v4.33.1\n"
    assert b"mathlib" not in files["lakefile.toml"]  # the fixture pins no Mathlib (Lean core)
    assert json.loads(files["lake-manifest.json"])["packages"] == []
    assert (
        files["LICENSE"].decode().startswith(" " * 32 + "Apache License")
        or b"Apache License" in files["LICENSE"]
    )
    out.write(tmp_path / "wrapper")
    assert (tmp_path / "wrapper" / ex.PREFLIGHT_PATH).is_file()


def test_the_challenge_is_the_statement_with_a_module_header(tmp_path: Path) -> None:
    root = ready(tmp_path)
    files = run(root).files
    challenge = files["Challenge.lean"].decode()
    statement = (nodes_dir(root) / ROOT_NODE / "Statement.lean").read_text()
    assert challenge.startswith("module\n\n")
    assert "import Nodes" not in challenge, "the own-Context import is dropped from the Challenge"
    assert "public import" not in challenge, "a core-only statement imports nothing"
    assert ex.SECTION + "\n\n" in challenge
    body = challenge.split(ex.SECTION + "\n\n", 1)[1]
    assert body == statement.split("Context\n\n", 1)[1]  # the theorem text, byte for byte
    assert palomar.measure(files["Challenge.lean"]).lines < 20


def test_the_solution_is_the_proof_importing_its_retained_deps(tmp_path: Path) -> None:
    root = ready(tmp_path)
    files = run(root).files
    solution = files["Solution.lean"].decode()
    proof = (nodes_dir(root) / ROOT_NODE / "Proof.lean").read_text()
    assert solution.startswith("module\n\n")
    assert f"public import {PKG}.Nodes.tutorial_and_swap\n" in solution
    assert f"public import {PKG}.Nodes.and_reassoc\n" in solution
    assert "Nodes.«" not in solution
    body = solution.split(ex.SECTION + "\n\n", 1)[1]
    assert body == proof.split("Context\n\n", 1)[1]
    dep = files[f"{PKG}/Nodes/and_reassoc.lean"].decode()
    assert dep.startswith("module\n\n") and ex.SECTION in dep
    assert dep.split(ex.SECTION + "\n\n", 1)[1] == (nodes_dir(root) / B / "Proof.lean").read_text()
    lib = files[f"{PKG}.lean"].decode()
    wanted = {
        f"public import {PKG}.Nodes.and_reassoc",
        f"public import {PKG}.Nodes.tutorial_and_swap",
    }
    assert (
        lib.startswith("module\n\n")
        and set(ln for ln in lib.splitlines() if ln and ln != "module") == wanted
    )


def test_comparator_names_the_root_theorem_and_the_allowlist(tmp_path: Path) -> None:
    files = run(ready(tmp_path)).files
    doc = palomar.read_comparator(files["comparator.json"].decode())
    assert doc.theorem_names == ("OpnProp.and_swap_reassoc",)
    assert doc.definition_names == ()
    assert set(doc.permitted_axioms) == {"propext", "Classical.choice", "Quot.sound"}
    assert doc.challenge_module == "Challenge" and doc.solution_module == "Solution"


def test_the_record_carries_every_hash_and_the_closure(tmp_path: Path) -> None:
    root = ready(tmp_path)
    out = run(root)
    record = json.loads(out.files[ex.EXPORT_RECORD])
    assert record["graph_commit"] == GRAPH_COMMIT and record["root"] == ROOT_NODE
    assert record["declaration"] == "OpnProp.and_swap_reassoc"
    assert record["attestation"] == "000003.json" and record["merge_commit"] == MERGE
    assert set(record["closure"]) == {A, B, ROOT_NODE}
    assert record["licence"] == {"spdx": "Apache-2.0", "source": "graph"}
    assert record["hashes_in"]["Solution.lean"] == proof_hash(root, ROOT_NODE)
    assert record["hashes_in"]["Challenge.lean"] == schemas.content_hash(
        (nodes_dir(root) / ROOT_NODE / "Statement.lean").read_bytes()
    )
    for rel, digest in record["hashes_out"].items():
        assert hashlib.sha256(out.files[rel]).hexdigest() == digest, rel
    assert ex.EXPORT_RECORD not in record["hashes_out"]
    assert record["module_system"] is True


def test_the_preflight_workflow_is_pinned(tmp_path: Path) -> None:
    text = run(ready(tmp_path)).files[ex.PREFLIGHT_PATH].decode()
    sha = palomar.pins()["repositories"]["PalomarRegistry/PalomarSubmission"]["commit"]
    assert f"submission.yml@{sha}" in text and f'pipeline_commit: "{sha}"' in text
    assert not re.search(r"\{\{[A-Z_]+\}\}", text) and f"opn-{TARGET}-" in text
    assert "mode: full" in text and "palomar-standard-v1" in text


# --- formalization.yaml and README from the record ------------------------------------------


def ledger_file(root: Path, identity: str, *, node: str, line: str = "proof") -> None:
    doc = {
        "schema": "ledger/v2",
        "identity": identity,
        "entries": [
            {
                "line": line,
                "target": TARGET,
                "node": node,
                "artifact": "Proof.lean",
                "merge_commit": MERGE,
                "date": "2026-09-09T12:00:00Z",
                "tooling": "claude-fable-5-1 Claude Code",
                "status": "active",
                "automation": None,
            }
        ],
    }  # fmt: skip
    (root / "ledger").mkdir(exist_ok=True)
    (root / "ledger" / f"{identity}.json").write_bytes(schemas.canonical_json(doc))


def test_formalization_yaml_validates_and_names_the_ledgers_authors(tmp_path: Path) -> None:
    root = ready(tmp_path)
    ledger_file(root, "prover-one", node=ROOT_NODE)
    ledger_file(root, "prover-two", node=B)
    ledger_file(root, "bystander", node="some-other-node")
    (root / "names").mkdir()
    (root / "names" / "prover-two.yaml").write_text(
        yaml.safe_dump(samples.display_name(pseudonym="prover-two", name="Two, A.")),
        encoding="utf-8",
    )
    doc = palomar.read_formalization(run(root).files["formalization.yaml"].decode())
    assert doc.version == "v0.4"
    assert doc.authors == ["prover-one", "Two, A."]  # the display name replaces the pseudonym
    assert doc.project["responsible_maintainers"] == ["curator"]
    assert doc.project["license"] == "Apache-2.0"
    assert doc.sections["classification"] == {"arxiv": ["math.NT"], "msc2020": ["11A41"]}
    assert (
        doc.sections["status"]["sorry_count"] == 0
        and doc.sections["status"]["main_results"][0]["declaration"] == "OpnProp.and_swap_reassoc"
    )
    assert doc.sections["repository"] == {"role": "substantive-development"}
    assert doc.review_status in ("agent-reviewed", "author-verified")
    assert "mechanical-only" in doc.sections["fidelity"]["divergences"]
    text = run(root).files["formalization.yaml"].decode()
    assert "&id" not in text and "*id" not in text  # no YAML anchors or aliases
    # the inherited statement is a related formalization at the upstream file, not the problem page
    root2 = ready(tmp_path / "fc")
    rec = yaml.safe_load(intake.record_path(root2 / "targets" / TARGET).read_text())
    rec["source"] = {
        "kind": "formal-conjectures",
        "ref": "FormalConjectures/ErdosProblems/1.lean",
        "url": "https://www.erdosproblems.com/1",
    }
    rec["provenance"] = {  # a target/v2 record: the path lives in source.ref, not here
        "statement_source": "formal-conjectures",
        "author": "The Formal Conjectures Authors",
        "adversarially_reviewed": False,
        "upstream_commit": "c" * 40,
    }
    intake.record_path(root2 / "targets" / TARGET).write_text(yaml.safe_dump(rec, sort_keys=False))
    fc = palomar.read_formalization(run(root2).files["formalization.yaml"].decode())
    [related] = fc.sections["related_formalizations"]
    assert (
        related["id"]
        == "https://github.com/google-deepmind/formal-conjectures/blob/"
        + "c" * 40
        + "/FormalConjectures/ErdosProblems/1.lean"
    )
    assert related["relationship"] == "builds-on"
    # a formalization-track record is a known result: independently-proves, never original-proof
    rels = [s.get("relationship") for s in doc.sections["sources"]]
    assert "independently-proves" in rels and "other" not in rels


def test_old_merges_map_their_string_honestly(tmp_path: Path) -> None:
    root = ready(
        tmp_path,
        model_and_tooling="Claude Fable 5.1 (Claude Code agent, unattended calibration run)",
    )
    doc = palomar.read_formalization(run(root).files["formalization.yaml"].decode())
    methods = doc.automation_methods
    assert any(m["method"] == "autonomous" for m in methods)  # "unattended" in the string
    assert all("framework" not in m or m["framework"] for m in methods)
    assert any(ex.NOT_RECONSTRUCTED in (m.get("prompting_notes") or "") for m in methods)
    assert ex.NOT_RECONSTRUCTED in doc.sections["automation"]["spend_usd"]
    assert ex.method_from_string("undeclared") == {
        "method": "other",
        "models": [],
        "prompting_notes": ex.NOT_RECONSTRUCTED,
    }


def test_structured_automation_reaches_the_methods(tmp_path: Path) -> None:
    block = samples.automation(
        wall_time="40 minutes", spend="subscription", tokens={"input": 10, "output": 5}
    )
    root = ready(tmp_path, automation=block)
    doc = palomar.read_formalization(run(root).files["formalization.yaml"].decode())
    mine = [m for m in doc.automation_methods if m.get("framework") == "Claude Code 2.1"]
    assert mine and mine[0]["method"] == "agent" and mine[0]["models"] == ["claude-fable-5-1"]
    assert mine[0]["cost"] == {"wall_time": "40 minutes", "spend_usd": "subscription"}
    assert "tokens: 10 in, 5 out" in mine[0]["prompting_notes"]


def test_the_readme_declares_the_gaps(tmp_path: Path) -> None:
    root = ready(tmp_path)
    text = run(root).files["README.md"].decode()
    assert "## Declared gaps" in text and "Witness.lean" in text
    assert GRAPH_COMMIT in text and "000003" in text and "{{" not in text
    assert f"`{PKG}.Nodes.and_reassoc`" in text


# --- the closure: footprint, pruning, keeping by text ---------------------------------------


def narrow_root_proof(root: Path) -> None:
    """The root's proof without the call to tutorial-and-swap's theorem, so the footprint can
    honestly leave A out."""
    path = nodes_dir(root) / ROOT_NODE / "Proof.lean"
    text = path.read_text().replace("OpnProp.and_swap p q h.1", "⟨h.1.2, h.1.1⟩")
    assert "and_swap p q" not in text
    path.write_text(text, encoding="utf-8")


def test_a_declared_dep_outside_the_footprint_is_pruned_when_the_text_does_not_name_it(
    tmp_path: Path,
) -> None:
    root = copy_graph(tmp_path, publish=True)
    curate(root, classification=samples.classification())
    narrow_root_proof(root)
    prove_all(root, footprint=[B])
    out = run(root)
    assert out.closure.order == (B, ROOT_NODE)
    assert A in out.closure.pruned[ROOT_NODE]
    assert f"{PKG}/Nodes/tutorial_and_swap.lean" not in out.files
    solution = out.files["Solution.lean"].decode()
    assert (
        "tutorial_and_swap" not in solution and f"public import {PKG}.Nodes.and_reassoc" in solution
    )
    assert "tutorial-and-swap" in out.files["README.md"].decode()  # the gap is declared


def test_a_declared_dep_outside_the_footprint_is_kept_when_the_text_names_it(
    tmp_path: Path,
) -> None:
    root = ready(tmp_path, footprint=[B])  # the record says B alone; the text names and_swap
    out = run(root)
    assert set(out.closure.order) == {A, B, ROOT_NODE}
    assert out.closure.kept_by_text == {ROOT_NODE: (A,)}
    assert out.closure.pruned == {}


def test_an_unmeasured_footprint_follows_the_declared_deps(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    curate(root, classification=samples.classification())
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint={"nodes": []})
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    out = run(root)
    assert set(out.closure.order) == {A, B, ROOT_NODE} and ROOT_NODE in out.closure.unmeasured
    assert "not measured" in out.files["README.md"].decode()


# --- refusals (R9), each by name -----------------------------------------------------------


def refused(root: Path, code: str, **kw: Any) -> None:
    with pytest.raises(ex.ExportError) as caught:
        run(root, **kw)
    assert caught.value.diagnostic.code == code, caught.value.diagnostic


def test_refusals(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    curate(root, classification=samples.classification())
    refused(root, "export-root-unproved")
    prove_all(root)
    (root / "LICENSE").unlink()
    refused(root, "export-licence-missing")
    assert run(root, licence="Apache-2.0").record["licence"] == {
        "spdx": "Apache-2.0",
        "source": "flag",
    }
    refused(root, "export-licence-unsupported", licence="MIT")
    (root / "LICENSE").write_text("MIT License\n\nCopyright...\n")
    refused(root, "export-licence-unsupported")
    (root / "LICENSE").write_text(palomar.licence_text())
    curate(root, classification=None)
    refused(root, "export-classification-missing")
    curate(root, classification=samples.classification())
    run(root)


def test_refuses_the_compiler_as_a_trust_base(tmp_path: Path) -> None:
    root = ready(tmp_path, trust_base="compiler")
    refused(root, "export-trust-base-compiler")
    root2 = ready(tmp_path / "two")
    waiver = nodes_dir(root2) / B / paths.WAIVER_PATH
    waiver.parent.mkdir()
    waiver.write_text(yaml.safe_dump(samples.waiver()))
    refused(root2, "export-trust-base-compiler")


def test_refuses_sorry_private_helpers_foreign_imports_and_caps(tmp_path: Path) -> None:
    edits: list[tuple[Callable[[Path], str], str]] = [
        (
            lambda p: p.read_text() + "\ntheorem OpnProp.extra : True := by\n  sorry\n",
            "export-sorry",
        ),
        (
            lambda p: p.read_text() + "\nprivate theorem OpnProp.helper : True := trivial\n",
            "export-private-helper",
        ),
    ]
    for i, (edit, code) in enumerate(edits):
        root = copy_graph(tmp_path / str(i), publish=True)
        curate(root, classification=samples.classification())
        dep = nodes_dir(root) / B / "Proof.lean"
        dep.write_text(edit(dep), encoding="utf-8")
        prove_all(root)
        refused(root, code)
    root = copy_graph(tmp_path / "cap", publish=True)
    curate(root, classification=samples.classification())
    big = root / "targets" / TARGET / "defs" / "Big.lean"
    big.write_text("def Opn.big : Nat := 1\n" + "-- padding\n" * 1001, encoding="utf-8")
    prove_all(root)
    refused(root, "export-cap")
    # a foreign import never reaches the export on a graph (layout.load_node refuses it first);
    # the transform refuses it by name all the same, for a file handed to it directly
    with pytest.raises(ex.ExportError) as caught:
        ex.transform(
            "import Foreign.Library\n\ntheorem t : True := trivial\n",
            package="P",
            node_id=None,
            retained_deps=(),
        )
    assert caught.value.diagnostic.code == "export-import-foreign"


def test_refuses_a_closure_node_without_a_proof(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    curate(root, classification=samples.classification())
    attest(root, B, n=2, footprint={"nodes": []})
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A, B]}
    )
    (nodes_dir(root) / A / "Proof.lean").unlink()
    # the root's status derives from its deps' proofs: with A unproved the root is blocked, so
    # the first refusal is the root's; the dep rule is reached when the record is inconsistent
    with pytest.raises(ex.ExportError) as caught:
        run(root)
    assert caught.value.diagnostic.code in ("export-root-unproved", "export-dep-unproved")


# --- the transform on its own ---------------------------------------------------------------


COPYRIGHT = (
    "/-\nCopyright 2025 The Formal Conjectures Authors.\n\nLicensed under the Apache "
    "License, Version 2.0.\n-/\n\n"
)


def test_transform_three_header_shapes() -> None:
    a = (
        COPYRIGHT
        + "import Mathlib\nimport Nodes.«erdos-1050».Context\n\n/-! Erdős 1050 -/\n\ntheorem "
        "Opn.erdos_1050 : True := by\n  trivial\n"
    )
    out = ex.transform(
        a, package="OpnErdos1050", node_id="erdos-1050", retained_deps=("erdos-1050--h1-v2",)
    )
    assert out == (
        COPYRIGHT
        + "module\n\npublic import Mathlib\npublic import OpnErdos1050.Nodes.erdos_1050__h1_v2\n\n"
        + ex.SECTION
        + "\n\n/-! Erdős 1050 -/\n\ntheorem Opn.erdos_1050 : True := by\n  trivial\n"
    )
    b = (
        "import Mathlib.Tactic\nimport Nodes.«x».Context\nimport Nodes.«y».Proof\n\ntheorem T : "
        "True := trivial\n"
    )
    out_b = ex.transform(b, package="P", node_id="x", retained_deps=("z",))
    assert (
        out_b
        == (
            "module\n\npublic import Mathlib.Tactic\npublic import P.Nodes.z\npublic import "
            "P.Nodes.y\n\n"
        )
        + ex.SECTION
        + "\n\ntheorem T : True := trivial\n"
    )
    c = (
        "import Mathlib\nimport Defs.IsPrime\n\ndef Opn.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 "
        "=> (n + 1) * Opn.fact n\n"
    )
    out_c = ex.transform(c, package="P", node_id=None, retained_deps=())
    assert (
        out_c
        == "module\n\npublic import Mathlib\npublic import P.Defs.IsPrime\n\n"
        + ex.SECTION
        + "\n\ndef Opn.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 => (n + 1) * Opn.fact n\n"
    )
    # inlining a definition into the Challenge removes its import and places the body first
    out_d = ex.transform(
        c,
        package="P",
        node_id=None,
        retained_deps=(),
        defs_inline=[("P.Defs.IsPrime", "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p")],
    )
    assert "public import P.Defs.IsPrime" not in out_d
    assert "-- inlined by the network from P.Defs.IsPrime" in out_d and out_d.index(
        "def Opn.IsPrime"
    ) < out_d.index("def Opn.fact")


def test_transform_is_idempotent_and_keeps_the_body() -> None:
    src = (
        "import Mathlib\nimport Nodes.«a».Context\n\ntheorem X : 1 = 1 := by\n  -- a "
        "comment\n  rfl\n"
    )
    once = ex.transform(src, package="P", node_id="a", retained_deps=("b",))
    twice = ex.transform(once, package="P", node_id="a", retained_deps=("b",))
    assert once == twice
    assert once.split(ex.SECTION + "\n\n", 1)[1] == src.split("\n\n", 1)[1]
    # a registered entry's Challenge is already in this shape and stays itself
    registered = (
        Path(__file__).parent
        / "fixtures"
        / "palomar"
        / "PALOMAR-2026-10-03-000008"
        / "Challenge.lean"
    ).read_text()
    header = ex.split_header(registered)
    assert all(layout_ok(m) for m in header.imports)


def layout_ok(module: str) -> bool:
    return module.partition(".")[0] in ("Mathlib", "Init", "Std", "Lean", "Batteries", "Aesop")


def test_split_header_keeps_leading_comments_and_finds_the_body() -> None:
    h = ex.split_header(
        "-- a line\n/- block\nmore -/\nimport A\nimport B.C\n\n/-- doc -/\ntheorem t : True := "
        "trivial\n"
    )
    assert h.imports == ["A", "B.C"]
    assert "".join(h.leading) == "-- a line\n/- block\nmore -/\n"
    assert "".join(h.rest).startswith("/-- doc -/\ntheorem t")


def test_lakefile_and_manifest(tmp_path: Path) -> None:
    lake = ex.lakefile("OpnX", "a" * 40)
    assert (
        'name = "OpnX"' in lake and f'rev = "{"a" * 40}"' in lake and "autoImplicit = false" in lake
    )
    assert "mathlib" not in ex.lakefile("OpnX", None)
    manifest = json.loads(ex.manifest("OpnX", "a" * 40))
    assert (
        manifest["packages"][0]["name"] == "mathlib" and manifest["packages"][0]["rev"] == "a" * 40
    )
    assert manifest["name"] == "OpnX"
