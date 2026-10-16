"""A rendered-site fixture: the propositional graph in a curated state with its products.

Fixed commit strings, merge commits and timestamps make the rendering deterministic, so the
golden pages compare byte for byte. Injection strings live in the explainer and annex so the
escaping tests (T3) and the goldens cover the same tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph
from test_finding_hole_frontier import write_hole

from opn_gate import curator, products, schemas

COMMIT = "6" * 40
MERGE = "4" * 40
NOW = "2026-09-09T12:00:00Z"
EXPLAINER = (
    "---\nauthor: thisisanameforsure\nmodel: claude-fable-5-1\ndate: 2026-09-09\n---\n"
    "Swap the two halves of the conjunction.\n\n<script>alert(1)</script>\n"
)
ANNEX = "Informal sketch <img src=x onerror=alert(1)> with & and <b>tags</b>.\n"
#: T15: a partial assembly a postmortem names, and one nothing names — the live graph carries
#: both. The payload rides in the Lean so the escaping tests cover an artifact, not only prose.
PARTIAL = (
    "theorem partial_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n"
    "  intro p q h -- <script>alert(1)</script>\n"
    "  sorry\n"
)
UNNAMED_PARTIAL = "theorem unnamed_route : ∀ p : Prop, p → p := by\n  sorry\n"


def nodes_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def attest(root: Path, node_id: str, n: int, **kw: object) -> None:
    # The attestation covers the Proof.lean in the tree, as a live one does: every proved node
    # on the graph has artifact_hash equal to its proof's sha256 (checked 2026-09-18, 8 of 8).
    # The sample's placeholder would leave every fixture proof unverifiable against its record.
    proof = nodes_dir(root) / node_id / "Proof.lean"
    covered: dict[str, object] = (
        {"artifact_hash": schemas.content_hash(proof.read_bytes())} if proof.is_file() else {}
    )
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=schemas.content_hash(
            (nodes_dir(root) / node_id / "Statement.lean").read_bytes()
        ),
        merge_commit=MERGE,
        graph_commit=MERGE,
        runner="hosted",
        review={"kind": "pr-approval", "reviewer": "reviewer-one", "reference": None},
        **{**covered, **kw},
    )
    att = root / "attestations"
    att.mkdir(exist_ok=True)
    (att / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


#: T15: the sample attestation lists steps 1, 2, 4 and 5 only, so nothing in it names step 7 —
#: the step a live attestation always carries (checked on the graph's own attestations). The
#: tutorial's run carries it, so the witness block's "checked at step 7" branch is reachable by
#: a test and not only by the live graph.
WITNESS_STEP = {"step": 7, "name": "witness", "result": "pass", "diagnostic": None}


#: F04-T39 (D-12 v3.38): the fixture's one lemma. A merged partial of the proved tutorial node
#: restated ``and-reassoc`` (a sibling under the root, not a hole of the tutorial) as its hole
#: ``h_reassoc``, so the tutorial node carries it as a lemma: drawn on once proved, never waited
#: on, and not among its deps (D-3). The products are rewritten to ``graph/v8`` with it, since
#: the fixture's tree holds no such partial for the gate to extract.
LEMMA_PARENT = "tutorial-and-swap"
LEMMA_NODE = "and-reassoc"
LEMMA_HOLE = "h_reassoc"


def build(tmp_path: Path) -> Path:
    """The graph in its curated state with products written; returns the checkout root."""
    root = curated(tmp_path)
    prod = products.generate(root, rendered_from=COMMIT, commit_time=NOW)
    prod.write(root)
    publish_v336(root, lemmas={LEMMA_PARENT: [{"hole": LEMMA_HOLE, "node": LEMMA_NODE}]})
    return root


def curated(tmp_path: Path) -> Path:
    """``build`` before its products are rendered, so a builder can grow the tree first."""
    root = copy_graph(tmp_path, publish=True)
    attest(
        root,
        "tutorial-and-swap",
        1,
        steps=[*samples.attestation()["steps"], WITNESS_STEP],
    )
    attest(root, "and-reassoc", 2, trust_base="compiler")
    st = nodes_dir(root) / "and-swap-reassoc" / "status"
    # The root stays ready (both deps proved); give it attempts and prose.
    att = nodes_dir(root) / "and-swap-reassoc" / "attempts"
    (att / "2026-09-01-a.yaml").write_text(
        yaml.safe_dump(
            samples.postmortem(
                node="and-swap-reassoc",
                route_class="case-split",
                artifacts={"partial_proof": "attempts/2026-09-01-a-partial.lean"},
            )
        ),
        encoding="utf-8",
    )
    (att / "2026-09-02-b.yaml").write_text("route: [oops\n", encoding="utf-8")
    (att / "2026-09-01-a-partial.lean").write_text(PARTIAL, encoding="utf-8")
    (att / "2026-09-03-c-partial.lean").write_text(UNNAMED_PARTIAL, encoding="utf-8")
    (nodes_dir(root) / "and-swap-reassoc" / "annex" / "sketch.md").write_text(ANNEX)
    (nodes_dir(root) / "tutorial-and-swap" / "explainer" / "why.md").write_text(EXPLAINER)
    assert not st.exists()
    return root


# --- F04-T17, T18: a hole awaiting its witness, and a hole a D-8 revision replaced -------------

#: The shapes the live graph has carried since 2026-09-17 and no site fixture had: a hole whose
#: only obstacle is its witness slot (``blocked``, cause ``witness-missing``, claimable on the
#: frontier), and a hole a curator revised — the original ``superseded`` with a record naming its
#: successor, the successor carrying ``supersedes`` and the slot it inherited.
HOLE = "and-swap-reassoc--h1"
REVISED_HOLE = "and-swap-reassoc--h2"
REVISION = REVISED_HOLE + "-v2"
REVISION_CAUSE = (
    f"superseded by {REVISION} on revision request targets/{TARGET}/nodes/{REVISED_HOLE}/"
    "revisions/20260917T173437Z-curator.yaml (wrong-domain; D-8)"
)
STUB_WITNESS = "theorem witness : True := by\n  sorry\n"


def build_with_revised_hole(tmp_path: Path) -> Path:
    """The curated graph plus the three nodes above, written as the gate's own writers write
    them (the gate tests' ``write_hole`` and the curator's record writer), products rendered."""
    root = curated(tmp_path)
    write_hole(root, witness=STUB_WITNESS, node_id=HOLE)
    write_hole(root, witness=STUB_WITNESS, node_id=REVISED_HOLE)
    write_hole(root, witness=STUB_WITNESS, node_id=REVISION, supersedes=REVISED_HOLE)
    doc = curator.node_status_doc(
        "superseded", REVISION_CAUSE, author="curator", date="2026-09-17", reference=REVISION
    )
    curator.write_record(nodes_dir(root) / REVISED_HOLE, doc, author="curator", date="2026-09-17")
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


def build_with_frozen_target(tmp_path: Path) -> Path:
    """The listed fixture with an upstream edit flagged on its root: since F14-R1 a listed target
    is claimable, and the drift freeze is the live case of a curated target that is not, so the
    pages that explain why keep a real reason to explain."""
    from harness import freeze_upstream  # noqa: PLC0415

    root = build_with_listed_target(tmp_path)
    freeze_upstream(root / "targets" / LISTED_TARGET)
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return root


EVIDENCE_INJECTION = "<script>alert('reason')</script>"


def build_with_evidenced_target(tmp_path: Path) -> Path:
    """The listed fixture with F14's evidence on its root: a catalog row at six points (one reason
    carries an injection string), and a second formalization proved equivalent to the root through
    a QA row that names it (F14-R3, R7, R8, R10)."""
    import re  # noqa: PLC0415

    from opn_gate import evidence, formalizations, qa  # noqa: PLC0415

    root = build_with_listed_target(tmp_path)
    target = root / "targets" / LISTED_TARGET
    row = {
        "key": "erdos:42",
        "file": "FormalConjectures/ErdosProblems/42.lean",
        "score": 6,
        "letter": "A",
        "reasons": [
            "+2 Bloom selected it for FrontierMath Erdős",
            "+2 attempted by AlphaProof Nexus (Feb 2026), not solved",
            f"+1 no misformalization issue ever filed {EVIDENCE_INJECTION}",
            "+1 Lean statement public for 180+ days",
        ],
        "history": {"first": "2025-04-26", "last": "2026-07-16", "n": 13},
        "issues": [],
        "local_defs": [],
        "hazards": ["density"],
        "site_status": "OPEN",
        "mathlib_definition": None,
    }
    catalog = {"schema": evidence.CATALOG_SCHEMA, "fc_commit": "b" * 40, "rows": [row]}
    evidence.write(
        target,
        evidence.doc_from_row(
            catalog,
            row,
            statement_hash=qa.subject_hash(target, "root"),
            network_commit="1" * 40,
            recorded_by="curator",
            date="2026-09-14",
            attempts_recorded=0,
        ),
    )

    statement = (target / "nodes" / LISTED_ROOT / "Statement.lean").read_text(encoding="utf-8")
    alt = re.sub(r"theorem\s+\S+", "theorem OpnAlt.listed", statement, count=1)
    alt = "\n".join(line for line in alt.splitlines() if not line.startswith("import ")) + "\n"
    directory = formalizations.formalizations_dir(target) / "alt"
    directory.mkdir(parents=True)
    (directory / formalizations.STATEMENT_FILE).write_text(alt, encoding="utf-8")
    alt_hash = schemas.content_hash(alt.encode("utf-8"))
    (directory / formalizations.RECORD_FILE).write_text(
        yaml.safe_dump(
            {
                "schema": formalizations.SCHEMA,
                "name": "alt",
                "declaration": "OpnAlt.listed",
                "statement_hash": alt_hash,
                "author": "curator",
                "source": {
                    "kind": "network",
                    "ref": "the root restated",
                    "url": None,
                    "licence": "Apache-2.0",
                    "attribution": "the Open Proof Network curators",
                },
                "provenance": {"upstream_commit": None, "upstream_path": None},
                "date": "2026-09-14",
            }
        ),
        encoding="utf-8",
    )
    rel, digest = qa.store_exhibit(
        target,
        "root-equivalence-1.lean",
        "theorem OpnQa.equiv_forward : True := trivial\n"
        "theorem OpnQa.equiv_backward : True := trivial\n",
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


# --- F15: stewards, the digestion state, a signed explainer, a calibration target (AC10) ---------

STEWARDED_TARGET = "stewarded-target"
STEWARDLESS_TARGET = "stewardless-target"
RESOLVED_TARGET = "resolved-target"
CALIBRATION_TARGET = "calibration-target"
STEWARD_LOGIN = "alice-steward"
STEWARD_NAME = "Alice Steward <b>not bold</b>"
STEWARD_LINK = "https://orcid.org/0000-0002-1825-0097"
SIGNER_LOGIN = "curator-one"


def _staged_root(root: Path, tmp_path: Path, node_id: str, *, proved: bool) -> Path:
    import shutil  # noqa: PLC0415

    staged = tmp_path / node_id
    shutil.copytree(nodes_dir(root) / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = node_id
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    if not proved:
        (staged / "Proof.lean").unlink(missing_ok=True)
    return staged


def build_with_stewards(tmp_path: Path) -> Path:
    """The curated fixture plus, under an enforced steward rule: an open target with a steward
    (claimable), an open target with none (``no-steward``), a resolved target with no explainer
    signed (undigested), a signed explainer on the fixture's proved interior node, and a
    calibration target on the formalization track (F15-R10; AC10)."""
    import subprocess  # noqa: PLC0415

    from harness import take_in  # noqa: PLC0415

    from opn_gate import explainers, policy, steward  # noqa: PLC0415
    from opn_gate.signer import SshKeygenSigner  # noqa: PLC0415

    root = build(tmp_path)
    signer = SshKeygenSigner()
    key = tmp_path / "steward-key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)

    take_in(
        root,
        target_id=STEWARDED_TARGET,
        root_dir=_staged_root(root, tmp_path, "stewarded-lemma", proved=False),
        title="An open problem with a steward",
        track="open",
    )
    steward.write(
        root / "targets" / STEWARDED_TARGET,
        action=steward.COMMIT,
        login=STEWARD_LOGIN,
        name=STEWARD_NAME,
        link=STEWARD_LINK,
        date="2026-09-16",
        key_path=key,
        signer=signer,
    )
    take_in(
        root,
        target_id=STEWARDLESS_TARGET,
        root_dir=_staged_root(root, tmp_path, "stewardless-lemma", proved=False),
        title="An open problem waiting for a steward",
        track="open",
    )
    take_in(
        root,
        target_id=RESOLVED_TARGET,
        root_dir=_staged_root(root, tmp_path, "resolved-lemma", proved=True),
        title="A resolved known result",
        track="formalization",
    )
    resolved_node = root / "targets" / RESOLVED_TARGET / "nodes" / "resolved-lemma"
    doc = samples.attestation(
        node_id="resolved-lemma",
        statement_hash=schemas.content_hash((resolved_node / "Statement.lean").read_bytes()),
        merge_commit=MERGE,
        graph_commit=MERGE,
        runner="hosted",
        review={"kind": "pr-approval", "reviewer": "reviewer-one", "reference": None},
        graph_id=RESOLVED_TARGET,
    )
    (root / "attestations" / "000009.json").write_bytes(schemas.canonical_json(doc))
    take_in(
        root,
        target_id=CALIBRATION_TARGET,
        root_dir=_staged_root(root, tmp_path, "calibration-lemma", proved=False),
        title="A calibration target",
        track="formalization",
        calibration=True,
    )
    # A hash-named explainer on the fixture's proved interior node, signed by a curator.
    text = "---\nauthor: someone\ndate: 2026-09-16\n---\nReassociate; both halves are in hand.\n"
    digest = schemas.content_hash(text.encode("utf-8"))
    (nodes_dir(root) / "and-reassoc" / "explainer" / f"{digest}.md").write_text(text)
    explainers.sign(
        nodes_dir(root) / "and-reassoc",
        digest,
        target_id=TARGET,
        signer_login=SIGNER_LOGIN,
        date="2026-09-16",
        key_path=key,
        signer=signer,
    )
    policy.write(
        root,
        policy.document(
            enforced=True, since="2026-09-16", evidence="engineering/evidence/F15/calibration.md"
        ),
    )
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return root


# --- F04-T31: a problem resolved by each root-level D-12 artifact ------------------------------

#: target id -> the artifact merged on its root (``settle``'s suffix, D-12): a proof, a
#: counterexample, a vacuity certificate.
RESOLUTIONS = {
    "proved-target": "",
    "disproved-target": "_refuted",
    "ill-posed-target": "_vacuous",
}


def build_with_resolutions(tmp_path: Path) -> Path:
    """The curated fixture plus three open-track targets, each resolved (F03-T17, D-33) by a
    different root-level D-12 artifact, products rendered."""
    import harness  # noqa: PLC0415
    from test_finding_closed_root import settle  # noqa: PLC0415

    from opn_gate import graph  # noqa: PLC0415

    root = curated(tmp_path)
    for n, (tid, suffix) in enumerate(RESOLUTIONS.items(), start=9):
        harness.take_in(root, tid, track="open")
        settle(root, graph.load_target(root, tid).root, suffix, n, tid)
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return root


# --- Decisions v3.35 (F04-T37, T38): the products as the gate writes them since graph/v6 ----------

#: A literature record as the products publish it (``graph/v6`` ``literature`` /
#: ``literature_proposed``), by what a test needs to say; the record file itself is written by
#: ``write_literature``.
LITERATURE_WORDS = {
    "open": "Open problem: no proof is known",
    "known": "Known: a proof is published and not formalised",
    "elementary": "Elementary: a routine formalisation of a known fact",
}


def write_literature(
    root: Path,
    node_id: str,
    *,
    status: str,
    contributor: str,
    date: str,
    references: list[dict[str, Any]] | None = None,
    summary: str = "What the literature says, in the contributor's words.",
    confirms: str | None = None,
    signed: bool = False,
    target: str = TARGET,
) -> str:
    """One ``literature/v1`` record under the node, as the service files it: unsigned for a
    proposal; for a confirmation (``signed``) the signature fields are filled with the shape
    the schema wants (the site reads the *products* for who confirmed, never the signature).
    Returns the record's path relative to the node (``literature/<file>``)."""
    stamp = date.replace("-", "").replace(":", "")
    rel = f"literature/{stamp}-{contributor}.yaml"
    doc: dict[str, Any] = {
        "schema": "literature/v1",
        "node": node_id,
        "contributor": contributor,
        "date": date,
        "status": status,
        "references": references
        if references is not None
        else [{"title": "Where the problem is listed", "url": None, "note": None}],
        "summary": summary,
        "model_and_tooling": None,
        "confirms": confirms,
        "via": "approval-key" if signed else None,
        "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeKeyForTheFixtureOnly0000000000000000000"
        if signed
        else None,
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"
        if signed
        else None,
    }
    path = root / "targets" / target / "nodes" / node_id / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True, allow_unicode=True), encoding="utf-8")
    return rel


def publish_v335(
    root: Path,
    *,
    literature: dict[str, dict[str, Any]] | None = None,
    literature_proposed: dict[str, dict[str, Any]] | None = None,
    target: str = TARGET,
) -> None:
    """Rewrite the rendered products with the literature fields v3.35 added (``graph/v6``
    ``literature`` / ``literature_proposed``, carried by every later version) on the named rows,
    at the current contract (``graph/v11``, ``frontier/v6``; F08-T42 retired v6's ``circular``).
    The documents are validated against the schemas, so a test feeds the site exactly the shape
    the gate's contract names."""
    literature = literature or {}
    literature_proposed = literature_proposed or {}

    def extend(row: dict[str, Any]) -> None:
        nid = str(row["node_id"])
        row["literature"] = literature.get(nid)
        row["literature_proposed"] = literature_proposed.get(nid)

    graph_path = root / "targets" / target / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["schema"] = "graph/v11"
    for row in graph["nodes"]:
        extend(row)
        row.setdefault("lemmas", [])
    graph_path.write_text(json.dumps(schemas.validate(graph, "graph/v11"), indent=1) + "\n")

    frontier_path = root / "frontier.json"
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    frontier["schema"] = "frontier/v6"
    for entry in frontier["entries"]:
        if entry["target_id"] == target:
            extend(entry)
    frontier_path.write_text(json.dumps(schemas.validate(frontier, "frontier/v6"), indent=1) + "\n")


def publish_circular_snapshot(
    root: Path,
    circular: dict[str, list[dict[str, str]]],
    *,
    target: str = TARGET,
) -> None:
    """An older snapshot (D-34): the rendered products lowered to ``graph/v9`` and
    ``frontier/v5``, the last versions whose rows carry ``circular`` (``[{ancestor, claim}]``,
    the claim relative to the target's ``nodes/``) — the given labels on the named rows, none
    elsewhere. F04-T53 (D-12 v3.43): the site ignores the field, so such a snapshot renders as
    the current one does. Validated against the older schemas."""

    def lower(row: dict[str, Any]) -> None:
        row["circular"] = list(circular.get(str(row["node_id"]), []))

    graph_path = root / "targets" / target / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["schema"] = "graph/v9"
    for row in graph["nodes"]:
        lower(row)
        row.pop("closure", None)  # graph/v10 (F28-T8) added it
    graph_path.write_text(json.dumps(schemas.validate(graph, "graph/v9"), indent=1) + "\n")

    frontier_path = root / "frontier.json"
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    frontier["schema"] = "frontier/v5"
    for entry in frontier["entries"]:
        lower(entry)
    frontier_path.write_text(json.dumps(schemas.validate(frontier, "frontier/v5"), indent=1) + "\n")


# --- Decisions v3.38 (F04-T39): lemmas, the products as the gate writes them since graph/v8 -------


def publish_v336(
    root: Path,
    *,
    lemmas: dict[str, list[dict[str, str]]] | None = None,
    target: str = TARGET,
) -> None:
    """Rewrite the rendered ``graph.json`` as the v3.38 gate writes it: ``graph/v8``, every row
    carrying ``lemmas`` (``[{hole, node}]``, D-12 v3.38) — the given ones on the named nodes,
    none elsewhere. Idempotent over a document the gate already wrote at v7. The document is
    validated against the schema, so a test feeds the site exactly the contract's shape."""
    lemmas = lemmas or {}
    graph_path = root / "targets" / target / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["schema"] = "graph/v11"
    for row in graph["nodes"]:
        row["lemmas"] = list(lemmas.get(str(row["node_id"]), row.get("lemmas") or []))
    graph_path.write_text(json.dumps(schemas.validate(graph, "graph/v11"), indent=1) + "\n")


# --- F26-T12 (R16, R17; D-9 v3.39): a formalization review written by hand ---------------------

#: The review's records as the service and the gate's job would file them (every one validated
#: against its schema on the way in, so a test feeds the site the contract's shape): four
#: candidates — a person's surviving, a model's surviving in the same cluster, one discarded by an
#: intent test's exhibit, one the format rule returned — two tests, one question answered (with no
#: source cited) and one waiting, one pair proved both ways and one open, and the intent signer's
#: accept. Ids follow the id grammar (``c-<8 hex>`` of the Lean's sha256, ``t-``, ``e-``,
#: ``q-<n>``).
REVIEW_WORDS = "For all propositions p and q, p and q implies q and p. <b>&</b>"
REVIEW_PROPOSER = "alice-proposer"
REVIEW_INJECTION = "<script>alert('review')</script>"
REVIEW_QUESTION_WAITING = "Suppose p were the only true proposition. Would q and p still hold?"
REVIEW_QUESTION_ANSWERED = "Does the conjecture say anything when p is false?"
REVIEW_ANSWER = f"Yes: the implication holds vacuously. {REVIEW_INJECTION}"
REVIEW_TOOLCHAIN = "leanprover/lean4:v4.33.1"
REVIEW_SIG = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"
REVIEW_SIGNED = {"via": "approval-key", "key": "ssh-ed25519 AAAA", "signature": REVIEW_SIG}
CANDIDATE_LEAN = {
    "person": "theorem Opn.swap (p q : Prop) : p ∧ q → q ∧ p := by\n  sorry\n",
    "model": "theorem Opn.swap' : ∀ (p q : Prop), p ∧ q → q ∧ p := by\n  sorry\n",
    "dropped": "theorem Opn.swap_weak (p q : Prop) : p ∧ q → p := by\n  sorry\n",
    "inline": "theorem Opn.swap_inline (p q : Prop) : (p ∧ q) → (q ∧ p) ∧ True := by\n  sorry\n",
}


def candidate_id(lean: str) -> str:
    return "c-" + schemas.content_hash(lean.encode("utf-8"))[:8]


REVIEW_IDS = {k: candidate_id(v) for k, v in CANDIDATE_LEAN.items()}
TEST_LEAN = {
    "t-0000aaaa": "example : True := trivial -- p = True, q = True\n",
    "t-0000bbbb": "example : True := trivial -- p = False\n",
}


def _exhibit(
    eid: str,
    kind: str,
    candidate: str,
    result: str,
    detail: str,
    *,
    test: str | None = None,
    lean: str | None = "theorem OpnReview.exhibit : True := trivial\n",
) -> dict[str, Any]:
    return {
        "schema": "exhibit/v1",
        "target": TARGET,
        "id": eid,
        "kind": kind,
        "candidate": candidate,
        "test": test,
        "result": result,
        "detail": detail,
        "lean_file": f"{eid}.lean" if lean is not None else None,
        "toolchain": REVIEW_TOOLCHAIN,
        "mathlib_sha": None,
        "run": "local",
        "date": "2026-10-12",
        "_lean": lean,
    }


def review_records() -> dict[str, dict[str, Any]]:
    """path under ``targets/<t>/review/`` -> the record (``_lean`` is the file beside it)."""
    ids = REVIEW_IDS
    day = "2026-10-12"
    docs: dict[str, dict[str, Any]] = {
        "review.yaml": {
            "schema": "review/v1",
            "target": TARGET,
            "opened_by": {"identity": REVIEW_PROPOSER, "role": "proposer"},
            "date": "2026-10-11",
            "words": REVIEW_WORDS,
            "cases": [{"kind": "small-value", "text": "p = q = True: the conclusion holds."}],
            "concepts": ["And"],
            "source": {"kind": "proposal", "ref": "issue:7"},
            "tracking": "issue:7",
            "supersedes": None,
        },
    }
    for key, author, method, models in (
        ("person", "alice", "manual", []),
        ("model", "agent-two", "agent", ["claude-opus-5"]),
        ("dropped", "agent-three", "agent", ["claude-haiku-5"]),
        ("inline", "carol", "manual", []),
    ):
        lean = CANDIDATE_LEAN[key]
        docs[f"candidates/{ids[key]}.yaml"] = {
            "schema": "candidate/v1",
            "target": TARGET,
            "id": ids[key],
            "author": author,
            "method": method,
            "models": models,
            "read_others": False if key == "person" else None,
            "origin": "submitted",
            "source": None,
            "lean_file": f"{ids[key]}.lean",
            "statement_hash": schemas.content_hash(lean.encode("utf-8")),
            "date": day,
            "_lean": lean,
        }
    for tid, (case, source, ref) in {
        "t-0000aaaa": ("p = True, q = True", "agreement", "agreement:2"),
        "t-0000bbbb": ("p = False", "answer", "a-1"),
    }.items():
        docs[f"tests/{tid}.yaml"] = {
            "schema": "intent-test/v1",
            "target": TARGET,
            "id": tid,
            "case": case,
            "probe": "holds",
            "concept": None,
            "expected": {"value": True, "source": source, "ref": ref},
            "author": "gate",
            "lean_file": f"{tid}.lean",
            "date": day,
            "_lean": TEST_LEAN[tid],
        }
    docs["questions/q-1.yaml"] = {
        "schema": "review-question/v1",
        "target": TARGET,
        "id": "q-1",
        "question": REVIEW_QUESTION_ANSWERED,
        "raised_by": {"kind": "disagreement", "ref": "e-0000cccc"},
        "asked_to": "intent",
        "date": day,
    }
    docs["questions/q-2.yaml"] = {
        "schema": "review-question/v1",
        "target": TARGET,
        "id": "q-2",
        "question": REVIEW_QUESTION_WAITING,
        "raised_by": {"kind": "mutant", "ref": "e-0000ffff"},
        "asked_to": "intent",
        "date": day,
    }
    docs["answers/a-1.yaml"] = {
        "schema": "review-answer/v1",
        "target": TARGET,
        "id": "a-1",
        "question": "q-1",
        "answer": REVIEW_ANSWER,
        "cites": None,
        "date": day,
        "login": REVIEW_PROPOSER,
        **REVIEW_SIGNED,
    }
    a, b = sorted((ids["person"], ids["model"]))
    docs[f"pairs/{a}--{b}.yaml"] = {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "forward": {"state": "proved", "exhibit": "e-0000aaaa", "attempt": None},
        "backward": {"state": "proved", "exhibit": "e-0000bbbb", "attempt": None},
        "date": day,
    }
    a2, b2 = sorted((ids["person"], ids["dropped"]))
    docs[f"pairs/{a2}--{b2}.yaml"] = {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a2,
        "b": b2,
        "forward": {"state": "proved", "exhibit": "e-0000dddd", "attempt": None},
        "backward": {
            "state": "open",
            "exhibit": None,
            "attempt": {"who": "gate", "tool": "grind", "budget_s": 20},
        },
        "date": day,
    }
    exhibits = [
        _exhibit("e-0000aaaa", "pair", a, "proved", f"{a} implies {b}", test=b),
        _exhibit("e-0000bbbb", "pair", b, "proved", f"{b} implies {a}", test=a),
        _exhibit(
            "e-0000cccc",
            "intent-test",
            ids["dropped"],
            "fail",
            "holds at p = True, q = True: expected true, the candidate says false "
            + REVIEW_INJECTION,
            test="t-0000aaaa",
            lean="example : ¬ True := by\n  decide -- the kernel's decision on this candidate\n",
        ),
        _exhibit("e-0000dddd", "pair", a2, "proved", f"{a2} implies {b2}", test=b2),
        _exhibit(
            "e-0000eeee",
            "format",
            ids["inline"],
            "returned",
            "the concept And is written inline; name it as a predicate (F26-R5)",
            lean=None,
        ),
        _exhibit("e-0000ffff", "mutant", ids["person"], "pass", "mutant: or for and in the goal"),
        _exhibit("e-0000ff01", "mutant", ids["person"], "fail", "mutant: dropped hypothesis"),
        _exhibit("e-0000ff02", "mutant", ids["person"], "fail", "mutant: q and q for q and p"),
        _exhibit("e-0000ab01", "screen", ids["person"], "pass", "negation not proved"),
        _exhibit("e-0000ab02", "screen", ids["model"], "pass", "negation not proved"),
        _exhibit("e-0000ab03", "compile", ids["person"], "pass", "elaborates at the pin"),
        # the job compiles before it screens, so a screened candidate has a compile on record
        _exhibit("e-0000ab04", "compile", ids["model"], "pass", "elaborates at the pin"),
    ]
    for hexes, cand in (("aa", "person"), ("bb", "model")):
        for n, tid in enumerate(TEST_LEAN):
            exhibits.append(
                _exhibit(
                    f"e-00{hexes}00{n:02d}",
                    "intent-test",
                    ids[cand],
                    "pass",
                    f"{tid} holds as expected",
                    test=tid,
                )
            )
    for ex in exhibits:
        docs[f"exhibits/{ex['id']}.json"] = ex
    docs["signatures/intent-2026-10-12-1.yaml"] = {
        "schema": "review-signature/v1",
        "target": TARGET,
        "role": "intent",
        "decision": "accept",
        "cluster": ids["person"],
        "question": None,
        "date": day,
        "login": REVIEW_PROPOSER,
        **REVIEW_SIGNED,
    }
    return docs


def write_review(root: Path, *, target: str = TARGET) -> Path:
    """Write ``review_records`` under ``targets/<target>/review/``, each validated against its
    schema first (the contract, not a guess), with its Lean beside it; returns the directory."""
    base = root / "targets" / target / "review"
    for rel, doc in review_records().items():
        record = {k: v for k, v in doc.items() if k != "_lean"}
        record["target"] = target
        schemas.validate(record, str(record["schema"]))
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_bytes(schemas.canonical_json(record))
        else:
            path.write_text(
                yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
        if doc.get("_lean") is not None:
            path.with_suffix(".lean").write_text(str(doc["_lean"]), encoding="utf-8")
    return base


def build_with_review(tmp_path: Path) -> Path:
    """The curated fixture with the review above on its target, products rendered by the gate
    (``graph/v9`` and later carry the review's derived state and the open pair directions)."""
    root = curated(tmp_path)
    write_review(root)
    prod = products.generate(root, rendered_from=COMMIT, commit_time=NOW)
    prod.write(root)
    publish_v336(root, lemmas={LEMMA_PARENT: [{"hole": LEMMA_HOLE, "node": LEMMA_NODE}]})
    return root


def publish_review_state(root: Path, state: dict[str, Any], *, target: str = TARGET) -> None:
    """Rewrite the target's ``graph.json`` ``review`` object as the gate would publish it at a
    later stage (T2's derivation), validated against ``graph/v11``; the records are untouched."""
    graph_path = root / "targets" / target / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["review"] = {**graph["review"], **state}
    graph_path.write_text(json.dumps(schemas.validate(graph, "graph/v11"), indent=1) + "\n")


def publish_v8(root: Path, *, target: str = TARGET) -> None:
    """The target's ``graph.json`` as the v3.38 gate wrote it: ``graph/v8``, no review fields."""
    graph_path = root / "targets" / target / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["schema"] = "graph/v8"
    graph.pop("review", None)
    graph.pop("open_pairs", None)
    for row in graph["nodes"]:  # v6-v10 rows carry ``circular``, which F08-T42 dropped in v11
        row.setdefault("circular", [])
        row.pop("closure", None)  # graph/v10 (F28-T8)
    graph_path.write_text(json.dumps(schemas.validate(graph, "graph/v8"), indent=1) + "\n")
