"""F19-T2: the outline wrapper (R1, R2, R5) over the fake toolchain. Fast tier.

The program's answers here are written in the shape ``opn-outline`` prints (its contract, read
from the real program in ``test_outline_lean.py``), never imitating Lean's own output.
"""

from __future__ import annotations

import copy
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest
from fakes import FAKE_RESOLVED, FakeToolchain, metaprogram_garbage, outline_result

from opn_gate import config, layout, outline, schemas
from opn_gate.sandbox import MemoryExceeded
from opn_gate.toolchain import MetaprogramResult, OutlineRequest

GATE = "a" * 40
HASH_A = "1" * 64
HASH_B = "2" * 64
DECL = "OpnOutline.steps"


def text(t: str, printed: str = "reliable") -> dict[str, str]:
    return {"text": t, "printed": printed}


def step(
    kind: str,
    name: str | None,
    lines: tuple[int, int],
    *,
    uses: list[str] | None = None,
    closed: tuple[str, list[str]] = ("steps", []),
    children: list[dict[str, Any]] | None = None,
    claim: str | None = "a + 1 ≤ b",
) -> dict[str, Any]:
    """One step as ``opn-outline`` prints it."""
    return {
        "kind": kind,
        "name": name,
        "claim": None if claim is None else text(claim),
        "goal": {
            "target": text("a + 1 ≤ b ∧ True"),
            "hypotheses": [{"name": "h", "type": text("a < b")}],
        },
        "span": {"start_line": lines[0], "end_line": lines[1]},
        "uses": uses or [],
        "closed_by": {"kind": closed[0], "tactics": closed[1]},
        "children": children or [],
    }


CONSTANTS: dict[str, dict[str, Any]] = {
    "Nat.add_zero": {
        "module": "Init.Core",
        "doc": "Adding zero changes nothing.  This is a second sentence.\n\nA paragraph.",
        "tags": [],
    },
    "Nat.Prime.two_le": {
        "module": "Mathlib.Data.Nat.Prime.Defs",
        "doc": "A prime is at least two! More text.",
        "tags": [{"database": "stacks", "tag": "0ABC"}],
    },
    "Opn.fact": {"module": "Defs.Fact", "doc": "a definition's own doc", "tags": []},
    "OpnProp.lemma_one": {"module": "Nodes.«lemma-one».Proof", "doc": None, "tags": []},
    "OpnProp.own_hole": {"module": "Nodes.«root».Context", "doc": None, "tags": []},
    "OpnProp.aux": {"module": None, "doc": "the contributor's own docstring", "tags": []},
    "Elsewhere.thing": {"module": "Elsewhere.Module", "doc": "not a library", "tags": []},
}


def answer(*, shift: int = 0) -> dict[str, Any]:
    """The program's answer for a small proof; ``shift`` moves every span as a comment added
    above the proof would."""

    def at(a: int, b: int) -> tuple[int, int]:
        return (a + shift, b + shift)

    steps = [
        step("have", "h1", at(2, 2), closed=("automation", ["omega"]), uses=["Nat.add_zero"]),
        step(
            "have",
            "key",
            at(3, 6),
            uses=["Nat.Prime.two_le", "Opn.fact"],
            children=[
                step("obtain", None, at(4, 4), closed=("term", [])),
                step("show", None, at(5, 5)),
            ],
        ),
        step("case", None, at(7, 7), claim=None),
        step(
            "have",
            "this",
            at(8, 8),
            uses=["OpnProp.lemma_one", "OpnProp.own_hole", "OpnProp.aux", "Elsewhere.thing"],
        ),
    ]
    return outline_result(steps, CONSTANTS, decl=DECL).doc


def job(node: str = "root", artifact_hash: str = HASH_A, **kw: Any) -> outline.Job:
    base = outline.Job(
        target="tgt",
        node=node,
        artifact=outline.Artifact(path="Proof.lean", hash=artifact_hash, kind="proof"),
        file=Path("Proof.lean"),
        module=f"Nodes.«{node}».Proof",
        decl=DECL,
        holes={},
    )
    return replace(base, **kw)


def ids(steps: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for s in steps:
        out.append(s["id"])
        out += ids(s["children"])
    return out


def spans(steps: list[dict[str, Any]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for s in steps:
        out.append((s["span"]["start_line"], s["span"]["end_line"]))
        out += spans(s["children"])
    return out


CAPS = outline.Caps()


def test_ids_depend_on_the_artifact_alone() -> None:
    """F19-AC2: the same artifact twice gives the same ids; with a comment added above it the
    spans move and the ids do not."""
    first = outline.build(answer(), job(), gate=GATE, caps=CAPS)
    second = outline.build(answer(), job(), gate=GATE, caps=CAPS)
    moved = outline.build(answer(shift=3), job(), gate=GATE, caps=CAPS)
    assert ids(first["steps"]) == ["h1", "key", "key.s1", "key.s2", "s3", "this"]
    assert ids(second["steps"]) == ids(first["steps"])
    assert ids(moved["steps"]) == ids(first["steps"])
    assert spans(moved["steps"]) == [(a + 3, b + 3) for a, b in spans(first["steps"])]
    assert first == second


def test_document_validates_and_splits_constants_by_origin() -> None:
    """R1, R4: the document satisfies outline/v1; graph nodes, definitions and library
    constants are apart, the node's own modules and every other source are not recorded, and a
    library constant carries its docstring's first sentence and its tags."""
    doc = outline.build(answer(), job(), gate=GATE, caps=CAPS)
    schemas.validate(doc, "outline/v1")
    assert doc["schema"] == "outline/v1" and doc["gate"] == GATE
    assert doc["artifact"] == {"path": "Proof.lean", "hash": HASH_A, "kind": "proof"}
    h1, key, _case, this = doc["steps"]
    assert h1["uses"] == {
        "nodes": [],
        "defs": [],
        "mathlib": [{"name": "Nat.add_zero", "doc": "Adding zero changes nothing.", "tags": []}],
    }
    assert key["uses"]["defs"] == ["Opn.fact"]
    assert key["uses"]["mathlib"] == [
        {
            "name": "Nat.Prime.two_le",
            "doc": "A prime is at least two!",
            "tags": [{"database": "stacks", "tag": "0ABC"}],
        }
    ]
    assert this["uses"] == {"nodes": ["lemma-one"], "defs": [], "mathlib": []}
    assert h1["closed_by"] == {"kind": "automation", "tactics": ["omega"]}
    assert h1["claim"] == {"text": "a + 1 ≤ b", "printed": "reliable", "truncated": False}
    assert all(s["child_node"] is None for s in doc["steps"])


def test_text_over_its_cap_keeps_a_prefix_and_is_marked() -> None:
    """§6, R5: a claim, target or hypothesis longer than the text cap keeps its first ``cap``
    characters and says ``truncated``; a docstring sentence is cut at the doc cap."""
    raw = answer()
    long = "x = " + "y + " * 50 + "y"
    raw["steps"][0]["claim"] = text(long)
    raw["steps"][0]["goal"]["hypotheses"][0]["type"] = text(long, "unreliable")
    caps = outline.Caps(text=40, doc=10)
    doc = outline.build(raw, job(), gate=GATE, caps=caps)
    claim = doc["steps"][0]["claim"]
    assert claim == {"text": long[:40], "printed": "reliable", "truncated": True}
    hyp = doc["steps"][0]["goal"]["hypotheses"][0]["type"]
    assert hyp == {"text": long[:40], "printed": "unreliable", "truncated": True}
    assert doc["steps"][0]["goal"]["target"]["truncated"] is False
    assert doc["steps"][0]["uses"]["mathlib"][0]["doc"] == "Adding zer"


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["h₁", "h₂"], ["h1", "h2"]),
        (["h\u03b1", None], ["h_x3b1", "s2"]),  # h and a Greek alpha
        (["h₁", "h1"], ["s1", "s2"]),  # one id after NFKC: neither is unique
        (["h", "h", "k"], ["s1", "s2", "k"]),
        (["s2", "h", "h"], ["s1", "s2", "s3"]),  # the name s2 is a fallback's id
        (["x", "s1", None], ["x", "s1", "s3"]),
        (["1st", "'q"], ["_1st", "_'q"]),
    ],
)
def test_names_become_ascii_ids_and_collisions_fall_back(
    names: list[str | None], expected: list[str]
) -> None:
    """R2: a non-ASCII name maps to an ASCII id deterministically; a name that is not unique
    among its siblings, or would collide with another sibling's ``s<n>``, falls back to its own
    ``s<n>``; every id is unique and matches the schema's pattern."""
    got = outline.sibling_ids(names)
    assert got == expected
    assert len(set(got)) == len(got)
    assert all(outline._ID_PART_RE.match(i) for i in got)


def test_a_non_ascii_name_survives_validation_as_its_ascii_id() -> None:
    raw = answer()
    raw["steps"][0]["name"] = "h₁"
    raw["steps"][1]["children"][0]["name"] = "h\u03b1"
    doc = outline.build(raw, job(), gate=GATE, caps=CAPS)
    assert ids(doc["steps"])[:3] == ["h1", "key", "key.h_x3b1"]
    assert doc["steps"][0]["name"] == "h₁"


def test_hole_steps_take_their_child_from_the_callers_mapping() -> None:
    """R1, AC13's wrapper half: a hole names the child node the caller's decompositions give it,
    and ``null`` for a hole the record has none for; no other step carries one."""
    raw = outline_result(
        [
            step("hole", "h1", (2, 2), closed=("hole", [])),
            step("hole", "h2", (3, 3), closed=("hole", [])),
            step("have", "h3", (4, 4)),
        ],
        {},
        decl=DECL,
    ).doc
    holes = {"h1": "root--h1", "h2": None, "h3": "not-a-hole"}
    doc = outline.build(raw, job(holes=holes), gate=GATE, caps=CAPS)
    assert [s["child_node"] for s in doc["steps"]] == ["root--h1", None, None]


@dataclass
class PerDecl(FakeToolchain):
    """A fake that answers per artifact file, or raises what it is told to."""

    by_file: dict[str, MetaprogramResult | BaseException] = field(default_factory=dict)

    def outline(
        self,
        tc: Any,
        req: OutlineRequest,
        search_path: Any,
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.outline_requests.append(req)
        found = self.by_file[req.file.name]
        if isinstance(found, BaseException):
            raise found
        return found


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and OUTLINE_DIR not in p.parts
    }


OUTLINE_DIR = outline.OUTLINES_DIR


def test_one_failure_writes_nothing_and_stops_nothing(tmp_path: Path) -> None:
    """F19-AC5: of two proofs, the one whose extraction fails writes no outline and is named
    with its reason; the other's outline is written; nothing else in the target changes."""
    target_dir = tmp_path / "targets" / "tgt"
    (target_dir / "nodes" / "root").mkdir(parents=True)
    (target_dir / "frontier.json").write_text('{"keep": true}\n')
    (target_dir / "nodes" / "root" / "Proof.lean").write_text("theorem x : True := trivial\n")
    before = tree_bytes(target_dir)
    good = job(node="root", artifact_hash=HASH_A, file=Path("Good.lean"))
    bad = job(node="other", artifact_hash=HASH_B, file=Path("Bad.lean"))
    tc = PerDecl(
        by_file={
            "Bad.lean": MetaprogramResult(
                ok=False,
                doc={"ok": False, "error": "artifact does not elaborate: unknown identifier"},
                exit_code=1,
            ),
            "Good.lean": MetaprogramResult(ok=True, doc=answer()),
        }
    )
    report = outline.run(
        [bad, good], lambda _t: target_dir, toolchain=tc, tc=FAKE_RESOLVED, gate=GATE, caps=CAPS
    )
    assert [o.reason for o in report] == [outline.FAILED, None]
    assert "unknown identifier" in report[0].detail and report[0].written is None
    assert report[1].written == target_dir / "outlines" / f"{HASH_A}.json"
    assert sorted(p.name for p in (target_dir / "outlines").iterdir()) == [f"{HASH_A}.json"]
    written = schemas.load_json(report[1].written, "outline/v1")
    assert written["node"] == "root"
    assert tree_bytes(target_dir) == before
    assert report[0].as_dict()["reason"] == "extraction-failed"
    assert report[0].as_dict()["node"] == "other"


@pytest.mark.parametrize(
    ("raised_or_result", "reason"),
    [
        (subprocess.TimeoutExpired(["opn-outline"], 300), outline.TIMEOUT),
        (MemoryExceeded(["opn-outline"], 300, 4096), outline.MEMORY),
        (RuntimeError("docker cp failed"), outline.TOOLCHAIN),
        (metaprogram_garbage(), outline.CONTRACT),
        (MetaprogramResult(ok=True, doc={"ok": True, "decl": "Other.decl"}), outline.CONTRACT),
        (MetaprogramResult(ok=True, doc={"ok": True, "decl": DECL, "steps": []}), outline.CONTRACT),
    ],
)
def test_every_failure_is_a_named_reason_and_writes_nothing(
    tmp_path: Path, raised_or_result: MetaprogramResult | BaseException, reason: str
) -> None:
    """R5, C7: a timeout, a memory kill, a toolchain error and a broken contract each leave no
    file and a named reason; ``extract`` never raises."""
    tc = PerDecl(by_file={"Proof.lean": raised_or_result})
    [out] = outline.run(
        [job()], lambda _t: tmp_path, toolchain=tc, tc=FAKE_RESOLVED, gate=GATE, caps=CAPS
    )
    assert out.reason == reason and out.doc is None and out.written is None
    assert reason in outline.REASONS
    assert not (tmp_path / "outlines").exists()


def test_a_document_the_schema_refuses_is_named_and_not_written(tmp_path: Path) -> None:
    """R5: a tag that is not a four-character Stacks tag, or a kind outside the enum, makes a
    document outline/v1 refuses; it is named ``schema-invalid`` and nothing is written."""
    raw = answer()
    bad = copy.deepcopy(raw)
    bad["constants"]["Nat.Prime.two_le"]["tags"] = [{"database": "stacks", "tag": "not-a-tag"}]
    tc = PerDecl(by_file={"Proof.lean": MetaprogramResult(ok=True, doc=bad)})
    [out] = outline.run(
        [job()], lambda _t: tmp_path, toolchain=tc, tc=FAKE_RESOLVED, gate=GATE, caps=CAPS
    )
    assert out.reason == outline.SCHEMA_INVALID and "0-9A-Z" in out.detail
    assert not (tmp_path / "outlines").exists()


def test_the_request_carries_config_and_the_library_prefixes() -> None:
    """C6, F19-Q5: the automation list and the timeout come from config; the docstring prefixes
    are the gate's one list of library modules."""
    settings = config.load(
        {
            "OPN_OUTLINE_AUTOMATION": "omega, simp,omega",
            "OPN_OUTLINE_TIMEOUT_S": "12.5",
            "OPN_OUTLINE_TEXT_CAP": "99",
            "OPN_OUTLINE_DOC_CAP": "7",
        }
    )
    caps = outline.Caps.from_settings(settings)
    assert caps == outline.Caps(text=99, doc=7, timeout_s=12.5, automation=("omega", "simp"))
    req = outline.request(job(), caps)
    assert req.automation == ("omega", "simp")
    assert req.doc_modules == layout.LIBRARY_PREFIXES
    assert req.args()[-4:] == [
        "--automation",
        "omega,simp",
        "--doc-modules",
        ",".join(layout.LIBRARY_PREFIXES),
    ]
    tc = FakeToolchain(outline_doc=MetaprogramResult(ok=True, doc=answer()))
    out = outline.extract(tc, FAKE_RESOLVED, job(), gate=GATE, caps=caps)
    assert out.reason is None and tc.outline_requests == [req]


def test_outline_defaults_and_refusals_in_config() -> None:
    """§6's defaults, and a bad value refused at load (C7)."""
    s = config.load({})
    assert (s.outline_text_cap, s.outline_doc_cap, s.outline_timeout_s) == (2000, 300, 300.0)
    assert s.outline_automation == (
        "omega",
        "simp",
        "norm_num",
        "ring",
        "linarith",
        "nlinarith",
        "positivity",
        "decide",
        "field_simp",
        "aesop",
    )
    for env in (
        {"OPN_OUTLINE_TEXT_CAP": "0"},
        {"OPN_OUTLINE_DOC_CAP": "many"},
        {"OPN_OUTLINE_TIMEOUT_S": "-1"},
        {"OPN_OUTLINE_AUTOMATION": "omega; rm -rf"},
    ):
        with pytest.raises(config.ConfigError):
            config.load(env)


@pytest.mark.parametrize(
    ("doc", "cap", "expected"),
    [
        (None, 300, None),
        ("", 300, None),
        ("One. Two.", 300, "One."),
        ("`a.b` is a thing. More.", 300, "`a.b` is a thing."),
        ("No full stop\nacross lines\n\nNext paragraph.", 300, "No full stop across lines"),
        ("Version 1.2 is out. Yes.", 300, "Version 1.2 is out."),
        ("abcdef", 3, "abc"),
    ],
)
def test_first_sentence(doc: str | None, cap: int, expected: str | None) -> None:
    assert outline.first_sentence(doc, cap) == expected
