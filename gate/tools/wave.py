"""F14-T11 (R13): draft one reviewable intake directory per high-graded catalog row.

    uv run python gate/tools/wave.py --catalog docs/lean_conjecture_catalog.json \\
        --fc <formal-conjectures checkout at the catalog's pin> \\
        --out engineering/onramp/open/wave1 [--min-score 5] [--skip erdos:376 ...] [--curator NAME]

For each row scoring at least ``--min-score`` (an Erdős row must also be open on the site), the
driver reads the registry file at the pin and writes ``<out>/<target-id>/`` with ``record.yaml``,
``Statement.lean`` (the upstream header verbatim, ``import Mathlib``, the file's ``open`` lines, and
the main open statement as ``Opn.<name>``, a registry question ``answer(sorry) ↔ P`` stated as P,
F11-Q24) and ``Witness.lean``; the upstream file under ``<out>/upstream/``; an ``import.sh``
that runs ``intake import-fc`` once per draft with the row's evidence (F14-R4); and
``REPORT.md``.

It refuses, naming why, what it cannot draft honestly (F14-Q11): a statement that uses a name the
registry's own helper library declares (``FormalConjecturesForMathlib``) or a file-local definition,
both of which need a port into ``defs/``; a value-typed statement (``= answer(sorry)``), which is a
question and not a conjecture; a theorem with binders before its colon, whose witness is not
``True`` and must be written by hand, and for the same reason one whose leading ``∀`` binders
carry hypotheses (F14-T15); a use of a file-local ``notation``; a ``let``/``have`` opening spanning
lines; a file with no copyright header to keep. Every draft is a
curator's to read before the import runs (R13): the driver writes files, never the graph.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import intake, layout, schemas

ROOT = Path(__file__).resolve().parents[2]
FC_REPO = "google-deepmind/formal-conjectures"
FC_AUTHOR = "The Formal Conjectures Authors"
ATTRIBUTION = f"{FC_AUTHOR} ({FC_REPO}), Apache-2.0"
HELPER_LIBRARY = "FormalConjecturesForMathlib"
#: AMS subject classes to the graph's domain tags (D-6); an unmapped class drafts nothing. The
#: four classes D-6 excludes map to the excluded tags themselves, so ``intake.check_domains``
#: refuses the record in D-6's own words (F14-T18).
DOMAINS: dict[str, str] = {
    "3": "logic",
    "5": "combinatorics",
    "6": "order-theory",
    "11": "number-theory",
    "12": "field-theory",
    "13": "commutative-algebra",
    "14": "algebraic-geometry",
    "15": "linear-algebra",
    "20": "group-theory",
    "26": "real-analysis",
    "28": "measure-theory",
    "30": "complex-analysis",
    "33": "special-functions",
    "35": "pde",
    "37": "dynamical-systems",
    "40": "sequences-and-series",
    "42": "harmonic-analysis",
    "46": "functional-analysis",
    "51": "geometry",
    "52": "discrete-geometry",
    "53": "differential-geometry",
    "54": "topology",
    "55": "algebraic-topology",
    "60": "probability",
    "68": "computer-science",
    "81": "quantum-theory",
    "90": "optimization",
}
#: AMS subject classes to arXiv categories, for the record's F25-R4 classification; a class with
#: no arXiv home (quantum physics is `quant-ph`, outside the schema's `archive.XX` grammar)
#: contributes its MSC range only.
ARXIV: dict[str, str] = {
    "3": "math.LO",
    "5": "math.CO",
    "6": "math.CO",
    "11": "math.NT",
    "12": "math.RA",
    "13": "math.AC",
    "14": "math.AG",
    "15": "math.RA",
    "20": "math.GR",
    "26": "math.CA",
    "28": "math.CA",
    "30": "math.CV",
    "33": "math.CA",
    "35": "math.AP",
    "37": "math.DS",
    "40": "math.CA",
    "42": "math.CA",
    "46": "math.FA",
    "51": "math.MG",
    "52": "math.MG",
    "53": "math.DG",
    "54": "math.GN",
    "55": "math.AT",
    "60": "math.PR",
    "68": "cs.CC",
    "90": "math.OC",
}
WITNESS = (
    "/-! Non-vacuity witness (D-4 step 7): the statement has no hypotheses, so the expected\n"
    "witness type is `True`. -/\n\ntheorem witness : True := trivial\n"
)
#: The witness for a statement whose leading ``∀`` binders bind data and no hypothesis: step 7
#: closes every leading binder, so ``∀ n : Nat, P n`` expects ``∃ n, True``, which ``default``
#: inhabits (the docker-tier admission of a drafted row found the driver writing ``True``).
CLOSED_WITNESS = (
    "/-! Non-vacuity witness (D-4 step 7): the statement opens with binders that carry no\n"
    "hypothesis, so the expected witness type is their closure over `True`, inhabited by\n"
    "`default`. -/\n\ntheorem witness : ∃ {binders}, True := ⟨{terms}⟩\n"
)
_DECL_NAME_RE = re.compile(
    r"^\s*(?:noncomputable\s+)?(?:def|abbrev|structure|class|theorem|lemma|instance|inductive)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_.']*)",
    re.M,
)
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_OPEN_RE = re.compile(r"^open\b.*$", re.M)


@dataclass
class Draft:
    key: str
    target_id: str
    reasons: list[str] = field(default_factory=list)
    directory: Path | None = None
    hand: str = ""  # which hand files the draft used, for the report (F14-T18)
    defs: tuple[str, ...] = ()  # the ported modules, for import.sh --defs
    hazards: bool = False  # a hazards.yaml travels with the draft, for import.sh --hazards

    @property
    def drafted(self) -> bool:
        return self.directory is not None


#: The Mathlib namespaces the helper library extends with new definitions: a dotted use such as
#: ``S.IsAPOfLength`` or ``n.maxPrimeFac`` reaches one of those, while ``A.card`` or ``f.eval`` is
#: Mathlib's own member even though the library declares an unrelated ``card`` or ``eval``.
MATHLIB_NAMESPACES: frozenset[str] = frozenset(
    {
        "ENat", "Filter", "Finset", "Function", "Int", "List", "Multiset", "NNReal", "Nat",
        "Polynomial", "Rat", "Real", "Set", "SimpleGraph", "ZMod",
    }
)  # fmt: skip
_DEFINITION_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+|protected\s+|private\s+)*"
    r"(?:def|abbrev|structure|class|inductive)\s+(?P<name>[A-Za-z_][A-Za-z0-9_.']*)"
)
_NAMESPACE_RE = re.compile(r"^\s*(?P<kind>namespace|section|end)\b\s*(?P<name>[A-Za-z0-9_.']*)")


def helper_names(fc: Path) -> dict[str, set[str]]:
    """Every definition the registry's helper library declares, by short name, with the namespace
    it lives in (theorems are not vocabulary a statement can use without the library)."""
    index: dict[str, set[str]] = {}
    for path in sorted((fc / HELPER_LIBRARY).rglob("*.lean")):
        stack: list[tuple[str, str]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            scope = _NAMESPACE_RE.match(line)
            if scope is not None:
                kind, name = scope.group("kind"), scope.group("name")
                if kind in ("namespace", "section"):
                    stack.append((kind, name))
                elif stack:
                    stack.pop()
                continue
            m = _DEFINITION_RE.match(line)
            if m is None:
                continue
            parts = [n for k, n in stack if k == "namespace" and n] + m.group("name").split(".")
            index.setdefault(parts[-1], set()).add(".".join(parts[:-1]))
    return index


def bound_names(prop: str) -> set[str]:
    """Names the statement binds itself (∀, ∃, fun, binder groups, tuple patterns): a bound ``S``
    or ``b`` is a variable, whatever the helper library calls its definitions."""
    bound: set[str] = set()
    for m in re.finditer(r"(?:∀ᶠ|∃ᶠ|∀ᵉ|∃!|∀|∃|fun|λ)\s*([^,:=↦∈⊆<>≤≥]+)", prop):
        bound.update(_TOKEN_RE.findall(m.group(1).split(" in ")[0]))
    # A parenthesised `(x y : T)` is a binder group only right after a binder keyword or another
    # group; elsewhere it is a type ascription, `(sumRep A n : Real)`, whose names are not bound.
    group = r"[(\{⦃\[]\s*([A-Za-z_][A-Za-z0-9_' ]*?)\s*:[^)\}⦄\]]*[)\}⦄\]]"
    for m in re.finditer(rf"(?:∀ᶠ|∃ᶠ|∀ᵉ|∃!|∀|∃|fun|λ)((?:\s*{group})+)", prop):
        for inner in re.finditer(group, m.group(1)):
            bound.update(_TOKEN_RE.findall(inner.group(1)))
    for m in re.finditer(
        r"\(\s*([A-Za-z_][A-Za-z0-9_']*)\s*,\s*([A-Za-z_][A-Za-z0-9_']*)\s*\)", prop
    ):
        bound.update(m.groups())
    return bound


def helpers_used(prop: str, index: dict[str, set[str]]) -> list[str]:
    """The helper definitions a statement uses: a bare name the library defines and the statement
    does not bind (the file may ``open`` the namespace it lives in, so the namespace cannot excuse
    it), or a dotted name the library defines inside a Mathlib namespace it extends, or writes out
    in full (``EuclideanGeometry.triangle_area``). Found reading the drafts by hand: narrowing the
    bare rule to top-level names let ``hypergraphRamsey``, ``sumRep`` and ``lcmInterval``
    through."""
    bound = bound_names(prop)
    used: set[str] = set()
    for m in _TOKEN_RE.finditer(prop):
        name = m.group(0)
        if name not in index or name in bound:
            continue
        dotted = m.start() > 0 and prop[m.start() - 1] == "."
        spaces = index[name]
        if not dotted or any(
            s and (s.rsplit(".", 1)[-1] in MATHLIB_NAMESPACES or f"{s}.{name}" in prop)
            for s in spaces
        ):
            used.add(name)
    return sorted(used)


def target_id_for(row: dict[str, Any]) -> str:
    if row["kind"] == "erdos":
        return f"erdos-{row['key'].split(':', 1)[1]}"
    decl = str(row["decl"]).rsplit(".", 1)[-1]
    return re.sub(r"(?<!^)(?=[A-Z])", "-", decl).replace("_", "-").lower()


def theorem_name(row: dict[str, Any]) -> str:
    if row["kind"] == "erdos":
        return f"Opn.erdos_{row['key'].split(':', 1)[1]}"
    return "Opn." + re.sub(r"[^A-Za-z0-9_]", "_", str(row["decl"]).rsplit(".", 1)[-1])


BINDERS_BEFORE_COLON = "binders before the colon: the witness is not `True`, write it by hand"


def extract(text: str, decl: str) -> tuple[str | None, str, str]:
    """The main statement's proposition, how it was taken (``as stated`` / ``adapted``) and the
    binders before its colon (empty for none), or ``None`` and why it cannot be taken as it
    stands. Binders before the colon are kept as the registry writes them: the draft is refused
    unless the curator supplies the witness by hand (F14-T18)."""
    # The catalog names a declaration as the file writes it (``erdos_1065.parts.i``), so the full
    # name is the one to find; the short name is only the fallback for a namespaced file.
    m = None
    for name in dict.fromkeys((decl, decl.rsplit(".", 1)[-1])):
        m = re.search(
            rf"^theorem\s+{re.escape(name)}(?![\w.'])(?P<rest>[\s\S]*?):=\s*(?:by\s+)?sorry",
            text,
            re.M,
        )
        if m is not None:
            break
    if m is None:
        return None, f"no `theorem {decl} ... := by sorry` in the registry file", ""
    rest = m.group("rest")
    colon = _top_level(rest, ":")
    if colon < 0:
        return None, "no colon after the theorem's binders", ""
    binders = " ".join(rest[:colon].split())
    prop = rest[colon + 1 :].strip()
    value_typed = "value-typed (`answer(sorry)` as a value): a question, not a conjecture"
    if prop.startswith("answer(sorry)"):
        stripped = prop[len("answer(sorry)") :].lstrip()
        if not stripped.startswith("↔"):
            return None, value_typed, ""
        return stripped[1:].strip(), "adapted", binders
    if "answer(sorry)" in prop:
        return None, value_typed, ""
    return prop, "as stated", binders


_OPENERS = {"(": ")", "[": "]", "{": "}", "⦃": "⦄", "⟨": "⟩"}
_CLOSERS = frozenset(_OPENERS.values())
_RELATION_RE = re.compile(r"[<>≤≥∈∉⊆⊂≠]")
#: ``∀ᶠ x in l, P`` is ``Filter.Eventually``, a proposition and not a binder (Green's problem 58
#: read as an uncloseable binder until F14-T18).
_LEADING_FORALL_RE = re.compile(r"^(?:∀ᵉ|∀(?!ᶠ))\s*")


def _top_level(text: str, target: str) -> int:
    """The index of the first ``target`` outside every bracket, or -1."""
    depth = 0
    for i, ch in enumerate(text):
        if ch in _OPENERS:
            depth += 1
        elif ch in _CLOSERS:
            depth = max(depth - 1, 0)
        elif depth == 0 and text.startswith(target, i):
            return i
    return -1


def _binder_has_condition(segment: str) -> bool:
    """A binder carries a hypothesis when a name is bounded (``n > 1``, ``(m ≥ 2)``, ``x ∈ S``):
    the relation sits before any ``:`` of the binder, never inside its type."""
    groups = re.findall(r"[(⦃{]([^()⦃⦄{}]*)[)⦄}]", segment)
    bare = re.sub(r"[(\[⦃{][^()\[\]⦃⦄{}]*[)\]⦄}]", " ", segment)
    return any(_RELATION_RE.search(part.split(":", 1)[0]) for part in [bare, *groups])


def leading_hypotheses(prop: str) -> bool:
    """Whether the proposition opens with ``∀``/``∀ᵉ`` binders that carry hypotheses, a bounded
    binder or an implication among them. Step 7 takes its witness type from those (F14-T15: nine
    live intakes drafted ``True`` for such statements and failed admission), so they are hand work.
    """
    body = prop.strip()
    seen_forall = False
    while (m := _LEADING_FORALL_RE.match(body)) is not None:
        seen_forall = True
        rest = body[m.end() :]
        comma = _top_level(rest, ",")
        if comma < 0:
            return False
        if _binder_has_condition(rest[:comma]):
            return True
        body = rest[comma + 1 :].strip()
    return seen_forall and _top_level(body, "→") >= 0


_NOTATION_RE = re.compile(r'^\s*(?:local\s+|scoped\s+)?notation\s*"([^"]+)"', re.M)
_GROUP_RE = re.compile(r"\(([^()]*)\)")


def leading_binders(prop: str) -> tuple[str, int] | None:
    """The leading ``∀`` binders as one ``∃`` binder list and the number of names they bind, or
    ``None`` when the driver cannot close them: none at all, an implicit, strict-implicit or
    instance binder, an untyped name, or a binder the hypotheses rule owns. Each group is
    parenthesised (``∀ n m : Nat`` becomes ``(n m : Nat)``) so several ``∀``s chain into one ``∃``.
    """
    body = prop.strip()
    groups: list[str] = []
    names = 0
    while (m := _LEADING_FORALL_RE.match(body)) is not None:
        rest = body[m.end() :]
        comma = _top_level(rest, ",")
        if comma < 0:
            return None
        segment = rest[:comma].strip()
        if any(ch in segment for ch in "{⦃[") or _binder_has_condition(segment):
            return None
        parts = _GROUP_RE.findall(segment) if segment.startswith("(") else [segment]
        if segment.startswith("(") and _GROUP_RE.sub("", segment).strip():
            return None  # something beside parenthesised groups
        for part in parts:
            head, colon, _typ = part.partition(":")
            bound = head.split()
            if not colon or not bound or any(not _TOKEN_RE.fullmatch(n) for n in bound):
                return None
            groups.append(f"({part.strip()})")
            names += len(bound)
        body = rest[comma + 1 :].strip()
    if not groups or _top_level(body, "→") >= 0:
        return None
    return " ".join(groups), names


def witness_for(prop: str) -> str:
    """``Witness.lean`` for a proposition the driver drafts: ``True`` when nothing is bound,
    the closure over ``True`` when leading binders bind data (``leading_binders``)."""
    closed = leading_binders(prop)
    if closed is None:
        return WITNESS
    binders, names = closed
    return CLOSED_WITNESS.format(
        binders=binders, terms=", ".join(["default"] * names + ["trivial"])
    )


def parse_refusal(prop: str) -> str | None:
    """Why a proposition cannot be re-stated under the drafted theorem at all, or ``None``."""
    if re.match(r"(?:letI|haveI|let|have)\b", prop) and "\n" in prop:
        # erdos-1139, live: a `letI` binding followed by the body on the next line does not parse
        # once re-indented under the drafted theorem (Lean 4.33, "expected ';' or line break").
        return "the statement opens with a `let`/`have` binding spanning lines: restate it by hand"
    return None


def witness_refusal(prop: str) -> str | None:
    """Why the driver cannot write the proposition's witness, or ``None``. A curator's hand
    `Witness.lean` lifts this refusal (F14-T18)."""
    if leading_hypotheses(prop):
        return (
            "leading ∀ binders carry hypotheses (a bounded binder or an implication): the "
            "witness is not `True`, write it by hand"
        )
    if _LEADING_FORALL_RE.match(prop.strip()) and leading_binders(prop) is None:
        return (
            "leading ∀ binders the driver cannot close (implicit, instance or untyped): the "
            "witness is their closure over `True`, write it by hand"
        )
    return None


def shape_refusal(prop: str) -> str | None:
    """Why a proposition's shape needs a hand-written draft, or ``None``."""
    return parse_refusal(prop) or witness_refusal(prop)


@dataclass(frozen=True)
class Hand:
    """The curator's hand files for one target (``--overrides DIR/<target-id>/``): a
    ``Witness.lean`` where the driver cannot write the witness, and ``defs/*.lean`` ports where
    the statement uses a name the registry's helper library or its own file defines."""

    witness: Path | None = None
    defs: tuple[Path, ...] = ()
    hazards: Path | None = None  # the curator's step-6 acknowledgements (F02-R4), a YAML list

    @classmethod
    def read(cls, overrides: Path | None, target_id: str) -> Hand:
        if overrides is None or not (overrides / target_id).is_dir():
            return cls()
        here = overrides / target_id
        witness = here / "Witness.lean"
        hazards = here / "hazards.yaml"
        return cls(
            witness if witness.is_file() else None,
            tuple(sorted((here / "defs").glob("*.lean"))),
            hazards if hazards.is_file() else None,
        )

    @property
    def note(self) -> str:
        parts = (
            (["Witness.lean"] if self.witness else [])
            + (["defs " + " ".join(p.stem for p in self.defs)] if self.defs else [])
            + (["hazards.yaml"] if self.hazards else [])
        )
        return f" (hand: {'; '.join(parts)})" if parts else ""


def classification_for(ams: list[str]) -> tuple[list[str], list[str]]:
    """F25-R4's block from the registry's AMS classes: the arXiv categories they map to (the
    first two, in the registry's order) and every class as an MSC 2020 range."""
    arxiv = list(dict.fromkeys(ARXIV[a] for a in ams if a in ARXIV))[:2]
    msc = [f"{a.zfill(2)}-xx" for a in ams][:8]
    return arxiv, msc


_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)


def heading_of(text: str) -> str | None:
    """The `# heading` of the registry file's module doc, which names the problem."""
    m = _HEADING_RE.search(text)
    return m.group(1) if m else None


def record_for(
    row: dict[str, Any], catalog: dict[str, Any], curator: str, heading: str | None = None
) -> dict[str, Any]:
    number = row["key"].split(":", 1)[1] if row["kind"] == "erdos" else None
    site = f"https://www.erdosproblems.com/{number}" if number else None
    docstring = " ".join(str(row.get("docstring") or "").split())
    first = re.split(r"(?<=[.?])\s", docstring, maxsplit=1)[0] if docstring else ""
    part = re.search(r"\.parts\.([A-Za-z0-9_]+)$", str(row["decl"]))
    label = f"Erdős problem {number}" + (f", part {part.group(1)}" if part else "")
    # An Erdős row is titled by its number and the docstring's first sentence; any other row by
    # its file's heading (F14-T18: a docstring opens with context, "Suppose $A, B ⊆ ...").
    title = f"{label}: " + (first or str(row["decl"])) if number else heading or str(row["decl"])
    reasons = "; ".join(str(r) for r in row["reasons"])
    attempts = ", ".join(row.get("nexus_attempted") or []) or "none on record"
    history = row.get("history") or {}
    doc: dict[str, Any] = {
        "schema": intake.SCHEMA,
        "id": target_id_for(row),
        "title": title[:200],
        "informal": docstring[:4000] or None,
        "paraphrase": None if docstring else str(row["decl"]),
        "track": "open",
        "source": {"kind": "formal-conjectures", "ref": row["file"], "url": site or ""},
        "curator": curator,
        "prior_art": {
            "arxiv_query": None,
            "forum_url": site,
            "summary": (
                f"Catalog score {row['score']} ({row['letter']}) at registry commit "
                f"{catalog['fc_commit'][:12]}: {reasons}. AlphaProof Nexus attempts: {attempts}. "
                f"In the registry since {history.get('first', 'unknown')}. Drafted by "
                "gate/tools/wave.py (F14-T11); the curator reads it before import (R13)."
            )[:4000],
        },
        "library_coverage": {"mathlib_sha": catalog["mathlib_rev"], "missing_prerequisites": []},
        "provenance": {
            "statement_source": "formal-conjectures",
            "author": FC_AUTHOR,
            "adversarially_reviewed": False,
            "upstream_commit": catalog["fc_commit"],
        },
        "sources": [],
        "attack_routes": [],
        "posting": None,
        "domains": sorted({DOMAINS[a] for a in row.get("ams") or [] if a in DOMAINS}),
        "qa_summary": None,
    }
    if not doc["source"]["url"]:
        doc["source"]["url"] = (
            f"https://github.com/{FC_REPO}/blob/{catalog['fc_commit']}/{row['file']}"
        )
    arxiv, msc = classification_for([str(a) for a in row.get("ams") or []])
    if arxiv and msc:
        doc = intake.with_classification(doc, arxiv=arxiv, msc=msc)
    return doc


def draft_row(  # noqa: PLR0911, PLR0912, PLR0913, PLR0915, PLR0917 — a check per refusal, an input per fact
    row: dict[str, Any],
    catalog: dict[str, Any],
    fc: Path,
    out: Path,
    helpers: dict[str, set[str]],
    curator: str,
    overrides: Path | None = None,
) -> Draft:
    draft = Draft(row["key"], target_id_for(row))
    hand = Hand.read(overrides, draft.target_id)
    draft.hand = hand.note
    if ".variants." in str(row["decl"]):
        # R13, found reading the first real run: erdos_267 is resolved upstream, and its only open
        # declaration is a generalisation. Listing that as the problem misstates the target, so it
        # is refused whatever the file holds.
        draft.reasons.append(
            f"the open statement is a variant ({row['decl']}), not the problem itself: "
            "curate by hand"
        )
        return draft
    source = fc / row["file"]
    if not source.is_file():
        draft.reasons.append(f"{row['file']} is not in the checkout")
        return draft
    text = source.read_text(encoding="utf-8")
    header = intake.copyright_header(text)
    if header is None:
        draft.reasons.append("the registry file carries no copyright header to keep")
        return draft
    prop, how, binders = extract(text, str(row["decl"]))
    if prop is None:
        draft.reasons.append(how)
        return draft
    shape = parse_refusal(prop)
    if shape is not None:
        draft.reasons.append(shape)
    # The witness: the driver's where it can write one, the curator's hand file otherwise
    # (F14-T18); without either the row is refused by the reason the driver cannot.
    witness = witness_refusal(prop) or (BINDERS_BEFORE_COLON if binders else None)
    if witness is not None and hand.witness is None:
        draft.reasons.append(witness)
    # Names the statement takes from its file or the helper library: a port under defs/ (R12)
    # lifts the refusal; the curator supplies it by hand, the driver only imports it.
    tokens = set(_TOKEN_RE.findall(prop))
    notations = sorted(n for n in _NOTATION_RE.findall(text) if n in tokens)
    if notations and not hand.defs:
        # erdos-812, live: `local notation "R" => hypergraphRamsey 2` is neither a def nor a
        # helper-library declaration, and it does not survive the statement leaving its file.
        draft.reasons.append("uses file-local notation (port into defs/): " + ", ".join(notations))
    local = sorted(n for n in row.get("local_defs") or [] if n.rsplit(".", 1)[-1] in tokens)
    if local and not hand.defs:
        draft.reasons.append("uses file-local definitions (port into defs/): " + ", ".join(local))
    locals_short = {n.rsplit(".", 1)[-1] for n in row.get("local_defs") or []}
    used = [n for n in helpers_used(prop, helpers) if n not in locals_short]
    if used and not hand.defs:
        draft.reasons.append(
            f"uses names {HELPER_LIBRARY} declares (port first): " + ", ".join(used)
        )
    domains = {DOMAINS.get(a) for a in row.get("ams") or []}
    if not (domains - {None}):
        draft.reasons.append(f"no graph domain for AMS {', '.join(row.get('ams') or []) or 'none'}")
    if draft.reasons:
        return draft

    doc = record_for(row, catalog, curator, heading_of(text))
    try:
        schemas.validate(doc, intake.SCHEMA)
        intake.check_artifacts(doc)
        intake.check_domains(doc)
        intake.check_quotation(doc)
    except (schemas.SchemaError, intake.IntakeError) as exc:
        draft.reasons.append(f"the drafted record is refused: {exc}")
        return draft
    opens = "\n".join(_OPEN_RE.findall(text))
    note = (
        "the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its "
        "affirmative reading (F11-Q24)"
        if how == "adapted"
        else "stated as the registry states it"
    )
    if hand.defs:
        note += "; the names it takes from the registry's library are ported under defs/ (R12)"
    imports = "import Mathlib\n" + "".join(f"import Defs.{p.stem}\n" for p in hand.defs)
    head = f"theorem {theorem_name(row)}" + (f" {binders} :" if binders else " :")
    statement = (
        f"{header}\n\n{imports}\n/-! {doc['title']} — imported from {FC_REPO} "
        f"({row['file']} at {catalog['fc_commit']}, Apache-2.0); {note}. Drafted by "
        "gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/\n\n"
        + (f"{opens}\n\n" if opens else "")
        + f"{head}\n    {prop} := by\n  sorry\n"
    )
    parsed = layout.parse_statement(statement)
    if not isinstance(parsed, layout.Statement):
        draft.reasons.append(f"the drafted statement does not parse: {parsed.message}")
        return draft
    directory = out / draft.target_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "record.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "Statement.lean").write_text(statement, encoding="utf-8")
    if hand.witness is not None:
        shutil.copyfile(hand.witness, directory / "Witness.lean")
    else:
        (directory / "Witness.lean").write_text(witness_for(prop), encoding="utf-8")
    if hand.defs:
        (directory / "defs").mkdir(exist_ok=True)
        for port in hand.defs:
            shutil.copyfile(port, directory / "defs" / port.name)
        draft.defs = tuple(p.stem for p in hand.defs)
    if hand.hazards is not None:
        shutil.copyfile(hand.hazards, directory / "hazards.yaml")
        draft.hazards = True
    upstream = out / "upstream" / row["file"]
    upstream.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, upstream)
    draft.directory = directory
    return draft


def import_script(
    drafts: list[Draft], rows: dict[str, dict[str, Any]], catalog: dict[str, Any]
) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "# Wave one, drafted by gate/tools/wave.py (F14-T11): one intake import-fc per target,",
        "# each with its catalog evidence (F14-R4). Read every draft first (R13).",
        "# One target per pull request (F11-Q26): run with --branch per target, or import on",
        "# main and split.",
        "#",
        "#   <out>/import.sh [../open_proof_network_graph] [--sandbox]",
        "set -euo pipefail",
        'HERE="$(cd "$(dirname "$0")" && pwd)"',
        'ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"',
        'GRAPH="${1:-$ROOT/../open_proof_network_graph}"',
        'MODE="${2:---no-toolchain}"',
        'NETWORK="${NETWORK:-$(git -C "$ROOT" rev-parse HEAD)}"',
        'AUTHOR="${AUTHOR:-thisisanameforsure}"',
        f"PIN={catalog['fc_commit']}",
        'export PYTHONPATH="$ROOT/gate${PYTHONPATH:+:$PYTHONPATH}"',
    ]
    for d in drafts:
        if not d.drafted:
            continue
        row = rows[d.key]
        lines.append(
            f'uv run --frozen --project "$ROOT" python -m opn_gate.cli intake import-fc '
            f'"$HERE/upstream/{row["file"]}" --at "$PIN" --graph "$GRAPH" --target {d.target_id} '
            f'--from "$HERE/{d.target_id}/record.yaml" '
            f'--witness "$HERE/{d.target_id}/Witness.lean" '
            f'--statement "$HERE/{d.target_id}/Statement.lean" '
            + (f'--defs "$HERE/{d.target_id}/defs" ' if d.defs else "")
            + (f'--hazards "$HERE/{d.target_id}/hazards.yaml" ' if d.hazards else "")
            + f"--path {row['file']} "
            f"--repo {FC_REPO} "
            f'--url "https://github.com/{FC_REPO}/blob/$PIN/{row["file"]}" --licence Apache-2.0 '
            f'--attribution "{ATTRIBUTION}" --upstream-author "{FC_AUTHOR}" --author "$AUTHOR" '
            f'--evidence-from "$ROOT/docs/lean_conjecture_catalog.json" --key {d.key} '
            '--network-commit "$NETWORK" '
            '$( [ "$MODE" = "--sandbox" ] && echo --sandbox || echo --no-toolchain ) | tail -3'
        )
    return "\n".join(lines) + "\n"


def report(
    drafts: list[Draft], catalog: dict[str, Any], min_score: int, keys: list[str] | None = None
) -> str:
    done = [d for d in drafts if d.drafted]
    held = [d for d in drafts if not d.drafted]
    which = (
        f"the rows named with --key: {', '.join(keys)}"
        if keys
        else f"rows scoring {min_score} or more"
    )
    out = [
        "# Wave drafts (F14-T11, T18)",
        "",
        f"Catalog at registry commit {catalog['fc_commit']}, {which}.",
        f"Drafted {len(done)}, refused {len(held)}. Read every draft before import (F14-R13).",
        "",
        "## Drafted",
        "",
        *[f"- `{d.key}` → `{d.target_id}/`{d.hand}" for d in done],
        "",
        "## Refused (a later wave, or a port by hand; F14-Q11)",
        "",
        *[f"- `{d.key}`: {'; '.join(d.reasons)}" for d in held],
        "",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "docs" / "lean_conjecture_catalog.json"
    )
    parser.add_argument("--fc", type=Path, required=True, help="formal-conjectures at the pin")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-score", type=int, default=5)
    parser.add_argument("--skip", action="append", default=[], help="a key already listed")
    parser.add_argument(
        "--key",
        action="append",
        default=[],
        help="draft only these keys, whatever their score (wave two loads every open statement)",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        help="the curator's hand files: <dir>/<target-id>/Witness.lean and defs/*.lean (F14-T18)",
    )
    parser.add_argument("--curator", default="thisisanameforsure")
    args = parser.parse_args(argv)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows = {r["key"]: r for r in catalog["rows"]}
    chosen = [
        r
        for r in catalog["rows"]
        if r["score"] is not None
        and (r["key"] in args.key if args.key else r["score"] >= args.min_score)
        and r["key"] not in args.skip
        and (r["kind"] != "erdos" or str(r.get("site_status") or "").upper() == "OPEN")
    ]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    helpers = helper_names(args.fc)
    drafts = [
        draft_row(r, catalog, args.fc, out, helpers, args.curator, args.overrides) for r in chosen
    ]
    script = out / "import.sh"
    script.write_text(import_script(drafts, rows, catalog), encoding="utf-8")
    script.chmod(0o755)
    (out / "REPORT.md").write_text(
        report(drafts, catalog, args.min_score, args.key), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "drafted": [d.key for d in drafts if d.drafted],
                "refused": [{"key": d.key, "reasons": d.reasons} for d in drafts if not d.drafted],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
