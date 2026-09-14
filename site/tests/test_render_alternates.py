"""F07-T13: the node page lists alternate proofs (R7; AC26; D-25 v3.13).

A theorem keeps every proof. The first merged ``Proof.lean`` stays the node's proof on the page;
each later proof merged as ``attempts/<ts>-<pseudonym>-alternate.lean`` is listed beside it, linked
at the commit that merged it, which is found by the attestation whose ``artifact_hash`` is the
alternate's (F07-R15). A node with no alternates shows no section, so every golden page is
unchanged.
"""

from __future__ import annotations

from pathlib import Path

import fixture
import samples

from opn_gate import schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE = "tutorial-and-swap"
PAGE = f"nodes/propositional/{NODE}/index.html"
FIRST = "20260913T090000Z-alice-alternate.lean"
SECOND = "20260913T100000Z-bob-alternate.lean"


def with_alternates(tmp_path: Path) -> tuple[Path, dict[str, tuple[str, str]]]:
    """The curated fixture with two alternates merged on the tutorial node, each with its own
    attestation: ``{file name: (merge commit, submitter)}``."""
    root = fixture.build(tmp_path)
    node = fixture.nodes_dir(root) / NODE
    proof = (node / "Proof.lean").read_text(encoding="utf-8")
    statement_hash = schemas.content_hash((node / "Statement.lean").read_bytes())
    merged: dict[str, tuple[str, str]] = {}
    cases = (
        (FIRST, "a" * 40, "alice", "exact And.intro h.2 h.1"),
        (SECOND, "b" * 40, "bob", "exact ⟨h.right, h.left⟩"),
    )
    for n, (name, merge, who, body) in enumerate(cases, start=10):
        text = proof.replace("exact ⟨h.2, h.1⟩", body)
        assert text != proof  # guard: the fixture's proof still has the body this rewrites
        (node / "attempts" / name).write_text(text, encoding="utf-8")
        doc = samples.attestation(
            node_id=NODE,
            statement_hash=statement_hash,
            merge_commit=merge,
            graph_commit=merge,
            runner="hosted",
            artifact_hash=schemas.content_hash(text.encode("utf-8")),
            submitter=who,
        )
        (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))
        merged[name] = (merge, who)
    return root, merged


def test_node_page_lists_alternates(tmp_path: Path) -> None:
    """AC26: both alternates are listed in merge order with links at their merge commits and
    their submitters; the node's own proof link is unchanged; a node with none has no section."""
    root, merged = with_alternates(tmp_path / "with")
    html = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[PAGE]
    assert "Alternate proofs" in html
    for name, (merge, who) in merged.items():
        rel = f"targets/propositional/nodes/{NODE}/attempts/{name}"
        assert f'href="{REPO}/blob/{merge}/{rel}"' in html, name
        assert f"by <code>{who}</code>" in html, who
    assert html.index(FIRST) < html.index(SECOND)
    # The first merged proof is still the node's proof (the fixture merged it at MERGE).
    assert f"Proof merged in commit <code>{fixture.MERGE[:12]}</code>" in html

    plain = render.render_site(
        model.load_site(fixture.build(tmp_path / "plain"), fixture.COMMIT), repo_url=REPO
    )[PAGE]
    assert "Alternate proofs" not in plain
