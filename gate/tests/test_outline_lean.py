"""F19-T1, T3: ``opn-outline`` with the real toolchain over Lean-core fixtures (AC1, AC3, AC4,
AC6, AC13). Lean tier.

The fixtures are under ``fixtures/outline/``, one theorem each (``Casts`` has two), Lean core
only, so the tier needs no Mathlib. The Mathlib half of AC4 (a real Stacks tag at the pinned
Mathlib) is the measurement script's to show (``gate/tools/measure_outline.py``); here the tag
path is driven through a stand-in for Mathlib's reader (``Tagged.lean`` says how).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opn_gate import outline, schemas
from opn_gate.toolchain import LocalToolchain, MetaprogramResult, OutlineRequest, ResolvedToolchain

pytestmark = pytest.mark.lean

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "outline"
GATE = "f" * 40
CAPS = outline.Caps()


@pytest.fixture(scope="module")
def seam(real_toolchain: LocalToolchain, lean_pkg: Path) -> LocalToolchain:
    assert (lean_pkg / "opn-outline").is_file()
    return LocalToolchain(real_toolchain.elan, lean_pkg)


def job(stem: str, decl: str, *, holes: dict[str, str | None] | None = None) -> outline.Job:
    return outline.Job(
        target="fixture",
        node="root",
        artifact=outline.Artifact(path=f"{stem}.lean", hash="0" * 64, kind="proof"),
        file=FIXTURES / f"{stem}.lean",
        module=stem,
        decl=decl,
        holes=holes or {},
    )


def raw(
    seam: LocalToolchain, pinned: ResolvedToolchain, stem: str, decl: str, *extra: str
) -> dict[str, Any]:
    """The program's own answer; ``extra`` arguments go to the binary (``--printer plain``)."""
    req = outline.request(job(stem, decl), CAPS)
    result: MetaprogramResult = seam._metaprogram_run(
        pinned, "opn-outline", [*req.args(), *extra], [], 300
    )
    assert result.ok, result.output or result.doc
    return result.doc


def doc(seam: LocalToolchain, pinned: ResolvedToolchain, j: outline.Job) -> dict[str, Any]:
    """The validated outline/v1 document, through the wrapper."""
    out = outline.extract(seam, pinned, j, gate=GATE, caps=CAPS)
    assert out.reason is None, (out.reason, out.detail)
    assert out.doc is not None
    return schemas.validate(out.doc, "outline/v1")


def brief(steps: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    """(id, kind, name, span, closing) for every step, depth first."""
    out: list[tuple[Any, ...]] = []
    for s in steps:
        span = (s["span"]["start_line"], s["span"]["end_line"])
        closing = (s["closed_by"]["kind"], tuple(s["closed_by"]["tactics"]))
        out.append((s["id"], s["kind"], s["name"], span, closing))
        out += brief(s["children"])
    return out


def test_have_tree_with_kinds_spans_and_closing(
    seam: LocalToolchain, pinned: ResolvedToolchain
) -> None:
    """F19-AC1: two named haves, the first closed by ``omega`` (automation), the second by three
    tactics with a nested ``obtain``; kinds, names, spans and closings as written."""
    d = doc(seam, pinned, job("Steps", "OpnOutline.steps"))
    assert brief(d["steps"]) == [
        ("h1", "have", "h1", (6, 6), ("automation", ("omega",))),
        ("key", "have", "key", (7, 10), ("steps", ())),
        ("key.s1", "obtain", None, (8, 8), ("term", ())),
        ("key.s2", "show", None, (9, 9), ("steps", ())),
        # F22-T14: the trailing `exact`, which no step encloses, is the `close` step.
        ("close", "term", None, (11, 11), ("steps", ())),
    ]
    h1, key, _ = d["steps"]
    assert h1["claim"] == {"text": "a + (1 : Nat) ≤ b", "printed": "reliable", "truncated": False}
    # The goal h1 leaves: the theorem's target, with h1 the one hypothesis it introduced.
    assert [h["name"] for h in h1["goal"]["hypotheses"]] == ["h1"]
    assert h1["goal"]["target"]["printed"] == "reliable"
    obtain, show = key["children"]
    assert [h["name"] for h in obtain["goal"]["hypotheses"]] == ["x", "y"]
    assert show["claim"]["text"] == "x + (0 : Nat) = x"
    # The `exact` after the `show` is written in `key`, not in the `show`: a tactic folds into
    # the step whose source contains it, so `key` uses `Nat.add_zero` and the `show` uses nothing.
    assert show["uses"] == {"nodes": [], "defs": [], "mathlib": []}
    assert [c["name"] for c in key["uses"]["mathlib"]] == ["Nat.add_zero"]


def test_claims_read_back_or_are_marked(seam: LocalToolchain, pinned: ResolvedToolchain) -> None:
    """F19-AC3: a claim over the integers with natural casts reads back under the hole writer's
    options; printed without them (``--printer plain``, the stub that drops ascriptions) it does
    not, and is marked; and a claim that names an inaccessible local is unreliable whatever the
    printer, because no source can name it."""
    good = raw(seam, pinned, "Casts", "OpnOutline.casts")["steps"][0]
    assert good["name"] == "hc"
    assert good["claim"]["printed"] == "reliable"
    assert "(↑n : Int)" in good["claim"]["text"], good["claim"]
    plain = raw(seam, pinned, "Casts", "OpnOutline.casts", "--printer", "plain")["steps"][0]
    assert plain["claim"]["printed"] == "unreliable", plain["claim"]
    assert "Int" not in plain["claim"]["text"]
    hidden = raw(seam, pinned, "Casts", "OpnOutline.hidden")["steps"][0]
    assert hidden["name"] == "e" and "✝" in hidden["claim"]["text"]
    assert hidden["claim"]["printed"] == "unreliable"
    # Through the wrapper, the mark survives into the document.
    d = doc(seam, pinned, job("Casts", "OpnOutline.hidden"))
    assert d["steps"][0]["claim"]["printed"] == "unreliable"


def test_mathlib_docs_and_tags(seam: LocalToolchain, pinned: ResolvedToolchain) -> None:
    """F19-AC4 in Lean core: a used core constant carries its docstring's first sentence, one
    without a docstring carries ``null``, and with no cross-reference attribute nothing has a
    tag. With a stand-in for Mathlib's reader, each tagged constant carries its Stacks or Kerodon
    tag and no other database's; and no constant from any other source is recorded."""
    plain = doc(seam, pinned, job("Docs", "OpnOutline.docs"))
    h, e, close = plain["steps"]  # F22-T14: the trailing `exact` is the close step
    assert close["id"] == "close"
    assert h["uses"]["mathlib"] == [
        {"name": "Or.inl", "doc": '`Or.inl` is "left injection" into an `Or`.', "tags": []}
    ]
    assert [c["name"] for c in e["uses"]["mathlib"]] == ["Nat.add_zero"]
    assert all(c["tags"] == [] for s in plain["steps"] for c in s["uses"]["mathlib"])

    tagged = doc(seam, pinned, job("Tagged", "OpnOutline.tagged"))
    h, e, _ = tagged["steps"]
    assert h["uses"]["mathlib"] == [
        {
            "name": "Or.inl",
            "doc": '`Or.inl` is "left injection" into an `Or`.',
            "tags": [{"database": "stacks", "tag": "0ABC"}],
        }
    ]
    assert e["uses"]["mathlib"][0]["tags"] == [{"database": "kerodon", "tag": "01AZ"}]
    assert all(s["uses"]["nodes"] == [] and s["uses"]["defs"] == [] for s in tagged["steps"])


def test_term_proof_is_one_step(seam: LocalToolchain, pinned: ResolvedToolchain) -> None:
    """F19-AC6: a term-mode proof is one ``term`` step whose claim is the statement."""
    d = doc(seam, pinned, job("Term", "OpnOutline.term"))
    assert brief(d["steps"]) == [("s1", "term", None, (4, 4), ("term", ()))]
    [only] = d["steps"]
    assert only["claim"] == {
        "text": "∀ (n : Nat), n + (0 : Nat) = n",
        "printed": "reliable",
        "truncated": False,
    }
    assert only["goal"] is None
    assert [c["name"] for c in only["uses"]["mathlib"]] == ["Nat.add_zero"]


def test_partial_assembly_marks_holes(seam: LocalToolchain, pinned: ResolvedToolchain) -> None:
    """F19-AC13: a two-hole partial assembly's ``sorry`` steps are hole steps, each naming the
    child node the caller's decompositions give it (``by sorry`` as much as ``sorry``)."""
    holes: dict[str, str | None] = {"h1": "root--h1", "h2": "root--h2"}
    d = doc(seam, pinned, job("Partial", "OpnOutline.partial", holes=holes))
    assert brief(d["steps"]) == [
        ("h1", "hole", "h1", (4, 4), ("hole", ())),
        ("h2", "hole", "h2", (5, 5), ("hole", ())),
        ("close", "term", None, (6, 6), ("steps", ())),  # F22-T14
    ]
    assert [s["child_node"] for s in d["steps"]] == ["root--h1", "root--h2", None]
    assert [s["claim"]["text"] for s in d["steps"][:2]] == ["n ≠ (0 : Nat)", "(1 : Nat) ≤ n"]


def test_the_seam_names_a_file_that_does_not_elaborate(
    seam: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    """R5 with the real program: an artifact that does not elaborate is a named reason."""
    bad = tmp_path / "Bad.lean"
    bad.write_text("theorem OpnOutline.bad : 1 = 2 := rfl\n", encoding="utf-8")
    j = outline.Job(
        target="fixture",
        node="root",
        artifact=outline.Artifact(path="Bad.lean", hash="0" * 64, kind="proof"),
        file=bad,
        module="Bad",
        decl="OpnOutline.bad",
        holes={},
    )
    out = outline.extract(seam, pinned, j, gate=GATE, caps=CAPS)
    assert out.reason == outline.FAILED and "does not elaborate" in out.detail


def test_request_shape_is_the_programs(seam: LocalToolchain, pinned: ResolvedToolchain) -> None:
    """The arguments the wrapper builds are the ones the program reads (no drift)."""
    req = OutlineRequest(
        file=FIXTURES / "Term.lean",
        module="Term",
        decl="OpnOutline.term",
        automation=("omega",),
        doc_modules=("Init",),
    )
    result = seam.outline(pinned, req, [], timeout_s=300)
    assert result.ok and result.doc["decl"] == "OpnOutline.term"


def hypotheses(step: dict[str, Any]) -> list[str]:
    return [h["name"] for h in (step["goal"] or {}).get("hypotheses", [])]


@pytest.mark.parametrize("decl", ["OpnOutline.split", "OpnOutline.alts", "OpnOutline.named"])
def test_a_case_branch_lists_what_its_split_introduced(
    seam: LocalToolchain, pinned: ResolvedToolchain, decl: str
) -> None:
    """F22-T14 (testers 2026-10-06, FR J): a branch's goal lists the hypotheses the split gave it
    (``a`` in the left branch, ``b`` in the right), read against the goal before the split and
    not against the goal the branch itself starts on, which already holds them. Three shapes: a
    ``·`` after ``rcases``, an alternative of ``cases … with``, and ``case inl a =>``, whose
    renaming keeps the variable but changes its name."""
    d = doc(seam, pinned, job("Cases", decl))
    assert [(s["id"], s["kind"]) for s in d["steps"]] == [("s1", "case"), ("s2", "case")]
    assert [hypotheses(s) for s in d["steps"]] == [["a"], ["b"]]


def test_trailing_closing_tactics_are_the_close_step(
    seam: LocalToolchain, pinned: ResolvedToolchain
) -> None:
    """F22-T14: the tactics after a proof's last top-level step, which no step encloses, are one
    step with the reserved id ``close``, outside the ``s<n>`` numbering so no other id moves; its
    claim is the goal they close and it uses the constants written in them. A proof with no step
    at all is one ``close`` step."""
    d = doc(seam, pinned, job("Cases", "OpnOutline.closing"))
    assert [(s["id"], s["kind"], s["span"]["start_line"], s["span"]["end_line"])
            for s in d["steps"]] == [("h", "have", 20, 20), ("close", "term", 21, 22)]  # fmt: skip
    close = d["steps"][1]
    assert close["claim"]["text"] == "n + (0 : Nat) = n ∧ (0 : Nat) + n = n", close["claim"]
    assert close["goal"] is None and close["children"] == [] and close["name"] is None
    assert [c["name"] for c in close["uses"]["mathlib"]] == ["And.intro", "Nat.zero_add"]
    only = doc(seam, pinned, job("Cases", "OpnOutline.onlyClose"))
    assert [(s["id"], s["span"]["start_line"]) for s in only["steps"]] == [("close", 25)]
    # A proof whose last top-level step closes it has no close step.
    split = doc(seam, pinned, job("Cases", "OpnOutline.split"))
    assert "close" not in [s["id"] for s in split["steps"]]


PUBLISHED = FIXTURES / "published"


@pytest.mark.parametrize(
    ("digest", "decl"),
    [
        ("721b98ef97040596c6625c36749b28dfddbe4156fb84c31dcb5e4145b4f4222d", "OpnProp.and_swap"),
        (
            "df375af29a9b41444121a30a5577ad2324708de0aec71444cbdcb2f5c56302b0",
            "OpnProp.and_left_of_and_swap",
        ),
    ],
)
def test_a_published_outline_keeps_every_id(
    seam: LocalToolchain, pinned: ResolvedToolchain, digest: str, decl: str
) -> None:
    """F22-T14's invariant on outlines the live graph published: the graph's two Lean-core ones
    (tutorial, at graph 3257eb5c, extracted by gate 82834c46), copied with their artifacts under
    ``fixtures/outline/published/``. Outlined again by this gate, every id they carry is there
    with the same span (``outline.lost_ids``), because explainers anchor on them; what is new is
    only added. The Mathlib outlines are checked by ``gate/tools/check_outline_ids.py``."""
    published = schemas.validate(
        json.loads((PUBLISHED / f"{digest}.json").read_text(encoding="utf-8")),
        "outline/v1",
    )
    j = outline.Job(
        target="tutorial",
        node=published["node"],
        artifact=outline.Artifact(
            path=published["artifact"]["path"], hash=digest, kind=published["artifact"]["kind"]
        ),
        file=PUBLISHED / f"{digest}.lean",
        module="Published",
        decl=decl,
        holes={},
    )
    again = doc(seam, pinned, j)
    assert outline.lost_ids(published, again) == []
    assert [s["id"] for s in again["steps"]][-1] == "close"  # both end in an unenclosed `exact`
