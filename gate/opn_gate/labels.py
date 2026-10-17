"""Labels, claims and approaches (F29; D-3, D-12, D-25 v3.44).

A partial proof names its work in its own comments, in a grammar the gate reads
(``declarations``): one ``-- approach:`` line before its first hole, one ``-- licence:`` line for
those words (D-23), and in the comment block directly above each hole's ``have`` a ``-- label:``
line and a ``-- claim: $…$`` line, the rest of the block being prose about the hole. ``problems``
says what a partial is missing, by name, so the service can refuse it before any precheck is
spent and the gate at step 4 (``partial-unlabelled``); the post-merge job files each hole's label
and claim as that hole's first statement gloss, authored by the partial's author.

A node's label is its current statement gloss's, else the name its hole bore in the route that
made it, else the target's title (a root), else its id (``label_of``); its claim is the display
its current statement gloss opens with (``claim_of``). A route's approach is the partial's own
line, else for an older partial its leading comment paragraph, else the first sentence of the
annex it cites (``approach_of``). All derived at render; nothing recorded beyond the gloss and the
partial. Every string here is contributor text, untrusted downstream (D-28).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

#: The licences a contributor may name for prose (D-23 v3.37); one home, the service reads it.
LICENCES: tuple[str, ...] = ("CC-BY-4.0", "CDLA-Permissive-2.0", "Apache-2.0")
LABEL_MAX = 60
APPROACH_MAX = 300
CLAIM_MAX = 4000

_COMMENT_RE = re.compile(r"^\s*--\s?(?P<text>.*)$")
_KEY_RE = re.compile(r"^(?P<key>approach|licence|label|claim|annex):\s*(?P<value>.*)$", re.S)
_HAVE_RE = re.compile(r"^(?P<indent>\s*)have\s+(?P<name>[^\s:(]+)\s*(?:\(.*?\)\s*)*:")
_ASSIGN_RE = re.compile(r":=\s*(?P<rest>.*)$")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\\$])")
_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n?", re.S)
#: A claim is ``$…$`` or ``$$…$$`` with something inside; a label is one line of plain text.
_CLAIM_RE = re.compile(r"\A\$(?P<inner>\$?.+?\$?)\$\Z", re.S)


@dataclass(frozen=True)
class HoleWords:
    """What the comment block above one hole declares."""

    name: str
    label: str | None
    claim: str | None
    prose: str
    line: int  # 1-based line of the ``have``


@dataclass(frozen=True)
class Declarations:
    approach: str | None
    licence: str | None
    holes: dict[str, HoleWords] = field(default_factory=dict)
    #: Every ``-- label:``/``-- claim:`` line seen outside a hole's block, by line: a line the
    #: author put somewhere the rule does not read (reported so it is not silently lost).
    stray: tuple[int, ...] = ()


@dataclass(frozen=True)
class Problem:
    code: str
    message: str
    hole: str | None = None
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "hole": self.hole, "line": self.line}


def _comment_lines(lines: Sequence[str], end: int) -> list[tuple[int, str]]:
    """The contiguous comment lines directly above ``lines[end]``, in order, as (index, text)."""
    out: list[tuple[int, str]] = []
    i = end - 1
    while i >= 0:
        m = _COMMENT_RE.match(lines[i])
        if m is None:
            break
        out.append((i, m.group("text").rstrip()))
        i -= 1
    out.reverse()
    return out


def _keyed(block: Iterable[tuple[int, str]]) -> tuple[dict[str, str], list[str]]:
    """Split a comment block into its keyed lines and its prose. A ``claim:`` runs on over the
    following comment lines until one ends with ``$``."""
    keyed: dict[str, str] = {}
    prose: list[str] = []
    pending: str | None = None
    for _, text in block:
        if pending is not None:
            keyed[pending] = (keyed[pending] + " " + text.strip()).strip()
            if text.rstrip().endswith("$"):
                pending = None
            continue
        m = _KEY_RE.match(text.strip())
        if m is None:
            prose.append(text.strip())
            continue
        key, value = m.group("key"), m.group("value").strip()
        keyed.setdefault(key, value)
        if (
            key == "claim"
            and value.startswith("$")
            and not (len(value) > 1 and value.endswith("$"))
        ):
            pending = key
    return keyed, [p for p in prose if p]


def _is_hole(lines: Sequence[str], start: int) -> bool:  # noqa: PLR0911 — one per shape
    """Whether the ``have`` at ``lines[start]`` is bound to ``sorry`` (directly or as ``by`` then
    ``sorry``): the shape every hole has (step 4, ``hole-unnamed``)."""
    indent = len(lines[start]) - len(lines[start].lstrip())
    for j in range(start, len(lines)):
        if j > start:
            here = len(lines[j]) - len(lines[j].lstrip())
            if lines[j].strip() and here <= indent:
                return False  # the next statement at the same depth: no ``:=`` was found
        m = _ASSIGN_RE.search(lines[j])
        if m is None:
            continue
        rest = m.group("rest").strip()
        if rest.startswith("sorry"):
            return True
        if rest == "by" or rest.startswith("by "):
            after = rest[2:].strip()
            if after:
                return after.startswith("sorry")
            for k in range(j + 1, len(lines)):
                s = lines[k].strip()
                if not s or s.startswith("--"):
                    continue
                return s.startswith("sorry")
            return False
        return False
    return False


def declarations(partial_text: str) -> Declarations:
    """Read the grammar off a partial's text (D-12 v3.44)."""
    lines = partial_text.splitlines()
    approach: str | None = None
    licence: str | None = None
    holes: dict[str, HoleWords] = {}
    claimed: set[int] = set()
    for i, line in enumerate(lines):
        m = _HAVE_RE.match(line)
        if m is None or not _is_hole(lines, i):
            continue
        block = _comment_lines(lines, i)
        claimed.update(idx for idx, _ in block)
        keyed, prose = _keyed(block)
        name = m.group("name")
        holes.setdefault(
            name,
            HoleWords(
                name=name,
                label=keyed.get("label") or None,
                claim=_claim_text(keyed.get("claim")),
                prose=" ".join(prose),
                line=i + 1,
            ),
        )
    stray: list[int] = []
    for i, line in enumerate(lines):
        m = _COMMENT_RE.match(line)
        if m is None:
            continue
        k = _KEY_RE.match(m.group("text").strip())
        if k is None:
            continue
        key, value = k.group("key"), k.group("value").strip()
        if key == "approach" and approach is None:
            approach = value or None
        elif key == "licence" and licence is None:
            licence = value or None
        elif key in ("label", "claim") and i not in claimed:
            stray.append(i + 1)
    return Declarations(approach, licence, holes, tuple(stray))


def _claim_text(raw: str | None) -> str | None:
    """The claim without its dollar delimiters, or ``None`` when the line is not ``$…$``."""
    if raw is None:
        return None
    raw = raw.strip()
    m = _CLAIM_RE.match(raw)
    if m is None:
        return None
    inner = m.group("inner")
    if inner.startswith("$") and inner.endswith("$") and len(inner) >= 2:
        inner = inner[1:-1]
    inner = inner.strip()
    return inner or None


def problems(partial_text: str, hole_names: Sequence[str] | None = None) -> list[Problem]:
    """What the partial is missing (D-12 v3.44), in the order a reader fixes it: the approach,
    the licence, then each hole's label and claim. ``hole_names`` are the extractor's, when the
    caller has them (step 4): a hole the text scan did not see is still held to the rule."""
    d = declarations(partial_text)
    out: list[Problem] = []
    if not d.approach:
        out.append(
            Problem(
                "approach",
                "a partial names its approach: one `-- approach: <one line>` comment before its "
                "first hole, saying what attack this decomposition takes (D-12 v3.44)",
            )
        )
    elif len(d.approach) > APPROACH_MAX:
        out.append(
            Problem(
                "approach-long",
                f"the `-- approach:` line is {len(d.approach)} characters; at most {APPROACH_MAX}",
            )
        )
    if not d.licence:
        out.append(
            Problem(
                "licence",
                "a partial licenses its words: one `-- licence: <licence>` comment, one of "
                + ", ".join(LICENCES)
                + " (D-23); the labels and claims are filed as the author's gloss on each hole",
            )
        )
    elif d.licence not in LICENCES:
        out.append(
            Problem(
                "licence-invalid",
                f"`-- licence: {d.licence}` is not one of " + ", ".join(LICENCES),
            )
        )
    names = list(hole_names) if hole_names is not None else list(d.holes)
    for name in names:
        h = d.holes.get(name)
        line = h.line if h is not None else None
        label = h.label if h is not None else None
        if label is None:
            out.append(
                Problem(
                    "label",
                    f"hole {name}: no `-- label: <at most {LABEL_MAX} characters>` line in the "
                    "comment block directly above its `have` (D-12 v3.44)",
                    hole=name,
                    line=line,
                )
            )
        elif len(label) > LABEL_MAX:
            out.append(
                Problem(
                    "label-long",
                    f"hole {name}: its label is {len(label)} characters; at most {LABEL_MAX}",
                    hole=name,
                    line=line,
                )
            )
        elif "$" in label or "\n" in label:
            out.append(
                Problem(
                    "label-form",
                    f"hole {name}: a label is one line of plain text, no notation; the claim "
                    "line carries the notation",
                    hole=name,
                    line=line,
                )
            )
        claim = h.claim if h is not None else None
        if claim is None:
            out.append(
                Problem(
                    "claim" if h is None or not _has_claim_line(partial_text, h) else "claim-form",
                    f"hole {name}: "
                    + (
                        "no `-- claim: $<the hole in notation>$` line in the comment block "
                        "directly above its `have`"
                        if h is None or not _has_claim_line(partial_text, h)
                        else "its `-- claim:` line is not `$…$` with something inside: the hole "
                        "in notation between dollar signs (a `$$…$$` display is accepted too)"
                    )
                    + " (D-12 v3.44)",
                    hole=name,
                    line=line,
                )
            )
        elif len(claim) > CLAIM_MAX:
            out.append(
                Problem(
                    "claim-long",
                    f"hole {name}: its claim is {len(claim)} characters; at most {CLAIM_MAX}",
                    hole=name,
                    line=line,
                )
            )
    return out


def _has_claim_line(partial_text: str, h: HoleWords) -> bool:
    lines = partial_text.splitlines()
    block = _comment_lines(lines, h.line - 1)
    return any(_KEY_RE.match(t.strip()) and t.strip().startswith("claim:") for _, t in block)


# --- a route's approach, with its fallbacks for partials merged before v3.44 (R4) ---------------


def _cut(text: str, width: int) -> str:
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    return text[: width - 1].rstrip() + "…"


def leading_comment(partial_text: str) -> str | None:
    """The first comment paragraph after the theorem's ``:= by`` line, with the keyed lines
    (annex, licence, approach, label, claim) left out; ``None`` when the body opens with code."""
    lines = partial_text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if _ASSIGN_RE.search(ln) and ln.rstrip().endswith("by")),
        None,
    )
    if start is None:
        return None
    found: list[str] = []
    for line in lines[start + 1 :]:
        m = _COMMENT_RE.match(line)
        if m is None:
            if line.strip() and found:
                break
            if line.strip():
                return None
            continue
        text = m.group("text").strip()
        if _KEY_RE.match(text):
            continue
        if not text and found:
            break
        if text:
            found.append(text)
    return " ".join(found) if found else None


def annex_first_sentence(annex_text: str | None) -> str | None:
    if not annex_text:
        return None
    body = _FRONT_MATTER_RE.sub("", annex_text, count=1).strip()
    if not body:
        return None
    paragraph = " ".join(body.split("\n\n", 1)[0].split())
    sentence = _SENTENCE_END_RE.split(paragraph, maxsplit=1)[0].strip()
    return sentence or None


def approach_of(partial_text: str, *, annex: str | None = None) -> str | None:
    """The route's approach: declared, else the leading comment, else the annex's first
    sentence, else ``None``; never longer than the schema's width."""
    d = declarations(partial_text)
    for candidate in (d.approach, leading_comment(partial_text), annex_first_sentence(annex)):
        if candidate:
            return _cut(candidate, APPROACH_MAX)
    return None


# --- a node's label and claim (R3; D-3 v3.44) ----------------------------------------------------

_OPENING_RE = re.compile(
    r"\A\s*(?:\$\$(?P<display>.+?)\$\$|\$(?=[^\s$])(?P<inline>[^$\n]*?)(?<=[^\s$])\$(?!\d))", re.S
)


def claim_of(body: str) -> str | None:
    """The claim a gloss body opens with (F20-T16's math-first form), without its delimiters."""
    m = _OPENING_RE.match(body or "")
    if m is None:
        return None
    inner = m.group("display") if m.group("display") is not None else m.group("inline")
    inner = (inner or "").strip()
    return inner or None


def label_of(
    node_id: str,
    *,
    gloss_label: str | None,
    hole_name: str | None,
    title: str | None = None,
) -> tuple[str, str]:
    """``(label, source)``: the gloss's label, else the hole's name, else the target's title,
    else the id (D-3 v3.44)."""
    if gloss_label:
        return _cut(gloss_label, 200), "gloss"
    if hole_name:
        return _cut(hole_name, 200), "hole"
    if title:
        return _cut(title, 200), "target"
    return node_id, "id"
