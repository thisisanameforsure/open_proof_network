"""F14-T12: one target's whole life under F14, low grade and high grade side by side (AC13).

A graph gains two curated targets imported from Formal Conjectures: ``fc-low``, whose catalog
evidence scores 3 (C), and ``fc-high``, scoring 5 (B+) with a second formalization proved
equivalent to its root. The test walks what an agent and the site see:

1. the products say both roots are claimable while listed and unsigned, and the high one's
   formalization is no frontier node; an upstream-drift freeze still refuses (the control);
2. the api, served those products, answers ``POST /claims`` with 201 on both roots;
3. ``opn-gate classify`` over a proof asks a reviewer on the low root and none on the high one,
   and a proof that brings its own evidence is ``mode-mixed``;
4. after the high proof merges with its attestation, the products regenerate byte for byte,
   the root is proved and the target resolved;
5. the site renders the evidence, the formalization and who has to look at a proof.

The sandboxed verdict itself is out of scope here: ``test_cli_sandboxed.py`` and
``test_postmerge_apply.py`` cover it. The merge is recorded the way the site fixture records one,
with an attestation file.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from api_fakes import make_harness
from fixture import COMMIT, MERGE, NOW, build, nodes_dir
from harness import freeze_upstream, take_in
from test_finding_step9_certified import FC_COMMIT, Repo, classify, step9, write_curators

from opn_gate import evidence, formalizations, products, qa, schemas
from opn_site import model, render

LOW, HIGH = "fc-low", "fc-high"
ROOTS = {LOW: "low-lemma", HIGH: "high-lemma"}
SCORES = {LOW: (3, "C"), HIGH: (5, "B+")}
PROVER = "prover"


def stage_root(root: Path, tmp: Path, node_id: str) -> tuple[Path, str]:
    """A copy of the fixture's ``and-reassoc`` renamed, without its proof; returns the directory
    and the proof text a prover will later submit."""
    staged = tmp / node_id
    shutil.copytree(nodes_dir(root) / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = node_id
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    proof = staged / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    proof.unlink()
    return staged, text


def record_evidence(target: Path, target_id: str) -> str:
    score, letter = SCORES[target_id]
    root_hash = qa.subject_hash(target, "root")
    doc = samples.statement_evidence(statement_hash=root_hash)
    doc["catalog"] = {
        **doc["catalog"],
        "key": f"fc:FormalConjectures/Wikipedia/{target_id}.lean#Opn.{target_id}",
        "score": score,
        "letter": letter,
    }
    path = evidence.write(target, doc)
    return f"evidence:evidence/{path.name}@{root_hash}:{score}"


def add_formalization(target: Path, node_id: str) -> None:
    """A second statement of the root under ``formalizations/alt`` and a passing equivalence row
    naming it, as ``qa equivalence --formalization`` records one."""
    statement = (target / "nodes" / node_id / "Statement.lean").read_text(encoding="utf-8")
    alt = re.sub(r"theorem\s+\S+", "theorem OpnAlt.high", statement, count=1)
    alt = "\n".join(line for line in alt.splitlines() if not line.startswith("import ")) + "\n"
    directory = formalizations.formalizations_dir(target) / "alt"
    directory.mkdir(parents=True)
    (directory / formalizations.STATEMENT_FILE).write_text(alt, encoding="utf-8")
    alt_hash = schemas.content_hash(alt.encode("utf-8"))
    (directory / formalizations.RECORD_FILE).write_text(
        yaml.safe_dump(samples.formalization(name="alt", declaration="OpnAlt.high",
                                             statement_hash=alt_hash)),
        encoding="utf-8",
    )  # fmt: skip
    rel, digest = qa.store_exhibit(
        target, "root-equivalence-1.lean", "theorem OpnQa.equiv : True := trivial\n"
    )
    qa.write(
        target,
        "root",
        [
            qa.row(
                "equivalence",
                "pass",
                tool="opn-gate qa equivalence",
                tool_version="0.0.0",
                timestamp="2026-09-14T10:00:00Z",
                exhibit=rel,
                exhibit_sha256=digest,
                against={"kind": "formalization", "ref": "alt", "statement_hash": alt_hash},
            )
        ],
        date="2026-09-14T10:00:00Z",
        produced_by="opn-gate qa equivalence",
    )


def fc_provenance() -> dict[str, Any]:
    return {
        "statement_source": "formal-conjectures",
        "author": "author",
        "adversarially_reviewed": False,
        "upstream_commit": FC_COMMIT,
        "upstream_path": "FormalConjectures/ErdosProblems/7.lean",
    }


def render_products(root: Path) -> None:
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)


def read_json(root: Path, rel: str) -> Any:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def row_of(root: Path, target_id: str) -> dict[str, Any]:
    rows = read_json(root, "targets/index.json")["targets"]
    [row] = [r for r in rows if r["target_id"] == target_id]
    return dict(row)


def entry_of(root: Path, node_id: str) -> dict[str, Any] | None:
    entries = read_json(root, "frontier.json")["entries"]
    found = [e for e in entries if e["node_id"] == node_id]
    return dict(found[0]) if found else None


class Graph:
    def __init__(self, repo: Repo, proofs: dict[str, str]) -> None:
        self.repo = repo
        self.proofs = proofs

    def target(self, target_id: str) -> Path:
        return self.repo.root / "targets" / target_id

    def node(self, target_id: str) -> Path:
        return self.target(target_id) / "nodes" / ROOTS[target_id]


@pytest.fixture
def graph(tmp_path: Path) -> Graph:
    root = build(tmp_path / "g")
    proofs: dict[str, str] = {}
    for target_id, node_id in ROOTS.items():
        staged, proofs[target_id] = stage_root(root, tmp_path, node_id)
        take_in(root, target_id, root_dir=staged, provenance=fc_provenance())
        record_evidence(root / "targets" / target_id, target_id)
    add_formalization(root / "targets" / HIGH, ROOTS[HIGH])
    write_curators(root, "curator")
    render_products(root)
    repo = Repo(root)
    repo.git("init", "-q", "-b", "main")
    repo.commit("base: two imported targets with their evidence")
    return Graph(repo, proofs)


def test_the_whole_life(graph: Graph, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # noqa: PLR0915 — one life, walked in order
    started = time.monotonic()
    root = graph.repo.root

    # 1. Claimable while listed and unsigned; the formalization is no frontier node.
    for target_id, node_id in ROOTS.items():
        row = row_of(root, target_id)
        assert row["claimable"] is True and row["not_claimable"] == [], row
        assert row["statement_evidence"]["score"] == SCORES[target_id][0], row
        entry = entry_of(root, node_id)
        assert entry is not None and entry["claimable"] is True, entry
    assert row_of(root, LOW)["step9"] == "review"
    assert row_of(root, HIGH)["step9"] == "evidence"
    [formalization] = row_of(root, HIGH)["formalizations"]
    assert formalization["name"] == "alt" and formalization["equivalence"] == "pass", formalization
    assert entry_of(root, "alt") is None

    frozen = tmp_path / "frozen"
    shutil.copytree(root, frozen)
    freeze_upstream(frozen / "targets" / LOW)
    render_products(frozen)
    assert row_of(frozen, LOW)["not_claimable"] == ["upstream-drift"]
    assert entry_of(frozen, ROOTS[LOW])["claimable"] is False  # type: ignore[index]

    # 2. The api serves the products and takes a claim on each root.
    h = make_harness()
    h.githost.files["frontier.json"] = (root / "frontier.json").read_bytes()
    h.githost.files["targets/index.json"] = (root / "targets" / "index.json").read_bytes()
    h.context.files.clear()
    token = h.token_for("code_alice", "alice-p")
    for node_id in ROOTS.values():
        made = h.client.post("/claims", json={"node_id": node_id}, headers=h.auth(token))
        assert made.status_code == 201, made.text

    # 3. Step 9 follows the grade; a proof cannot bring its own evidence.
    repo = graph.repo
    base = repo.git("rev-parse", "HEAD")
    for target_id, expected in [
        (LOW, (True, "pr-approval", None)),
        (HIGH, (False, "provenance", evidence.current(graph.target(HIGH)).reference())),  # type: ignore[union-attr]
    ]:
        repo.git("checkout", "-q", "-b", f"proof-{target_id}", base)
        (graph.node(target_id) / "Proof.lean").write_text(graph.proofs[target_id], encoding="utf-8")
        repo.commit(f"a proof of {target_id}")
        code, out = classify(repo, capsys, author=PROVER)
        assert code == 0 and out["mode"] == "proof", out
        assert step9(out) == expected, out

    repo.git("checkout", "-q", "-b", "mixed", base)
    (graph.node(LOW) / "Proof.lean").write_text(graph.proofs[LOW], encoding="utf-8")
    record_evidence(graph.target(LOW), HIGH)  # a second record at five, brought by the prover
    repo.commit("a proof and evidence for its own statement")
    code, out = classify(repo, capsys, author=PROVER)
    assert code != 0 and "mode-mixed" in [p["code"] for p in out["problems"]], out

    # 4. The high proof merges; the products regenerate byte for byte.
    repo.git("checkout", "-q", "proof-fc-high")
    node = graph.node(HIGH)
    doc = samples.attestation(
        node_id=ROOTS[HIGH],
        statement_hash=schemas.content_hash((node / "Statement.lean").read_bytes()),
        merge_commit=MERGE,
        graph_commit=MERGE,
        runner="hosted",
        review={
            "kind": "provenance",
            "reviewer": None,
            "reference": evidence.current(graph.target(HIGH)).reference(),  # type: ignore[union-attr]
        },
    )
    (root / "attestations" / "000900.json").write_bytes(schemas.canonical_json(doc))
    render_products(root)
    first = {p: (root / p).read_bytes() for p in ("frontier.json", "targets/index.json")}
    render_products(root)
    assert first == {p: (root / p).read_bytes() for p in first}
    assert row_of(root, HIGH)["status"] == "resolved", row_of(root, HIGH)
    assert row_of(root, LOW)["claimable"] is True
    assert entry_of(root, ROOTS[HIGH]) is None or entry_of(root, ROOTS[HIGH])["claimable"] is False  # type: ignore[index]

    # 5. The site shows it.
    pages = render.render_site(model.load_site(root, COMMIT), repo_url="https://github.com/x/g")
    high = pages[f"targets/{HIGH}/index.html"]
    low = pages[f"targets/{LOW}/index.html"]
    assert "score <strong>5</strong> (B+)" in high
    assert "without a human reviewer" in high
    assert "alt" in high
    assert "score <strong>3</strong> (C)" in low
    assert "without a human reviewer" not in low

    assert time.monotonic() - started < 10
