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


# --- F12: a curated target with a QA pass, two signers, three attempts and a drift flag (AC11) ----

QA_TARGET = "qa-target"
QA_ROOT = "qa-lemma"
DIFF_INJECTION = "<img src=x onerror=alert('drift')>"
DRIFT_DIFF = (
    "--- pinned/FormalConjectures/ErdosProblems/68.lean\n"
    "+++ head/FormalConjectures/ErdosProblems/68.lean\n"
    "-theorem erdos_68 : Irrational s := by\n"
    f"+theorem erdos_68 : Irrational s' := by -- {DIFF_INJECTION}\n"
)


def build_with_qa_target(tmp_path: Path) -> Path:
    """The curated fixture plus a target that has been through the QA pass: a complete pass on
    the root, two signers on it, three documented attempts of which one no longer counts, and
    an upstream-drift flag whose diff carries an injection string (F12-R14)."""
    import shutil  # noqa: PLC0415

    from harness import take_in  # noqa: PLC0415

    from opn_gate import fidelity, qa, watch  # noqa: PLC0415

    root = build(tmp_path)
    src = nodes_dir(root) / "and-reassoc"
    staged = tmp_path / QA_ROOT
    shutil.copytree(src, staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = QA_ROOT
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (staged / "Proof.lean").unlink(missing_ok=True)
    take_in(root, target_id=QA_TARGET, root_dir=staged, title="A checked target")
    target = root / "targets" / QA_TARGET
    when = "2026-09-12T10:00:00Z"
    rows = [
        qa.row(
            c,
            "pass",
            tool="opn-gate qa",
            tool_version="0.0.0",
            timestamp=when,
            model="claude-opus-5" if qa.KIND_OF[c] == "brief" else None,
            model_version="claude-opus-5-20260401" if qa.KIND_OF[c] == "brief" else None,
        )
        for c in qa.FLOOR_ROOT
    ]
    qa.write(target, "root", rows, date=when, produced_by="opn-gate qa screen")
    for who, day in (("reviewer-one", "2026-09-12"), ("reviewer-two", "2026-09-13")):
        fidelity.attest(
            target, "root", "screened-and-signed", attestor=who, date=day, evidence="agreed"
        )
    current = qa.subject_hash(target, "root")
    for n, (day, hash_) in enumerate(
        (("2026-08-01", current), ("2026-08-02", current), ("2026-08-03", "0" * 64)), start=1
    ):
        qa.record_attempt(
            target,
            venue="Formal Conjectures sweep",
            system=f"prover-{n}",
            date=day,
            url=f"https://example.org/attempts/{n}",
            statement_hash=hash_,
        )
    watch.write_drift(
        target,
        watch.DriftRecord(
            kind="upstream-edit",
            state="flagged",
            statement_hash=current,
            date="2026-09-12T04:17:00Z",
            author="opn-watcher",
            upstream={
                "repo": "google-deepmind/formal-conjectures",
                "path": "FormalConjectures/ErdosProblems/68.lean",
                "pinned_commit": "c" * 40,
                "head_commit": "d" * 40,
            },
            diff=DRIFT_DIFF,
        ),
    )
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return root
