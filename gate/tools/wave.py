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

A statement that uses a name the registry's own helper library declares
(``FormalConjecturesForMathlib``) or a file-local definition is drafted with the port under
``defs/`` (F14-R12, T19): the library module that declares the name, and the modules it imports,
copied verbatim and named by their path inside the library; the registry file's own definitions as
``Local.lean``, its theorems gone. Both lose the module syntax (``module``, ``public import``, the
exposed public section, ``public``, ``@[expose]``) so the gate elaborates them under ``import
Mathlib``. A curator's hand ``defs/`` (``--overrides``) wins over the mechanical port.

It refuses, naming why, what it cannot draft honestly (F14-Q11): a value-typed statement
(``= answer(sorry)``), which is a question and not a conjecture; a theorem whose binders, before or
after its colon, carry a hypothesis, so the witness is not their closure over ``True`` and must be
written by hand (F14-T15); a use of a file-local ``notation``; a ``let``/``have`` opening spanning
lines; a file with no copyright header to keep. Every draft is a
curator's to read before the import runs (R13): the driver writes files, never the graph.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import shutil
import sys
import unicodedata
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
#: A Lean identifier, Greek letters included: `\w` is Unicode-aware, a digit cannot lead.
_TOKEN_RE = re.compile(r"[^\W\d][\w']*")
#: An `open` command names a namespace (or `scoped`); a prose line "open; [Kat16] gives …" in a
#: module doc does not (F14-T19).
_OPEN_RE = re.compile(r"^open\s+(?:scoped\s+)?[A-Z].*$", re.M)


@dataclass
class Draft:
    key: str
    target_id: str
    reasons: list[str] = field(default_factory=list)
    directory: Path | None = None
    hand: str = ""  # which hand files the draft used, for the report (F14-T18)
    defs: tuple[str, ...] = ()  # the ported modules, for import.sh --defs
    hazards: bool = False  # a hazards.yaml travels with the draft, for import.sh --hazards
    ports: tuple[str, ...] = ()  # the modules the driver ported itself, for the report (F14-T19)
    refused_dir: Path | None = None  # the statement written for a hand witness (F14-T21)

    @property
    def drafted(self) -> bool:
        return self.directory is not None

    @property
    def notes(self) -> str:
        return self.hand + (f" (port: {' '.join(self.ports)})" if self.ports else "")


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
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+|protected\s+|private\s+|public\s+)*"
    r"(?:def|abbrev|structure|class|inductive)\s+(?P<name>[A-Za-z_][A-Za-z0-9_.']*)"
)
#: A namespace name may carry guillemets (`Arxiv.«1601.03081»`, the registry's arXiv papers).
_NAMESPACE_RE = re.compile(r"^\s*(?P<kind>namespace|section|end)\b\s*(?P<name>[A-Za-z0-9_.'«»]*)")
_THEOREM_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:protected\s+|private\s+|public\s+)*"
    r"(?:theorem|lemma)\s+(?P<name>[A-Za-z_][A-Za-z0-9_.']*)"
)


_LIBRARY_NOTATION_RE = re.compile(
    r"^\s*(?:scoped(?:\[[^\]]*\])?\s+|local\s+)?(?:notation3?|infixl?|infixr|prefix|postfix)"
    r'(?::\d+)?\s*(?:\(.*?\)\s*)?"([^"]+)"'
)


@functools.lru_cache(maxsize=4)
def _scan_library(
    fc: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    """Every definition the registry's helper library declares, by short name: the namespaces it
    lives in, and the library modules that declare it (F14-T19, for the port); and every notation
    literal the library declares, by the modules declaring it (a notation is not a name the token
    scan sees: `ℝ²` is Geometry/2d.lean's)."""
    names: dict[str, set[str]] = {}
    modules: dict[str, set[str]] = {}
    notations: dict[str, set[str]] = {}
    lemmas: dict[str, set[str]] = {}  # a definition's body may cite the library's lemmas (T25)
    for path in sorted((fc / HELPER_LIBRARY).rglob("*.lean")):
        module = ".".join(path.relative_to(fc).with_suffix("").parts)
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
            n = _LIBRARY_NOTATION_RE.match(line)
            if n is not None:
                literal = n.group(1).strip()
                if literal and literal not in names:
                    notations.setdefault(literal, set()).add(module)
                continue
            t = _THEOREM_RE.match(line)
            if t is not None:
                parts = [n for k, n in stack if k == "namespace" and n] + t.group("name").split(".")
                lemmas.setdefault(parts[-1], set()).add(".".join(parts[:-1]))
                modules.setdefault(parts[-1], set()).add(module)
                continue
            m = _DEFINITION_RE.match(line)
            if m is None:
                continue
            parts = [n for k, n in stack if k == "namespace" and n] + m.group("name").split(".")
            names.setdefault(parts[-1], set()).add(".".join(parts[:-1]))
            modules.setdefault(parts[-1], set()).add(module)
    return names, modules, notations, lemmas


def helper_names(fc: Path) -> dict[str, set[str]]:
    """Every definition the registry's helper library declares, by short name, with the namespace
    it lives in (theorems are not vocabulary a statement can use without the library)."""
    return _scan_library(fc)[0]


def helper_modules(fc: Path) -> dict[str, set[str]]:
    """The library modules declaring each short name (F14-T19)."""
    return _scan_library(fc)[1]


def helper_notations(fc: Path) -> dict[str, set[str]]:
    """The library modules declaring each notation literal (F14-T19)."""
    return _scan_library(fc)[2]


def helper_lemmas(fc: Path) -> dict[str, set[str]]:
    """The namespaces of each library theorem, by short name (F14-T25: a ported definition's body
    may cite one, `Nat.squarefree_infinite`)."""
    return _scan_library(fc)[3]


def notations_used(text: str, notations: dict[str, set[str]]) -> list[str]:
    """The library notation literals that occur in ``text``."""
    return sorted(lit for lit in notations if lit in text)


# --- F14-T19: the mechanical port of a registry file into defs/ --------------------------------

_IMPORT_RE = re.compile(r"^(?:public\s+)?import\s+(?P<module>[A-Za-z0-9_.']+)\s*$")
#: The exposed public section becomes a plain (or `noncomputable`) section: its `end`, if any,
#: still closes it, and a `noncomputable` on it still covers every definition under it.
_PUBLIC_SECTION_RE = re.compile(
    r"^@\[expose\]\s*public\s+(?P<kind>(?:noncomputable\s+)?section)\s*$"
)
_HASH_COMMAND_RE = re.compile(r"^#[a-z_]+\b")
_PROOF_DECL_RE = re.compile(
    r"^(?:(?:noncomputable|private|protected|public|meta|partial|unsafe|nonrec)\s+)*"
    r"(?:theorem|lemma|example)\b"
)
_ANY_DECL_RE = re.compile(
    r"^(?:(?:noncomputable|private|protected|public|meta|partial|unsafe|nonrec)\s+)*"
    r"(?:theorem|lemma|example|def|abbrev|structure|class|inductive|instance|opaque|axiom|"
    r"notation|macro|syntax|elab|macro_rules|declare_syntax_cat|initialize)\b"
)
#: `public`, `meta` and `public meta` are module-system modifiers on imports, sections and
#: declarations alike.
_MODIFIER_PREFIX_RE = re.compile(r"^(?:(?:public|meta)\s+)+")
_LINTER_OPTION_RE = re.compile(r"^set_option\s+linter\.")
_IN_PREFIX_RE = re.compile(r"^(?:open|set_option|variable|omit|include)\b.*\bin$")
#: Attributes only the registry's own util library defines (`category research open`, `AMS 11`,
#: `optimization_constant "6a"`, `question`) and `expose`: none exists under Mathlib alone, and
#: none changes a definition's meaning, so each goes from its list and an emptied list goes whole.
_REGISTRY_ATTRIBUTE_RE = re.compile(
    r"(?:expose|category\b[^,\]]*|AMS\b[^,\]]*|optimization_constant\b[^,\]]*|question\b[^,\]]*)"
)
_ATTRIBUTE_LIST_RE = re.compile(r"@\[([^\]]*)\]([ \t]*)")
PORT_NOTE = (
    "/-! Ported mechanically from `{rel}` at registry commit {pin} ({repo}, Apache-2.0) by "
    "gate/tools/wave.py (F14-T19): {what}. The module syntax is stripped so the gate elaborates it "
    "under `import Mathlib`; nothing else is changed. -/\n"
)


class PortError(Exception):
    """A registry file the driver cannot port mechanically, and why."""


def _strip_attributes(m: re.Match[str]) -> str:
    kept = [
        a.strip()
        for a in m.group(1).split(",")
        if a.strip() and not _REGISTRY_ATTRIBUTE_RE.fullmatch(a.strip())
    ]
    return f"@[{', '.join(kept)}]{m.group(2)}" if kept else ""


def _strip_module_syntax(line: str) -> str:
    line = _ATTRIBUTE_LIST_RE.sub(
        _strip_attributes, line
    )  # before the modifiers: `@[expose] public`
    return _MODIFIER_PREFIX_RE.sub("", line)


def _is_conjecture(prefix: list[str], block: list[str]) -> bool:
    """A problem file's theorem is one of its stated conjectures or their tests — a `category`
    attribute, or a `sorry` body — and not a proved lemma of its own."""
    text = "\n".join(block)
    return any("@[category" in p or "category " in p for p in prefix) or bool(
        re.search(r"\bsorry\b", text)
    )


def port_body(  # noqa: PLR0912, PLR0915 — one branch per line kind
    text: str, *, keep_theorems: bool = False
) -> tuple[str, list[str]]:
    """The mechanical port of a registry file: its definitions, instances, `variable`s and scope
    lines as written; every theorem, lemma and example gone with its docstring, its attributes and
    an `open ... in` prefix (a problem file's are the stated conjectures and their tests; a library
    module's are its proved lemmas and stay, ``keep_theorems``); every `#` command gone; the
    module syntax stripped, the exposed public section kept as a plain section.
    Returns the body (without the copyright header, which the caller writes) and the modules the
    file imported, in order."""
    header = intake.copyright_header(text)
    if header is not None and text.startswith(header):
        text = text[len(header) :]
    imports: list[str] = []
    out: list[str] = []
    pending: list[str] = []  # docstring, attribute, `open ... in` and blank lines awaiting a decl
    raw_pending: list[str] = []  # the same lines as the registry wrote them (`@[category …]`)
    lines = text.splitlines()
    i = 0

    def block_end(start: int) -> int:
        """The index after a declaration: its continuation lines are indented or blank."""
        j = start + 1
        while j < len(lines) and (not lines[j].strip() or lines[j][0] in " \t"):
            j += 1
        return j

    while i < len(lines):
        line = _MODIFIER_PREFIX_RE.sub("", lines[i])  # `public meta import`, `meta section`
        stripped = line.strip()
        if stripped == "module" or _LINTER_OPTION_RE.match(line):
            # A linter option the registry defines (`linter.style.formal_proof_palomar`) does not
            # exist under Mathlib alone and changes no meaning; with its `in`, it goes.
            i += 1
            continue
        m = _IMPORT_RE.match(line)
        if m is not None:
            imports.append(m.group("module"))
            i += 1
            continue
        section = _PUBLIC_SECTION_RE.match(line)
        if section is not None:
            out.extend(pending)
            pending.clear()
            raw_pending.clear()
            out.append(section.group("kind"))
            i += 1
            continue
        if _HASH_COMMAND_RE.match(line):
            # `#guard_msgs in`, `#eval`, `#check`: the registry's own tests, declaring nothing;
            # a `#guard_msgs` docstring is the pretty-printer's text and changes with it.
            pending.clear()
            raw_pending.clear()
            i = block_end(i)
            continue
        if line.startswith("/--") or line.startswith("@[") or _IN_PREFIX_RE.match(line):
            # A docstring or attribute may span lines; with an `open … in` or `set_option … in`
            # prefix it belongs to the declaration that follows.
            j = i
            if line.startswith("/--"):
                while j < len(lines) and "-/" not in lines[j]:
                    j += 1
            elif line.startswith("@["):
                while j < len(lines) and lines[j].count("[") > lines[j].count("]"):
                    j += 1
                while j < len(lines) and "]" not in lines[j]:
                    j += 1
            tail = _strip_module_syntax(lines[j])
            inline = re.sub(r"^@\[[^\]]*\]\s*", "", tail)  # `@[simp] instance … := …` on one line
            if _PROOF_DECL_RE.match(inline) and not keep_theorems:
                end = block_end(j)
                if _is_conjecture([*raw_pending, *lines[i:j]], lines[j:end]):
                    pending.clear()
                    raw_pending.clear()
                    i = end
                    continue
            if _ANY_DECL_RE.match(inline):
                end = block_end(j)
                out.extend(pending)
                pending.clear()
                out.extend(_strip_module_syntax(ln) for ln in lines[i:j])
                out.append(tail)
                out.extend(_strip_module_syntax(ln) for ln in lines[j + 1 : end])
                i = end
                continue
            pending.extend(_strip_module_syntax(ln) for ln in lines[i : j + 1])
            raw_pending.extend(lines[i : j + 1])
            i = j + 1
            continue
        if not stripped:
            (pending if pending else out).append(line)
            if pending:
                raw_pending.append(line)
            i += 1
            continue
        if _PROOF_DECL_RE.match(line) and not keep_theorems:
            # A problem file's theorems are its conjectures and their tests, dropped; a proved
            # lemma of its own that a definition cites (`exists_p`, erdos-1055) stays (T25).
            end = block_end(i)
            if _is_conjecture(raw_pending, lines[i:end]):
                pending.clear()
                raw_pending.clear()
                i = end
                continue
            out.extend(pending)
            pending.clear()
            raw_pending.clear()
            out.extend(_strip_module_syntax(ln) for ln in lines[i:end])
            i = end
            continue
        if _ANY_DECL_RE.match(line):
            end = block_end(i)
            out.extend(pending)
            pending.clear()
            raw_pending.clear()
            out.extend(_strip_module_syntax(ln) for ln in lines[i:end])
            i = end
            continue
        # A scope or other command line (`open`, `namespace`, `end`, `variable`, `section`,
        # `set_option`, `universe`, `attribute`, a module doc `/-! ... -/`, a comment).
        if line.startswith("/-"):
            j = i
            while j < len(lines) and "-/" not in lines[j]:
                j += 1
            out.extend(pending)
            pending.clear()
            raw_pending.clear()
            out.extend(lines[i : j + 1])
            i = j + 1
            continue
        out.extend(pending)
        pending.clear()
        raw_pending.clear()
        # A `local notation` is the file's; in its own module it would reach nothing, so the port
        # makes it plain (the statement and its proofs import the module).
        out.append(
            re.sub(r"^local\s+(notation|infix|prefix|postfix)", r"\1", _strip_module_syntax(line))
        )
        i += 1
    out.extend(p for p in pending if not p.strip())  # trailing blanks only: a docstring with no
    # declaration left to document is dropped
    body = "\n".join(out).strip("\n") + "\n"
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body, imports


def _port_imports(
    imports: list[str], fc: Path, out_defs: dict[str, str], catalog: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Resolve a ported file's imports: Mathlib and the registry's util hub collapse into
    `import Mathlib`; another library module the gate's toolchain carries (`Batteries.*`, the
    layout's library prefixes) is kept as written; a helper-library module is ported too and
    imported as `Defs.<stem>`; anything else is a refusal. Returns the `Defs.*` stems and the
    library modules this file imports."""
    stems: list[str] = []
    kept: list[str] = []
    for module in imports:
        if (
            module == "Mathlib"
            or module.startswith("Mathlib.")
            or module == "FormalConjecturesUtil"
        ):
            continue
        if module.startswith(HELPER_LIBRARY + "."):
            stems.append(port_library_module(fc, module, out_defs, catalog))
            continue
        if layout.module_origin(module)[0] == "library":
            kept.append(module)
            continue
        msg = f"imports {module}, which the port cannot supply"
        raise PortError(msg)
    return stems, kept


def library_stem(module: str) -> str:
    """`FormalConjecturesForMathlib.Combinatorics.SimpleGraph.Clique` becomes
    `CombinatoricsSimpleGraphClique`:
    a `Defs.*` name unique within the library (its file stems repeat: ten `Basic.lean`s)."""
    return "".join(module.split(".")[1:])


def _port_file(  # noqa: PLR0913, PLR0917 — one input per fact about the file
    rel: str,
    text: str,
    fc: Path,
    out_defs: dict[str, str],
    catalog: dict[str, Any],
    what: str,
    *,
    keep_theorems: bool,
) -> tuple[str, list[str]]:
    header = intake.copyright_header(text)
    if header is None:
        msg = f"{rel} carries no copyright header to keep"
        raise PortError(msg)
    body, imports = port_body(text, keep_theorems=keep_theorems)
    stems, kept = _port_imports(imports, fc, out_defs, catalog)
    note = PORT_NOTE.format(rel=rel, pin=catalog["fc_commit"], repo=FC_REPO, what=what)
    ported = (
        f"{header}\n\nimport Mathlib\n"
        + "".join(f"import {m}\n" for m in kept)
        + "".join(f"import Defs.{s}\n" for s in sorted(set(stems)))
        + f"\n{note}\n{body}"
    )
    return ported, stems


def port_library_module(
    fc: Path, module: str, out_defs: dict[str, str], catalog: dict[str, Any]
) -> str:
    """Port one helper-library module (and, recursively, the library modules it imports) into
    ``out_defs`` (stem → file text); returns its stem."""
    stem = library_stem(module)
    if stem in out_defs:
        return stem
    rel = module.replace(".", "/") + ".lean"
    path = fc / rel
    if not path.is_file():
        msg = f"{rel} is not in the checkout"
        raise PortError(msg)
    out_defs[stem] = ""  # claim the name first: the library's import graph may have cycles
    text, _stems = _port_file(
        rel,
        path.read_text(encoding="utf-8"),
        fc,
        out_defs,
        catalog,
        f"the module `{module}`, lemmas included",
        keep_theorems=True,
    )
    out_defs[stem] = text
    return stem


def port_local(  # noqa: PLR0913, PLR0917 — one input per fact about the file
    rel: str,
    text: str,
    fc: Path,
    out_defs: dict[str, str],
    catalog: dict[str, Any],
    extra: list[str],
) -> None:
    """Port the registry file's own definitions as ``Local.lean``, importing the helper modules
    it or the statement uses (``extra``: stems already ported for the statement)."""
    out_defs[LOCAL_STEM] = ""
    ported, stems = _port_file(
        rel,
        text,
        fc,
        out_defs,
        catalog,
        "the file's own definitions, without the conjectures it states and their tests",
        keep_theorems=False,
    )
    missing = sorted(set(extra) - set(stems))
    if missing:
        head, sep, tail = ported.partition("\n/-! Ported mechanically")
        ported = head + "".join(f"import Defs.{s}\n" for s in missing) + sep + tail
    out_defs[LOCAL_STEM] = ported


LOCAL_STEM = "Local"


_VARIABLE_RE = re.compile(r"^variable\s+(?P<groups>.+?)\s*$")
_GROUP_SPLIT_RE = re.compile(r"[({\[⦃][^(){}\[\]⦃⦄]*[)}\]⦄]")


def _theorem_line(text: str, decl: str) -> int:
    """The line index where the registry states ``decl``, or -1."""
    short = decl.rsplit(".", 1)[-1]
    for i, line in enumerate(text.splitlines()):
        if re.match(rf"^theorem\s+(?:{re.escape(decl)}|{re.escape(short)})(?![\w.'])", line):
            return i
    return -1


def section_variables(text: str, decl: str) -> list[str]:
    """The binder groups of every `variable` line in scope where the registry states ``decl``, in
    the file's order (a `section`'s or `namespace`'s variables end with it)."""
    stop = _theorem_line(text, decl)
    if stop < 0:
        return []
    stack: list[list[str]] = [[]]
    for line in text.splitlines()[:stop]:
        scope = _NAMESPACE_RE.match(line)
        if scope is not None:
            if scope.group("kind") in ("namespace", "section"):
                stack.append([])
            elif len(stack) > 1:
                stack.pop()
            continue
        m = _VARIABLE_RE.match(line)
        if m is not None:
            stack[-1].extend(g.strip() for g in _GROUP_SPLIT_RE.findall(m.group("groups")))
    return [g for frame in stack for g in frame]


def used_variables(groups: list[str], statement_text: str) -> str:
    """The section variables a statement uses, as binders before its colon: a named group whose
    name occurs in the statement, and an instance group over a name so chosen (F14-T23: the
    registry states `minDegree` over `variable {alpha : Type*} [Fintype alpha]`, and a draft
    that drops the instance does not elaborate; an unused variable would be an unused binder,
    F02)."""
    tokens = set(_TOKEN_RE.findall(statement_text))
    chosen: list[str] = []
    names: set[str] = set()
    for group in groups:
        inner = group[1:-1]
        if group.startswith("["):
            if any(n in names for n in _TOKEN_RE.findall(inner)):
                chosen.append(group)
            continue
        head = inner.split(":", 1)[0]
        bound = [n for n in head.split() if _TOKEN_RE.fullmatch(n)]
        if any(n in tokens for n in bound):
            chosen.append(group)
            names.update(bound)
    return " ".join(chosen)


def enclosing_namespaces(text: str, decl: str) -> list[str]:
    """The `namespace` lines open where the registry states ``decl`` (the statement is lifted out
    of them, so the draft opens each)."""
    names: list[str] = []
    stack: list[tuple[str, str]] = []
    for line in text.splitlines():
        if re.match(rf"^theorem\s+{re.escape(decl)}(?![\w.'])", line) or re.match(
            rf"^theorem\s+{re.escape(decl.rsplit('.', 1)[-1])}(?![\w.'])", line
        ):
            names = [n for k, n in stack if k == "namespace" and n]
            break
        scope = _NAMESPACE_RE.match(line)
        if scope is None:
            continue
        kind, name = scope.group("kind"), scope.group("name")
        if kind in ("namespace", "section"):
            stack.append((kind, name))
        elif stack:
            stack.pop()
    return names


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


def declared_namespaces(text: str) -> list[str]:
    """The `namespace X` lines of a file, in order."""
    out = []
    for line in text.splitlines():
        m = _NAMESPACE_RE.match(line)
        if m is not None and m.group("kind") == "namespace" and m.group("name"):
            out.append(m.group("name"))
    return out


@functools.lru_cache(maxsize=4)
def registry_namespaces(fc: Path) -> frozenset[str]:
    """Every namespace a registry problem file declares (`Erdos507`, `Green77`, …)."""
    out: set[str] = set()
    for path in (fc / "FormalConjectures").rglob("*.lean"):
        for m in declared_namespaces(path.read_text(encoding="utf-8")):
            out.add(m)
            out.add(m.split(".")[0])
    return frozenset(out)


def opened_namespaces(text: str) -> set[str]:
    """The namespaces a file's `open` lines name (`open Filter Topology`, `open scoped X in`,
    `open Nat (factorial)`): where a bare helper name in the file's own definitions can resolve."""
    out: set[str] = set()
    for line in _OPEN_RE.findall(text):
        words = re.sub(r"\(.*?\)", " ", line).split()
        out.update(w for w in words[1:] if w not in ("scoped", "in", "hiding", "renaming"))
    return out


def helpers_used_in_body(
    body: str,
    index: dict[str, set[str]],
    opened: set[str],
    lemmas: dict[str, set[str]] | None = None,
) -> list[str]:
    """The helper definitions a file's own definitions use (F14-T21): a name counts when the library
    declares it at the root or under a namespace the file opens, or when the body writes it with
    its namespace (`MilnorK.of`). The bare-name rule of `helpers_used` is the statement's, where a
    bare `S` is a use; in a body of definitions `S` and `of` are everyone's own names, and the
    pilot's erdos-509 ported four unrelated modules on them."""
    used: set[str] = set()
    for name, spaces in [*index.items(), *(lemmas or {}).items()]:
        if not re.search(rf"(?<![\w']){re.escape(name)}(?![\w'])", body):
            continue
        dotted_on_a_value = re.search(rf"[\w')\]]\.{re.escape(name)}(?![\w'])", body)
        if any(
            s == ""
            or s in opened
            or f"{s}.{name}" in body
            or (s and dotted_on_a_value)  # `n.Composite`: the library's `Nat.Composite` (T25)
            for s in spaces
        ):
            used.add(name)
    return sorted(used)


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
        # A dotted use (`M.IsSynchronizing`, `S.IsAPOfLength`) is the library's whenever it declares
        # the name under some namespace: `DFA` was not on the list of Mathlib namespaces the library
        # extends, and nine of run 2's statements did not elaborate (F14-T25). A theorem is never
        # in this index, so `A.card` stays Mathlib's.
        if not dotted or any(s for s in spaces):
            used.add(name)
    return sorted(used)


_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₖₗₘₙₚₛₜ", "0123456789aeoxklmnpst")


def target_id_for(row: dict[str, Any]) -> str:
    """The target id: `erdos-<n>`, or the declaration's short name in kebab case; a subscript in
    the registry's name (`moment_is_equiv₃`) becomes the plain letter the id grammar allows
    (F14-T19). A row the catalog-wide assignment has named carries its id (F14-T32)."""
    if row.get("target_id"):
        return str(row["target_id"])
    if row["kind"] == "erdos":
        return f"erdos-{row['key'].split(':', 1)[1]}"
    decl = str(row["decl"]).rsplit(".", 1)[-1].translate(_SUBSCRIPTS)
    kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", decl).replace("_", "-").lower()
    short = re.sub(r"-{2,}", "-", kebab).strip("-")  # `_M5` → `--m5` on the live record (T25)
    # F14-T32: only an id the grammar refuses is respelled, so no id that could be live moves:
    # a Greek letter by its name (`reed_conjecture_δ_6_ω_2`), anything else outside it dropped
    # (`«167»`).
    short = short if _ID_RE.fullmatch(short) else _kebab(_ascii(decl))
    if len(short) <= NODE_ID_MAX:
        return short
    digest = hashlib.sha256(str(row["key"]).encode()).hexdigest()[:8]
    return f"{short[: NODE_ID_MAX - 9].rstrip('-')}-{digest}"  # no id that long can be live


class WaveError(Exception):
    """A catalog the driver cannot name targets for without guessing."""


HOLDERS = ROOT / "docs" / "lean_conjecture_holders.json"


def load_holders(path: Path = HOLDERS) -> dict[str, str]:
    """The live ids the rule does not compute for their rows, each with the row it holds."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in doc.items() if not k.startswith("_")}


def assign_ids(
    rows: list[dict[str, Any]], *, live: set[str], holders: dict[str, str]
) -> dict[str, str]:
    """Each draftable row's target id, by key (F14-T32).

    A short id one row alone claims is the row's. Where several rows claim one, the row
    ``holders`` names keeps it and every other row is named by its registry file and full
    declaration (``qualified_id``). A row ``holders`` names under another id keeps that id: a
    live id the rule no longer computes (T25 collapsed ``--`` after ``buchi-problem--m5``
    landed, and the row was imported again as ``buchi-problem-m5``). A live id several rows
    claim with no holder named, or a holder that is not among the claimants, is refused: a
    wrong guess drafts the live statement again under a second id."""
    claimants: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if draftable_id(r):
            claimants.setdefault(target_id_for(r), []).append(r)
    held = {key: target_id for target_id, key in holders.items()}
    out: dict[str, str] = {}
    for short, group in claimants.items():
        if len(group) == 1:  # a held row keeps its live id, whatever the rule now computes
            out[group[0]["key"]] = held.get(group[0]["key"], short)
            continue
        holder = holders.get(short)
        if holder is None and short in live:
            msg = (
                f"target id {short!r} is live and {len(group)} catalog rows claim it; name its "
                f"holder in {HOLDERS.name} (the row whose declaration the live statement is)"
            )
            raise WaveError(msg)
        if holder is not None and holder not in {r["key"] for r in group}:
            msg = f"the holder {holder!r} named for {short!r} is not one of the rows that claim it"
            raise WaveError(msg)
        for r in group:
            out[r["key"]] = short if r["key"] == holder else held.get(r["key"]) or qualified_id(r)
    named: dict[str, str] = {}
    for key, target_id in out.items():
        if target_id in named:
            msg = f"{key} and {named[target_id]} would both be target {target_id!r}"
            raise WaveError(msg)
        named[target_id] = key
    return out


_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def _ascii(text: str) -> str:
    """Greek letters by their names, separated; every other character outside ASCII dropped."""
    out = []
    for ch in text:
        if ch.isascii():
            out.append(ch)
            continue
        name = unicodedata.name(ch, "")
        if name.startswith("GREEK"):
            out.append(f"_{name.rsplit(' ', 1)[-1].lower()}_")
    return "".join(out)


def _kebab(text: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", text.translate(_SUBSCRIPTS))
    return re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9]+", "-", text)).strip("-").lower()


def qualified_id(row: dict[str, Any]) -> str:
    """A shared short id's other claimants: the registry file (less ``FormalConjectures/`` and
    ``.lean``) and the full declaration, in kebab case."""
    path = str(row["file"]).removeprefix("FormalConjectures/").removesuffix(".lean")
    full = _kebab(f"{path}-{row['decl']}")
    if len(full) <= NODE_ID_MAX:
        return full
    # A target id is its root node's id, at most 64 characters: the file's stem then, and past
    # that a cut with a hash of the row's key so two long rows cannot meet (F14-T32).
    short = _kebab(f"{Path(path).name}-{row['decl']}")
    if len(short) <= NODE_ID_MAX:
        return short
    digest = hashlib.sha256(str(row["key"]).encode()).hexdigest()[:8]
    return f"{short[: NODE_ID_MAX - 9].rstrip('-')}-{digest}"


#: A node id's length limit (``layout``'s id grammar), which a target's root id meets.
NODE_ID_MAX = 64


def draftable_id(r: dict[str, Any]) -> bool:
    return r["kind"] == "erdos" or bool(r.get("decl"))


def theorem_name(row: dict[str, Any]) -> str:
    if row["kind"] == "erdos":
        return f"Opn.erdos_{row['key'].split(':', 1)[1]}"
    return "Opn." + re.sub(r"[^A-Za-z0-9_]", "_", str(row["decl"]).rsplit(".", 1)[-1])


BINDERS_BEFORE_COLON = (
    "binders before the colon carry a hypothesis (or cannot be closed): the witness is not their "
    "closure over `True`, write it by hand"
)


def extract(text: str, decl: str) -> tuple[str | None, str, str]:  # noqa: PLR0911 — one per refusal
    """The main statement's proposition, how it was taken (``as stated`` / ``adapted``) and the
    binders before its colon (empty for none), or ``None`` and why it cannot be taken as it
    stands. Binders before the colon are kept as the registry writes them: the draft is refused
    unless the curator supplies the witness by hand (F14-T18)."""
    # The catalog names a declaration as the file writes it (``erdos_1065.parts.i``), so the full
    # name is the one to find; the short name is only the fallback for a namespaced file.
    m = None
    for name in dict.fromkeys((decl, decl.rsplit(".", 1)[-1])):
        found = list(
            re.finditer(
                rf"^theorem\s+{re.escape(name)}(?![\w.'])(?P<rest>[\s\S]*?):=\s*(?:by\s+)?sorry",
                text,
                re.M,
            )
        )
        # F14-T32: the short name is the fallback for a namespaced file, and only when one
        # theorem has it; two (`riemannZeta.distinct_prop_lt`, `DirichletCharacter.…`) would
        # take the first for both rows and import one statement twice under two names.
        if len(found) > 1:
            return None, f"{len(found)} theorems named `{name}` in the file: curate by hand", ""
        if found:
            m = found[0]
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


_NOTATION_RE = re.compile(
    r"^\s*(?:local\s+|scoped(?:\[\w+\])?\s+)?(?:notation3?|infixl?|infixr|prefix|postfix)"
    r'(?::\d+)?\s*(?:\(.*?\)\s*)?"([^"]+)"',
    re.M,
)
_GROUP_RE = re.compile(r"\(([^()]*)\)")


def leading_binders(prop: str) -> tuple[str, int] | None:  # noqa: PLR0911 — one exit per shape
    """The leading ``∀`` binders as one ``∃`` binder list and the number of names they bind, or
    ``None`` when the driver cannot close them: none at all, an implicit, strict-implicit or
    instance binder, an untyped name, or a binder the hypotheses rule owns. Each group is
    parenthesised (``∀ n m : Nat`` becomes ``(n m : Nat)``) so several ``∀``s chain into one ``∃``.
    """
    body = prop.strip()
    groups: list[str] = []
    names = 0
    seen: set[str] = set()
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
            head, colon, typ = part.partition(":")
            bound = head.split()
            if not colon or not bound or any(not _TOKEN_RE.fullmatch(n) for n in bound):
                return None
            if _type_is_hypothesis(bound, typ, seen):
                return None
            seen.update(bound)
            groups.append(f"({part.strip()})")
            names += len(bound)
        body = rest[comma + 1 :].strip()
    if not groups or _top_level(body, "→") >= 0:
        return None
    return " ".join(groups), names


_HYPOTHESIS_NAME_RE = re.compile(r"^h(?:[A-Z0-9_'].*|[a-z]{0,2})$")


def _type_is_hypothesis(bound: list[str], typ: str, earlier: set[str]) -> bool:
    """Whether a binder ``(bound : typ)`` states a hypothesis rather than binding data (F14-T19:
    `default` inhabits no proposition). Read off the text: a relation or connective in the type,
    a predicate applied to an earlier binder (`n.Prime`, `A.Infinite`), or a name written as a
    hypothesis is (`h`, `hn`, `hA`, `h1`). A function type (naturals to reals) is data."""
    typ = typ.strip()
    if _RELATION_RE.search(typ) or re.search(
        "[=\u2227\u2228\u00ac\u2194\u2203\u2200\u2223]|\\bIs[A-Z]", typ
    ):
        return True
    if any(re.search(rf"(?<![\w.']){re.escape(n)}\.[A-Z]", typ) for n in earlier):
        return True
    return any(_HYPOTHESIS_NAME_RE.match(n) for n in bound)


def closed_prop(prop: str, binders: str) -> str:
    """The proposition with the theorem's binders before the colon as leading ``∀``s: the same
    binders to step 7, which closes every leading one (F14-T19)."""
    return f"∀ {binders}, {prop}" if binders else prop


def witness_for(prop: str, binders: str = "") -> str:
    """``Witness.lean`` for a proposition the driver drafts: ``True`` when nothing is bound,
    the closure over ``True`` when leading binders (before or after the colon) bind data
    (``leading_binders``)."""
    closed = leading_binders(closed_prop(prop, binders))
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


HYPOTHESES_REFUSAL = (
    "leading ∀ binders carry hypotheses (a bounded binder or an implication): the "
    "witness is not `True`, write it by hand"
)
UNCLOSEABLE_REFUSAL = (
    "leading ∀ binders the driver cannot close (implicit, instance or untyped): the "
    "witness is their closure over `True`, write it by hand"
)
#: The refusals a hand witness lifts: a row refused for these alone still has a statement the
#: driver can write for the witness's author (F14-T21, `--write-refused`).
WITNESS_REFUSALS = frozenset({HYPOTHESES_REFUSAL, UNCLOSEABLE_REFUSAL, BINDERS_BEFORE_COLON})


def witness_refusal(prop: str) -> str | None:
    """Why the driver cannot write the proposition's witness, or ``None``. A curator's hand
    `Witness.lean` lifts this refusal (F14-T18)."""
    if leading_hypotheses(prop):
        return HYPOTHESES_REFUSAL
    if _LEADING_FORALL_RE.match(prop.strip()) and leading_binders(prop) is None:
        return UNCLOSEABLE_REFUSAL
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
    write_refused: bool = False,
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
    # The section's `variable`s the statement uses come first among its binders (F14-T23).
    section = used_variables(section_variables(text, str(row["decl"])), f"{binders} {prop}")
    if section:
        binders = f"{section} {binders}".strip()
    shape = parse_refusal(prop)
    if shape is not None:
        draft.reasons.append(shape)
    if "type_of%" in prop:
        # erdos-1135 (run 2): `type_of% CollatzConjecture.collatz_conjecture` is another statement.
        draft.reasons.append(
            "the statement is another statement's type (`type_of%`): curate by hand"
        )
    here = set(declared_namespaces(text))
    foreign = sorted(
        ns for ns in opened_namespaces(text) if ns in registry_namespaces(fc) and ns not in here
    )
    if foreign:
        # green-77 (run 2): `open Erdos507` names a namespace another registry file declares, which
        # the file imports; the statement's meaning reaches across files.
        draft.reasons.append(
            f"opens another registry file's namespace ({', '.join(foreign)}): a cross-file "
            "statement, curate by hand"
        )
    # The witness: the driver's where it can write one (binders before the colon are leading
    # binders to step 7, F14-T19), the curator's hand file otherwise (F14-T18); without either
    # the row is refused by the reason the driver cannot.
    witness = witness_refusal(prop)
    if witness is None and binders and leading_binders(closed_prop(prop, binders)) is None:
        witness = BINDERS_BEFORE_COLON
    if witness is not None and hand.witness is None:
        draft.reasons.append(witness)
    # Names the statement takes from its file or the helper library: a port under defs/ (R12).
    # The curator's hand port wins; otherwise the driver ports mechanically (F14-T19).
    # The names the statement uses are in its binders before the colon as much as after it
    # (crystals-components-unique on the pilot: the local definition sat in a hypothesis binder).
    whole = closed_prop(prop, binders)
    tokens = set(_TOKEN_RE.findall(whole))
    # A file-local notation the statement uses (`local notation "R" => …`, `"F(" s ", " n ")"`) is
    # ported into Local.lean as a plain notation (F14-T23; T11 refused it, T19 ported names only).
    notations = sorted(n for n in _NOTATION_RE.findall(text) if n in whole)
    # The file's own definitions the statement uses: the catalog's list, and the file's own
    # declarations read here (the catalog missed `IsGoormaghtighNumber` on the witness pass).
    declared = {m.group("name").rsplit(".", 1)[-1] for m in _DEFINITION_RE.finditer(text)}
    local = sorted(
        {n for n in row.get("local_defs") or [] if n.rsplit(".", 1)[-1] in tokens}
        | {n for n in declared if n in tokens}
        | set(notations)
    )
    locals_short = {n.rsplit(".", 1)[-1] for n in row.get("local_defs") or []}
    used = [n for n in helpers_used(whole, helpers) if n not in locals_short]
    ports: dict[str, str] = {}
    opens_namespaces: list[str] = []
    lib_notations = helper_notations(fc)
    literals = notations_used(whole, lib_notations)
    if (local or used or literals) and not hand.defs:  # local: names and notations
        modules = helper_modules(fc)
        try:
            body = ""
            if local:
                # The file's own definitions may use the library too: port what they use.
                body, _imports = port_body(text)
                in_body = helpers_used_in_body(
                    body, helpers, opened_namespaces(text), helper_lemmas(fc)
                )
                used = sorted(set(used) | {n for n in in_body if n not in locals_short})
                literals = sorted(set(literals) | set(notations_used(body, lib_notations)))
            wanted = [m for name in used for m in sorted(modules.get(name, ()))] + [
                m for lit in literals for m in sorted(lib_notations[lit])
            ]
            for module in dict.fromkeys(wanted):
                port_library_module(fc, module, ports, catalog)
            if local:
                resting = sorted(
                    n
                    for n in row.get("local_defs") or []
                    if re.search(
                        rf"(?:def|abbrev)\s+(?:[\w.']*\.)?{re.escape(n.rsplit('.', 1)[-1])}\b"
                        r"[^\n]*:=\s*(?:by\s+)?"
                        r"(?:answer\(sorry\)|sorry)\s*$",
                        body,
                        re.M,
                    )
                )
                if resting or re.search(r"\bsorry\b", body):
                    draft.reasons.append(
                        "the file's definitions rest on `sorry` (an answer the registry leaves "
                        "open): " + (", ".join(resting) or "see the file")
                    )
                else:
                    port_local(row["file"], text, fc, ports, catalog, sorted(ports))
                    opens_namespaces = enclosing_namespaces(text, str(row["decl"]))
        except PortError as exc:
            draft.reasons.append(f"cannot port its definitions mechanically: {exc}")
    domains = {DOMAINS.get(a) for a in row.get("ams") or []}
    if not (domains - {None}):
        draft.reasons.append(f"no graph domain for AMS {', '.join(row.get('ams') or []) or 'none'}")
    # A row refused for its witness alone still has a statement worth writing, for the person or
    # agent who writes the witness (F14-T21): under refused/, with no Witness.lean.
    for_witness = bool(draft.reasons) and all(r in WITNESS_REFUSALS for r in draft.reasons)
    if draft.reasons and not (write_refused and for_witness):
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
    # An `open … in` prefix on the theorem is the theorem's: opened plainly here, never with the
    # `in`, which would swallow the statement's next line (erdos-883 on the pilot, F14-T21).
    opens = "\n".join(
        [
            *(re.sub(r"\s+in$", "", o) for o in _OPEN_RE.findall(text)),
            *(f"open {ns}" for ns in opens_namespaces),
        ]
    )
    note = (
        "the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its "
        "affirmative reading (F11-Q24)"
        if how == "adapted"
        else "stated as the registry states it"
    )
    stems = [p.stem for p in hand.defs] if hand.defs else sorted(ports)
    if hand.defs:
        note += "; the names it takes from the registry's library are ported under defs/ (R12)"
    elif ports:
        note += (
            "; the names it takes from its file or the registry's library are ported "
            "mechanically under defs/ (R12, F14-T19)"
        )
    imports = "import Mathlib\n" + "".join(f"import Defs.{s}\n" for s in stems)
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
    directory = (out / "refused" / draft.target_id) if draft.reasons else (out / draft.target_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "record.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "Statement.lean").write_text(statement, encoding="utf-8")
    if draft.reasons:
        pass  # the witness is what is missing: nothing stands in for it
    elif hand.witness is not None:
        shutil.copyfile(hand.witness, directory / "Witness.lean")
    else:
        (directory / "Witness.lean").write_text(witness_for(prop, binders), encoding="utf-8")
    if hand.defs:
        (directory / "defs").mkdir(exist_ok=True)
        for port in hand.defs:
            shutil.copyfile(port, directory / "defs" / port.name)
        draft.defs = tuple(p.stem for p in hand.defs)
    elif ports:
        (directory / "defs").mkdir(exist_ok=True)
        for stem, ported in ports.items():
            (directory / "defs" / f"{stem}.lean").write_text(ported, encoding="utf-8")
        draft.defs = draft.ports = tuple(sorted(ports))
    if hand.hazards is not None:
        shutil.copyfile(hand.hazards, directory / "hazards.yaml")
        draft.hazards = True
    upstream = out / "upstream" / row["file"]
    upstream.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, upstream)
    # The manifest the admission runner reads (F14-T20): one source for a draft's inputs.
    (directory / "draft.json").write_text(
        json.dumps(
            {
                "key": draft.key,
                "target_id": draft.target_id,
                "file": row["file"],
                "defs": list(draft.defs),
                "hazards": draft.hazards,
                **({"refused": list(draft.reasons)} if draft.reasons else {}),
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    if draft.reasons:
        draft.refused_dir = directory
        return draft
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
        *[f"- `{d.key}` → `{d.target_id}/`{d.notes}" for d in done],
        "",
        "## Refused (a later wave, or a port by hand; F14-Q11)",
        "",
        *[
            f"- `{d.key}`: {'; '.join(d.reasons)}"
            + (" (statement written under refused/ for a hand witness)" if d.refused_dir else "")
            for d in held
        ],
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
    parser.add_argument(
        "--write-refused",
        action="store_true",
        help="write the statement and record of a row refused for its witness alone under "
        "<out>/refused/<target-id>/, for the hand witness (F14-T21)",
    )
    parser.add_argument(
        "--live-index",
        type=Path,
        help="the graph's targets/index.json: a live id several rows claim needs a named holder "
        "(F14-T32)",
    )
    args = parser.parse_args(argv)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    holders = load_holders()
    live = set(holders)
    if args.live_index is not None:
        index = json.loads(args.live_index.read_text(encoding="utf-8"))
        live |= {str(t["target_id"]) for t in index["targets"]}
    # F14-T32: ids are assigned over the whole catalog, so a row's id does not depend on which
    # rows this run drafts; each row carries its own into the draft.
    try:
        assigned = assign_ids(catalog["rows"], live=live, holders=holders)
    except WaveError as exc:
        sys.stderr.write(f"wave: {exc}\n")
        return 1
    for r in catalog["rows"]:
        if r["key"] in assigned:
            r["target_id"] = assigned[r["key"]]
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
        draft_row(
            r, catalog, args.fc, out, helpers, args.curator, args.overrides, args.write_refused
        )
        for r in chosen
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
