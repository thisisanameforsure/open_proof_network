"""F07-T75 (R23): a hole's node is born without the ``-- hole:`` line its carried witness came with.

The finding (testers 2026-10-08, erdos-1094): the record's
``targets/erdos-1094/nodes/erdos-1094--h1/Witness.lean`` begins ``-- hole: h_fixed_k``, a blank
line, then ``import Mathlib``. The line is how a carried witness (``attempts/<name>.<n>.witness``)
says which hole it is for, because the node's id does not exist before the merge (F07-Q57 (3)).
Once the node exists its directory says that, and the line names a ``have`` of the parent's
assembly that the child's own statement never mentions: transport, not content.

So the text a hole's node is born with is the carried text less its marker line (and, when the
marker heads the file, the blank lines around it). Step 7 stages exactly that text, because it
builds the child through the same ``postmerge.child_proposal`` the writer uses; the carried file
itself stays in the parent's ``attempts/`` with its marker and its hash, which is what the
verdict records and what the service binds a submission to (F07-T53).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from harness import TARGET, node_dir
from test_cli_sandboxed import NODES, Seam, run
from test_finding_partial_carries_witnesses import (
    BOTH,
    NODE_WITNESS,
    STAMP_FILE,
    STEM,
    W_LEFT,
    W_RIGHT,
    PerHole,
    art_hole,
    carrying,
    decomposed,
    holes_report,
    merged_with_witnesses,
    postmerge_argv,
    witness_text,
)
from test_partial import ROOT
from test_postmerge import PSEUDONYM, STAMP

from opn_gate import carried, cli, pipeline, postmerge, schemas
from opn_gate.paths import Change
from opn_gate.steps.artifact import ARTIFACT_KEY


def lean_of(text: str) -> str:
    """What ``witness_text`` builds, less its first two lines: the marker and the blank after."""
    head, _, rest = text.partition("\n\n")
    assert head.startswith("-- hole: ")
    return rest


def test_a_child_is_born_without_the_marker(tmp_path: Path) -> None:
    """The writer: each child's ``Witness.lean`` is the witness, beginning with its Lean."""
    root, merged = decomposed(tmp_path, {"right": W_RIGHT, "left": W_LEFT})
    nodes = root / "targets" / TARGET / "nodes"
    h1, h2 = merged.children
    for child, sent in ((h1, W_RIGHT), (h2, W_LEFT)):
        born = (nodes / child / "Witness.lean").read_text(encoding="utf-8")
        assert "-- hole:" not in born
        assert born == lean_of(sent)
        assert born.startswith("theorem witness")


def test_step_7_checks_the_text_the_child_is_born_with(tmp_path: Path) -> None:
    """Step 7 stages the stripped text, so what is checked is what is written; the verdict still
    names each carried file by the hash of the file as submitted, marker and all."""
    ctx, fake = carrying(tmp_path, BOTH)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    decls = ("and_swap_reassoc__h1", "and_swap_reassoc__h2")
    for decl, sent in zip(decls, BOTH.values(), strict=True):
        assert fake.seen[decl][1] == lean_of(sent)
    for entry, (name, sent) in zip(ctx.data[carried.DATA_KEY], BOTH.items(), strict=True):
        assert entry["path"] == f"attempts/{name}"
        assert entry["sha256"] == schemas.content_hash(sent.encode("utf-8"))


def test_the_post_merge_command_writes_the_witness_and_keeps_the_carried_file(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end through ``opn-gate postmerge --apply-partial``: the child has the witness, the
    parent's ``attempts/`` keeps the carried file as it was submitted (the record of what was
    carried, D-3)."""
    root = merged_with_witnesses(tmp_path, {f"{STEM}.1.witness": witness_text("left")})
    seam.fake = PerHole(witness=NODE_WITNESS, artifact=holes_report())
    code, _out, err = run(capsys, *postmerge_argv(root, tmp_path / "o"))
    assert code == cli.EXIT_PASS, err
    nodes = root / NODES
    assert (nodes / f"{ROOT}--h2" / "Witness.lean").read_text() == lean_of(witness_text("left"))
    kept = (nodes / ROOT / "attempts" / f"{STEM}.1.witness").read_text()
    assert kept == witness_text("left")


def test_windows_line_ends_survive_the_strip(tmp_path: Path) -> None:
    """F07-T53 still holds for everything but the marker: a witness sent with ``\\r\\n`` is
    hashed as its bytes, and the child is born with those bytes less the marker's lines."""
    text = witness_text("right").replace("\n", "\r\n")
    name = f"{STEM}.1.witness"
    ctx, _fake = carrying(tmp_path, {})
    (node_dir(ctx) / "attempts" / name).write_bytes(text.encode("utf-8"))
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{name}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    (checked,) = ctx.data[carried.DATA_KEY]
    assert checked["sha256"] == schemas.content_hash(text.encode("utf-8"))
    want = lean_of(witness_text("right")).replace("\n", "\r\n").encode("utf-8")
    staged = ctx.workdir / "holes" / "src" / "Nodes" / f"{ROOT}--h1" / "Witness.lean"
    assert staged.read_bytes() == want
    held = replace(verdict, data=ctx.data)
    assert cli.checked_witnesses(held, node_dir(ctx)) == {"right": text}
    postmerge.apply_partial(
        node_dir(ctx),
        [art_hole(h) for h in ctx.data[ARTIFACT_KEY]["holes"]],
        partial_text=(node_dir(ctx) / "attempts" / STAMP_FILE).read_text(encoding="utf-8"),
        pseudonym=PSEUDONYM,
        stamp=STAMP,
        assembly_path=f"attempts/{STAMP_FILE}",
        witnesses={"right": text},
    )
    born = (node_dir(ctx).parent / f"{ROOT}--h1" / "Witness.lean").read_bytes()
    assert born == want


# --- the rule, over text --------------------------------------------------------------------------

LEAN = "import Mathlib\n\ntheorem witness : True :=\n  trivial\n"


@pytest.mark.parametrize(
    ("sent", "born"),
    [
        # The shape on the record: marker, blank line, the witness.
        ("-- hole: h_fixed_k\n\n" + LEAN, LEAN),
        # Blank lines before the marker go with it; the witness starts the file.
        ("\n\n-- hole: h\n\n\n" + LEAN, LEAN),
        # No blank line after it.
        ("-- hole: h\n" + LEAN, LEAN),
        # Indented, spaced out: the grammar step 2 reads (``hole_named``).
        ("  --   hole:   h  \n\n" + LEAN, LEAN),
        # Below the imports: the line alone goes, its neighbours stay.
        (
            "import Mathlib\n\n-- hole: h\ntheorem witness : True :=\n  trivial\n",
            "import Mathlib\n\ntheorem witness : True :=\n  trivial\n",
        ),
        # As the last line, with no newline after it.
        (
            "theorem witness : True :=\n  trivial\n-- hole: h",
            "theorem witness : True :=\n  trivial\n",
        ),
        # Only the line step 2 named the hole by: a second marker is the author's comment.
        ("-- hole: a\n\n-- hole: b\n" + LEAN, "-- hole: b\n" + LEAN),
        # A comment that mentions a hole is not the marker.
        ("-- the hole: see below\n" + LEAN, "-- the hole: see below\n" + LEAN),
        # Nothing to strip: unchanged, byte for byte.
        (LEAN, LEAN),
        ("", ""),
    ],
)
def test_the_marker_line_is_what_is_stripped(sent: str, born: str) -> None:
    assert carried.as_witness(sent) == born
    if carried.hole_named(sent) is not None:
        assert carried.hole_named(born) != carried.hole_named(sent) or "-- hole: b" in born


def test_the_strip_is_idempotent_and_keeps_line_ends() -> None:
    crlf = ("-- hole: h\n\n" + LEAN).replace("\n", "\r\n")
    once = carried.as_witness(crlf)
    assert once == LEAN.replace("\n", "\r\n")
    assert carried.as_witness(once) == once


# --- the guide ------------------------------------------------------------------------------------


def test_the_guide_says_the_marker_is_not_written() -> None:
    """An agent reads the guide, not the writer: it says the line is dropped, in the section on
    carrying witnesses and where it says what the hole is born with."""
    guide = (Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    section = " ".join(
        guide.split("### Carrying the holes' witnesses in the skeleton", 1)[1]
        .split("### After the skeleton merges", 1)[0]
        .split()
    )
    assert "less its `-- hole:` line" in section
    assert "with that file, less its `-- hole:` line, as its `Witness.lean`" in section
