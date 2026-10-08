"""F04-T35: a merged partial, and a proved node, name who the record says submitted them.

Found 2026-10-08 on the live site (graph at or after ``6af6af057``): on ``erdos-1094`` and
``erdos-1094--h3`` the partial-assembly panel said "author not recorded", "no postmortem record
names this file" and "No attestation covers a partial", while ``attestations/000441.json`` and
``000448.json`` are passing, merged attestations whose step 2 took exactly that file
(``partial-submission``) and whose ``submitter`` is ``t1008-a`` — and ``ledger/t1008-a.json``
credits both. The renderer looked for an author in a postmortem only. And the proved hole
``erdos-1094--h1`` showed its attestation's toolchain, Mathlib and steps but never its
``submitter`` (``t1008-b`` in ``000450.json``).

Published state is actual state: the page names what the record names. A partial still never
reads as a proof (F03-Q7): its attestation is a pass against the parent's statement hash that
says the gate took the file as a partial, and nothing in the record hashes its bytes.
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import pytest
import samples

from opn_gate import products, schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
PARENT = "and-swap-reassoc"
PROVED = "tutorial-and-swap"
#: The fixture's partial no postmortem names: the live shape (a merged partial has an
#: attestation, not a postmortem).
UNNAMED = "attempts/2026-09-03-c-partial.lean"
MERGE = "7" * 40


def _partial_steps(path: str) -> list[dict[str, object]]:
    """The steps a live partial's attestation carries (000441.json): step 2 names the file."""
    steps = [dict(s) for s in samples.attestation()["steps"]]
    steps[1]["diagnostic"] = {
        "code": "partial-submission",
        "message": f"a partial proof: {path} (D-12 #5)",
        "details": {"path": path},
    }
    return steps


def _attest_partial(root: Path, n: int, **kw: object) -> None:
    """A passing, merged partial attestation of ``PARENT`` in the live shape of 000441.json:
    ``artifact_hash`` null, the parent's statement hash, step 2 naming the file."""
    doc = samples.attestation(
        **{
            "node_id": PARENT,
            "statement_hash": schemas.content_hash(
                (fixture.nodes_dir(root) / PARENT / "Statement.lean").read_bytes()
            ),
            "artifact_hash": None,
            "merge_commit": MERGE,
            "graph_commit": MERGE,
            "runner": "hosted",
            "submitter": "t1008-a",
            "review": {"kind": "intermediate", "reviewer": None, "reference": None},
            "steps": _partial_steps(UNNAMED),
            **kw,
        }
    )
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def _render(root: Path) -> dict[str, str]:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def _page(files: dict[str, str], node_id: str) -> str:
    return files[f"nodes/{TARGET}/{node_id}/index.html"]


def _partial_label(page: str, file_name: str) -> str:
    """The label paragraph of the partial block rendered from ``file_name``."""
    for block in re.findall(
        r'<div class="prose-block untrusted" data-block="partial">.*?</p>'
        r'<p class="label">(.*?)</p>',
        page,
        re.S,
    ):
        if file_name in block:
            return str(block)
    msg = f"no partial block for {file_name}"
    raise AssertionError(msg)


def _partial_block_label(page: str, file_name: str) -> str:
    """The provenance line (``block-label``) of the partial block rendered from ``file_name``."""
    for head, label in re.findall(
        r'<div class="prose-block untrusted" data-block="partial">(<p class="block-label".*?</p>)'
        r'<p class="label">(.*?)</p>',
        page,
        re.S,
    ):
        if file_name in label:
            return str(head)
    msg = f"no partial block for {file_name}"
    raise AssertionError(msg)


@pytest.fixture
def attested(tmp_path: Path) -> dict[str, str]:
    root = fixture.curated(tmp_path)
    _attest_partial(root, 900)
    return _render(root)


# --- (a) a merged partial ----------------------------------------------------------------------


def test_a_merged_partial_names_the_submitter_its_attestation_records(
    attested: dict[str, str],
) -> None:
    label = _partial_label(_page(attested, PARENT), "2026-09-03-c-partial.lean")
    assert "by t1008-a" in label, label
    assert "author not recorded" not in label, label


def test_a_merged_partial_links_the_attestation_that_took_it(attested: dict[str, str]) -> None:
    label = _partial_label(_page(attested, PARENT), "2026-09-03-c-partial.lean")
    assert "attestations/000900.json" in label, label
    assert MERGE[:12] in label, label
    assert "No attestation covers" not in label, label
    head = _partial_block_label(_page(attested, PARENT), "2026-09-03-c-partial.lean")
    assert "no attestation covers it" not in head, head


def test_a_merged_partial_still_reads_as_an_attempt_not_a_proof(attested: dict[str, str]) -> None:
    """F03-Q7: the attestation says the gate took the file as a partial; it proves nothing, and
    no hash in the record binds these bytes, so the block stays untrusted contributor text."""
    page = _page(attested, PARENT)
    label = _partial_label(page, "2026-09-03-c-partial.lean")
    assert "not a proof" in label, label
    head = _partial_block_label(page, "2026-09-03-c-partial.lean")
    assert 'data-provenance="untrusted"' in head, head
    assert "a partial" in head, head


def test_the_other_partial_keeps_its_postmortem_author(attested: dict[str, str]) -> None:
    """The postmortem-named partial is untouched by the attestation of its sibling."""
    label = _partial_label(_page(attested, PARENT), "2026-09-01-a-partial.lean")
    assert "by thisisanameforsure" in label, label
    assert "attestations/000900.json" not in label, label


def test_a_failing_attestation_naming_the_file_credits_no_one(tmp_path: Path) -> None:
    """Only a passing, merged attestation is the record of a merge (``graph.partials_of``)."""
    root = fixture.curated(tmp_path)
    _attest_partial(root, 900, verdict="fail", first_failing_step=4, merge_commit=None)
    label = _partial_label(_page(_render(root), PARENT), "2026-09-03-c-partial.lean")
    assert "t1008-a" not in label, label
    assert "author not recorded" in label, label


def test_an_attestation_of_another_node_naming_the_same_path_credits_no_one(
    tmp_path: Path,
) -> None:
    root = fixture.curated(tmp_path)
    _attest_partial(
        root,
        900,
        node_id="and-reassoc",
        statement_hash=schemas.content_hash(
            (fixture.nodes_dir(root) / "and-reassoc" / "Statement.lean").read_bytes()
        ),
    )
    label = _partial_label(_page(_render(root), PARENT), "2026-09-03-c-partial.lean")
    assert "t1008-a" not in label, label


def test_a_partial_without_any_record_still_says_so(tmp_path: Path) -> None:
    """The fixture as it was: no attestation and no postmortem name the file."""
    label = _partial_label(
        _page(_render(fixture.curated(tmp_path)), PARENT), "2026-09-03-c-partial.lean"
    )
    assert "author not recorded" in label, label
    assert "No attestation covers a partial" in label, label


# --- (b) a proved node -------------------------------------------------------------------------


def _attestation_facts(page: str) -> str:
    m = re.search(r'<div class="attestation-block".*?<dl class="facts">(.*?)</dl>', page, re.S)
    assert m is not None, "no attestation facts on the page"
    return m.group(1)


def test_a_proved_nodes_attestation_names_its_submitter(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    fixture.attest(
        root,
        PROVED,
        1,
        submitter="t1008-b",
        steps=[*samples.attestation()["steps"], fixture.WITNESS_STEP],
    )
    facts = _attestation_facts(_page(_render(root), PROVED))
    assert "<dt>Submitter</dt><dd><code>t1008-b</code></dd>" in facts, facts


def test_an_attestation_with_no_submitter_says_it_records_none(tmp_path: Path) -> None:
    """Older attestations carry ``submitter: null``; the page says so rather than inventing one."""
    facts = _attestation_facts(_page(_render(fixture.curated(tmp_path)), PROVED))
    assert "<dt>Submitter</dt><dd>not recorded</dd>" in facts, facts


# --- (c) the live shape: a node whose only merge is a partial -----------------------------------


def _live_shaped(tmp_path: Path) -> dict[str, str]:
    """erdos-1094 on 2026-10-08: the node has no ``Proof.lean`` and one merged partial, so the
    partial's attestation is the only attestation of the node and must not read as a proof."""
    root = fixture.curated(tmp_path)
    (fixture.nodes_dir(root) / PARENT / "Proof.lean").unlink()
    _attest_partial(root, 900)
    return _render(root)


def _attestation_section(page: str) -> str:
    m = re.search(r"<h2>Attestation</h2>(.*?)<h2>", page, re.S)
    assert m is not None, "no Attestation section"
    return m.group(1)


def test_a_node_whose_only_merge_is_a_partial_does_not_say_nothing_merged(
    tmp_path: Path,
) -> None:
    """Live 2026-10-08: the root of erdos-1094 said "No attestation: nothing has been merged for
    this statement" beside the partial that merged under attestations/000441.json."""
    page = _page(_live_shaped(tmp_path), PARENT)
    section = _attestation_section(page)
    assert "nothing has been merged" not in section, section
    assert "No proof" in section, section
    assert "attestations/000900.json" in section, section


def test_a_node_whose_only_merge_is_a_partial_is_still_not_proved(tmp_path: Path) -> None:
    """F03-Q7: the partial's passing attestation proves nothing."""
    page = _page(_live_shaped(tmp_path), PARENT)
    assert "status-proved" not in page
    assert "Checked by the kernel" not in _attestation_section(page)


def test_a_node_with_nothing_merged_still_says_so(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    (fixture.nodes_dir(root) / PARENT / "Proof.lean").unlink()
    section = _attestation_section(_page(_render(root), PARENT))
    assert "No attestation: nothing has been merged for this statement." in section, section
