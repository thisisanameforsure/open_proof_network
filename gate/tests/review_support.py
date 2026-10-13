"""Shared fixtures for the review job's tests (F26-T5, T6, T7): a graph with a review on a core-Lean
target, the prototype's candidates, records built the way the service and the job build them, and
``ReviewFake`` — the toolchain seam's fake for the fast tier.

``ReviewFake`` answers each file the job elaborates from the file's ``-- opn-review:`` header and
a Python model of each candidate (``Model``): the same Lean text the lean tier elaborates goes
through ``Toolchain.elaborate``, and the fake decides it as the kernel would for that model. It
keeps every text it was handed, so a test can check that every Lean file the job wrote was one the
toolchain accepted.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from fakes import FakeToolchain

from opn_gate import review_lean
from opn_gate.toolchain import ElabResult, Message, ResolvedToolchain

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "gate" / "tests" / "fixtures" / "review"
PROPOSITIONAL = ROOT / "gate" / "tests" / "fixtures" / "graphs" / "propositional"
PROTOTYPE = json.loads((FIXTURES / "prototype.json").read_text(encoding="utf-8"))
DATE = "2026-10-12"
SIG = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"

Pred = Callable[[int], bool]


def is_prime(p: int) -> bool:
    return p >= 2 and all(p % d for d in range(2, int(p**0.5) + 1))


@dataclass
class Model:
    """A candidate's meaning: its claim at ``n`` given the concept predicate, its own predicate,
    and what the bounded tactics can prove about it."""

    claim: Callable[[int, Pred], bool]
    prime: Pred | None = is_prime
    compiles: bool = True
    provable: bool = False  # the statement screen fires
    vacuous: bool = False  # the False screen fires

    def value(self, case: dict[str, Any]) -> bool:
        probe, n = case["probe"], case["n"]
        if probe == "concept":
            return bool(self.prime and self.prime(n))
        if probe == "covers":
            return self.claim(n, lambda _x: False)
        if probe == "witness":
            s = set(case["set"] or ())
            return self.claim(n, lambda x: x in s)
        return self.claim(n, self.prime or (lambda _x: False))


def legendre(
    *, lo: int = 1, closed: bool = False, two: bool = False, hi: Callable[[int], int] | None = None
) -> Callable[[int, Pred], bool]:
    """Legendre's conjecture read with a domain ``n ≥ lo``, an open or closed interval, one prime
    or two (the strength drift), an upper end ``hi``."""
    top = hi or (lambda n: (n + 1) ** 2)

    def claim(n: int, p: Pred) -> bool:
        if n < lo:
            return True
        a, b = n * n, top(n)
        xs = range(a, b + 1) if closed else range(a + 1, b)
        found = [x for x in xs if p(x)]
        return len(found) >= (2 if two else 1)

    return claim


@dataclass
class ReviewFake(FakeToolchain):
    """The seam's fake for the review job: decides each file by its header and the models."""

    models: dict[str, Model] = field(default_factory=dict)
    #: directions ``(a, b)`` the bounded tactics prove; ``trivial`` claims they prove outright
    implies: set[tuple[str, str]] = field(default_factory=set)
    trivial: set[str] = field(default_factory=set)
    #: cases the kernel refuses although a table said otherwise (a lying search)
    kernel_refuses: set[str] = field(default_factory=set)
    #: mutant index -> model; a mutant with none does not elaborate
    mutant_models: dict[int, Model] = field(default_factory=dict)
    texts: list[str] = field(default_factory=list)
    accepted: set[str] = field(default_factory=set)

    def model(self, cid: str) -> Model | None:
        if cid in self.models:
            return self.models[cid]
        if "-m" in cid:
            return self.mutant_models.get(int(cid.rsplit("-m", 1)[1]))
        return None

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        root: Path | None = None,
        timeout_s: float | None = None,
    ) -> ElabResult:
        text = source.read_text(encoding="utf-8")
        self.texts.append(text)
        self.calls.append(f"elaborate:{module}")
        head = review_lean.header_of(text) or {}
        ok, messages = self._decide(head)
        if ok:
            self.accepted.add(text)
            olean = out_dir / f"{module}.olean"
            olean.parent.mkdir(parents=True, exist_ok=True)
            olean.write_bytes(b"fake")
            return ElabResult(ok=True, messages=tuple(messages))
        err = Message(str(source), 1, 0, "error", "fake: the kernel says no")
        return ElabResult(ok=False, messages=(*messages, err))

    def _decide(self, head: dict[str, Any]) -> tuple[bool, list[Message]]:  # noqa: PLR0911, PLR0912
        op = head.get("op")
        if op == "test":
            return True, []
        if op in ("compile", "compile-mutant"):
            m = self.model(str(head.get("cand")))
            return (m is not None and m.compiles), []
        if op == "survey":
            m = self.model(str(head["cand"]))
            if m is None or not m.compiles:
                return False, []
            out = []
            for row in head["rows"]:
                bits = "".join(
                    "1"
                    if m.value(
                        {
                            "probe": row["probe"],
                            "n": n,
                            "set": row["set"],
                            "concept": row["concept"],
                        }
                    )
                    else "0"
                    for n in range(row["n_max"] + 1)
                )
                out.append(Message("f", 1, 0, "information", f"OPN|{row['key']}|{bits}\n"))
            return True, out
        if op == "decide":
            m = self.model(str(head["cand"]))
            token = json.dumps(head["case"], sort_keys=True)
            if m is None or token in self.kernel_refuses:
                return False, []
            return m.value(head["case"]) == head["value"], []
        if op == "instance":
            a, b = self.model(str(head["a"])), self.model(str(head["b"]))
            token = json.dumps(head["case"], sort_keys=True)
            if a is None or b is None or token in self.kernel_refuses:
                return False, []
            return a.value(head["case"]) and not b.value(head["case"]), []
        if op == "screen":
            m = self.model(str(head["cand"]))
            if m is None:
                return False, []
            which = head["screen"]
            if which == "statement":
                return m.provable, []
            if which == "false":
                return m.vacuous, []
            n = head.get("n")
            return (n is not None and not m.claim(n, m.prime or (lambda _x: False))), []
        if op == "link":
            a, b = self.model(str(head["a"])), self.model(str(head["b"]))
            if a is None or b is None or a.prime is None or b.prime is None:
                return False, []
            same = all(a.prime(x) == b.prime(x) for x in range(60))
            return same, []
        if op == "direction":
            x, y = str(head["a"]), str(head["b"])
            if head.get("guard"):
                return y in self.trivial, []
            return (x, y) in self.implies or y in self.trivial, []
        if op == "equivalent":
            x, y = str(head["a"]), str(head["b"])
            return (x, y) in self.implies and (y, x) in self.implies, []
        return False, []


# --- the graph -------------------------------------------------------------------------------


def candidate_id(lean: str) -> str:
    return "c-" + hashlib.sha256(lean.encode()).hexdigest()[:8]


def make_graph(
    tmp: Path,
    *,
    target: str = "legendre",
    words: str = "For every positive integer n, there is a prime strictly between n² and (n+1)².",
    concepts: tuple[str, ...] = ("prime",),
    candidates: dict[str, str],
    people: tuple[str, ...] = (),
) -> tuple[Path, dict[str, str]]:
    """A graph with one core-Lean target holding a review and ``candidates`` (name -> Lean), the
    ``gate-spec.json`` the propositional fixture pins. Returns the graph and name -> id."""
    graph = tmp / "graph"
    tdir = graph / "targets" / target
    tdir.mkdir(parents=True)
    spec = json.loads(
        (PROPOSITIONAL / "targets" / "propositional" / "gate-spec.json").read_text(encoding="utf-8")
    )
    spec["graph_id"] = target
    (tdir / "gate-spec.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    base = tdir / "review"
    (base / "candidates").mkdir(parents=True)
    head = {
        "schema": "review/v1",
        "target": target,
        "opened_by": {"identity": "curator", "role": "curator"},
        "date": DATE,
        "words": words,
        "cases": [],
        "concepts": list(concepts),
        "source": {"kind": "proposal", "ref": None},
        "tracking": None,
        "supersedes": None,
    }
    (base / "review.yaml").write_text(yaml.safe_dump(head, sort_keys=False, allow_unicode=True))
    ids: dict[str, str] = {}
    for name, lean in candidates.items():
        cid = candidate_id(lean)
        ids[name] = cid
        person = name in people
        doc = {
            "schema": "candidate/v1",
            "target": target,
            "id": cid,
            "author": name,
            "method": "manual" if person else "agent",
            "models": [] if person else ["a-model"],
            "read_others": False,
            "origin": "submitted",
            "source": None,
            "lean_file": f"{cid}.lean",
            "statement_hash": hashlib.sha256(lean.encode()).hexdigest(),
            "date": DATE,
        }
        (base / "candidates" / f"{cid}.yaml").write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
        )
        (base / "candidates" / f"{cid}.lean").write_text(lean, encoding="utf-8")
    return graph, ids


def prototype_lean(conj: str, name: str) -> str:
    return (FIXTURES / conj / f"{name}.lean").read_text(encoding="utf-8")


def add_test_record(  # noqa: PLR0917
    graph: Path, target: str, case: review_lean.Case, expected: bool, source: str, ref: str
) -> str:
    """An intent test on record, built as the job builds one."""
    from opn_gate import review_job  # noqa: PLC0415

    tid = review_job.test_id(case, expected, source, ref)
    base = graph / "targets" / target / "review" / "tests"
    base.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "intent-test/v1",
        "target": target,
        "id": tid,
        "case": case.words(),
        "probe": case.probe,
        "concept": case.concept,
        "expected": {"value": expected, "source": source, "ref": ref},
        "author": "curator",
        "lean_file": f"{tid}.lean",
        "date": DATE,
    }
    (base / f"{tid}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    (base / f"{tid}.lean").write_text(
        review_lean.test_text(tid, case, expected, source, ref), encoding="utf-8"
    )
    return tid


def add_answer(graph: Path, target: str, question: str, words: str, aid: str = "a-1") -> str:
    base = graph / "targets" / target / "review" / "answers"
    base.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "review-answer/v1",
        "target": target,
        "id": aid,
        "question": question,
        "answer": words,
        "cites": None,
        "date": DATE,
        "login": "proposer",
        "via": "approval-key",
        "key": "ssh-ed25519 AAAA approval",
        "signature": SIG,
    }
    (base / f"{aid}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return aid


def tree(graph: Path) -> dict[str, bytes]:
    return {
        p.relative_to(graph).as_posix(): p.read_bytes()
        for p in sorted(graph.rglob("*"))
        if p.is_file()
    }


def copy_graph(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst
