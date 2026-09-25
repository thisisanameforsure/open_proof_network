#!/usr/bin/env python3
"""opn-prove: hand a node of the Open Proof Network to any prover, and its answer back (F17).

    python3 opn_prove.py export  --graph CLONE --node ID [--out problem.lean] [--project DIR]
    python3 opn_prove.py import  --graph CLONE --node ID ANSWER [--out Proof.lean]
    python3 opn_prove.py run     --problem problem.lean --answer answer.txt [--timeout S] -- ARGV...
    python3 opn_prove.py check   --api URL --graph CLONE --node ID FILE
    python3 opn_prove.py submit  --api URL --graph CLONE --node ID FILE --model NAME
    python3 opn_prove.py postmortem --graph CLONE --node ID --run run.json [--send --api URL]

One file, the Python standard library only, Python 3.10 or later: a contributor clones the graph
and downloads this file, nothing else. ``export`` writes the node's statement as one
self-contained file, its definitions and its own Context inlined exactly as the network's fast
check forwards it, so a prover that takes "a Lean file with sorry" can take it. ``import`` turns
whatever the prover answered (a whole file, a fenced block after a proof plan, a bare tactic
block) into the ``Proof.lean`` the gate admits, or refuses with the reason; it never edits the
statement, adds an import or drops a declaration it cannot place. ``run`` runs any command as the
prover. Named provers are only defaults for that command: the network blesses none (D-1).

The token for ``submit`` is read from ``OPN_TOKEN`` and never from a flag or a file.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VERSION = "1"
HARNESS = "opn-prove"

# --- the graph's layout (the same rules as the network's own opn_gate.layout) ---------------------

IMPORT_RE = re.compile(r"^import\s+(?P<module>\S+)", re.M)
IMPORT_LINE_RE = re.compile(r"^import\s+\S+[ \t]*$", re.M)
THEOREM_RE = re.compile(
    r"^(?:@\[[^\]\n]*\]\s*)*(?:(?:private|protected|noncomputable)\s+)*(?:theorem|lemma)\s+"
    r"(?P<name>[^\s:({\[]+)",
    re.M,
)
SORRY_BODY_RE = re.compile(r":=\s*(?:by\s+)?sorry\b")
SORRY_TOKEN_RE = re.compile(r"(?<![\w'.!?])sorry(?![\w'.!?])")
DECL_RE = re.compile(
    r"^(?:@\[[^\]\n]*\]\s*)*(?:(?:private|protected|noncomputable|partial|unsafe)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|axiom|structure|inductive|class|opaque|example)"
    r"\b[ \t]*(?P<name>[^\s:({\[]*)",
    re.M,
)
FENCE_RE = re.compile(r"```[ \t]*(?:lean4?|Lean4?)?[ \t]*\n(?P<body>.*?)```", re.S)
LIBRARY_PREFIXES = ("Init", "Std", "Lean", "Mathlib", "Batteries", "Aesop")
DEFS_PREFIX, NODES_PREFIX = "Defs", "Nodes"


class Refused(Exception):  # noqa: N818 — a refusal is an answer the caller acts on
    """A refusal with a code the caller can act on; nothing was written."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class Statement:
    decl_name: str
    text: str
    prefix: str  # everything up to and including the `:=` that opens the sorry body
    suffix: str  # everything after the `sorry`


def parse_statement(text: str) -> Statement:
    theorems = list(THEOREM_RE.finditer(text))
    bodies = list(SORRY_BODY_RE.finditer(text))
    if len(theorems) != 1 or len(bodies) != 1 or bodies[0].start() < theorems[0].end():
        raise Refused("statement-shape", "Statement.lean must declare one sorry-bodied theorem")
    body = bodies[0]
    return Statement(theorems[0].group("name"), text, text[: body.start() + 2], text[body.end() :])


def imports_of(text: str) -> list[str]:
    return [m.group("module") for m in IMPORT_RE.finditer(text)]


def module_origin(module: str) -> str:
    head, _, rest = module.partition(".")
    if head in LIBRARY_PREFIXES:
        return "library"
    if head == DEFS_PREFIX:
        return "defs"
    if head == NODES_PREFIX and rest:
        return "node"
    return "other"


def node_module(node_id: str, stem: str) -> str:
    return f"{NODES_PREFIX}.«{node_id}».{stem}"


def defs_modules(text: str) -> list[str]:
    return [m for m in imports_of(text) if module_origin(m) == "defs"]


# --- the graph clone ------------------------------------------------------------------------------


@dataclass
class Node:
    graph: Path
    target_id: str
    node_id: str

    @property
    def target_dir(self) -> Path:
        return self.graph / "targets" / self.target_id

    @property
    def dir(self) -> Path:
        return self.target_dir / "nodes" / self.node_id

    def read(self, name: str) -> str:
        return (self.dir / name).read_text(encoding="utf-8")

    def gate_spec(self) -> dict[str, Any]:
        path = self.target_dir / "gate-spec.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def find_node(graph: Path, node_id: str, target_id: str | None = None) -> Node:
    targets = graph / "targets"
    if not targets.is_dir():
        raise Refused("graph-missing", f"{graph} is not a clone of the graph (no targets/)")
    found = [
        t.name
        for t in sorted(targets.iterdir())
        if (t / "nodes" / node_id / "Statement.lean").is_file()
        and (target_id is None or t.name == target_id)
    ]
    if len(found) != 1:
        where = f" in {target_id}" if target_id else ""
        raise Refused("node-unknown", f"{node_id}{where}: found in {len(found)} targets")
    return Node(graph, found[0], node_id)


# --- export ---------------------------------------------------------------------------------------


def inlined_modules(node: Node, statement: Statement) -> list[tuple[str, str]]:
    """The statement's Defs modules and everything they import, dependencies first, then the
    node's own Context when the statement imports it: as (module, source without its imports).
    The same order the network's fast check inlines in (api ``checks.inline_defs``)."""
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(module: str, trail: tuple[str, ...]) -> None:
        if module in seen:
            return
        if module in trail:
            raise Refused("defs-cycle", " -> ".join((*trail, module)))
        stem = module.partition(".")[2]
        path = node.target_dir / "defs" / f"{stem}.lean"
        if not path.is_file():
            raise Refused("defs-unknown", f"{node.target_id} has no {module}")
        source = path.read_text(encoding="utf-8")
        for dep in defs_modules(source):
            visit(dep, (*trail, module))
        seen.add(module)
        ordered.append((module, IMPORT_LINE_RE.sub("", source).strip("\n")))

    for module in defs_modules(statement.text):
        visit(module, ())
    own = node_module(node.node_id, "Context")
    if own in imports_of(statement.text) and (node.dir / "Context.lean").is_file():
        source = node.read("Context.lean")
        for dep in defs_modules(source):
            visit(dep, (own,))
        ordered.append((own, IMPORT_LINE_RE.sub("", source).strip("\n")))
    return ordered


def forwarded_text(content: str, defs: Sequence[tuple[str, str]]) -> str:
    """``content`` with its Defs and inlined imports removed and the definitions' sources placed
    after its remaining header (api ``checks.forwarded_text``)."""
    if not defs:
        return content
    inlined = {module for module, _ in defs}
    lines = [
        line
        for line in content.splitlines(keepends=True)
        if not (
            line.startswith("import ")
            and (module_origin(line.split()[1]) == "defs" or line.split()[1] in inlined)
        )
    ]
    last = max((i for i, line in enumerate(lines) if line.startswith("import ")), default=-1)
    block = "".join(
        f"\n-- inlined by the network from {module} (F13-R5)\n{src}\n" for module, src in defs
    )
    return "".join(lines[: last + 1]) + block + "\n" + "".join(lines[last + 1 :])


def export(node: Node) -> str:
    """The problem file: exactly what the network's fast check forwards for the statement."""
    statement = parse_statement(node.read("Statement.lean"))
    return forwarded_text(statement.text, inlined_modules(node, statement))


def header_comment(node: Node) -> str:
    spec = node.gate_spec()
    toolchain = spec.get("lean_toolchain") or "the graph's pinned toolchain"
    mathlib = spec.get("mathlib_sha") or "none (Lean core only)"
    return (
        f"-- opn-prove export of {node.target_id}/{node.node_id}\n"
        f"-- toolchain: {toolchain}; Mathlib: {mathlib}\n"
        "-- Replace the `sorry`. Do not change anything above it: the gate refuses a proof whose\n"
        "-- header or statement differs from the node's (D-3, F00-R19).\n"
    )


def write_project(node: Node, directory: Path) -> Path:
    """A minimal Lake project around the problem file, for provers that take a project (F17-R2).
    The Lean toolchain and the Mathlib commit are the graph's pins."""
    spec = node.gate_spec()
    directory.mkdir(parents=True, exist_ok=True)
    toolchain = spec.get("lean_toolchain")
    if toolchain:
        (directory / "lean-toolchain").write_text(f"{toolchain}\n", encoding="utf-8")
    mathlib = spec.get("mathlib_sha")
    require = (
        '\n[[require]]\nname = "mathlib"\ngit = "https://github.com/leanprover-community/mathlib4"\n'
        f'rev = "{mathlib}"\n'
        if mathlib
        else ""
    )
    (directory / "lakefile.toml").write_text(
        'name = "opn_problem"\ndefaultTargets = ["Problem"]\n'
        f'{require}\n[[lean_lib]]\nname = "Problem"\n',
        encoding="utf-8",
    )
    problem = directory / "Problem.lean"
    problem.write_text(header_comment(node) + export(node), encoding="utf-8")
    return problem


# --- import ---------------------------------------------------------------------------------------


@dataclass
class Imported:
    kind: str  # proof | partial
    text: str
    notes: list[str] = field(default_factory=list)


def lean_block(answer: str) -> str:
    """The Lean the answer carries: the last fenced block when there is one (a proof plan comes
    first in the answers of the common open-weight provers), else the whole answer."""
    answer = answer.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [m.group("body") for m in FENCE_RE.finditer(answer)]
    return blocks[-1] if blocks else answer


def _signature(prefix: str) -> str:
    """The statement's declaration from its keyword to the ``:=``, whitespace-normalised, with the
    theorem's name taken out, so a renamed theorem still matches."""
    decl = THEOREM_RE.search(prefix)
    assert decl is not None
    tail = prefix[decl.end() : -2]
    return " ".join(tail.split())


def _declarations(text: str) -> list[tuple[int, str, str]]:
    return [(m.start(), m.group("kind"), m.group("name")) for m in DECL_RE.finditer(text)]


def _extract_body(statement: Statement, problem: str, lean: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    theorems = list(THEOREM_RE.finditer(lean))
    if not theorems:
        body = lean.strip("\n")
        if not body.strip():
            raise Refused("answer-empty", "the answer carries no Lean")
        if not body.lstrip().startswith("by"):
            body = "by\n" + "\n".join(
                "  " + line if line.strip() else line for line in body.split("\n")
            )
        notes.append("the answer was a bare tactic block")
        return " " + body.strip("\n") if not body.startswith(" ") else body, notes
    wanted = _signature(statement.prefix)
    for match in reversed(theorems):
        start = match.end()
        assign = _top_level_assign(lean, start)
        if assign is None:
            continue
        if " ".join(lean[start:assign].split()) != wanted:
            continue
        if match.group("name") != statement.decl_name:
            notes.append(
                f"the answer renamed the theorem {match.group('name')}; kept the node's name"
            )
        end = _next_declaration(lean, assign)
        body = lean[assign + 2 : end].rstrip()
        _refuse_outside_declarations(problem, lean, match.start(), end)
        return body, notes
    raise Refused(
        "signature-changed",
        "the answer does not contain the node's theorem with its statement unchanged",
    )


def _top_level_assign(text: str, start: int) -> int | None:
    depth = 0
    i = start
    while i < len(text) - 1:
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and text[i + 1] == "=" and depth == 0:
            return i
        i += 1
    return None


def _next_declaration(text: str, after: int) -> int:
    later = [pos for pos, _, _ in _declarations(text) if pos > after]
    ends = [m.start() for m in re.finditer(r"^(?:end\b|namespace\b|section\b)", text, re.M)]
    candidates = [p for p in (*later, *(e for e in ends if e > after)) if p > after]
    return min(candidates) if candidates else len(text)


def _refuse_outside_declarations(problem: str, lean: str, start: int, end: int) -> None:
    """Anything the answer declares or opens outside the theorem that the problem file did not
    already have: an import, an ``open``, a ``set_option`` or a helper declaration. ``Proof.lean``
    can carry none of them, so each is refused by name rather than dropped (C7, F17-R6). A
    definition the prover echoed back from the inlined ``Defs`` or Context is the problem's own."""
    outside = lean[:start] + lean[end:]
    have = set(imports_of(problem))
    added = [m for m in imports_of(outside) if m not in have and module_origin(m) != "defs"]
    if added:
        raise Refused("import-added", f"the answer imports {', '.join(added)}; a proof cannot")
    problem_lines = {line.strip() for line in problem.splitlines()}
    for line in outside.splitlines():
        s = line.strip()
        if (s.startswith("open ") or s.startswith("set_option ")) and s not in problem_lines:
            code = "open-added" if s.startswith("open ") else "option-outside-body"
            raise Refused(code, f"the answer adds `{s}` outside the proof")
    known = {name for _, _, name in _declarations(problem)}
    for _, kind, name in _declarations(outside):
        if name not in known:
            raise Refused(
                "helper-declaration", f"the answer declares {kind} {name} outside the proof"
            )


def import_answer(node: Node, answer: str) -> Imported:
    statement = parse_statement(node.read("Statement.lean"))
    body, notes = _extract_body(statement, export(node), lean_block(answer))
    tokens = [m.start() for m in SORRY_TOKEN_RE.finditer(_strip_comments(body))]
    kind = "proof"
    if tokens:
        stripped = _strip_comments(body)
        lines = stripped.splitlines()
        for pos in tokens:
            line_no = stripped.count("\n", 0, pos)
            here = lines[line_no]
            above = lines[line_no - 1] if line_no else ""
            if not (re.search(r"\bhave\b", here) or re.search(r"\bhave\b.*:=\s*by\s*$", above)):
                raise Refused(
                    "sorry-left",
                    f"the answer leaves `sorry` outside a `have` (line {line_no + 1} of the proof)",
                )
        kind = "partial"
        notes.append("every sorry sits in a have: a partial proof, whose holes become nodes (D-12)")
    if not body.strip():
        raise Refused("proof-empty", "the answer's proof body is empty")
    text = statement.prefix + (body if body.startswith((" ", "\n")) else " " + body)
    suffix = statement.suffix.rstrip()
    text = text.rstrip() + ("\n" + suffix.lstrip("\n") if suffix.strip() else "") + "\n"
    return Imported(kind, text, notes)


def _strip_comments(text: str) -> str:
    out = re.sub(r"/-.*?-/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"--[^\n]*", "", out)


# --- run ------------------------------------------------------------------------------------------


def run_backend(problem: Path, answer: Path, argv: Sequence[str], timeout: float) -> dict[str, Any]:
    """Run any command as the prover, ``{problem}`` and ``{answer}`` substituted in its argv."""
    args = [a.replace("{problem}", str(problem)).replace("{answer}", str(answer)) for a in argv]
    started = time.monotonic()
    record: dict[str, Any] = {
        "schema": "opn-prove-run/v1",
        "backend": "command",
        "program": Path(args[0]).name if args else None,
        "started": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeout_s": timeout,
    }
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        record.update(exit=done.returncode, timed_out=False, stderr_tail=done.stderr[-2000:])
    except subprocess.TimeoutExpired:
        record.update(exit=None, timed_out=True, stderr_tail="")
    except OSError as exc:
        record.update(exit=None, timed_out=False, stderr_tail=str(exc))
    record["elapsed_s"] = round(time.monotonic() - started, 3)
    record["answered"] = answer.is_file() and bool(answer.read_text(encoding="utf-8").strip())
    return record


# --- presets: defaults for a named prover, never code the network depends on (D-1) ----------------

#: F17-Q2: the one prompt DeepSeek-Prover-V2, Goedel-Prover-V2 and Pythagoras-Prover share, word
#: for word from their READMEs (read 2026-09-24), sent as one chat user message.
WHOLE_FILE_PROMPT = (
    "Complete the following Lean 4 code:\n\n```lean4\n{problem}\n```\n\n"
    "Before producing the Lean 4 code to formally prove the given theorem, provide a detailed "
    "proof plan outlining the main proof steps and strategies.\n"
    "The plan should highlight key ideas, intermediate lemmas, and proof structures that will "
    "guide the construction of the final formal proof."
)
#: The Lean those models were trained and evaluated on (their READMEs; F17-T9 measured what that
#: costs at the network's pin: 47 of 73 published proofs survive unchanged).
WHOLE_FILE_LEAN = "v4.9"


def version_warning(node: Node, declared: str) -> str | None:
    """F17-R10: a preset's declared Lean against the graph's pin, as one warning or none."""
    pinned = str(node.gate_spec().get("lean_toolchain") or "")
    if declared and declared not in pinned:
        return (
            f"this prover targets Lean {declared}; the graph pins {pinned or 'another toolchain'}. "
            "Renamed lemmas and changed syntax fail at the pin: run `check` before `submit`."
        )
    return None


def run_whole_file(  # noqa: PLR0913 — one keyword per request parameter the endpoint takes
    problem: Path,
    answer: Path,
    *,
    endpoint: str,
    model: str,
    max_tokens: int,
    timeout: float,
    temperature: float = 1.0,
) -> dict[str, Any]:
    """Ask an OpenAI-compatible chat endpoint (vLLM, SGLang, a hosted API) with the shared prompt
    and write the reply to ``answer``; ``import`` takes it from there."""
    started = time.monotonic()
    record: dict[str, Any] = {
        "schema": "opn-prove-run/v1",
        "backend": "whole-file",
        "program": model,
        "started": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeout_s": timeout,
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": WHOLE_FILE_PROMPT.format(problem=problem.read_text(encoding="utf-8")),
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if not endpoint.startswith(("https://", "http://")):
        raise Refused("usage", f"the prover endpoint must be http(s): {endpoint}")
    token = os.environ.get("OPN_PROVER_API_KEY")  # the prover's, never the network's token
    request = urllib.request.Request(  # noqa: S310 — checked above
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": f"{HARNESS}/{VERSION}"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            doc = json.loads(response.read() or b"{}")
        text = doc["choices"][0]["message"]["content"]
        answer.write_text(str(text), encoding="utf-8")
        record.update(exit=0, timed_out=False, stderr_tail="")
    except TimeoutError:
        record.update(exit=None, timed_out=True, stderr_tail="")
    except (urllib.error.URLError, ValueError, KeyError, IndexError) as exc:
        record.update(exit=1, timed_out=False, stderr_tail=f"{type(exc).__name__}: {exc}"[-2000:])
    record["elapsed_s"] = round(time.monotonic() - started, 3)
    record["answered"] = answer.is_file() and bool(answer.read_text(encoding="utf-8").strip())
    return record


# --- the service ----------------------------------------------------------------------------------


def http(
    method: str, url: str, body: dict[str, Any] | None = None, token: str | None = None
) -> tuple[int, dict[str, Any]]:
    if not url.startswith(("https://", "http://")):
        raise Refused("usage", f"the service URL must be http(s): {url}")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)  # noqa: S310 — checked above
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", f"{HARNESS}/{VERSION}")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 — the api URL
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {"error": "unreadable", "message": str(exc)}


TS_FORMAT = "%Y%m%dT%H%M%SZ"  # the stamp of a file under attempts/ (D-3, D-13)


def bundle_path(
    node: Node, kind: str, pseudonym: str | None, now: _dt.datetime | None = None
) -> str:
    """Where the artifact goes: ``Proof.lean`` for a proof, an attempts file for a partial,
    never the other way round (the gate refuses ``artifact-path-mismatch``)."""
    base = f"targets/{node.target_id}/nodes/{node.node_id}"
    if kind == "proof":
        return f"{base}/Proof.lean"
    if not pseudonym:
        raise Refused("usage", "a partial proof's file names its author: give --pseudonym")
    stamp = (now or _dt.datetime.now(_dt.UTC)).strftime(TS_FORMAT)
    return f"{base}/attempts/{stamp}-{pseudonym}-partial.lean"


def check(api: str, node: Node, text: str) -> dict[str, Any]:
    """The fast, non-authoritative check (F13): the text against the node's statement."""
    status, body = http(
        "POST",
        f"{api}/check",
        {"target_id": node.target_id, "node_id": node.node_id, "content": text, "mode": "verify"},
    )
    return {"status": status, **body}


def submit(  # noqa: PLR0913 — one argument per thing a submission names
    api: str,
    node: Node,
    text: str,
    *,
    kind: str,
    model: str,
    token: str,
    pseudonym: str | None = None,
    backend: str = "command",
    poll_s: float = 10.0,
    max_wait_s: float = 1800.0,
) -> dict[str, Any]:
    """Precheck, then submit on a pass: the two calls the guide's HTTP path makes (D-28)."""
    path = bundle_path(node, kind, pseudonym)
    request = {"node_id": node.node_id, "bundle": {path: text}, "artifact_type": kind}
    status, job = http("POST", f"{api}/precheck", request, token)
    if status != 202 or "id" not in job:
        return {"stage": "precheck", "status": status, **job}
    deadline = time.monotonic() + max_wait_s
    while job.get("state") not in ("done", "error"):
        if time.monotonic() > deadline:
            return {"stage": "precheck", "state": job.get("state"), "error": "precheck-timeout"}
        time.sleep(poll_s)
        status, job = http("GET", f"{api}/precheck/{job['id']}", None, token)
    result = job.get("result") or {}
    if job.get("state") != "done" or result.get("verdict") != "pass":
        return {"stage": "precheck", "state": job.get("state"), "result": result}
    submission = {
        "node_id": node.node_id,
        "artifact_type": kind,
        "bundle": {path: text},
        "precheck_job_id": job["id"],
        "tooling": {"model": model, "version": None, "harness": f"{HARNESS}/{backend}"},
    }
    status, body = http("POST", f"{api}/submissions", submission, token)
    return {"stage": "submission", "status": status, **body}


#: F17-R8: how a failed run reads as a postmortem (D-13). A refusal to import that names a
#: helper lemma is the prover telling us a lemma is missing; the rest are routes that dead-ended.
FAILURES = {
    "timeout": ("exhausted", "budget-exhausted"),
    "no-answer": ("abandoned-early", "route-dead-ends"),
    "helper-declaration": ("exhausted", "missing-library"),
    "unimportable": ("exhausted", "route-dead-ends"),
}
DETAIL_MAX = 4000


def postmortem(  # noqa: PLR0913 — one argument per field the record requires
    node: Node,
    run: dict[str, Any],
    contributor: str,
    route_class: str,
    *,
    refusal: dict[str, Any] | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    """A draft ``postmortem/v1`` for a run that produced no admissible proof. It is a draft: the
    route and its class are the contributor's to confirm, and nothing is sent without ``--send``."""
    if run.get("timed_out"):
        key = "timeout"
    elif not run.get("answered"):
        key = "no-answer"
    elif refusal is not None and refusal.get("error") == "helper-declaration":
        key = "helper-declaration"
    else:
        key = "unimportable"
    outcome, failure_class = FAILURES[key]
    program = run.get("program") or "a prover"
    record: dict[str, Any] = {
        "schema": "postmortem/v1",
        "node": f"{node.target_id}/{node.node_id}",
        "contributor": contributor,
        "route": (route or f"automated proof search by {program} on the exported statement")[:500],
        "route_class": route_class,
        "outcome": outcome,
        "failure_class": failure_class,
    }
    elapsed, budget = run.get("elapsed_s"), run.get("timeout_s")
    detail = [f"{HARNESS} run: exit {run.get('exit')}, {elapsed} s of {budget} s"]
    if refusal is not None:
        detail.append(f"import refused: {refusal.get('error')}: {refusal.get('message')}")
    if run.get("stderr_tail"):
        detail.append("prover output (untrusted): " + str(run["stderr_tail"]))
    record["detail"] = "\n".join(detail)[:DETAIL_MAX]
    if key == "helper-declaration" and refusal is not None:
        name = str(refusal.get("message", "")).split(" outside the proof")[0].split()[-1:]
        if name:
            record["artifacts"] = {"missing_lemmas": name}
    return record


def _print(doc: Any) -> None:
    print(json.dumps(doc, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:  # noqa: PLR0911, PLR0912, PLR0915
    # one branch per subcommand, kept in one place so the file stays a single readable script
    parser = argparse.ArgumentParser(prog="opn-prove", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("export", help="the node as one self-contained file with sorry")
    p.add_argument("--graph", type=Path, required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--target")
    p.add_argument("--out", type=Path)
    p.add_argument("--project", type=Path, help="write a Lake project here instead")

    p = sub.add_parser("import", help="a prover's answer as the node's Proof.lean")
    p.add_argument("--graph", type=Path, required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--target")
    p.add_argument("answer", type=Path)
    p.add_argument("--out", type=Path)

    p = sub.add_parser("run", help="run any command as the prover")
    p.add_argument("--problem", type=Path, required=True)
    p.add_argument("--answer", type=Path, required=True)
    p.add_argument(
        "--timeout", type=float, default=float(os.environ.get("OPN_PROVE_TIMEOUT_S", "1800"))
    )
    p.add_argument("--record", type=Path, default=Path("run.json"))
    p.add_argument("--preset", choices=("command", "whole-file"), default="command")
    p.add_argument("--endpoint", help="whole-file: an OpenAI-compatible base URL (vLLM, ...)")
    p.add_argument("--model", help="whole-file: the model name the endpoint serves")
    p.add_argument("--max-tokens", type=int, default=32768)
    p.add_argument("--graph", type=Path, help="for the Lean-version warning (F17-R10)")
    p.add_argument("--node")
    p.add_argument("--target")
    p.add_argument("argv", nargs=argparse.REMAINDER)

    for name, help_ in (
        ("check", "the fast check against the node"),
        ("submit", "precheck, then submit"),
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--api", required=True)
        p.add_argument("--graph", type=Path, required=True)
        p.add_argument("--node", required=True)
        p.add_argument("--target")
        p.add_argument("file", type=Path)
        if name == "submit":
            p.add_argument(
                "--model", required=True, help="the model that produced the proof (D-23)"
            )
            p.add_argument("--kind", choices=("proof", "partial"), default="proof")
            p.add_argument("--pseudonym", help="a partial proof's file names its author")
            p.add_argument("--backend", default="command")

    p = sub.add_parser("postmortem", help="draft a D-13 postmortem for a failed run")
    p.add_argument("--graph", type=Path, required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--target")
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--refusal", type=Path, help="the JSON import printed when it refused")
    p.add_argument("--contributor", required=True)
    p.add_argument("--route-class", required=True)
    p.add_argument("--route")
    p.add_argument("--send", action="store_true")
    p.add_argument("--api")

    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            node = find_node(args.graph, args.node, args.target)
            if args.project:
                path = write_project(node, args.project)
                _print({"ok": True, "project": str(args.project), "problem": str(path)})
                return 0
            text = header_comment(node) + export(node)
            if args.out:
                args.out.write_text(text, encoding="utf-8")
                _print({"ok": True, "problem": str(args.out)})
            else:
                sys.stdout.write(text)
            return 0
        if args.command == "import":
            node = find_node(args.graph, args.node, args.target)
            imported = import_answer(node, args.answer.read_text(encoding="utf-8"))
            out = args.out or Path("Proof.lean" if imported.kind == "proof" else "partial.lean")
            out.write_text(imported.text, encoding="utf-8")
            _print({"ok": True, "kind": imported.kind, "file": str(out), "notes": imported.notes})
            return 0
        if args.command == "run":
            if args.preset == "whole-file":
                if not args.endpoint or not args.model:
                    raise Refused("usage", "the whole-file preset needs --endpoint and --model")
                if args.graph and args.node:
                    node = find_node(args.graph, args.node, args.target)
                    warning = version_warning(node, WHOLE_FILE_LEAN)
                    if warning:
                        print(f"warning: {warning}", file=sys.stderr)
                record = run_whole_file(
                    args.problem,
                    args.answer,
                    endpoint=args.endpoint,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
            else:
                argv_ = [a for a in args.argv if a != "--"]
                if not argv_:
                    raise Refused("usage", "give the prover's command after --")
                record = run_backend(args.problem, args.answer, argv_, args.timeout)
            args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            _print(record)
            return 0 if record["answered"] else 1
        if args.command == "check":
            node = find_node(args.graph, args.node, args.target)
            doc = check(args.api.rstrip("/"), node, args.file.read_text(encoding="utf-8"))
            _print(doc)
            return 0 if doc.get("okay") is True else 1
        if args.command == "submit":
            token = os.environ.get("OPN_TOKEN")
            if not token:
                raise Refused("no-token", "set OPN_TOKEN to your write token (never a flag)")
            node = find_node(args.graph, args.node, args.target)
            doc = submit(
                args.api.rstrip("/"),
                node,
                args.file.read_text(encoding="utf-8"),
                kind=args.kind,
                model=args.model,
                token=token,
                pseudonym=args.pseudonym,
                backend=args.backend,
                poll_s=float(os.environ.get("OPN_PROVE_POLL_S", "10")),
            )
            _print(doc)
            return 0 if doc.get("stage") == "submission" and doc.get("status") in (200, 201) else 1
        if args.command == "postmortem":
            node = find_node(args.graph, args.node, args.target)
            run = json.loads(args.run.read_text(encoding="utf-8"))
            refusal = json.loads(args.refusal.read_text(encoding="utf-8")) if args.refusal else None
            record = postmortem(
                node, run, args.contributor, args.route_class, refusal=refusal, route=args.route
            )
            if not args.send:
                _print({"ok": True, "draft": record, "sent": False})
                return 0
            token = os.environ.get("OPN_TOKEN")
            if not token or not args.api:
                raise Refused("usage", "--send needs --api and OPN_TOKEN")
            status, body = http(
                "POST", f"{args.api.rstrip('/')}/postmortems",
                {"node_id": node.node_id, "yaml": record}, token,
            )  # fmt: skip
            _print({"ok": status in (200, 201), "status": status, **body})
            return 0 if status in (200, 201) else 1
    except Refused as exc:
        _print({"ok": False, "error": exc.code, "message": exc.message})
        return 1
    except OSError as exc:
        _print({"ok": False, "error": "io", "message": str(exc)})
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
