"""F21-T10 / AC10 (states), AC12: words by section — drafted, written, verified, pending (R11,
R13, R15; D-3 v3.31, Q7, Q8).

A gloss is one section, ``whole``. An explainer is its level-2 sections, each known by the steps
its heading names (``steps:`` and the sorted ids), the unanchored one by ``overview``; an
explainer with no anchors at all is one ``overview``. Over a chain, in chain order, a section
unchanged from what the chain shows keeps its state; a model's change over drafted (or absent)
words is ``drafted`` and a person's ``written``, both shown at once; a person's change over
written or verified words is ``pending`` and not shown; a section a valid signature approves is
``verified`` and shown. The model lock itself (R12, ``locked-by-a-person``) is F21-T11.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET
from test_gloss_chains import (
    NODE,
    SIGNER,
    STEWARD,
    chains_of,
    codes,
    explainer,
    front,
    gloss,
    keys,
    node_dir,
    problems,
    put,
    rel,
    root,
    sign_explainer,
)
from test_modes import CURATOR
from test_products import ROOT_NODE, attest, generate, loads

from opn_gate import explainers, glosses, schemas, sections, signed
from opn_gate.paths import Change
from opn_gate.sections import DRAFTED, PENDING, UNCHANGED, VERIFIED, WRITTEN, Entry, Part

__all__ = ["keys", "root"]  # the fixtures, imported for pytest

A, B, C = "overview", "steps:s1", "steps:s2,s3"


def entry(
    version: str,
    *,
    model: bool,
    withdrawn: bool = False,
    author: str | None = None,
    **texts: str,
) -> Entry:
    """A version with sections A, B, C as given (``a=``, ``b=``, ``c=``), in that order."""
    keyed = {"a": A, "b": B, "c": C}
    parts = tuple(Part(keyed[k], t) for k, t in texts.items())
    return Entry(version, parts, model, withdrawn, author)


def placed(found: list[sections.Placed]) -> list[tuple[str, str, str]]:
    return [(p.key, p.version, p.state) for p in found]


# --- parsing (R11, Q8) --------------------------------------------------------------------------


ANCHORED = """## Idea and method
The plan.

## The bound {steps: s4.1 s3}
Two lines.

## The finish {steps: s5}
Done.
"""


def test_an_explainers_sections_are_keyed_by_their_steps() -> None:
    """R11, Q8: the unanchored section is ``overview``; an anchored one is ``steps:`` and its
    step ids sorted and comma-joined, whatever order the heading names them in; the text is the
    heading (without its anchor) and the body."""
    parts = sections.explainer_parts(ANCHORED, explainers.sections(ANCHORED))
    assert [p.key for p in parts] == ["overview", "steps:s3,s4.1", "steps:s5"]
    assert parts[1].text == "## The bound\nTwo lines."
    assert sections.duplicates(parts) == []


def test_an_explainer_without_anchors_is_one_overview() -> None:
    """Q8: an explainer that names no step — filed before F20, or a record on a proof with no
    outline — is one section, ``overview``, holding its whole body."""
    body = "## The idea\nOne.\n\n## More\nTwo.\n"
    [part] = sections.explainer_parts(body, explainers.sections(body))
    assert part.key == "overview" and part.text == body.rstrip()
    legacy = "---\nauthor: someone\ndate: 2026-09-16\n---\nWhy it holds.\n"
    assert sections.parts_of_text(legacy, gloss=False) == [Part("overview", "Why it holds.")]


def test_a_gloss_is_one_section() -> None:
    text = "---\nschema: gloss/v1\n---\nWhat the statement says.\n"
    assert sections.parts_of_text(text, gloss=True) == [Part("whole", "What the statement says.")]


def test_text_equality_ignores_trailing_whitespace_only() -> None:
    """Q8: exact after trimming trailing whitespace on each line and at the end."""
    assert sections.normalize("a  \nb\t\n\n\n") == sections.normalize("a\nb") == "a\nb"
    assert sections.normalize("  a") != sections.normalize("a")
    assert sections.normalize("a\n\nb") != sections.normalize("a\nb")


@pytest.mark.parametrize(
    "body",
    [
        "## One {steps: s1 s2}\nx\n## Two {steps: s2 s1}\ny\n",
        "## One {steps: s1}\nx\n## Two\ny\n## Three\nz\n",
    ],
)
def test_two_sections_of_one_key_are_duplicates(body: str) -> None:
    """R11: two sections naming the same steps (in any order), or two unanchored sections in an
    explainer that anchors others, share a key."""
    parts = sections.explainer_parts(body, explainers.sections(body))
    assert len(sections.duplicates(parts)) == 1


# --- deriving states over a chain (R11; AC10 states half) ----------------------------------------


def test_ac10_draft_edit_signature() -> None:
    """AC10: a model's draft of three sections; a person's edit of one is ``written`` and shown;
    a signature on another verifies it and shows it; the third stays ``drafted``."""
    v1 = entry("v1", model=True, a="draft a", b="draft b", c="draft c")
    v2 = entry("v2", model=False, a="draft a", b="person b", c="draft c")
    got = sections.derive([v1, v2], {"v2": [frozenset({C})]})
    assert got.states["v1"] == [(A, DRAFTED), (B, DRAFTED), (C, DRAFTED)]
    assert got.states["v2"] == [(A, UNCHANGED), (B, WRITTEN), (C, VERIFIED)]
    assert placed(got.shown) == [(A, "v1", DRAFTED), (B, "v2", WRITTEN), (C, "v2", VERIFIED)]
    assert got.pending == []
    assert not got.all_verified()


def test_ac10_a_persons_edit_of_verified_words_is_pending_until_signed() -> None:
    """AC10/AC11 (gate states): a person's edit of the verified section is ``pending``; the chain
    still shows the verified words; a later signature on that section of the edit verifies it,
    shows it, and clears the pending entry."""
    v1 = entry("v1", model=True, a="draft a", b="draft b", c="draft c")
    v2 = entry("v2", model=False, a="draft a", b="person b", c="draft c")
    v3 = entry("v3", model=False, a="draft a", b="person b", c="better c")
    approvals: dict[str, list[frozenset[str] | None]] = {"v2": [frozenset({C})]}
    got = sections.derive([v1, v2, v3], approvals)
    assert got.states["v3"] == [(A, UNCHANGED), (B, UNCHANGED), (C, PENDING)]
    assert placed(got.shown) == [(A, "v1", DRAFTED), (B, "v2", WRITTEN), (C, "v2", VERIFIED)]
    assert placed(got.pending) == [(C, "v3", PENDING)]
    approvals["v3"] = [frozenset({C})]
    got = sections.derive([v1, v2, v3], approvals)
    assert got.states["v3"] == [(A, UNCHANGED), (B, UNCHANGED), (C, VERIFIED)]
    assert placed(got.shown) == [(A, "v1", DRAFTED), (B, "v2", WRITTEN), (C, "v3", VERIFIED)]
    assert got.pending == []


def test_a_persons_edit_of_written_words_is_pending() -> None:
    """R11: written words are a person's; another person's change to them waits for approval."""
    v1 = entry("v1", model=False, author="carol", a="carol's a")
    v2 = entry("v2", model=False, author="dave", a="dave's a")
    got = sections.derive([v1, v2], {})
    assert placed(got.shown) == [(A, "v1", WRITTEN)]
    assert placed(got.pending) == [(A, "v2", PENDING)]


def test_an_authors_edit_of_their_own_written_words_is_shown_at_once() -> None:
    """The owner's ruling of 2026-10-06: a person's edit of words they wrote themselves, not yet
    verified, takes effect at once (``written``, shown). Authors are compared as the record writes
    them; a draft has no author, so no version is a draft's own edit."""
    v1 = entry("v1", model=False, author="carol", a="carol's a", b="carol's b")
    v2 = entry("v2", model=False, author="carol", a="carol's better a", b="carol's b")
    got = sections.derive([v1, v2], {})
    assert got.states["v2"] == [(A, WRITTEN), (B, UNCHANGED)]
    assert placed(got.shown) == [(A, "v2", WRITTEN), (B, "v1", WRITTEN)]
    assert got.pending == []


def test_an_authors_edit_of_their_own_verified_words_is_pending() -> None:
    """The ruling covers written words only: an edit of verified words is pending whoever wrote
    them, until a steward or curator signs it."""
    v1 = entry("v1", model=False, author="carol", a="carol's a")
    v2 = entry("v2", model=False, author="carol", a="carol's better a")
    got = sections.derive([v1, v2], {"v1": [None]})
    assert placed(got.shown) == [(A, "v1", VERIFIED)]
    assert placed(got.pending) == [(A, "v2", PENDING)]


def test_an_authors_own_edit_leaves_anothers_pending_edit_listed() -> None:
    """An author's own edit replaces their shown words but not another person's proposal: dave's
    pending edit stays listed for review (only a signature clears a pending edit)."""
    v1 = entry("v1", model=False, author="carol", a="carol's a")
    v2 = entry("v2", model=False, author="dave", a="dave's a")
    v3 = entry("v3", model=False, author="carol", a="carol's second a")
    got = sections.derive([v1, v2, v3], {})
    assert got.states["v3"] == [(A, WRITTEN)]
    assert placed(got.shown) == [(A, "v3", WRITTEN)]
    assert placed(got.pending) == [(A, "v2", PENDING)]


def test_only_a_named_author_edits_their_own_words() -> None:
    """Two versions with no author (drafts) are never one author's; a model's version by the
    shown words' own author is still the model lock's (read as pending)."""
    v1 = entry("v1", model=False, author="carol", a="carol's a")
    v2 = entry("v2", model=True, author="carol", a="a model's a")
    got = sections.derive([v1, v2], {})
    assert got.states["v2"] == [(A, PENDING)]
    assert placed(got.shown) == [(A, "v1", WRITTEN)]


def test_a_model_may_change_only_drafted_words() -> None:
    """R11: a model's change over drafted words is shown as drafted; over written words it is not
    shown — derived conservatively as pending (the gate refuses it outright, R12, F21-T11)."""
    v1 = entry("v1", model=True, a="draft a", b="draft b")
    v2 = entry("v2", model=False, a="person a", b="draft b")
    v3 = entry("v3", model=True, a="newer model a", b="newer model b")
    got = sections.derive([v1, v2, v3], {})
    assert got.states["v3"] == [(A, PENDING), (B, DRAFTED)]
    assert placed(got.shown) == [(A, "v2", WRITTEN), (B, "v3", DRAFTED)]


def test_a_repeated_pending_edit_is_listed_once() -> None:
    """A later version carrying an earlier pending edit unchanged is pending too, and the edit is
    listed once, under the version that first proposed it."""
    v1 = entry("v1", model=False, a="carol's a", b="carol's b")
    v2 = entry("v2", model=False, a="dave's a", b="carol's b")
    v3 = entry("v3", model=False, a="dave's a", b="erin's b")
    got = sections.derive([v1, v2, v3], {})
    assert got.states["v3"] == [(A, PENDING), (B, PENDING)]
    assert placed(got.pending) == [(A, "v2", PENDING), (B, "v3", PENDING)]


def test_omitted_sections() -> None:
    """Q (proposed): a later version that omits a drafted section removes it; one that omits a
    written or verified section leaves it shown, after the current version's own sections."""
    v1 = entry("v1", model=True, a="draft a", b="draft b", c="draft c")
    v2 = entry("v2", model=False, a="draft a", b="person b", c="draft c")
    v3 = entry("v3", model=False, c="draft c")
    got = sections.derive([v1, v2, v3], {})
    assert placed(got.shown) == [(C, "v1", DRAFTED), (B, "v2", WRITTEN)]


def test_a_withdrawn_version_shows_nothing() -> None:
    """R7: a withdrawn version is absent from its chain — its sections take no place in what is
    shown; its own states are read at its place without effect."""
    v1 = entry("v1", model=False, a="carol's a")
    v2 = entry("v2", model=False, withdrawn=True, a="dave's a")
    got = sections.derive([v1, v2], {"v2": [None]})
    assert placed(got.shown) == [(A, "v1", WRITTEN)]
    assert got.states["v2"] == [(A, VERIFIED)]
    assert got.pending == []
    assert sections.derive([v2], {}).shown == []


def test_a_legacy_draft_counts_as_a_models_words() -> None:
    """A version with F20's drafter block is a model's, for states, as ``drafted_with`` is."""
    draft = glosses.Version(
        "d" * 64, Path("x.md"), ("proof", NODE, None), None, None, {"name": "opn-drafter"}, None,
        "explainer/v1",
    )  # fmt: skip
    assert draft.by_model
    person = glosses.Version("e" * 64, Path("y.md"), ("proof", NODE, None), None, "carol", None,
                             None, "explainer/v2")  # fmt: skip
    assert not person.by_model
    assert glosses.Version(
        "f" * 64, Path("z.md"), ("proof", NODE, None), None, "carol", None, None,
        "explainer/v2", drafted_with="a model",
    ).by_model  # fmt: skip


# --- AC12: a signature approves the sections it names --------------------------------------------


THREE = """## Idea
The plan.

## The bound {steps: s1}
One.

## The finish {steps: s2 s3}
Two.
"""


def anchored_explainer(root: Path, body: str = THREE, *, author: str = "carol") -> str:
    proof = schemas.content_hash((node_dir(root) / "Proof.lean").read_bytes())
    doc = {
        "schema": "explainer/v1",
        "target": TARGET,
        "node": NODE,
        "proof": proof,
        "supersedes": None,
        "author": author,
        "drafter": None,
        "date": "2026-10-05",
        "licence": "CC-BY-4.0",
    }
    return put(node_dir(root) / "explainer", front(doc, body)).stem


def sign_sections(root: Path, digest: str, approves: list[str] | None, key: Path) -> Change:
    path = explainers.sign(
        node_dir(root), digest, target_id=TARGET, signer_login=CURATOR, date="2026-10-05",
        key_path=key, signer=SIGNER, approves=approves,
    )  # fmt: skip
    return Change("A", rel(root, path))


def test_a_signature_approves_the_sections_it_names(root: Path, keys: dict[str, Path]) -> None:
    """AC12: a v2 signature naming two of three sections verifies only those two; a v1
    signature verifies every section of its version. Both validate and pass the gate."""
    digest = anchored_explainer(root)
    change = sign_sections(root, digest, [A, B], keys[CURATOR])
    assert yaml_of(root, change)["schema"] == "explainer-signature/v2"
    assert codes(root, change, author=CURATOR) == []
    [chain] = chains_of_v2(root, "proof")
    assert chain["shown"] == [
        {"key": A, "version": digest, "state": VERIFIED},
        {"key": B, "version": digest, "state": VERIFIED},
        {"key": C, "version": digest, "state": WRITTEN},
    ]
    [version] = chain["versions"]
    assert version["signatures"][0]["sections"] == [A, B]
    whole = sign_sections(root, digest, None, keys[CURATOR])
    assert yaml_of(root, whole)["schema"] == "explainer-signature/v1"
    [chain] = chains_of_v2(root, "proof")
    assert [s["state"] for s in chain["shown"]] == [VERIFIED, VERIFIED, VERIFIED]
    assert chain["versions"][0]["signatures"][1]["sections"] is None


def test_a_signature_naming_an_unknown_section_is_refused(
    root: Path, keys: dict[str, Path]
) -> None:
    """R13: every section a v2 signature names is one the signed version has
    (``signature-section-unknown``); the writer refuses the same before writing anything."""
    digest = anchored_explainer(root)
    with pytest.raises(explainers.ExplainerError):
        sign_sections(root, digest, ["steps:s9"], keys[CURATOR])
    doc = {
        "schema": "explainer-signature/v2",
        "target": TARGET,
        "node": NODE,
        "explainer": digest,
        "affirmation": explainers.AFFIRMATION,
        "signer": CURATOR,
        "date": "2026-10-05",
        "sections": [A, "steps:s9"],
    }
    path = explainers.next_path(node_dir(root), digest)
    write_signed(path, doc, keys[CURATOR])
    assert codes(root, Change("A", rel(root, path)), author=CURATOR) == [
        "signature-section-unknown"
    ]
    # A gloss is one section, whole.
    g, _ = gloss(root, "Words.")
    gdoc = {
        "schema": "gloss-signature/v2",
        "target": TARGET,
        "node": NODE,
        "gloss": g,
        "affirmation": glosses.AFFIRMATION,
        "signer": CURATOR,
        "date": "2026-10-05",
        "sections": ["overview"],
    }
    gpath = glosses.next_signature_path(node_dir(root), g)
    write_signed(gpath, gdoc, keys[CURATOR])
    assert codes(root, Change("A", rel(root, gpath)), author=CURATOR) == [
        "signature-section-unknown"
    ]
    with pytest.raises(glosses.GlossError):
        glosses.sign(
            node_dir(root), g, target_id=TARGET, node_id=NODE, signer_login=CURATOR,
            date="2026-10-05", key_path=keys[CURATOR], signer=SIGNER, approves=["overview"],
        )  # fmt: skip
    ok = glosses.sign(
        node_dir(root), g, target_id=TARGET, node_id=NODE, signer_login=CURATOR,
        date="2026-10-05", key_path=keys[CURATOR], signer=SIGNER, approves=["whole"],
    )  # fmt: skip
    assert codes(root, Change("A", rel(root, ok)), author=CURATOR) == []


def test_a_version_with_two_sections_of_one_key_is_refused(root: Path) -> None:
    """AC10: an explainer record with two sections on the same steps is ``section-duplicate``."""
    digest = anchored_explainer(root, "## One {steps: s1 s2}\nx\n\n## Two {steps: s2 s1}\ny\n")
    path = node_dir(root) / "explainer" / f"{digest}.md"
    assert codes(root, Change("A", rel(root, path))) == ["section-duplicate"]


# --- the model lock (R12; AC10 lock half, F21-T11) ----------------------------------------------


#: The Lean lines each outline step spans in the fixture's outline of ``and-reassoc``'s proof.
SPANS = {"s1": (3, 4), "s2": (5, 7), "s3": (8, 12)}
MODEL = "anthropic/claude-opus-5.5 via Claude Code"


def write_outline(root: Path) -> str:
    """F19's committed outline of the node's ``Proof.lean``, steps s1 to s3 at ``SPANS``."""
    proof = schemas.content_hash((node_dir(root) / "Proof.lean").read_bytes())
    doc = {
        "schema": "outline/v1",
        "target": TARGET,
        "node": NODE,
        "artifact": {"path": "Proof.lean", "hash": proof, "kind": "proof"},
        "gate": "9" * 40,
        "steps": [lock_step(i, *SPANS[i]) for i in SPANS],
    }
    assert schemas.violations(doc, "outline/v1") == []
    out = root / "targets" / TARGET / "outlines" / f"{proof}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(schemas.canonical_json(doc))
    return proof


def lock_step(step_id: str, start: int, end: int) -> dict[str, Any]:
    claim = {"text": "True", "printed": "reliable", "truncated": False}
    return {
        "id": step_id, "kind": "have", "name": step_id, "claim": claim, "goal": None,
        "span": {"start_line": start, "end_line": end},
        "uses": {"nodes": [], "defs": [], "mathlib": []},
        "closed_by": {"kind": "automation", "tactics": ["simp"]}, "child_node": None,
        "children": [],
    }  # fmt: skip


def three(a: str, b: str, c: str) -> str:
    """An explainer body with sections A (overview), B (s1) and C (s2, s3)."""
    return (
        f"## Idea\n{a}\n\n## The bound {{steps: s1}}\n{b}\n\n## The finish {{steps: s2 s3}}\n{c}\n"
    )


def version(
    root: Path,
    body: str,
    *,
    author: str,
    drafted_with: str | None,
    supersedes: str | None = None,
) -> tuple[str, Change]:
    """An ``explainer/v2`` version of the node's proof, written into the tree."""
    doc = {
        "schema": "explainer/v2",
        "target": TARGET,
        "node": NODE,
        "proof": schemas.content_hash((node_dir(root) / "Proof.lean").read_bytes()),
        "supersedes": supersedes,
        "author": author,
        "drafter": None,
        "date": "2026-10-06",
        "licence": "CC-BY-4.0",
        "drafted_with": drafted_with,
    }
    path = put(node_dir(root) / "explainer", front(doc, body))
    return path.stem, Change("A", rel(root, path))


@pytest.fixture
def ac10(root: Path, keys: dict[str, Path]) -> tuple[Path, str]:
    """AC10's chain, merged: a model's draft of three sections (v1), a person's edit of B (v2)
    and a curator's signature on C of v2. Answers the root and v2, the chain's head."""
    write_outline(root)
    v1, _ = version(root, three("draft a", "draft b", "draft c"), author="carol",
                    drafted_with=MODEL)  # fmt: skip
    v2, _ = version(root, three("draft a", "dave's b", "draft c"), author="dave",
                    drafted_with=None, supersedes=v1)  # fmt: skip
    sign_sections(root, v2, [C], keys[CURATOR])
    return root, v2


def test_ac10_a_second_model_may_change_only_the_drafted_section(
    ac10: tuple[Path, str],
) -> None:
    """AC10: the chain shows A drafted, B written and C verified; a second model's version that
    changes only A is accepted."""
    root, v2 = ac10
    [chain] = chains_of_v2(root, "proof")
    assert [(s["key"], s["state"]) for s in chain["shown"]] == [
        (A, DRAFTED), (B, WRITTEN), (C, VERIFIED)
    ]  # fmt: skip
    _, change = version(root, three("a newer model's a", "dave's b", "draft c"), author="erin",
                        drafted_with="another model", supersedes=v2)  # fmt: skip
    assert codes(root, change) == []


@pytest.mark.parametrize(
    ("changed", "key", "lines"),
    [
        (three("draft a", "a model's b", "draft c"), B, [3, 4]),
        (three("draft a", "dave's b", "a model's c"), C, [5, 12]),
        ("## Idea\ndraft a\n\n## The finish {steps: s2 s3}\ndraft c\n", B, [3, 4]),
    ],
    ids=["changes-written", "changes-verified", "omits-written"],
)
def test_ac10_a_model_changing_written_or_verified_words_is_refused_naming_the_lines(
    ac10: tuple[Path, str], changed: str, key: str, lines: list[int]
) -> None:
    """R12: a version with ``drafted_with`` that changes or omits a section the chain shows as
    written or verified is ``locked-by-a-person``, naming the section and the Lean lines its steps
    span in the outline (the least start to the greatest end)."""
    root, v2 = ac10
    _, change = version(root, changed, author="erin", drafted_with="another model",
                        supersedes=v2)  # fmt: skip
    found = problems(root, change)
    assert [d.code for d in found] == ["locked-by-a-person"]
    assert found[0].details["section"] == key
    assert found[0].details["file"] == f"nodes/{NODE}/Proof.lean"
    assert found[0].details["lines"] == lines
    assert key in found[0].message and f"lines {lines[0]}-{lines[1]}" in found[0].message


def test_a_persons_version_is_never_refused_by_the_lock(ac10: tuple[Path, str]) -> None:
    """R12 binds models only: a person's change to written or verified words merges, pending."""
    root, v2 = ac10
    _, change = version(root, three("draft a", "erin's b", "erin's c"), author="erin",
                        drafted_with=None, supersedes=v2)  # fmt: skip
    assert codes(root, change) == []


def test_a_models_gloss_over_a_persons_words_is_refused_naming_the_file(root: Path) -> None:
    """A gloss is one section, ``whole``: a model's version over a person's gloss is
    ``locked-by-a-person`` naming the whole Lean file it describes (no line span)."""
    first, _ = gloss(root, "A person's words.")
    file = node_dir(root) / glosses.KIND_FILES["statement"]
    doc = {
        "schema": "gloss/v2",
        "target": TARGET,
        "subject": {"kind": "statement", "node": NODE, "module": None,
                    "lean_hash": schemas.content_hash(file.read_bytes())},
        "supersedes": first, "author": "erin", "drafter": None, "date": "2026-10-06",
        "licence": "CC-BY-4.0", "drafted_with": MODEL,
    }  # fmt: skip
    path = put(node_dir(root) / "gloss", front(doc, "A model's words."))
    found = problems(root, Change("A", rel(root, path)))
    assert [d.code for d in found] == ["locked-by-a-person"]
    assert found[0].details["section"] == "whole"
    assert found[0].details["file"] == f"nodes/{NODE}/Statement.lean"
    assert found[0].details["lines"] is None
    # A model's version that starts a chain of its own supersedes nothing a person wrote.
    doc |= {"supersedes": None}
    fresh = put(node_dir(root) / "gloss", front(doc, "A model's first words."))
    assert codes(root, Change("A", rel(root, fresh))) == []


# --- the product and digestion (R14, R15) --------------------------------------------------------


def test_the_product_publishes_shown_and_pending(root: Path, keys: dict[str, Path]) -> None:
    """R14: a person's edit of a signed explainer stays pending in ``glosses/v2`` and the chain
    shows the signed words; the product validates."""
    first, _ = explainer(root, "First account.")
    sign_explainer(root, first, STEWARD, keys[STEWARD])
    second, _ = explainer(root, "A rewrite.", supersedes=first, author="dave")
    [chain] = chains_of_v2(root, "proof")
    assert chain["current"] == second
    assert chain["shown"] == [{"key": A, "version": first, "state": VERIFIED}]
    assert chain["pending"] == [{"key": A, "version": second, "state": PENDING}]
    states = {v["hash"]: v["sections"] for v in chain["versions"]}
    assert states == {
        first: [{"key": A, "state": VERIFIED}],
        second: [{"key": A, "state": PENDING}],
    }


def test_digestion_counts_a_node_while_every_shown_section_is_verified(
    root: Path, keys: dict[str, Path]
) -> None:
    """R15: a node is explained while every section shown for its first proof is verified: a v2
    signature on two of three sections leaves it unexplained, one on the third explains it."""
    for n, node in enumerate(("tutorial-and-swap", "and-reassoc", ROOT_NODE), start=1):
        attest(root, node, n=n)
    for node in ("tutorial-and-swap", ROOT_NODE):
        head, _ = explainer(root, f"Why {node} holds.", node=node)
        sign_explainer(root, head, STEWARD, keys[STEWARD], node=node)
    digest = anchored_explainer(root)
    sign_sections(root, digest, [A, B], keys[CURATOR])

    def state() -> Any:
        return loads(generate(root), "targets/index.json")["targets"][0]["digestion"]["state"]

    assert state() == "undigested"
    sign_sections(root, digest, [C], keys[CURATOR])
    assert state() == "explained"


# --- helpers -------------------------------------------------------------------------------------


def chains_of_v2(root: Path, kind: str) -> list[dict[str, Any]]:
    doc = loads(generate(root), f"targets/{TARGET}/glosses.json")
    assert doc["schema"] == "glosses/v2"
    assert schemas.violations(doc) == []
    return chains_of(root, kind)


def yaml_of(root: Path, change: Change) -> dict[str, Any]:
    return dict(yaml.safe_load((root / change.path).read_text(encoding="utf-8")))


def write_signed(path: Path, doc: dict[str, Any], key: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = signed.sign(doc, key, SIGNER)
    path.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")


def test_an_own_edit_must_be_opened_by_its_author(ac10: tuple[Path, str]) -> None:
    """F21-Q14 (the owner's ruling on own edits, Q10, made safe): an author's edit of their own
    written words shows at once, so the gate must know the author is who opened the pull request.
    A hand-opened version naming ``dave`` that changes the section dave wrote is refused
    ``author-not-opener`` when someone else opened it, and passes when dave did. Only the own-edit
    privilege is checked: a version under someone else's name that merely proposes a change is
    pending, not refused (the service writes the author from the token, so its pull requests are
    never in question)."""
    root, v2 = ac10
    _, change = version(root, three("draft a", "dave's better b", "draft c"), author="dave",
                        drafted_with=None, supersedes=v2)  # fmt: skip
    assert codes(root, change, author="mallory") == ["author-not-opener"]
    assert codes(root, change, author="dave") == []


def test_a_proposal_under_another_name_is_pending_not_refused(ac10: tuple[Path, str]) -> None:
    """The rule is about the own-edit privilege only: a hand-opened version by ``erin`` changing
    dave's section is pending (never shown), so its author's name gains nothing and is not
    checked against the opener here."""
    root, v2 = ac10
    _, change = version(root, three("draft a", "erin's b", "draft c"), author="erin",
                        drafted_with=None, supersedes=v2)  # fmt: skip
    assert codes(root, change, author="mallory") == []
