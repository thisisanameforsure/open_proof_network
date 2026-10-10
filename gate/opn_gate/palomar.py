"""Palomar's documents as the network reads and writes them (F25-T6, T7; D-10 v3.37).

This module is pure: it reads and writes the registry's ``formalization.yaml`` (v0.4, the
schema vendored under ``gate/palomar/``), its ``comparator.json``, its entry records and the
network's pins of the registry's moving parts, and it measures a Challenge against the caps.
Nothing here talks to a host (``palomar_host``), runs Lean (``palomar_check``) or shells out
(``palomar_port``). The export (T7) builds on these readers and writers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

PALOMAR_DIR = Path(__file__).resolve().parents[1] / "palomar"
FORMALIZATION_SCHEMA_FILE = PALOMAR_DIR / "formalization.schema.v0.4.json"
ENTRY_SCHEMA_FILE = PALOMAR_DIR / "entry.schema.json"
PINS_FILE = PALOMAR_DIR / "PINS.json"
CORPUS_FILE = PALOMAR_DIR / "corpus.json"
TOOLCHAINS_FILE = PALOMAR_DIR / "toolchains.json"
LICENCE_FILE = PALOMAR_DIR / "LICENSE.apache-2.0"
FORMALIZATION_VERSION = "v0.4"
#: The order the network writes a formalization.yaml's sections in; sections the schema does
#: not name (a registered entry carries ``verification`` or ``limitations``) follow, as read.
SECTION_ORDER: tuple[str, ...] = (
    "version",
    "project",
    "repository",
    "classification",
    "sources",
    "related_formalizations",
    "status",
    "automation",
    "fidelity",
    "review",
    "alignment",
    "acknowledgements",
)
#: Palomar's method vocabulary (formalization.yaml v0.4), which D-23 v3.37 adopted verbatim.
METHODS: tuple[str, ...] = ("manual", "copilot", "agent", "autonomous", "other")


class PalomarDocumentError(Exception):
    """A document the registry would refuse, with every violation listed."""


# --- the vendored policy ---------------------------------------------------------------------


def pins() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    return doc


def corpus() -> list[dict[str, Any]]:
    doc = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = doc["entries"]
    return entries


def toolchain_minimum() -> str:
    doc = json.loads(TOOLCHAINS_FILE.read_text(encoding="utf-8"))
    return str(doc["minimum"])


def licence_text() -> str:
    return LICENCE_FILE.read_text(encoding="utf-8")


def _validator(schema_file: Path) -> jsonschema.Draft202012Validator:
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def violations(doc: object, schema_file: Path) -> list[str]:
    """Every violation of ``doc`` against the vendored schema, as ``$.path: message``."""
    out: list[str] = []
    for err in sorted(
        _validator(schema_file).iter_errors(doc), key=lambda e: list(map(str, e.path))
    ):
        where = "$" + "".join(f"[{p!r}]" for p in err.path)
        out.append(f"{where}: {err.message}")
    return out


def check(doc: object, schema_file: Path) -> None:
    problems = violations(doc, schema_file)
    if problems:
        msg = f"does not satisfy {schema_file.name}: " + "; ".join(problems)
        raise PalomarDocumentError(msg)


# --- formalization.yaml ----------------------------------------------------------------------


@dataclass(frozen=True)
class Formalization:
    """A ``formalization.yaml`` as a mapping of its sections, in the order they were read.
    Kept as data rather than typed fields because the registry's schema is open at the top and
    half of its fields are free text; what the network *writes* is built by ``export`` (T7)."""

    sections: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.sections.get("version") or "")

    @property
    def project(self) -> dict[str, Any]:
        value: dict[str, Any] = self.sections.get("project") or {}
        return value

    @property
    def authors(self) -> list[str]:
        return [str(a) for a in self.project.get("authors") or []]

    @property
    def automation_methods(self) -> list[dict[str, Any]]:
        auto = self.sections.get("automation") or {}
        methods: list[dict[str, Any]] = auto.get("methods") or []
        return methods

    @property
    def models(self) -> list[str]:
        return sorted(
            {str(m) for method in self.automation_methods for m in method.get("models") or []}
        )

    @property
    def review_status(self) -> str:
        review: dict[str, Any] = self.sections.get("review") or {}
        return str(review.get("status") or "")


def read_formalization(text: str) -> Formalization:
    """Parse and validate a ``formalization.yaml`` against the vendored v0.4 schema."""
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        msg = "formalization.yaml is not a mapping"
        raise PalomarDocumentError(msg)
    check(doc, FORMALIZATION_SCHEMA_FILE)
    return Formalization(dict(doc))


def write_formalization(doc: Formalization) -> str:
    """The YAML the registry reads: sections in :data:`SECTION_ORDER`, then any others as read,
    validated before it is written. Mappings keep their key order; nothing is sorted, so a
    document read and written again means what it meant."""
    check(doc.sections, FORMALIZATION_SCHEMA_FILE)
    ordered: dict[str, Any] = {k: doc.sections[k] for k in SECTION_ORDER if k in doc.sections}
    for k, v in doc.sections.items():
        ordered.setdefault(k, v)
    schema_id = str(
        json.loads(FORMALIZATION_SCHEMA_FILE.read_text(encoding="utf-8")).get("$id", "")
    )
    head = "# yaml-language-server: $schema=" + schema_id
    body: str = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100)
    return head + "\n" + body


# --- comparator.json -------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparatorDoc:
    """Comparator's configuration (``lake comparator``, ``leanprover/comparator``)."""

    challenge_module: str
    solution_module: str
    theorem_names: tuple[str, ...]
    definition_names: tuple[str, ...] = ()
    permitted_axioms: tuple[str, ...] = ("propext", "Quot.sound", "Classical.choice")
    enable_nanoda: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "challenge_module": self.challenge_module,
            "solution_module": self.solution_module,
            "theorem_names": list(self.theorem_names),
            "definition_names": list(self.definition_names),
            "permitted_axioms": list(self.permitted_axioms),
            "enable_nanoda": self.enable_nanoda,
        }
        doc.update(self.extra)
        return doc


def read_comparator(text: str) -> ComparatorDoc:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        msg = "comparator.json is not an object"
        raise PalomarDocumentError(msg)
    known = {
        "challenge_module",
        "solution_module",
        "theorem_names",
        "definition_names",
        "permitted_axioms",
        "enable_nanoda",
    }
    for key in ("challenge_module", "solution_module", "theorem_names", "permitted_axioms"):
        if key not in raw:
            msg = f"comparator.json lacks {key}"
            raise PalomarDocumentError(msg)
    return ComparatorDoc(
        challenge_module=str(raw["challenge_module"]),
        solution_module=str(raw["solution_module"]),
        theorem_names=tuple(str(t) for t in raw["theorem_names"]),
        definition_names=tuple(str(d) for d in raw.get("definition_names") or ()),
        permitted_axioms=tuple(str(a) for a in raw["permitted_axioms"]),
        enable_nanoda=bool(raw.get("enable_nanoda", True)),
        extra={k: v for k, v in raw.items() if k not in known},
    )


def write_comparator(doc: ComparatorDoc) -> str:
    return json.dumps(doc.as_dict(), indent=2) + "\n"


# --- the entry record ------------------------------------------------------------------------


def read_entry(doc: object) -> dict[str, Any]:
    """An ``entries/<id>-v<n>.json`` record, validated against the network's observed schema."""
    check(doc, ENTRY_SCHEMA_FILE)
    assert isinstance(doc, dict)
    return doc


# --- caps ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Measure:
    lines: int
    bytes: int

    def problems(self, *, lines_cap: int, bytes_cap: int, what: str) -> list[str]:
        out: list[str] = []
        if self.lines > lines_cap:
            out.append(f"{what} has {self.lines} lines; the cap is {lines_cap}")
        if self.bytes > bytes_cap:
            out.append(f"{what} is {self.bytes} bytes; the cap is {bytes_cap}")
        return out


def measure(text: bytes) -> Measure:
    """Physical lines (blank and comment lines count, as Palomar counts) and bytes."""
    lines = text.count(b"\n") + (1 if text and not text.endswith(b"\n") else 0)
    return Measure(lines=lines, bytes=len(text))


def challenge_problems(text: bytes) -> list[str]:
    caps = pins()["challenge_caps"]
    return measure(text).problems(
        lines_cap=int(caps["lines"]), bytes_cap=int(caps["bytes"]), what="Challenge.lean"
    )


def file_problems(text: bytes, name: str) -> list[str]:
    cap = int(pins()["file_cap_lines"])
    return measure(text).problems(lines_cap=cap, bytes_cap=2**62, what=name)
