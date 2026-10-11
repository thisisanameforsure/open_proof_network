"""Words by section: drafted, written, verified, pending (F21-R11, R13, R15; D-3 v3.31).

A gloss or an explainer is read section by section, a section being the words for some steps of
the proof's outline and so for some Lean lines (F21-R11). A section is known by its *key*, never
its heading (Q8): a gloss is one section, ``whole``; an explainer's level-2 section that names
steps (``## The bound {steps: s4.1 s3}``) is ``steps:`` and its step ids sorted and comma-joined
(``steps:s3,s4.1``); its unanchored section is ``overview``. An explainer that names no step at
all — one filed before F20, or a record on a proof with no outline — is one ``overview`` holding
its whole body. Two sections of one key in a version are refused at the gate
(``section-duplicate``); a merged version read here joins them, so one bad file never stops the
products.

Over a chain — its versions in chain order, withdrawn ones read at their place without effect —
each version's sections take a state, and the chain shows one text per key:

- unchanged from the text the chain shows: ``unchanged``, and the shown entry stays;
- changed by a model's version (one naming ``drafted_with``, or one of F20's drafts) over
  drafted or absent words: ``drafted``, shown;
- changed by a person's version over drafted or absent words: ``written``, shown;
- changed by a person over words they wrote themselves and nobody has verified: ``written``,
  shown at once (the owner's ruling of 2026-10-06). "Themselves" is the record's ``author``, the
  same string on both versions, as the ledger compares it (``ledger.writeup_entry``); a draft has
  no author and is nobody's own. Another person's pending edit of that section stays listed;
- changed by a person over another's written words, or over verified words (their own
  included): ``pending``, not shown, listed under the chain's ``pending`` until a signature
  approves it (Wikipedia-style, Q7);
- changed (or omitted) by a model over written or verified words: refused at the gate
  (``locked-by-a-person``, R12, F21-T11: ``breaches`` here, ``modes.check_model_lock`` there); a
  version that reached the record anyway is read conservatively as ``pending``, never shown;
- approved by a valid signature on the version — one naming the key, or one naming none (v1):
  ``verified``, shown, and every pending entry for that key is cleared (the approved words
  replace the text those edits were made against). Nothing else clears a pending entry.

A signature counts at its version's place in the chain: the derivation has no clock (no date in
a record is evidence of order, log 2026-09-19), so signing an older version re-verifies its words
at that place. A section the chain shows that a later version omits is removed if it was drafted
and kept if it was written or verified (a person's words are not deleted by omission any more
than they are changed by it). What the chain shows is ordered by the current version's sections,
then any kept section the current version lacks, in the order they were first shown.

Nothing here reads a signature or a file's validity: callers pass valid signatures only.
``derive`` is pure; ``parts_of_text`` and ``of_chain`` read a version's file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opn_gate.glosses import Chain

OVERVIEW = "overview"
WHOLE = "whole"
STEPS = "steps:"

DRAFTED = "drafted"
WRITTEN = "written"
VERIFIED = "verified"
PENDING = "pending"
UNCHANGED = "unchanged"
#: A section whose words are a person's or a steward's: a model may not change them (R12).
LOCKED = frozenset({WRITTEN, VERIFIED})


@dataclass(frozen=True)
class Part:
    """One section of one version: its key and its words, normalised (``normalize``)."""

    key: str
    text: str


def normalize(text: str) -> str:
    """Q8: text equality is exact after trimming trailing whitespace on each line and at the
    end. Leading whitespace and blank lines between paragraphs are words."""
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip()


def key_of(steps: Sequence[str]) -> str:
    """A section's key from the steps its heading names: ``overview`` for none."""
    ids = sorted(set(steps))
    return STEPS + ",".join(ids) if ids else OVERVIEW


def explainer_parts(body: str, found: Sequence[Any] | None) -> list[Part]:
    """An explainer body's sections, from ``explainers.sections(body)`` (``found``; ``None`` when
    the body is not sections). Without a single anchor the whole body is one ``overview``."""
    if not found or not any(s.steps for s in found):
        return [Part(OVERVIEW, normalize(body))]
    return [Part(key_of(s.steps), normalize(f"## {s.heading}\n{s.text}")) for s in found]


def gloss_parts(body: str) -> list[Part]:
    """A gloss is one section, ``whole`` (Q8: its file has no steps)."""
    return [Part(WHOLE, normalize(body))]


def duplicates(parts: Sequence[Part]) -> list[str]:
    """The keys more than one section of a version carries, in order (``section-duplicate``)."""
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p.key in seen and p.key not in out:
            out.append(p.key)
        seen.add(p.key)
    return out


def keyed(parts: Sequence[Part]) -> list[Part]:
    """One part per key, at its first place; a doubled key's words joined (a merged version the
    gate would refuse today is read, not dropped)."""
    order: list[str] = []
    texts: dict[str, list[str]] = {}
    for p in parts:
        if p.key not in texts:
            order.append(p.key)
            texts[p.key] = []
        texts[p.key].append(p.text)
    return [Part(k, "\n\n".join(texts[k])) for k in order]


@dataclass(frozen=True)
class Entry:
    """One version of a chain, as the derivation reads it."""

    version: str
    parts: tuple[Part, ...]
    by_model: bool
    withdrawn: bool = False
    #: The version's ``author``: a person's login or pseudonym, ``None`` for a draft.
    author: str | None = None


@dataclass(frozen=True)
class Placed:
    """A section the chain shows, or a pending one: its key, the version its words are from, and
    its state."""

    key: str
    version: str
    state: str

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "version": self.version, "state": self.state}


@dataclass
class Derived:
    """``derive``'s answer: every version's ``(key, state)`` list in its own section order, the
    sections the chain shows, and the pending ones."""

    states: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    shown: list[Placed] = field(default_factory=list)
    pending: list[Placed] = field(default_factory=list)
    #: The words each shown section holds, normalised, by key (what the model lock compares).
    shown_text: dict[str, str] = field(default_factory=dict)
    #: Who wrote each shown section's words, by key (``None`` for a draft): what an own edit of
    #: written words is checked against (F21-Q10, Q14).
    shown_author: dict[str, str | None] = field(default_factory=dict)

    def all_verified(self) -> bool:
        """R15: the chain shows something and every section it shows is verified."""
        return bool(self.shown) and all(p.state == VERIFIED for p in self.shown)


@dataclass
class _Shown:
    version: str
    text: str
    state: str
    author: str | None = None


def _approved(entry: Entry, approvals: Sequence[frozenset[str] | None]) -> frozenset[str]:
    keys = frozenset(p.key for p in entry.parts)
    out: set[str] = set()
    for named in approvals:
        out |= keys if named is None else keys & named
    return frozenset(out)


def _state(part: Part, entry: Entry, shown: _Shown | None) -> str:
    if shown is not None and shown.text == part.text:
        return UNCHANGED
    if shown is None or shown.state == DRAFTED:
        return DRAFTED if entry.by_model else WRITTEN
    if (
        shown.state == WRITTEN
        and not entry.by_model
        and entry.author is not None
        and entry.author == shown.author
    ):
        return WRITTEN  # the owner's ruling of 2026-10-06: one's own written words, at once
    return PENDING  # over another's written words or any verified ones: a person's awaits
    # approval; a model's is refused at the gate (R12) and, read anyway, is never shown


def derive(
    entries: Sequence[Entry], approvals: Mapping[str, Sequence[frozenset[str] | None]]
) -> Derived:
    """R11, R13: each version's section states over its chain and what the chain shows, from
    the versions in chain order and the valid signatures on each (``approvals``: per version
    hash, the keys each signature names, ``None`` for every section)."""
    out = Derived()
    shown: dict[str, _Shown] = {}
    pending: dict[str, list[tuple[str, str]]] = {}  # key -> [(version, text)], first proposed first
    for e in entries:
        parts = keyed(e.parts)
        approved = _approved(e, approvals.get(e.version, ()))
        states: list[tuple[str, str]] = []
        for p in parts:
            state = VERIFIED if p.key in approved else _state(p, e, shown.get(p.key))
            states.append((p.key, state))
            if e.withdrawn:
                continue  # read at its place, without effect: a withdrawn version is absent (R7)
            if state in (DRAFTED, WRITTEN, VERIFIED):
                shown[p.key] = _Shown(e.version, p.text, state, e.author)  # keeps its first place
                if state == VERIFIED:
                    pending.pop(p.key, None)  # only an approval answers the edits waiting on it
            elif state == PENDING:
                waiting = pending.setdefault(p.key, [])
                if all(text != p.text for _, text in waiting):
                    waiting.append((e.version, p.text))
        out.states[e.version] = states
        if e.withdrawn:
            continue
        present = {p.key for p in parts}
        for key in [k for k, s in shown.items() if k not in present and s.state == DRAFTED]:
            del shown[key]
    live = [e for e in entries if not e.withdrawn]
    if not live:
        return out
    order = [p.key for p in keyed(live[-1].parts) if p.key in shown]
    order += [k for k in shown if k not in order]
    out.shown = [Placed(k, shown[k].version, shown[k].state) for k in order]
    out.pending = [Placed(k, version, PENDING) for k in pending for version, _ in pending[k]]
    out.shown_text = {k: shown[k].text for k in order}
    out.shown_author = {k: shown[k].author for k in order}
    return out


def breaches(before: Derived, parts: Sequence[Part]) -> list[Placed]:
    """R12: the sections the chain shows as written or verified (``before``, derived over the
    versions ahead of a new one) that the new version's ``parts`` change or omit, in the order the
    chain shows them. Empty for a version that keeps every person's words exactly (Q8's
    equality); it says nothing of who wrote the version, which is the caller's question."""
    texts = {p.key: p.text for p in keyed(parts)}
    return [
        p
        for p in before.shown
        if p.state in LOCKED and texts.get(p.key) != before.shown_text.get(p.key)
    ]


def own_edits(before: Derived, parts: Sequence[Part], author: str | None) -> list[Placed]:
    """F21-Q10, Q14: the sections the chain shows as *written* by ``author`` that a new version by
    ``author`` changes — the edits the owner's ruling shows at once, without review. The caller
    must make sure the version's author is who filed it, or the privilege is anyone's."""
    if author is None:
        return []
    texts = {p.key: p.text for p in keyed(parts)}
    return [
        p
        for p in before.shown
        if p.state == WRITTEN
        and before.shown_author.get(p.key) == author
        and p.key in texts
        and texts[p.key] != before.shown_text.get(p.key)
    ]


def parts_of_text(text: str, *, gloss: bool) -> list[Part]:
    """The sections of one gloss or explainer file, from its text. An explainer whose front
    matter declares no schema (filed before F20) or whose body is not sections is one
    ``overview`` of its body."""
    from opn_gate import explainers, glosses  # noqa: PLC0415 — both import this module

    try:
        doc, body = glosses.split_front_matter(text)
    except ValueError:
        doc, body = None, text
    if gloss:
        return gloss_parts(body)
    if doc is None or "schema" not in doc:
        return explainer_parts(body, None)
    try:
        found = explainers.sections(body)
    except ValueError:
        return explainer_parts(body, None)
    return explainer_parts(body, found)


def of_chain(
    chain: Chain,
    approvals: Mapping[str, Sequence[frozenset[str] | None]],
    withdrawn: frozenset[str],
) -> Derived:
    """``derive`` over a ``glosses.Chain``, reading each version's sections from its file."""
    entries: list[Entry] = []
    for v in chain.versions:
        try:
            text = v.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        gloss = v.schema is not None and v.schema.startswith("gloss/")
        parts = tuple(parts_of_text(text, gloss=gloss))
        entries.append(Entry(v.hash, parts, v.by_model, v.hash in withdrawn, v.author))
    return derive(entries, approvals)
