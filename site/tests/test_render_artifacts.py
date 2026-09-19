"""F04-T15 (R14): the Lean itself on the statement page, rather than a link to the record host.

A reader who follows "View the proof →" must arrive at a proof. These cover the three artifacts
that reach the page — the proof, the witness, and each partial assembly — and, above all, what
each one is allowed to *claim*: only a proof's bytes are attested (``artifact_hash``), so only a
proof's caption may say the gate checked them, and a proof whose bytes disagree with the
attestation is withheld rather than shown or crashed over (Q17).
"""

from __future__ import annotations

from pathlib import Path

import fixture
import pytest
import samples
import yaml

from opn_gate import products, schemas
from opn_site import links, model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
PROVED = "tutorial-and-swap"
UNPROVED = "and-swap-reassoc"


def _page(files: dict[str, str], node_id: str) -> str:
    return files[f"nodes/{TARGET}/{node_id}/index.html"]


def _render(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def _node_dir(root: Path, node_id: str) -> Path:
    return root / "targets" / TARGET / "nodes" / node_id


def _regenerate(root: Path) -> None:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("artifacts"))
    return _render(root)


# --- the proof ---------------------------------------------------------------------------------


def test_a_proved_node_shows_its_proof_text_not_only_a_link(rendered: dict[str, str]) -> None:
    """R14: the tactic block itself is on the page, under the statement it discharges.

    The assertion is on the proof's *body*. Its declaration line is no evidence at all: a proof
    restates the statement verbatim (F00-R19), so ``theorem OpnProp.and_swap`` was already on
    the page from the statement block before this task existed. ``exact ...`` is in Proof.lean
    and nowhere else — the statement ends in ``sorry``.
    """
    page = _page(rendered, PROVED)
    assert "exact ⟨h.2, h.1⟩" in page
    assert '<pre class="lean">' in page
    # the link at the merge commit stays: the site shows the mathematics, the graph keeps it
    assert "Proof merged in commit" in page and "/Proof.lean" in page


def test_the_proofs_caption_says_its_bytes_are_the_attested_ones(rendered: dict[str, str]) -> None:
    """Only a proof can say this, because only a proof has an ``artifact_hash`` to compare."""
    page = _page(rendered, PROVED)
    assert "artifact_hash" in page
    assert "these are the bytes the gate checked" in page


def test_an_unproved_node_shows_no_proof_and_no_proof_text(rendered: dict[str, str]) -> None:
    page = _page(rendered, UNPROVED)
    assert "No proof merged yet." in page
    assert "bytes the gate checked" not in page


def test_a_proof_whose_bytes_are_not_the_attested_ones_is_withheld(tmp_path: Path) -> None:
    """Q17: the text is withheld and the reason named — the site still renders (2026-09-17's
    rule: one node's defect must not decide whether the graph has a site)."""
    root = fixture.build(tmp_path)
    proof = _node_dir(root, PROVED) / "Proof.lean"
    tampered = proof.read_text(encoding="utf-8") + "\n-- a byte the attestation never saw\n"
    proof.write_text(tampered, encoding="utf-8")
    files = _render(root)  # must not raise

    page = _page(files, PROVED)
    assert "is not the file the attestation covers" in page
    assert "Its text is withheld here" in page
    assert schemas.content_hash(tampered.encode("utf-8"))[:12] in page
    assert "a byte the attestation never saw" not in page  # the text itself is not shown
    # every other page still rendered
    assert _page(files, UNPROVED) and files["problems/index.html"]


def test_a_tampered_proof_does_not_claim_the_gate_checked_it(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    proof = _node_dir(root, PROVED) / "Proof.lean"
    proof.write_text("theorem wrong : True := trivial\n", encoding="utf-8")
    page = _page(_render(root), PROVED)
    assert "these are the bytes the gate checked" not in page
    assert "theorem wrong" not in page


# --- the witness -------------------------------------------------------------------------------


def test_the_witness_is_shown_with_the_step_that_checked_it(rendered: dict[str, str]) -> None:
    """R14: a witness has no hash anywhere in the protocol, so the page names the step that
    checked it and never claims the bytes were attested."""
    page = _page(rendered, PROVED)
    assert "<h2>Witness</h2>" in page
    assert "theorem witness" in page
    assert "checked at step 7 of the run recorded below" in page
    assert "pass</span>" in page


def test_a_witness_without_a_step_7_record_says_what_is_true_instead(tmp_path: Path) -> None:
    """The fixture's other nodes carry no witness step, so the page says the gate checks it on
    every submission rather than pointing at a run that does not record it."""
    page = _page(_render(fixture.build(tmp_path)), "and-reassoc")
    assert "theorem witness" in page
    assert "the gate checks it at step 7 of every submission" in page
    assert "checked at step 7 of the run recorded below" not in page


SLOT = "/-! Non-vacuity witness slot: `sorry` until someone fills it. -/\n\nsorry\n"


def _open_the_slot(root: Path, node_id: str) -> None:
    (_node_dir(root, node_id) / "Witness.lean").write_text(SLOT, encoding="utf-8")


def test_an_open_witness_slot_says_so_and_names_the_route(tmp_path: Path) -> None:
    """D-29: a hole is created with a slot, not a witness, and cannot pass step 7 until filled.
    The slot is the work, so the page shows it and names where a witness is proposed.

    This node is a hand-authored root, so the gate gives it no ``witness-missing`` cause —
    ``blocked_because`` reserves that for a compiler-derived hole that is blocked. An open slot
    is still work here, which is why the rule keys on the statuses that owe nothing instead.
    """
    root = fixture.build(tmp_path)
    _open_the_slot(root, UNPROVED)
    _regenerate(root)
    page = _page(_render(root), UNPROVED)
    assert "its slot is still open" in page
    assert "/proposals/witness" in page


def test_the_invitation_does_not_depend_on_the_gates_witness_missing_cause(
    tmp_path: Path,
) -> None:
    """The first version of this rule asked for ``cause == "witness-missing"`` and silenced a
    workable node. Pin the distinction: an open slot with no cause at all still invites work."""
    root = fixture.build(tmp_path)
    _open_the_slot(root, UNPROVED)
    _regenerate(root)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes[UNPROVED]

    assert nv.witness_open
    assert nv.cause is None  # the gate names no cause for a hand-authored node
    assert nv.status not in render.NO_WITNESS_OWED
    assert "/proposals/witness" in _page(_render(root), UNPROVED)


def test_a_superseded_nodes_open_slot_invites_nobody(tmp_path: Path) -> None:
    """Q17: found on the live graph — 6 of the 12 nodes with an unfilled slot are superseded by
    a D-8 revision, and the first wording told a reader to go witness every one of them.

    The invitation keys on the gate's own reason (``cause``), not on the stub: a superseded node
    keeps its empty slot for good and owes nobody that work. Same correction the frontier's
    membership rule took in F03-T10, a day before this.
    """
    root = fixture.build(tmp_path)
    _open_the_slot(root, UNPROVED)
    status_dir = _node_dir(root, UNPROVED) / "status"
    status_dir.mkdir(exist_ok=True)
    (status_dir / "20260918T120000Z-curator.yaml").write_text(
        yaml.safe_dump(
            samples.node_status(
                status="superseded",
                cause="curator: replaced by a corrected statement",
                reference="and-reassoc",
            )
        ),
        encoding="utf-8",
    )
    _regenerate(root)
    page = _page(_render(root), UNPROVED)

    assert "no witness is owed here" in page
    assert "superseded" in page
    assert "its slot is still open" not in page
    assert "/proposals/witness" not in page
    assert "sorry" in page  # the slot itself is still shown, as the artifact it is


# --- the partial assemblies --------------------------------------------------------------------


def test_each_partial_assembly_is_shown_as_untrusted_with_its_record(
    rendered: dict[str, str],
) -> None:
    """R4, R14: a partial is contributor Lean no attestation covers, so it is labelled untrusted
    and carries the postmortem's typed fields — outcome, route class, failure class."""
    page = _page(rendered, UNPROVED)
    assert page.count("Untrusted: partial assembly") == 2
    assert "theorem partial_swap" in page and "theorem unnamed_route" in page
    assert "No attestation covers a partial" in page
    assert "outcome <strong>refuted-route</strong>" in page
    assert "route class case-split" in page
    assert "by thisisanameforsure" in page


def test_a_partial_no_record_names_says_so(rendered: dict[str, str]) -> None:
    """The live graph carries bare ``*-partial.lean`` files with no postmortem beside them."""
    page = _page(rendered, UNPROVED)
    assert "no postmortem record names this file" in page
    assert "author not recorded" in page


def test_a_partials_lean_is_escaped(rendered: dict[str, str]) -> None:
    """R3: a partial is the one artifact a hostile contributor writes freely."""
    page = _page(rendered, UNPROVED)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)" not in page


def test_an_alternate_proof_is_not_counted_as_a_partial(tmp_path: Path) -> None:
    """D-25 v3.13: an alternate is a proof, not an attempt, and has its own block."""
    root = fixture.build(tmp_path)
    attempts = _node_dir(root, PROVED) / "attempts"
    attempts.mkdir(exist_ok=True)
    (attempts / "2026-09-04-d-alternate.lean").write_text("theorem alt : True := trivial\n")
    _regenerate(root)
    page = _page(_render(root), PROVED)
    assert "Untrusted: partial assembly" not in page


def test_a_node_with_no_partials_says_so(rendered: dict[str, str]) -> None:
    assert "No partial assembly filed." in _page(rendered, "and-reassoc")


def test_an_invalid_postmortem_does_not_stop_the_page(tmp_path: Path) -> None:
    """``records.load_attempts`` counts a malformed record as invalid rather than raising, and
    the page must agree: one contributor's bad yaml cannot take the site down."""
    root = fixture.build(tmp_path)
    (_node_dir(root, UNPROVED) / "attempts" / "2026-09-05-e.yaml").write_text(
        "schema: postmortem/v1\nnode: [unclosed\n", encoding="utf-8"
    )
    page = _page(_render(root), UNPROVED)
    assert page.count("Untrusted: partial assembly") == 2


def test_a_partial_named_by_a_record_in_a_subdirectory_form_still_matches(tmp_path: Path) -> None:
    """``artifacts.partial_proof`` is a path under ``attempts/``; the match is on the file name,
    so both the bare and the prefixed spelling name the same file."""
    root = fixture.build(tmp_path)
    record = _node_dir(root, UNPROVED) / "attempts" / "2026-09-01-a.yaml"
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    doc["artifacts"] = {"partial_proof": "2026-09-01-a-partial.lean"}  # bare, no attempts/ prefix
    record.write_text(yaml.safe_dump(doc), encoding="utf-8")
    page = _page(_render(root), UNPROVED)
    assert "by thisisanameforsure" in page
    assert page.count("no postmortem record names this file") == 1  # only the genuinely unnamed


# --- what the artifacts must never do ----------------------------------------------------------


def test_every_artifact_links_its_file_at_the_rendered_commit(rendered: dict[str, str]) -> None:
    """R2: showing the text does not replace the provenance link — the graph stays the record."""
    page = _page(rendered, UNPROVED)
    assert f"/blob/{fixture.COMMIT}/targets/{TARGET}/nodes/{UNPROVED}/Witness.lean" in page
    assert (
        f"/blob/{fixture.COMMIT}/targets/{TARGET}/nodes/{UNPROVED}"
        "/attempts/2026-09-01-a-partial.lean" in page
    )


def test_the_artifacts_add_no_script_and_no_off_origin_resource(rendered: dict[str, str]) -> None:
    """R10: the Lean is inert text; nothing about showing it loads anything.

    Only the statement pages are judged here — the copied decisions document is checked under
    its own rules in ``test_links.py`` — so the checker runs with no allowlist and the problems
    are filtered to the pages this task changed.
    """
    problems = links.check(rendered, repo_url=REPO)
    assert [p for p in problems if p.startswith("nodes/")] == []


def test_a_non_utf8_artifact_is_a_named_refusal(tmp_path: Path) -> None:
    """C7: the page would otherwise show replacement characters where the mathematics is.

    The artifact has to be a partial. The gate's own ``layout.check_imports`` decodes
    ``Statement.lean``, ``Proof.lean``, ``Witness.lean`` and ``Context.lean`` before
    ``load_node`` returns, so a node file that is not UTF-8 dies there with a bare
    ``UnicodeDecodeError`` and never reaches this loader; nothing reads an ``attempts/*.lean``
    before the site does, which is the one place the named refusal can fire.
    """
    root = fixture.build(tmp_path)
    bad = _node_dir(root, UNPROVED) / "attempts" / "2026-09-06-f-partial.lean"
    bad.write_bytes(b"theorem f : \xff\xfe := trivial\n")
    with pytest.raises(model.SiteError, match="not valid UTF-8"):
        model.load_site(root, fixture.COMMIT)
