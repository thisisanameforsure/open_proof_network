"""A rendered-site fixture: the propositional graph in a curated state with its products.

Fixed commit strings, merge commits and timestamps make the rendering deterministic, so the
golden pages compare byte for byte. Injection strings live in the explainer and annex so the
escaping tests (T3) and the goldens cover the same tree.
"""

from __future__ import annotations

from pathlib import Path

import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import products, schemas

COMMIT = "6" * 40
MERGE = "4" * 40
NOW = "2026-09-09T12:00:00Z"
EXPLAINER = (
    "---\nauthor: thisisanameforsure\nmodel: claude-fable-5-1\ndate: 2026-09-09\n---\n"
    "Swap the two halves of the conjunction.\n\n<script>alert(1)</script>\n"
)
ANNEX = "Informal sketch <img src=x onerror=alert(1)> with & and <b>tags</b>.\n"


def nodes_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def attest(root: Path, node_id: str, n: int, **kw: object) -> None:
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=schemas.content_hash(
            (nodes_dir(root) / node_id / "Statement.lean").read_bytes()
        ),
        merge_commit=MERGE,
        graph_commit=MERGE,
        runner="hosted",
        review={"kind": "pr-approval", "reviewer": "reviewer-one", "reference": None},
        **kw,
    )
    att = root / "attestations"
    att.mkdir(exist_ok=True)
    (att / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def build(tmp_path: Path) -> Path:
    """The graph in its curated state with products written; returns the checkout root."""
    root = copy_graph(tmp_path)
    attest(root, "tutorial-and-swap", 1)
    attest(root, "and-reassoc", 2, trust_base="compiler")
    st = nodes_dir(root) / "and-swap-reassoc" / "status"
    # The root stays ready (both deps proved); give it attempts and prose.
    att = nodes_dir(root) / "and-swap-reassoc" / "attempts"
    (att / "2026-09-01-a.yaml").write_text(
        yaml.safe_dump(samples.postmortem(node="and-swap-reassoc", route_class="case-split")),
        encoding="utf-8",
    )
    (att / "2026-09-02-b.yaml").write_text("route: [oops\n", encoding="utf-8")
    (nodes_dir(root) / "and-swap-reassoc" / "annex" / "sketch.md").write_text(ANNEX)
    (nodes_dir(root) / "tutorial-and-swap" / "explainer" / "why.md").write_text(EXPLAINER)
    assert not st.exists()
    prod = products.generate(root, rendered_from=COMMIT, commit_time=NOW)
    prod.write(root)
    return root


# --- F11: a curated target that is listed but not claimable (R10; AC9) --------------------------

LISTED_TARGET = "listed-target"
LISTED_ROOT = "listed-lemma"
UNLICENSED = {
    "kind": "erdos",
    "url": "https://www.erdosproblems.com/42",
    "accessed": "2026-09-09",
    "licence": "none-stated",
    "attribution": "erdosproblems.com, compiled by Thomas Bloom",
    "quote_policy": "cite",
}
PARAPHRASE = "Whether a certain sum over a set of integers can stay bounded."
UNLICENSED_WORDING = "THE-SOURCES-OWN-WORDING-WHICH-IS-NOT-LICENSED"
QA_SUMMARY = "Back-translated by hand on 2026-09-09; two edge cases checked; no drift found."


def build_with_listed_target(tmp_path: Path) -> Path:
    """The curated fixture plus a second target that is listed and not claimable.

    Its one source states no licence, so intake refuses to store the informal statement at all
    and the network's paraphrase stands in its place (R10) — which is exactly the property the
    page has to show without leaking.
    """
    import shutil  # noqa: PLC0415

    from harness import take_in  # noqa: PLC0415

    root = build(tmp_path)
    src = nodes_dir(root) / "and-reassoc"
    staged = tmp_path / LISTED_ROOT
    shutil.copytree(src, staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = LISTED_ROOT
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (staged / "Proof.lean").unlink(missing_ok=True)  # listed, so nothing is proved under it

    take_in(
        root,
        target_id=LISTED_TARGET,
        root_dir=staged,
        title="A listed open problem",
        track="open",
        informal=None,
        paraphrase=PARAPHRASE,
        sources=[UNLICENSED],
        qa_summary=QA_SUMMARY,
        domains=["number-theory"],
    )
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return root
