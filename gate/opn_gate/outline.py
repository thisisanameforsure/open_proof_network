"""F19-T2: the outline of a merged proof artifact (F19-R1, R2, R5; ``outline/v1``).

``opn-outline`` (``gate/lean/OpnGate/Outline.lean``) reads the step tree from the artifact's
elaboration: each step's kind, the name it binds, its claim and the goal it leaves (printed with
the hole writer's options and read back, F19-R3), its line span, the constants written in it with
their modules (and, for a library module, the docstring and Stacks/Kerodon tags, F19-R4), and how
it is closed. This module turns that into the ``outline/v1`` document:

* **Ids (F19-R2)** are a function of the artifact alone: a step's names and order come from its
  source syntax, never from its span, so a comment added above the proof moves every span and no
  id. Among one step's siblings (or the top level), a step whose bound name gives an id no other
  sibling's does is called by that id; every other step is ``s<n>``, ``n`` its 1-based position
  in source order among its siblings. A child's id is its parent's, a dot, and its own (``s3.1``,
  ``key.h1``). See ``name_id`` for how a name becomes ASCII.
* **Constants** are split by the gate's one reading of a module name (``layout.module_origin``,
  which step 8 uses too): a ``Nodes.«id».*`` module is a graph node (the node's own modules are
  not a use of anything), a ``Defs.*`` module a definition, a library prefix Mathlib or core. A
  constant of the artifact itself, or of any other module, is not recorded: R4 records no name
  from any other source. A library constant's docstring is cut to its first sentence, at the cap.
* **Caps (F19 §6)**: claim, goal and hypothesis text over ``OPN_OUTLINE_TEXT_CAP`` keeps its
  prefix and is marked ``truncated``; a docstring sentence is cut at ``OPN_OUTLINE_DOC_CAP``.
* **Failure (F19-R5, C7)**: a timeout, a memory kill, a program that fails or breaks its contract,
  or a document the schema refuses writes no outline and names the artifact and its reason
  (``REASONS``). One artifact's failure never stops another's (``run``).

A hole step's ``child_node`` is what the caller says it is (F18's decompositions name each hole's
child, ``products.decompositions_of``); this module never derives one.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import config, layout, schemas
from opn_gate.sandbox import MemoryExceeded
from opn_gate.toolchain import (
    MetaprogramResult,
    OutlineRequest,
    ResolvedToolchain,
    Toolchain,
)

SCHEMA = "outline/v1"

#: ``targets/<id>/outlines/<artifact-hash>.json`` (F19-R1).
OUTLINES_DIR = "outlines"

ARTIFACT_KINDS: tuple[str, ...] = ("proof", "alternate", "partial")

#: F22-T14: the reserved id of a proof's trailing closing tactics, which no step encloses; the
#: program marks that step with it (``"id"``), and it takes no ``s<n>`` position.
CLOSE_ID = "close"

#: The named reasons an artifact can be left without an outline (F19-R5).
TIMEOUT = "timeout"
MEMORY = "memory-exceeded"
TOOLCHAIN = "toolchain-error"
FAILED = "extraction-failed"
CONTRACT = "contract-broken"
SCHEMA_INVALID = "schema-invalid"
REASONS: tuple[str, ...] = (TIMEOUT, MEMORY, TOOLCHAIN, FAILED, CONTRACT, SCHEMA_INVALID)

#: The longest name or detail a report carries.
_DETAIL_CAP = 2000
_NAME_CAP = 200
_ID_PART_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
_GENERATED_RE = re.compile(r"^s[0-9]+$")


class OutlineError(ValueError):
    """The program's document cannot be made into an outline; ``reason`` is one of ``REASONS``."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class Caps:
    """The configured limits and the automation list (F19 §6, Q5; C6)."""

    text: int = config.DEFAULT_OUTLINE_TEXT_CAP
    doc: int = config.DEFAULT_OUTLINE_DOC_CAP
    timeout_s: float = config.DEFAULT_OUTLINE_TIMEOUT_S
    automation: tuple[str, ...] = config.DEFAULT_OUTLINE_AUTOMATION

    @classmethod
    def from_settings(cls, settings: config.Settings) -> Caps:
        return cls(
            text=settings.outline_text_cap,
            doc=settings.outline_doc_cap,
            timeout_s=settings.outline_timeout_s,
            automation=settings.outline_automation,
        )


@dataclass(frozen=True)
class Artifact:
    """One merged proof artifact: its path relative to the node, its hash, its kind."""

    path: str
    hash: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "hash": self.hash, "kind": self.kind}


@dataclass(frozen=True)
class Job:
    """What one outline needs: whose artifact it is, where the file and module are, the hole
    names' child nodes (empty for anything but a partial), and the search path it builds on."""

    target: str
    node: str
    artifact: Artifact
    file: Path
    module: str
    decl: str
    holes: Mapping[str, str | None]
    search_path: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Outcome:
    """An outline, or the named reason there is none (F19-R5)."""

    job: Job
    doc: dict[str, Any] | None
    reason: str | None = None
    detail: str = ""
    written: Path | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.job.target,
            "node": self.job.node,
            "path": self.job.artifact.path,
            "artifact_hash": self.job.artifact.hash,
            "written": None if self.written is None else str(self.written),
            "reason": self.reason,
            "detail": self.detail,
        }


# --- the pure half: the program's document to ``outline/v1`` ----------------------------------


def name_id(name: str) -> str:
    """A bound name as an id part (ASCII, the schema's pattern), deterministically.

    NFKC first, which turns the subscript digits Lean names carry into digits (``h₁`` is
    ``h1``) and a double-struck letter into its letter; then every character still outside
    ``[A-Za-z0-9_']`` becomes ``_x<hex>`` of its code point (h with a Greek alpha is
    ``h_x3b1``), and a leading digit or apostrophe gets a ``_`` before it. Two names can map to
    one id (``h₁`` and ``h1``); ``sibling_ids`` then treats both as not unique."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFKC", name):
        if ch.isascii() and (ch.isalnum() or ch in "_'"):
            out.append(ch)
        else:
            out.append(f"_x{ord(ch):x}")
    text = "".join(out) or "_"
    if not (text[0].isalpha() or text[0] == "_"):
        text = "_" + text
    return text


def sibling_ids(names: Sequence[str | None]) -> list[str]:
    """F19-R2 for one list of siblings, in source order: the name's id where no other sibling's
    name gives the same id and it is not the ``s<n>`` another sibling is called by; else
    ``s<n>``, ``n`` the 1-based position. Iterated to a fixed point, since a name that falls back
    frees nothing and a fallback can claim the ``s<n>`` a name had."""
    candidates = [None if n is None else name_id(n) for n in names]
    counts: dict[str, int] = {}
    for c in candidates:
        if c is not None:
            counts[c] = counts.get(c, 0) + 1
    fallback = {i for i, c in enumerate(candidates) if c is None or counts[c] > 1}
    while True:
        taken = {f"s{i + 1}" for i in fallback}
        more = {
            i
            for i, c in enumerate(candidates)
            if i not in fallback and c is not None and c in taken
        }
        if not more:
            break
        fallback |= more
    return [f"s{i + 1}" if i in fallback or c is None else c for i, c in enumerate(candidates)]


def step_ids(names: Sequence[str | None], closing: Sequence[bool]) -> list[str]:
    """F22-T14: the ids of one list of siblings, where ``closing`` marks the top level's trailing
    closing step. Every other step is numbered by ``sibling_ids`` as if the closing step were not
    there, so adding it moves no id an outline already published; it is ``close``, or, should a
    sibling's name already give that id, ``close`` with underscores before it until free."""
    kept = [i for i, c in enumerate(closing) if not c]
    numbered = sibling_ids([names[i] for i in kept])
    out: list[str] = [""] * len(names)
    for i, sid in zip(kept, numbered, strict=True):
        out[i] = sid
    for i, c in enumerate(closing):
        if c:
            sid = CLOSE_ID
            while sid in out:
                sid = "_" + sid
            out[i] = sid
    return out


def spans_by_id(steps: Sequence[Mapping[str, Any]]) -> dict[str, tuple[int, int]]:
    """Every step of an outline, children included, by id: its line span."""
    out: dict[str, tuple[int, int]] = {}
    stack = list(steps)
    while stack:
        step = stack.pop()
        out[str(step["id"])] = (int(step["span"]["start_line"]), int(step["span"]["end_line"]))
        stack.extend(step.get("children") or [])
    return out


def lost_ids(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[str]:
    """F22-T14's invariant between an outline already published and the same artifact outlined
    again: every id of ``old`` is in ``new`` with the same span, since explainers anchor on them
    (F20-R3). One line per id that is missing or moved; empty when the invariant holds."""
    before, after = spans_by_id(old.get("steps") or []), spans_by_id(new.get("steps") or [])
    out = []
    for sid, span in sorted(before.items()):
        if sid not in after:
            out.append(f"{sid}: missing (was lines {span[0]}-{span[1]})")
        elif after[sid] != span:
            out.append(f"{sid}: lines {span[0]}-{span[1]} became {after[sid][0]}-{after[sid][1]}")
    return out


def first_sentence(doc: str | None, cap: int) -> str | None:
    """A docstring's first sentence: up to the first ``.``, ``!`` or ``?`` followed by space or
    the end, or the first blank line, whitespace collapsed, cut at ``cap``. ``None`` for none."""
    if doc is None:
        return None
    para = re.split(r"\n\s*\n", doc.strip(), maxsplit=1)[0]
    flat = " ".join(para.split())
    if not flat:
        return None
    m = re.search(r"[.!?](?=\s|$)", flat)
    sentence = flat[: m.end()] if m else flat
    return sentence[:cap]


def _clip(text: str, cap: int) -> tuple[str, bool]:
    return (text[:cap], True) if len(text) > cap else (text, False)


def _text(raw: object, cap: int) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("text"), str):
        raise OutlineError(CONTRACT, f"a printed text is not an object with text: {raw!r:.200}")
    printed = raw.get("printed")
    if printed not in ("reliable", "unreliable"):
        raise OutlineError(CONTRACT, f"printed is {printed!r}")
    text, truncated = _clip(raw["text"], cap)
    return {"text": text, "printed": printed, "truncated": truncated}


def _goal(raw: object, cap: int) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("hypotheses"), list):
        raise OutlineError(CONTRACT, f"a goal is malformed: {raw!r:.200}")
    hyps = []
    for h in raw["hypotheses"]:
        if not isinstance(h, dict) or not isinstance(h.get("name"), str):
            raise OutlineError(CONTRACT, f"a hypothesis is malformed: {h!r:.200}")
        hyps.append({"name": h["name"][:_NAME_CAP], "type": _text(h.get("type"), cap)})
    return {"target": _text(raw.get("target"), cap), "hypotheses": hyps}


def _uses(
    names: object, constants: Mapping[str, Any], *, own: str, doc_cap: int
) -> dict[str, list[Any]]:
    if not isinstance(names, list):
        raise OutlineError(CONTRACT, "a step's uses is not a list")
    nodes: list[str] = []
    defs: list[str] = []
    library: list[dict[str, Any]] = []
    for name in names:
        entry = constants.get(name) if isinstance(name, str) else None
        if not isinstance(entry, dict):
            raise OutlineError(CONTRACT, f"constant {name!r} is not in the program's table")
        module = entry.get("module")
        if not isinstance(module, str):
            continue  # the artifact's own constant: not a use of anything
        kind, node_id = layout.module_origin(module)
        if kind == "node" and node_id is not None and node_id != own:
            if node_id not in nodes:
                nodes.append(node_id)
        elif kind == "defs":
            if name not in defs:
                defs.append(name)
        elif kind == "library" and all(e["name"] != name for e in library):
            raw_doc = entry.get("doc")
            raw_tags = entry.get("tags") or []
            library.append(
                {
                    "name": name,
                    "doc": first_sentence(raw_doc if isinstance(raw_doc, str) else None, doc_cap),
                    "tags": [
                        {"database": t.get("database"), "tag": t.get("tag")}
                        for t in raw_tags
                        if isinstance(t, dict)
                    ],
                }
            )
    return {"nodes": nodes, "defs": defs, "mathlib": library}


def _steps(  # noqa: PLR0913 — one argument per fact a step's fields are read against
    raws: object,
    prefix: str,
    *,
    constants: Mapping[str, Any],
    own: str,
    holes: Mapping[str, str | None],
    caps: Caps,
) -> list[dict[str, Any]]:
    if not isinstance(raws, list) or not all(isinstance(r, dict) for r in raws):
        raise OutlineError(CONTRACT, "steps is not a list of objects")
    names = [r.get("name") if isinstance(r.get("name"), str) else None for r in raws]
    ids = step_ids(names, [r.get("id") == CLOSE_ID and not prefix for r in raws])
    out = []
    for raw, local, name in zip(raws, ids, names, strict=True):
        sid = f"{prefix}.{local}" if prefix else local
        closed = raw.get("closed_by")
        span = raw.get("span")
        if not isinstance(closed, dict) or not isinstance(span, dict):
            raise OutlineError(CONTRACT, f"step {sid} lacks closed_by or span")
        kind = raw.get("kind")
        out.append(
            {
                "id": sid,
                "kind": kind,
                "name": None if name is None else name[:_NAME_CAP],
                "claim": _text(raw.get("claim"), caps.text),
                "goal": _goal(raw.get("goal"), caps.text),
                "span": {"start_line": span.get("start_line"), "end_line": span.get("end_line")},
                "uses": _uses(raw.get("uses"), constants, own=own, doc_cap=caps.doc),
                "closed_by": {
                    "kind": closed.get("kind"),
                    "tactics": list(closed.get("tactics") or []),
                },
                "child_node": holes.get(name) if kind == "hole" and name is not None else None,
                "children": _steps(
                    raw.get("children", []),
                    sid,
                    constants=constants,
                    own=own,
                    holes=holes,
                    caps=caps,
                ),
            }
        )
    return out


def build(raw: Mapping[str, Any], job: Job, *, gate: str, caps: Caps) -> dict[str, Any]:
    """The ``outline/v1`` document from ``opn-outline``'s answer, validated; ``OutlineError``
    (``CONTRACT`` or ``SCHEMA_INVALID``) otherwise."""
    constants = raw.get("constants")
    if not isinstance(constants, dict):
        raise OutlineError(CONTRACT, "the program's answer has no constants table")
    doc = {
        "schema": SCHEMA,
        "target": job.target,
        "node": job.node,
        "artifact": job.artifact.as_dict(),
        "gate": gate,
        "steps": _steps(
            raw.get("steps"),
            "",
            constants=constants,
            own=job.node,
            holes=job.holes,
            caps=caps,
        ),
    }
    try:
        return schemas.validate(doc, SCHEMA)
    except schemas.SchemaError as exc:
        raise OutlineError(SCHEMA_INVALID, str(exc)) from exc


# --- the impure half: run the program, write the file ----------------------------------------


def request(job: Job, caps: Caps) -> OutlineRequest:
    """The program's request: the automation list from config, the gate's library prefixes."""
    return OutlineRequest(
        file=job.file,
        module=job.module,
        decl=job.decl,
        automation=caps.automation,
        doc_modules=layout.LIBRARY_PREFIXES,
    )


def _failed(result: MetaprogramResult) -> str:
    return (result.error or result.output or f"exit {result.exit_code}")[:_DETAIL_CAP]


def extract(  # noqa: PLR0911 — one return per named reason (F19-R5)
    toolchain: Toolchain, tc: ResolvedToolchain, job: Job, *, gate: str, caps: Caps
) -> Outcome:
    """One artifact's outline, or the named reason there is none. Never raises for anything
    about the artifact or the toolchain (C7): the caller has other artifacts to outline."""
    try:
        result = toolchain.outline(
            tc, request(job, caps), list(job.search_path), timeout_s=caps.timeout_s
        )
    except MemoryExceeded as exc:
        return Outcome(
            job, None, MEMORY, f"killed at the sandbox's memory cap: {exc}"[:_DETAIL_CAP]
        )
    except subprocess.TimeoutExpired:
        return Outcome(job, None, TIMEOUT, f"over OPN_OUTLINE_TIMEOUT_S={caps.timeout_s:g}")
    except Exception as exc:  # one artifact's failure stops no other (F19-R5)
        return Outcome(job, None, TOOLCHAIN, f"{type(exc).__name__}: {exc}"[:_DETAIL_CAP])
    if not result.ok:
        reason = FAILED if result.doc else CONTRACT
        return Outcome(job, None, reason, _failed(result))
    if result.doc.get("decl") != job.decl:
        return Outcome(job, None, CONTRACT, f"answered for {result.doc.get('decl')!r}")
    try:
        doc = build(result.doc, job, gate=gate, caps=caps)
    except OutlineError as exc:
        return Outcome(job, None, exc.reason, str(exc)[:_DETAIL_CAP])
    return Outcome(job, doc)


def outline_path(target_dir: Path, artifact_hash: str) -> Path:
    """``targets/<id>/outlines/<artifact-hash>.json`` (F19-R1)."""
    return target_dir / OUTLINES_DIR / f"{artifact_hash}.json"


def write(target_dir: Path, outcome: Outcome) -> Outcome:
    """Write the outline, if there is one; nothing at all otherwise (F19-R5)."""
    if outcome.doc is None:
        return outcome
    dest = outline_path(target_dir, outcome.job.artifact.hash)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_bytes(schemas.canonical_json(outcome.doc))
    tmp.replace(dest)
    return Outcome(outcome.job, outcome.doc, written=dest)


def run(  # noqa: PLR0913 — the jobs, where they write, and the four facts every job shares
    jobs: Sequence[Job],
    target_dir_of: Callable[[str], Path],
    *,
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    gate: str,
    caps: Caps,
) -> list[Outcome]:
    """Outline every job; each writes its own file or names its reason, whatever the others do
    (F19-R5, AC5). The list is the job's report."""
    return [
        write(target_dir_of(job.target), extract(toolchain, tc, job, gate=gate, caps=caps))
        for job in jobs
    ]
