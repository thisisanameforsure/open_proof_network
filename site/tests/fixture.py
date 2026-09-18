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


def build(tmp_path: Path) -> Path:
    """The graph in its curated state with products written; returns the checkout root."""
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
