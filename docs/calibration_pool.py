"""F15-T14a: the calibration pool and the three calibration targets (R14, Q9, Q12; Stages v3.17).

    uv run python docs/calibration_pool.py pool
    uv run python docs/calibration_pool.py draft --fc <formal-conjectures at the pin> --out DIR

The pool is every problem in the committed seed dataset (``docs/seed_conjecture_sources.json``,
F11-Q23) that has a Lean statement in the pinned registry and whose erdosproblems.com status is
``PROVED``, ``SOLVED`` or ``DISPROVED`` with no Lean proof (a status carrying ``(LEAN)`` names a
formal proof and is out). The query is committed so the number in the spec is a fact the suite
checks rather than a sentence that rots (F15-Q12): ``gate/tests/test_calibration_pool.py``.

Three are chosen from it, graded easy, medium and one needing a skeleton, with the reasons
recorded in ``CHOICES``. ``draft`` writes each as a reviewable intake directory the way
``gate/tools/wave.py`` drafts a wave row — the registry header verbatim, ``import Mathlib``, the
file's ``open`` lines, the statement as ``Opn.erdos_<n>``, a ``True`` witness — except that the
record is on the ``formalization`` track with ``calibration: true`` and its prior art is the
literature proof (R14 c). The catalog's rows for solved problems are thin (no score, no
declaration), so the statement is read from the registry file by the driver's own extractor
and the helper-library check is the driver's too. Every draft is read by hand before intake.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gate"))

from opn_gate import intake, layout, schemas  # noqa: E402 — gate/ on the path above

DATASET = ROOT / "docs" / "seed_conjecture_sources.json"
CATALOG = ROOT / "docs" / "lean_conjecture_catalog.json"
#: The erdosproblems.com statuses that mean "solved in the literature, no Lean proof".
SOLVED_WITHOUT_LEAN: tuple[str, ...] = ("PROVED", "SOLVED", "DISPROVED")
FC_REPO = "google-deepmind/formal-conjectures"
FC_AUTHOR = "The Formal Conjectures Authors"
GRADES: tuple[str, ...] = ("easy", "medium", "skeleton")
WITNESS = (
    "/-! Non-vacuity witness (D-4 step 7): the statement has no hypotheses, so the expected\n"
    "witness type is `True`. -/\n\ntheorem witness : True := trivial\n"
)
_DOC_RE = r"/--(?P<doc>[\s\S]*?)-/\s*@\[category[^\]]*\]\s*theorem\s+{decl}(?![\w.'])"


def _wave() -> Any:
    """``gate/tools/wave.py`` is a script beside the other tools, not a package member."""
    path = ROOT / "gate" / "tools" / "wave.py"
    spec = importlib.util.spec_from_file_location("wave", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- the pool (R14 a) -----------------------------------------------------------------------------


def pool(dataset: Path = DATASET) -> list[dict[str, Any]]:
    """Every seed row with a Lean statement and a solved-without-Lean site status, by number."""
    doc = json.loads(dataset.read_text(encoding="utf-8"))
    out = []
    for row in doc["problems"]:
        status = str(row.get("site_status") or "").strip().upper()
        if not row.get("lean_files") or status not in SOLVED_WITHOUT_LEAN:
            continue
        out.append(
            {
                "number": int(row["number"]),
                "site_status": status,
                "standing_since": row.get("standing_since"),
                "lean_files": list(row["lean_files"]),
                "lean_declarations": list(row.get("lean_declarations") or []),
                "areas": list(row.get("areas") or []),
            }
        )
    return sorted(out, key=lambda r: r["number"])


# --- the three choices (R14 b) --------------------------------------------------------------------


@dataclass(frozen=True)
class Choice:
    number: int
    grade: str
    decl: str  # the main statement in the registry file, never a variant
    literature: str  # the proof the target cites as prior art (R14 c)
    reason: str
    #: For a registry theorem with binders before the colon, the proposition restated as one
    #: closed `∀`, and the witness for its hypotheses — written by hand, read by the curator, and
    #: checked only by the sandboxed admission of the intake (T14b); the driver refuses such a
    #: row rather than guessing (F14-T15), so the guess is recorded here as a guess.
    hand_statement: str | None = None
    hand_witness: str | None = None

    @property
    def target_id(self) -> str:
        return f"erdos-{self.number}"

    @property
    def file(self) -> str:
        return f"FormalConjectures/ErdosProblems/{self.number}.lean"


CHOICES: tuple[Choice, ...] = (
    Choice(
        number=1050,
        grade="easy",
        decl="erdos_1050",
        literature=(
            "P. B. Borwein, On the irrationality of sum 1/(q^n + r), J. Number Theory 37 (1991), "
            "253-259; a self-contained proof in Math. Proc. Camb. Phil. Soc. 112 (1992), 141-146"
        ),
        reason=(
            "One closed proposition over the reals, the irrationality of the sum of 1/(2^(n+1) - "
            "3), with no local "
            "definitions, no registry helpers and no hazard flag. Borwein's 1992 proof is a "
            "few pages of elementary analysis, and the registry itself records that a complete "
            "Lean 4 proof of this statement exists in an external gallery at a comparable Mathlib "
            "generation, so the mathematics is known to formalize; the calibration question is "
            "whether a fresh agent produces one under the gate with no help."
        ),
    ),
    Choice(
        number=69,
        grade="medium",
        decl="erdos_69",
        literature=(
            "P. Erdős, On arithmetical properties of Lambert series, J. Indian Math. Soc. 12 "
            "(1948), 63-66"
        ),
        reason=(
            "The irrationality of the sum of omega(n)/2^n, with omega the number of distinct "
            "prime divisors, a "
            "Mathlib arithmetic function; the registry files it as textbook. The route is two "
            "lemmas — the Lambert-series identity sum omega(n)/2^n = sum over primes p of 1/(2^p "
            "- 1), a rearrangement "
            "of absolutely convergent series, and Erdős's 1948 irrationality argument for the "
            "prime sum — each ordinary analysis with no known Lean proof, so the agent has to "
            "decompose and prove rather than transcribe."
        ),
    ),
    Choice(
        number=402,
        grade="skeleton",
        decl="erdos_402",
        literature=(
            "R. Balasubramanian and K. Soundararajan, On a conjecture of R. L. Graham, Acta "
            "Arith. 75 (1996), 1-38 (Graham's conjecture; Szegedy 1986 and Zaharescu 1987 for "
            "large sets)"
        ),
        reason=(
            "For every finite set A of positive integers there are a, b in A with gcd(a, b) at "
            "most "
            "a/|A|: Graham's 1970 conjecture, stated over Finset Nat and Rat with nothing but "
            "Mathlib. The proof is a multi-lemma argument (a Szemerédi-style reduction, a "
            "structure lemma for the extremal sets, and analytic estimates for large |A|) that no "
            "agent will close in one session; the honest first artifact is a skeleton whose "
            "holes are those lemmas (D-12 #5, D-31), which is the third shape the run must "
            "exercise."
        ),
        hand_statement=(
            "∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ)"  # noqa: RUF001 — Lean, as the registry writes it
        ),
        hand_witness=(
            "/-! Non-vacuity witness (D-4 step 7): the statement quantifies over a finite set with "
            "two hypotheses, so the expected witness type is their closure, an instance of\n"
            "`∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty`. Written by hand (the wave driver refuses binders "  # noqa: RUF001, E501 — Lean, as the registry writes it
            "before the colon) and checked only by the sandboxed admission at intake. -/\n\n"
            "theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty :=\n"  # noqa: RUF001 — Lean, as the registry writes it
            "  ⟨{1}, by simp, by simp⟩\n"
        ),
    ),
)


def choices_in_pool(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    numbers = {r["number"]: r for r in rows}
    return {c.number: numbers[c.number] for c in CHOICES if c.number in numbers}


# --- the drafts (R14 c, the wave driver's shape) --------------------------------------------------


def docstring_of(text: str, decl: str) -> str:
    m = re.search(_DOC_RE.format(decl=re.escape(decl)), text)
    return " ".join(m.group("doc").split()) if m else ""


def record_for(
    choice: Choice, row: dict[str, Any], catalog: dict[str, Any], text: str, *, curator: str
) -> dict[str, Any]:
    wave = _wave()
    site = f"https://www.erdosproblems.com/{choice.number}"
    docstring = docstring_of(text, choice.decl)
    doc: dict[str, Any] = {
        "schema": intake.SCHEMA,
        "id": choice.target_id,
        "title": f"Erdős problem {choice.number} (calibration): a known result",
        "informal": docstring[:4000] or None,
        "paraphrase": None if docstring else choice.decl,
        "track": "formalization",
        "calibration": True,
        "source": {"kind": "formal-conjectures", "ref": choice.file, "url": site},
        "curator": curator,
        "prior_art": {
            "arxiv_query": None,
            "forum_url": site,
            "summary": (
                f"A known result, on the calibration track (Stages v3.17, F15-R14): solved in the "
                f"literature by {choice.literature}, with no Lean proof at registry commit "
                f"{catalog['fc_commit'][:12]} (erdosproblems.com status {row['site_status']}, "
                f"standing since {row['standing_since']}). Graded {choice.grade}: {choice.reason} "
                "Drafted by docs/calibration_pool.py and read by the curator before intake."
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
        "attack_routes": [f"the literature proof: {choice.literature}"],
        "posting": None,
        "domains": sorted({wave.DOMAINS[a] for a in row.get("areas") or [] if a in wave.DOMAINS}),
        "qa_summary": None,
    }
    schemas.validate(doc, intake.SCHEMA)
    intake.check_artifacts(doc)
    intake.check_domains(doc)
    intake.check_quotation(doc)
    intake.check_calibration(doc)
    return doc


def draft(  # noqa: PLR0911 — one return per refusal, the driver's shape
    choice: Choice, *, fc: Path, out: Path, curator: str
) -> tuple[Path | None, list[str]]:
    """One reviewable intake directory, or the reasons it cannot be drafted honestly."""
    wave = _wave()
    rows = choices_in_pool(pool())
    if choice.number not in rows:
        return None, [f"erdos {choice.number} is not in the calibration pool"]
    row = rows[choice.number]
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = fc / choice.file
    if not source.is_file():
        return None, [f"{choice.file} is not in the checkout"]
    text = source.read_text(encoding="utf-8")
    header = intake.copyright_header(text)
    if header is None:
        return None, ["the registry file carries no copyright header to keep"]
    prop, how = wave.extract(text, choice.decl)
    if prop is None and choice.hand_statement is not None:
        prop, how = choice.hand_statement, f"restated by hand ({how})"
    if prop is None:
        return None, [how]
    reasons: list[str] = []
    shape = wave.shape_refusal(prop) if choice.hand_statement is None else None
    if shape is not None:
        reasons.append(shape)
    # A hand-restated proposition was read by a person, binder by binder; the driver's helper
    # check trips on `∃ᵉ (b ∈ A)`, whose bound `b` it does not see as bound.
    used = [] if choice.hand_statement else wave.helpers_used(prop, wave.helper_names(fc))
    if used:
        reasons.append(
            f"uses names {wave.HELPER_LIBRARY} declares (port first): " + ", ".join(used)
        )
    if reasons:
        return None, reasons
    doc = record_for(choice, row, catalog, text, curator=curator)
    opens = "\n".join(wave._OPEN_RE.findall(text))
    statement = (
        f"{header}\n\nimport Mathlib\n\n/-! {doc['title']} — imported from {FC_REPO} "
        f"({choice.file} at {catalog['fc_commit']}, Apache-2.0); {how}. A calibration target "
        "(Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by "
        "the curator before intake. -/\n\n"
        + (f"{opens}\n\n" if opens else "")
        + f"theorem Opn.erdos_{choice.number} :\n    {prop} := by\n  sorry\n"
    )
    parsed = layout.parse_statement(statement)
    if not isinstance(parsed, layout.Statement):
        return None, [f"the drafted statement does not parse: {parsed.message}"]
    directory = out / choice.target_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "record.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "Statement.lean").write_text(statement, encoding="utf-8")
    (directory / "Witness.lean").write_text(choice.hand_witness or WITNESS, encoding="utf-8")
    upstream = out / "upstream" / source.name
    upstream.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, upstream)
    return directory, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pool", help="print the calibration pool as JSON")
    dr = sub.add_parser("draft", help="draft the three calibration targets for review")
    dr.add_argument("--fc", type=Path, required=True, help="formal-conjectures at the pin")
    dr.add_argument("--out", type=Path, required=True)
    dr.add_argument("--curator", default="thisisanameforsure")
    args = parser.parse_args(argv)
    if args.command == "pool":
        rows = pool()
        print(json.dumps({"count": len(rows), "rows": rows}, indent=2, ensure_ascii=False))
        return 0
    result: dict[str, Any] = {"drafted": [], "refused": []}
    for choice in CHOICES:
        directory, reasons = draft(
            choice, fc=args.fc.resolve(), out=args.out.resolve(), curator=args.curator
        )
        if directory is None:
            result["refused"].append({"target": choice.target_id, "reasons": reasons})
        else:
            result["drafted"].append({"target": choice.target_id, "grade": choice.grade})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["refused"] else 1


if __name__ == "__main__":
    sys.exit(main())
