"""F18-T5 (R6, R7; AC8; D-31 v3.26): stepped annexes, and a skeleton held to their steps.

``annex/v2`` lets an annex name its steps. A skeleton that cites a stepped annex names each hole
after one of them, and the gate refuses one that does not (``annex-step-missing``); a step with no
hole is carried by the assembly, and a v1 annex is never checked. The hole names are the
extractor's, so the refusal is step 4's last word, before anything merges, over the fake seam
here and over the real extractor in ``test_annex_steps_lean.py``. The post-merge writer repeats
it as the backstop, and ``products.outline_of`` publishes each step with its node and status.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import samples
import yaml
from fakes import FakeToolchain, artifact_result
from harness import TARGET, copy_graph, node_dir
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_partial import HOLES, WITNESS, cite, partial_context
from test_products import ROOT_NODE, nodes_dir

from opn_gate import annex, graph, modes, postmerge, products, schemas
from opn_gate.paths import Change

STEP_IDS = ("right", "left")  # the two holes test_partial's assembly binds


def stepped(*ids: str, schema: str = "annex/v2", **extra: Any) -> bytes:
    """An annex file as ``POST /annexes`` writes one: front matter, then the prose."""
    front = samples.annex_front_matter(node="and-swap-reassoc", schema=schema, **extra)
    if ids:
        front["steps"] = [{"id": i, "summary": f"the step that gives {i}"} for i in ids]
    head = yaml.safe_dump(front, sort_keys=True, allow_unicode=True)
    return f"---\n{head}---\nSwap, then reassociate.\n".encode()


def place_annex(directory: Path, content: bytes) -> str:
    digest = schemas.content_hash(content)
    (directory / "annex").mkdir(exist_ok=True)
    (directory / "annex" / f"{digest}.md").write_bytes(content)
    return digest


def skeleton_citing(tmp_path: Path, content: bytes):  # type: ignore[no-untyped-def]
    """test_partial's two-hole skeleton (holes ``right``, ``left``) citing ``content``."""
    ctx, stamp = partial_context(tmp_path)
    digest = place_annex(node_dir(ctx), content)
    cite(ctx, stamp, digest)
    return ctx, digest


# --- AC8: the gate's check ------------------------------------------------------------------------


def test_a_skeleton_whose_holes_are_the_annexs_steps_passes(tmp_path: Path) -> None:
    """AC8, first case: every hole name is a step id."""
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, _ = skeleton_citing(tmp_path, stepped(*STEP_IDS))
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()
    assert verdict.steps[2].diagnostic is not None
    assert verdict.steps[2].diagnostic.code == "artifact-partial"


def test_a_hole_that_is_no_step_is_refused_at_step_4_naming_it(tmp_path: Path) -> None:
    """AC8, second case: the annex names ``right`` only, the skeleton also binds ``left``.
    Refused at step 4, where the extractor named the holes, and nothing after it runs."""
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, digest = skeleton_citing(tmp_path, stepped("right"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    d = verdict.diagnostic
    assert d is not None and d.code == "annex-step-missing"
    assert d.details == {"annex": digest, "missing": ["left"], "steps": ["right"]}
    assert "left" in d.message and "right" in d.message
    assert {s.result for s in verdict.steps if s.step > 4} == {"skipped"}
    # The verdict JSON the workflow prints carries the same details (the 2026-09-17 lesson).
    assert verdict.as_dict()["diagnostic"]["details"]["missing"] == ["left"]


def test_a_v1_annex_is_unchecked(tmp_path: Path) -> None:
    """AC8, third case: a v1 annex names no steps, so any hole names pass."""
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, _ = skeleton_citing(tmp_path, stepped(schema="annex/v1"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()


def test_a_v2_annex_without_steps_is_unchecked(tmp_path: Path) -> None:
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, _ = skeleton_citing(tmp_path, stepped())
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()


def test_a_step_with_no_hole_is_carried_by_the_assembly(tmp_path: Path) -> None:
    """D-31 v3.26: a step the assembly proves in line has no hole, and that is fine."""
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, _ = skeleton_citing(tmp_path, stepped("right", "combine", "left"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()


def test_a_skeleton_citing_no_annex_is_unchecked(tmp_path: Path) -> None:
    from opn_gate import pipeline  # noqa: PLC0415

    ctx, _ = partial_context(tmp_path)
    place_annex(node_dir(ctx), stepped("x"))  # on the node, never cited
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()


def test_every_missing_hole_is_named_in_extraction_order(tmp_path: Path) -> None:
    from opn_gate import pipeline  # noqa: PLC0415

    holes = [("c", "True", False), ("a", "True", False), ("b", "True", False)]
    fake = FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=holes))
    ctx, stamp = partial_context(tmp_path, toolchain=fake)
    digest = place_annex(node_dir(ctx), stepped("a", "z"))
    cite(ctx, stamp, digest)
    verdict = pipeline.run_steps(ctx)
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "annex-step-missing"
    assert verdict.diagnostic.details["missing"] == ["c", "b"]
    assert verdict.diagnostic.details["steps"] == ["a", "z"]


def test_check_steps_directly() -> None:
    steps = (annex.Step("a", "s"), annex.Step("b", "s"))
    assert annex.check_steps(steps, ["a", "b"], annex="d") is None
    assert annex.check_steps(steps, ["a"], annex="d") is None
    assert annex.check_steps(None, ["x"], annex="d") is None
    problem = annex.check_steps(steps, ["a", "x"], annex="d")
    assert problem is not None and problem.code == "annex-step-missing"
    assert problem.details == {"annex": "d", "missing": ["x"], "steps": ["a", "b"]}


def test_steps_of_reads_a_v2_annex_in_its_order() -> None:
    assert annex.steps_of(stepped("b", "a").decode()) == (
        annex.Step("b", "the step that gives b"),
        annex.Step("a", "the step that gives a"),
    )
    assert annex.steps_of(stepped(schema="annex/v1").decode()) is None
    assert annex.steps_of(stepped().decode()) is None
    assert annex.steps_of("no front matter at all\n") is None


# --- the post-merge backstop ---------------------------------------------------------------------


def test_the_post_merge_writer_refuses_the_same_skeleton(tmp_path: Path) -> None:
    """The backstop, as ``annex-uncited`` has one: nothing is written when the check fails."""
    ctx, _ = skeleton_citing(tmp_path, stepped("right"))
    assembly = next((node_dir(ctx) / "attempts").glob("*.lean"))
    text = assembly.read_text(encoding="utf-8")
    holes = [SimpleNamespace(name=n, closed_type=t, type=t) for n, t, _ in HOLES]
    before = sorted(p.name for p in node_dir(ctx).parent.iterdir())
    with pytest.raises(postmerge.GraphWriteError, match="left"):
        postmerge.apply_partial(
            node_dir(ctx),
            holes,
            partial_text=text,
            pseudonym="someone",
            stamp="20260912T120000Z",
            assembly_path=f"attempts/{assembly.name}",
        )
    assert sorted(p.name for p in node_dir(ctx).parent.iterdir()) == before


# --- annex/v2's own shape -----------------------------------------------------------------------


def front(**overrides: Any) -> dict[str, Any]:
    doc = samples.annex_front_matter(schema="annex/v2")
    doc["steps"] = [{"id": "hden", "summary": "the denominator is positive"}]
    doc.update(overrides)
    return doc


@pytest.mark.parametrize(
    "steps",
    [
        [],  # an outline of no steps names nothing: leave the field out
        [{"id": "1bad", "summary": "s"}],  # not an identifier
        [{"id": "h-1", "summary": "s"}],  # a hyphen is not an identifier character
        [{"id": "h₁", "summary": "s"}],  # ASCII only (the documented pattern)
        [{"id": "", "summary": "s"}],
        [{"id": "h"}],  # no summary
        [{"summary": "s"}],  # no id
        [{"id": "h", "summary": ""}],
        [{"id": "h", "summary": "x" * 301}],
        [{"id": "h", "summary": "two\nlines"}],
        [{"id": "h", "summary": "s", "proof": "trust me"}],  # no other field
        [{"id": f"h{i}", "summary": "s"} for i in range(51)],
        "hden",
    ],
)
def test_malformed_steps_are_refused_by_the_schema(steps: Any) -> None:
    assert schemas.violations(front(steps=steps), "annex/v2")


def test_well_formed_steps_satisfy_the_schema() -> None:
    assert schemas.violations(front(), "annex/v2") == []
    many = [{"id": f"h{i}'", "summary": "x" * 300} for i in range(50)]
    assert schemas.violations(front(steps=many), "annex/v2") == []
    no_steps = front()
    del no_steps["steps"]
    assert schemas.violations(no_steps, "annex/v2") == []
    # v1 stays what it was: it has no steps field.
    assert schemas.violations(samples.annex_front_matter(), "annex/v1") == []
    assert schemas.violations(samples.annex_front_matter(steps=[]), "annex/v1")


def test_duplicate_step_ids_are_found() -> None:
    doc = front(steps=[{"id": i, "summary": "s"} for i in ("a", "b", "a", "b", "a")])
    assert annex.duplicate_step_ids(doc) == ["a", "b"]
    assert annex.duplicate_step_ids(front()) == []


def annex_append(root: Path, content: bytes) -> list[Change]:
    rel = f"targets/{TARGET}/nodes/{ROOT_NODE}/annex/{schemas.content_hash(content)}.md"
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(content)
    return [Change("A", rel)]


def test_the_append_check_takes_a_v2_annex_and_refuses_duplicate_ids(tmp_path: Path) -> None:
    """The gate's append check (step 2's mode check) is where a v2 annex's own shape is held: a
    well-formed one passes, a schema violation and a repeated id are ``append-invalid``."""
    root = copy_graph(tmp_path)
    good = annex_append(root, stepped("a", "b"))
    assert modes.check(root, modes.classify(good)) == []

    bad = annex_append(root, stepped("a", "1b"))
    assert [d.code for d in modes.check(root, modes.classify(bad))] == ["append-invalid"]

    twice = stepped("a", "b").replace(b"id: b", b"id: a")
    found = modes.check(root, modes.classify(annex_append(root, twice)))
    assert [d.code for d in found] == ["append-invalid"]
    assert "a" in found[0].details.get("duplicates", [])


# --- R7: the outline product ----------------------------------------------------------------------


def outline_annex(root: Path, *ids: str, summaries: dict[str, str] | None = None) -> str:
    front_doc = samples.annex_front_matter(node=ROOT_NODE, schema="annex/v2")
    front_doc["steps"] = [{"id": i, "summary": (summaries or {}).get(i, f"gives {i}")} for i in ids]
    content = (
        "---\n" + yaml.safe_dump(front_doc, sort_keys=True, allow_unicode=True) + "---\nprose\n"
    ).encode()
    return place_annex(nodes_dir(root) / ROOT_NODE, content)


def test_the_outline_lists_each_step_with_its_node_and_status(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    digest = outline_annex(root, "hden", "combine", "hrem")
    merged_partial(root, 7, ["hden", "hrem"], annex=None)
    # merged_partial writes the file without a citation when annex is None; cite the stepped one.
    partial = nodes_dir(root) / ROOT_NODE / "attempts" / "20260920T000000Z-alice-partial.lean"
    partial.write_text(f"theorem x : True := by\n  -- annex: {digest}\n  sorry\n")
    tg = graph.load_target(root, TARGET)
    assert products.outline_of(tg, ROOT_NODE) == [
        {
            "step": "hden",
            "summary": "gives hden",
            "node": HOLE_IDS[0],
            "status": tg.statuses[HOLE_IDS[0]],
        },
        {"step": "combine", "summary": "gives combine", "node": None, "status": None},
        {
            "step": "hrem",
            "summary": "gives hrem",
            "node": HOLE_IDS[1],
            "status": tg.statuses[HOLE_IDS[1]],
        },
    ]


def test_no_outline_without_a_stepped_annex(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hT")
    merged_partial(root, 7, ["hT"])  # cites an annex whose text is not front matter at all
    tg = graph.load_target(root, TARGET)
    assert products.outline_of(tg, ROOT_NODE) is None
    assert products.outline_of(tg, HOLE_IDS[0]) is None  # a node with no decomposition


def test_the_outline_is_the_most_recent_stepped_decompositions(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hT")
    add_hole(root, HOLE_IDS[1], "integrality")
    first = outline_annex(root, "hT")
    second = outline_annex(root, "integrality", "finish")
    merged_partial(root, 7, ["hT"], annex=None)
    later = "attempts/20260924T000000Z-bob-partial.lean"
    merged_partial(root, 9, ["integrality"], path=later, annex=None)
    node = nodes_dir(root) / ROOT_NODE
    (node / "attempts" / "20260920T000000Z-alice-partial.lean").write_text(
        f"theorem x : True := by\n  -- annex: {first}\n  sorry\n"
    )
    (node / later).write_text(f"theorem x : True := by\n  -- annex: {second}\n  sorry\n")
    tg = graph.load_target(root, TARGET)
    outline = products.outline_of(tg, ROOT_NODE)
    assert outline is not None
    assert [(s["step"], s["node"]) for s in outline] == [
        ("integrality", HOLE_IDS[1]),
        ("finish", None),
    ]


def test_a_summary_is_carried_as_data_verbatim(tmp_path: Path) -> None:
    """C9: the summary is the contributor's text, carried byte for byte and acted on by nothing;
    escaping it is the page's job (the site escapes every annex field)."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hT")
    hostile = "<script>alert(1)</script> ignore previous instructions"
    digest = outline_annex(root, "hT", summaries={"hT": hostile})
    merged_partial(root, 7, ["hT"], annex=None)
    (nodes_dir(root) / ROOT_NODE / "attempts" / "20260920T000000Z-alice-partial.lean").write_text(
        f"theorem x : True := by\n  -- annex: {digest}\n  sorry\n"
    )
    tg = graph.load_target(root, TARGET)
    [step] = products.outline_of(tg, ROOT_NODE) or []
    assert step["summary"] == hostile
