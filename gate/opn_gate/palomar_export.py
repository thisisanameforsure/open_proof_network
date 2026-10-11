"""The export: one resolved target as a wrapper repository in Palomar's shape (F25-R8 to R10).

Stage A of ``opn-gate export-palomar`` (D-10 v3.37). Pure over the graph tree: it reads the
target, chooses the proof's closure by use (F18), rewrites each Lean file's header for the
module system with every body byte-identical, inlines the target's definitions into the
Challenge, writes the registry's documents from the record, and refuses by name what the
registry would refuse or what would misstate the record. Nothing here runs Lean
(``palomar_check``), talks to a host (``palomar_host``) or shells out (``palomar_port``).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import defs as defsmod
from opn_gate import fidelity as fidelitymod
from opn_gate import graph as graphmod
from opn_gate import intake, layout, ledger, palomar, paths, schemas
from opn_gate.diagnostic import Diagnostic

SITE_URL = "https://openproofnetwork.org/"
GRAPH_URL = "https://github.com/thisisanameforsure/open_proof_network_graph"
EXPORT_RECORD = "opn-export.json"
PREFLIGHT_PATH = ".github/workflows/palomar-preflight.yml"
#: The header the export writes in place of ``import`` lines: Palomar's module system.
SECTION = "@[expose] public section"
_IMPORT_LINE_RE = re.compile(r"^import[ \t]+(?P<module>\S+)[ \t]*$")
_PRIVATE_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?private\s+(?:theorem|lemma|def|abbrev|instance)\b", re.M
)
_DECL_RE = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+)?(?P<kind>def|abbrev|instance|structure|inductive|class)\s+(?P<name>[^\s:({\[]+)",
    re.M,
)
#: F25-Q9: the free ``model_and_tooling`` string of an older merge, read for a method only where
#: the string says it; everything else is ``other`` and the cost is not reconstructed.
METHOD_WORDS: tuple[tuple[str, str], ...] = (
    ("unattended", "autonomous"),
    ("autonomous", "autonomous"),
    ("agent", "agent"),
    ("copilot", "copilot"),
    ("by hand", "manual"),
    ("manual", "manual"),
)
NOT_RECONSTRUCTED = "not reconstructed (the merge predates the structured disclosure, D-23 v3.37)"


class ExportError(Exception):
    """A refusal, carrying the diagnostic the CLI prints."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(f"{diagnostic.code}: {diagnostic.message}")
        self.diagnostic = diagnostic


def refuse(code: str, message: str, details: dict[str, Any] | None = None) -> ExportError:
    return ExportError(Diagnostic(code, message, details or {}))


# --- names -----------------------------------------------------------------------------------


def package_name(target_id: str) -> str:
    """``erdos-1050`` → ``OpnErdos1050``: a Lean identifier, injective over target ids."""
    return "Opn" + "".join(part.capitalize() for part in target_id.split("-"))


def node_module(package: str, node_id: str) -> str:
    """``<Pkg>.Nodes.<id with - replaced by _>``: injective, since ids contain no ``_``."""
    return f"{package}.Nodes.{node_id.replace('-', '_')}"


def node_file(package: str, node_id: str) -> str:
    return f"{package}/Nodes/{node_id.replace('-', '_')}.lean"


def defs_module(package: str, stem: str) -> str:
    return f"{package}.Defs.{stem}"


# --- the closure -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Closure:
    root: str
    order: tuple[str, ...]  # build order: dependencies first, the root last
    pruned: dict[str, dict[str, str]]  # node -> {dep: why}
    kept_by_text: dict[str, tuple[str, ...]]  # node -> deps outside the footprint its text names
    unmeasured: tuple[str, ...]


def select_closure(tg: graphmod.TargetGraph, proof: graphmod.ProofRecord) -> Closure:
    """F25-R10: the proof's footprint closure (F18), plus any declared dependency outside it
    whose declaration the importing proof's text names (kept, never pruned on a guess), in
    build order. A node kept has to be proved."""
    footprint, unmeasured = _footprint_closure(tg, proof)
    members: set[str] = set(footprint)
    pruned: dict[str, dict[str, str]] = {}
    kept: dict[str, tuple[str, ...]] = {}
    stack = sorted(members)
    while stack:
        node_id = stack.pop()
        facts = tg.nodes[node_id]
        text = _proof_text(tg, node_id)
        stripped = layout.strip_comments(text)
        for dep in (*facts.deps, *facts.uses):
            if dep in members or dep not in tg.nodes:
                continue
            decl = _decl_name(tg, dep)
            if decl is not None and _mentions(stripped, decl):
                members.add(dep)
                kept.setdefault(node_id, ())
                kept[node_id] = (*kept[node_id], dep)
                stack.append(dep)
            else:
                pruned.setdefault(node_id, {})[dep] = (
                    f"declared, outside the proof term's footprint, and "
                    f"{decl or 'its declaration'} "
                    "is not named in the proof's text (F18, F25-Q8)"
                )
    for node_id in sorted(members):
        if tg.nodes[node_id].proof is None:
            raise refuse(
                "export-dep-unproved",
                f"{node_id} is in the proof's closure and has no merged Proof.lean",
                {"node": node_id},
            )
    order = _build_order(tg, members, tg.root)
    return Closure(tg.root, tuple(order), pruned, kept, tuple(sorted(unmeasured)))


def _footprint_closure(
    tg: graphmod.TargetGraph, proof: graphmod.ProofRecord
) -> tuple[set[str], set[str]]:
    from opn_gate import products  # noqa: PLC0415 — products imports half the gate

    closure, unmeasured = products.proof_closure(tg, tg.root, proof)
    return set(closure), set(unmeasured)


def _build_order(tg: graphmod.TargetGraph, members: set[str], root: str) -> list[str]:
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        if state.get(node_id) == 2:
            return
        if state.get(node_id) == 1:
            raise refuse("export-dep-cycle", f"dependency cycle through {node_id}")
        state[node_id] = 1
        facts = tg.nodes[node_id]
        for dep in sorted(set((*facts.deps, *facts.uses)) & members):
            visit(dep)
        state[node_id] = 2
        order.append(node_id)

    for node_id in sorted(members - {root}):
        visit(node_id)
    visit(root)
    return order


def _proof_text(tg: graphmod.TargetGraph, node_id: str) -> str:
    path = tg.nodes[node_id].path / "Proof.lean"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _decl_name(tg: graphmod.TargetGraph, node_id: str) -> str | None:
    path = tg.nodes[node_id].path / "Statement.lean"
    if not path.is_file():
        return None
    parsed = layout.parse_statement(path.read_text(encoding="utf-8"))
    return None if isinstance(parsed, Diagnostic) else parsed.decl_name


def _mentions(stripped: str, decl: str) -> bool:
    short = decl.rsplit(".", 1)[-1]
    return (
        re.search(rf"(?<![\w'.])(?:{re.escape(decl)}|{re.escape(short)})(?![\w'])", stripped)
        is not None
    )


# --- the transform ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Header:
    leading: list[str]  # comment and blank lines before the first import, verbatim
    imports: list[str]  # module names, in order
    rest: list[str]  # everything after the header, verbatim (the body)


def split_header(text: str) -> Header:
    """The file's header — leading comments and ``import`` lines — and its body. Comments may
    precede ``module`` in the module system, so they are kept where they are."""
    lines = text.splitlines(keepends=True)
    i, depth = 0, 0
    leading: list[str] = []
    imports: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if depth:
            leading.append(line)
            depth += stripped.count("/-") - stripped.count("-/")
            i += 1
            continue
        if (
            stripped.startswith("/-")
            and not stripped.startswith("/--")
            and not stripped.startswith("/-!")
        ):
            depth = stripped.count("/-") - stripped.count("-/")
            leading.append(line)
            i += 1
            continue
        if stripped.startswith("--") or not stripped:
            if stripped or not imports:
                leading.append(line)
            i += 1
            continue
        m = _IMPORT_LINE_RE.match(stripped)
        if m is not None:
            imports.append(m.group("module"))
            i += 1
            continue
        if stripped == "module" or stripped.startswith("public import ") or stripped == SECTION:
            # already in the module system: an idempotent pass
            if stripped.startswith("public import "):
                imports.append(stripped[len("public import ") :].strip())
            i += 1
            continue
        break
    body = lines[i:]
    while body and not body[0].strip():
        body = body[1:]
    return Header(leading, imports, body)


def transform(  # noqa: PLR0912, PLR0913 — one branch per kind of import line
    text: str,
    *,
    package: str,
    node_id: str | None,
    retained_deps: tuple[str, ...],
    defs_inline: list[tuple[str, str]] | None = None,
    extra_imports: tuple[str, ...] = (),
) -> str:
    """Rewrite one Lean file's header for the module system, the body byte-identical:
    ``module``, ``public import`` per library module, the node's own Context import replaced by
    one ``public import`` per retained dependency, use lines likewise, ``import Defs.X`` as the
    package's definition module (or inlined, for the Challenge), then ``@[expose] public
    section`` and the body. Idempotent on a file already in this shape."""
    header = split_header(text)
    modules: list[str] = []
    inlined = {m for m, _ in defs_inline} if defs_inline else set()
    for module in header.imports:
        kind, dep_id = layout.module_origin(module)
        if kind == "library":
            modules.append(module)
        elif kind == "defs":
            stem = module.partition(".")[2]
            if defs_module(package, stem) not in inlined and module not in inlined:
                modules.append(defs_module(package, stem))
        elif kind == "node" and dep_id is not None:
            if node_id is not None and module == layout.node_module(node_id, "Context"):
                modules.extend(node_module(package, d) for d in retained_deps)
            elif layout.used_node(module) is not None:
                modules.append(node_module(package, dep_id))
            else:
                raise refuse(
                    "export-import-foreign",
                    f"{module} is not a module the export can carry",
                    {"module": module},
                )
        elif module.startswith(package + "."):
            modules.append(module)  # already transformed
        else:
            raise refuse(
                "export-import-foreign",
                f"{module} is neither a library, a definition nor a node module",
                {"module": module},
            )
    modules.extend(m for m in extra_imports if m not in modules)
    ordered: list[str] = []
    for m in modules:
        if m not in ordered:
            ordered.append(m)
    out: list[str] = []
    leading = [ln for ln in header.leading if ln.strip() != "module"]
    out.extend(leading)
    if out and out[-1].strip():
        out.append("\n")
    out.append("module\n\n")
    for module in ordered:
        out.append(f"public import {module}\n")
    if ordered:
        out.append("\n")
    if defs_inline:
        for module, source in defs_inline:
            out.append(
                f"-- inlined by the network from {module} (F13-R5, F25-R8)\n{source.rstrip()}\n\n"
            )
    out.append(SECTION + "\n\n")
    body = "".join(header.rest)
    out.append(body if body.endswith("\n") or not body else body + "\n")
    return "".join(out)


def strip_imports(source: str) -> str:
    """A definition's source without its import lines, for inlining."""
    return "".join(
        line
        for line in source.splitlines(keepends=True)
        if _IMPORT_LINE_RE.match(line.strip()) is None
    ).strip("\n")


# --- the export --------------------------------------------------------------------------------


@dataclass
class Export:
    target_id: str
    package: str
    root: str
    decl: str
    closure: Closure
    files: dict[str, bytes] = field(default_factory=dict)
    record: dict[str, Any] = field(default_factory=dict)

    def write(self, out: Path) -> None:
        for rel, data in self.files.items():
            path = out / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


def export(  # noqa: PLR0912, PLR0915 — one refusal per rule, in the order the record is read
    graph_root: Path,
    target_id: str,
    *,
    graph_commit: str,
    licence: str | None = None,
    today: dt.date | None = None,
) -> Export:
    """Stage A (F25-R8): the wrapper repository's files, in memory, or a refusal (R9).

    ``licence`` names the SPDX identifier of the graph's root licence when the graph commit has
    no ``LICENSE`` file yet (F25-Q15: the rehearsal before the owner's commit); the record says
    where it came from."""
    tg = graphmod.load_target(graph_root, target_id)
    root = tg.root
    if tg.statuses.get(root) != "proved":
        raise refuse(
            "export-root-unproved",
            f"{root} is {tg.statuses.get(root)}; only a proved root is exported",
            {"status": tg.statuses.get(root)},
        )
    facts = tg.nodes[root]
    if not facts.proofs or facts.proofs[0].kind != "proof" or facts.proof is None:
        raise refuse(
            "export-proof-kind", f"{root} has no merged Proof.lean of kind proof to export"
        )
    proof = facts.proofs[0]
    attestations = dict(graphmod.load_attestations(graph_root))
    att = attestations.get(proof.attestation)
    if att is None:
        raise refuse(
            "export-attestation-missing", f"attestation {proof.attestation} is not on the graph"
        )
    target_dir = tg.path
    doc = intake.load_doc(target_dir)
    classification = intake.classification(doc)
    if classification is None:
        raise refuse(
            "export-classification-missing",
            f"{target_id}'s target.yaml carries no classification (arxiv and msc2020); add one "
            f"with intake new --arxiv --msc or a curator record (F25-R4)",
        )
    licence_source = "graph"
    if (graph_root / "LICENSE").is_file():
        spdx = _spdx_of((graph_root / "LICENSE").read_text(encoding="utf-8", errors="replace"))
    elif licence is not None:
        spdx, licence_source = licence, "flag"
    else:
        raise refuse(
            "export-licence-missing",
            "the graph commit has no root LICENSE file; the registry reads one SPDX identifier "
            "from it (D-23 v3.37), or pass --licence for a rehearsal",
        )
    if spdx != "Apache-2.0":
        raise refuse(
            "export-licence-unsupported",
            f"the graph's licence reads as {spdx}; the wrapper ships Apache-2.0 and the export "
            f"carries no other",
            {"licence": spdx},
        )
    closure = select_closure(tg, proof)
    for node_id in closure.order:
        node_dir = tg.nodes[node_id].path
        if (node_dir / paths.WAIVER_PATH).is_file():
            raise refuse(
                "export-trust-base-compiler",
                f"{node_id} carries a native_decide waiver; its proof rests on the compiler, "
                f"which the registry refuses",
                {"node": node_id},
            )
        node_att = _attestation_for(attestations, tg.nodes[node_id])
        if node_att is not None and node_att.get("trust_base") == "compiler":
            raise refuse(
                "export-trust-base-compiler",
                f"{node_id}'s attestation records trust_base compiler",
                {"node": node_id},
            )
    package = package_name(target_id)
    statement = layout.parse_statement((facts.path / "Statement.lean").read_text(encoding="utf-8"))
    if isinstance(statement, Diagnostic):
        raise refuse("export-statement-shape", statement.message)
    definitions = defsmod.order(target_dir)
    if isinstance(definitions, Diagnostic):
        raise refuse(definitions.code, definitions.message)
    inline = [(d.module, strip_imports(d.source.read_text(encoding="utf-8"))) for d in definitions]
    definition_names = [name for _, src in inline for name in _definition_names(src)]
    files: dict[str, bytes] = {}
    hashes_in: dict[str, str] = {}
    # Challenge: the statement, definitions inlined, own Context dropped (the deps are theorems
    # the Challenge does not state), the module system's header.
    challenge = transform(
        statement.text, package=package, node_id=root, retained_deps=(), defs_inline=inline
    )
    _check_no_private(challenge, "Challenge.lean")
    files["Challenge.lean"] = challenge.encode("utf-8")
    hashes_in["Challenge.lean"] = _sha(statement.text.encode("utf-8"))
    problems = palomar.challenge_problems(files["Challenge.lean"])
    if problems:
        raise refuse("export-cap", "; ".join(problems))
    # Definitions as modules, byte-identical bodies.
    for d in definitions:
        src = d.source.read_text(encoding="utf-8")
        rel = f"{package}/Defs/{d.source.stem}.lean"
        files[rel] = transform(src, package=package, node_id=None, retained_deps=()).encode("utf-8")
        hashes_in[rel] = _sha(src.encode("utf-8"))
    # Nodes of the closure, the root as Solution.
    for node_id in closure.order:
        src = _proof_text(tg, node_id)
        if layout.mentions_sorry(src):
            raise refuse(
                "export-sorry",
                f"{node_id}'s Proof.lean mentions sorry outside a comment",
                {"node": node_id},
            )
        node_facts = tg.nodes[node_id]
        retained = tuple(
            d for d in (*node_facts.deps, *node_facts.uses) if d in closure.order and d != node_id
        )
        rel = "Solution.lean" if node_id == root else node_file(package, node_id)
        text = transform(src, package=package, node_id=node_id, retained_deps=_dedupe(retained))
        if node_id != root:
            _check_no_private(text, rel)
        files[rel] = text.encode("utf-8")
        hashes_in[rel] = _sha(src.encode("utf-8"))
        cap = palomar.file_problems(files[rel], rel)
        if cap:
            raise refuse("export-cap", "; ".join(cap))
    # The library root: every development module, public.
    dev_modules = [defs_module(package, d.source.stem) for d in definitions] + [
        node_module(package, n) for n in closure.order if n != root
    ]
    files[f"{package}.lean"] = (
        "module\n\n" + "".join(f"public import {m}\n" for m in dev_modules)
    ).encode("utf-8")
    spec = tg.spec
    files["lean-toolchain"] = (str(spec["lean_toolchain"]) + "\n").encode("utf-8")
    files["lakefile.toml"] = lakefile(package, spec.get("mathlib_sha")).encode("utf-8")
    files["lake-manifest.json"] = manifest(package, spec.get("mathlib_sha")).encode("utf-8")
    files["LICENSE"] = palomar.licence_text().encode("utf-8")
    comparator = palomar.ComparatorDoc(
        challenge_module="Challenge",
        solution_module="Solution",
        theorem_names=(statement.decl_name,),
        definition_names=tuple(definition_names),
        permitted_axioms=tuple(spec.get("axiom_allowlist") or palomar.pins()["permitted_axioms"]),
    )
    files["comparator.json"] = palomar.write_comparator(comparator).encode("utf-8")
    meta = formalization_doc(
        graph_root, tg, doc or {}, classification, closure, proof, att, attestations,
        decl=statement.decl_name, package=package, today=today,
    )  # fmt: skip
    files["formalization.yaml"] = palomar.write_formalization(meta).encode("utf-8")
    pins = palomar.pins()
    files[PREFLIGHT_PATH] = preflight_workflow(target_id, pins).encode("utf-8")
    record: dict[str, Any] = {
        "schema": "opn-export/v1",
        "target_id": target_id,
        "package": package,
        "graph_commit": graph_commit,
        "root": root,
        "declaration": statement.decl_name,
        "statement_hash": facts.statement_hash,
        "attestation": proof.attestation,
        "merge_commit": proof.merge_commit,
        "lean_toolchain": spec["lean_toolchain"],
        "mathlib_sha": spec.get("mathlib_sha"),
        "closure": list(closure.order),
        "pruned": closure.pruned,
        "kept_by_text": {k: list(v) for k, v in closure.kept_by_text.items()},
        "unmeasured": list(closure.unmeasured),
        "licence": {"spdx": spdx, "source": licence_source},
        "module_system": True,
        "headers": "rewritten for the module system; every body byte-identical to the graph's "
        "(opn-export hashes_in are the graph's files, hashes_out the wrapper's)",
        "hashes_in": hashes_in,
        "hashes_out": {},
        "registry_pins_observed": pins["observed"],
    }
    readme = readme_text(
        tg,
        doc or {},
        closure,
        proof,
        meta,
        decl=statement.decl_name,
        package=package,
        graph_commit=graph_commit,
        inline=inline,
        licence_source=licence_source,
    )
    files["README.md"] = readme.encode("utf-8")
    record["hashes_out"] = {rel: _sha(data) for rel, data in sorted(files.items())}
    files[EXPORT_RECORD] = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return Export(target_id, package, root, statement.decl_name, closure, files, record)


def _dedupe(items: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for x in items:
        if x not in out:
            out.append(x)
    return tuple(out)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _spdx_of(text: str) -> str:
    head = text[:400]
    if "Apache License" in head and "Version 2.0" in head:
        return "Apache-2.0"
    if "MIT License" in head:
        return "MIT"
    return "unknown"


def _attestation_for(
    attestations: dict[str, dict[str, Any]], facts: graphmod.NodeFacts
) -> dict[str, Any] | None:
    if not facts.proofs:
        return None
    return attestations.get(facts.proofs[0].attestation)


def _definition_names(source: str) -> list[str]:
    names: list[str] = []
    for m in _DECL_RE.finditer(layout.strip_comments(source)):
        if m.group("kind") in ("def", "abbrev"):
            names.append(m.group("name"))
    return names


def _check_no_private(text: str, rel: str) -> None:
    if _PRIVATE_RE.search(layout.strip_comments(text)):
        raise refuse(
            "export-private-helper",
            f"{rel} declares a private helper; under the module system another module cannot "
            f"see it",
            {"file": rel},
        )


# --- lakefile, manifest, workflow ------------------------------------------------------------


def lakefile(package: str, mathlib_sha: str | None) -> str:
    require = (
        f'[[require]]\nname = "mathlib"\nscope = "leanprover-community"\nrev = "{mathlib_sha}"\n\n'
        if mathlib_sha
        else ""
    )
    return (
        f'name = "{package}"\n'
        f'defaultTargets = ["{package}", "Challenge", "Solution"]\n\n'
        "[leanOptions]\nautoImplicit = false\n\n"
        + require
        + f'[[lean_lib]]\nname = "{package}"\n\n'
        '[[lean_lib]]\nname = "Challenge"\nroots = ["Challenge"]\n\n'
        '[[lean_lib]]\nname = "Solution"\nroots = ["Solution"]\n'
    )


def manifest(package: str, mathlib_sha: str | None) -> str:
    """A minimal committed manifest: Mathlib at the graph's pin. Stage B's ``lake update``
    completes it with Mathlib's own dependencies at the registry's revision."""
    packages = (
        [
            {
                "url": "https://github.com/leanprover-community/mathlib4",
                "type": "git",
                "subDir": None,
                "scope": "leanprover-community",
                "rev": mathlib_sha,
                "name": "mathlib",
                "manifestFile": "lake-manifest.json",
                "inputRev": mathlib_sha,
                "inherited": False,
                "configFile": "lakefile.lean",
            }
        ]
        if mathlib_sha
        else []
    )
    return (
        json.dumps(
            {
                "version": "1.1.0",
                "packagesDir": ".lake/packages",
                "packages": packages,
                "name": package,
                "lakeDir": ".lake",
            },
            indent=2,
        )
        + "\n"
    )


def preflight_workflow(target_id: str, pins: dict[str, Any]) -> str:
    template = (palomar.PALOMAR_DIR / "preflight.workflow.template.yml").read_text(encoding="utf-8")
    sha = str(pins["repositories"]["PalomarRegistry/PalomarSubmission"]["commit"])
    return (
        template.replace("{{PIPELINE_SHA}}", sha)
        .replace("{{TARGET_ID}}", target_id)
        .replace("{{PINS_OBSERVED}}", str(pins["observed"]))
    )


# --- formalization.yaml from the record ------------------------------------------------------


def authors(graph_root: Path, target_id: str, closure: Closure) -> list[str]:
    """D-19 v3.37: the ledger identities on the statement and proof lines of the closure's
    nodes, each by its display name where one is recorded (``names/<pseudonym>.yaml``), else
    its pseudonym; first credited first; the registering curator is not an author by that act."""
    found: list[str] = []
    for identity, entries in ledger.contributions(graph_root).items():
        for e in entries:
            if (
                e.get("target") == target_id
                and e.get("line") in ("statement", "proof")
                and e.get("node") in closure.order
                and e.get("status") == "active"
            ):
                if identity not in found:
                    found.append(identity)
                break
    return [display_name(graph_root, p) or p for p in found]


def display_name(graph_root: Path, pseudonym: str) -> str | None:
    """The latest ``names/<pseudonym>.yaml``'s name, or ``None`` (F25-R6; the T4 reader,
    ``names.display_name``, is the same rule over the same file)."""
    path = graph_root / "names" / f"{pseudonym}.yaml"
    if not path.is_file():
        return None
    try:
        doc = schemas.load_yaml(path, "display-name/v1")
    except schemas.SchemaError:
        return None
    name = doc.get("name")
    return str(name) if isinstance(name, str) and name.strip() else None


def method_from_string(declared: str) -> dict[str, Any]:
    """F25-Q9: an older merge's free string as a Palomar method, honestly."""
    low = declared.lower()
    method = next((m for word, m in METHOD_WORDS if word in low), "other")
    return {
        "method": method,
        "models": [declared] if declared and declared != ledger.UNDECLARED else [],
        "prompting_notes": NOT_RECONSTRUCTED,
    }


def automation_methods(
    attestations: dict[str, dict[str, Any]], tg: graphmod.TargetGraph, closure: Closure
) -> tuple[list[dict[str, Any]], bool]:
    """One method per closure proof: the attestation's structured block where it has one, else
    the string mapped (Q9). The flag says whether every method came from a structured block."""
    out: list[dict[str, Any]] = []
    all_structured = True
    seen: set[str] = set()
    for node_id in closure.order:
        att = _attestation_for(attestations, tg.nodes[node_id])
        if att is None:
            continue
        block = att.get("automation")
        if isinstance(block, dict):
            method = {
                "method": block["method"],
                "models": list(block["models"]),
                "framework": block["framework"],
            }
            if block.get("tool_setup"):
                method["tool_setup"] = block["tool_setup"]
            cost: dict[str, Any] = {}
            if block.get("wall_time"):
                cost["wall_time"] = block["wall_time"]
            if block.get("hardware"):
                cost["hardware"] = block["hardware"]
            if block.get("spend"):
                cost["spend_usd"] = block["spend"]
            if cost:
                method["cost"] = cost
            if block.get("tokens"):
                method["prompting_notes"] = (
                    f"tokens: {block['tokens']['input']} in, {block['tokens']['output']} out "
                    f"({node_id})"
                )
        else:
            all_structured = False
            method = method_from_string(str(att.get("model_and_tooling") or ledger.UNDECLARED))
        key = json.dumps(method, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(method)
    if not out:
        out.append({"method": "other", "models": [], "prompting_notes": NOT_RECONSTRUCTED})
    return out, all_structured


def sources_doc(
    record: dict[str, Any], *, known_result: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Palomar's ``sources`` and ``related_formalizations`` from ``target.yaml``: a newly
    resolved open problem is an ``original-proof`` with the problem's page as background; a
    known result is ``independently-proves`` against its catalog entry; the inherited
    formal statement is a related formalization (``builds-on``)."""
    src = record.get("source") or {}
    title = str(record.get("title") or record.get("id") or "the problem")
    url = src.get("url")
    prior = (record.get("prior_art") or {}).get("summary")
    sources: list[dict[str, Any]] = []
    related: list[dict[str, Any]] = []
    forum = (record.get("prior_art") or {}).get("forum_url")
    page: dict[str, Any] = {"title": title, "type": "web discussion" if forum or url else "other"}
    if forum:
        page["id"] = str(forum)
    elif url and src.get("kind") != "formal-conjectures":
        page["id"] = str(url)
    if prior:
        page["note"] = str(prior)[:1000]
    if known_result:
        page["relationship"] = "independently-proves"
        page["note"] = (
            page.get("note", "")
            + " The result is known; the network's proof is an independent one, and the "
            "published proof the catalog cites is not on the network's record."
        ).strip()
        sources.append(page)
    else:
        sources.append(
            {
                "title": f"A proof of {title}",
                "type": "original-proof",
                "relationship": "other",
                "note": "First presented by this formalization, on the Open Proof Network's "
                "graph (kernel-checked; the network does not referee the mathematics).",
            }
        )
        page["relationship"] = "background"
        sources.append(page)
    for s in record.get("sources") or []:
        if s.get("kind") == "formal-conjectures" and s.get("url"):
            related.append(
                {
                    "id": str(s["url"]),
                    "relationship": "builds-on",
                    "note": "The formal statement was inherited from Formal Conjectures at this "
                    "commit (D-10); the network's root statement is that file's affirmative "
                    "reading.",
                }
            )
    if src.get("kind") == "formal-conjectures" and src.get("url") and not related:
        related.append(
            {
                "id": str(src["url"]),
                "relationship": "builds-on",
                "note": "The formal statement was inherited from Formal Conjectures (D-10).",
            }
        )
    return sources, related


def formalization_doc(  # noqa: PLR0913, PLR0917 — one argument per record the document is built from
    graph_root: Path,
    tg: graphmod.TargetGraph,
    record: dict[str, Any],
    classification: dict[str, Any],
    closure: Closure,
    proof: graphmod.ProofRecord,
    att: dict[str, Any],
    attestations: dict[str, dict[str, Any]],
    *,
    decl: str,
    package: str,
    today: dt.date | None,
) -> palomar.Formalization:
    target_id = tg.target_id
    curator = str(record.get("curator") or "")
    names = authors(graph_root, target_id, closure)
    if not names:
        names = [curator or "the Open Proof Network"]
    grade = fidelitymod.target_grade(tg.path) or "mechanical-only"
    signers: list[str] = []
    for subject, certs in fidelitymod.load(tg.path).items():
        if subject == tg.root:
            signers = list(fidelitymod.signers_of(certs))
    known = (
        str(record.get("track")) == "formalization"
        or intake.is_calibration(record)
        or (
            tg.statuses.get(tg.root) == "proved"
            and str(tg.declaration.status if tg.declaration else "") == "known-result"
        )
    )
    sources, related = sources_doc(record, known_result=known)
    methods, structured = automation_methods(attestations, tg, closure)
    axioms = list(tg.spec.get("axiom_allowlist") or palomar.pins()["permitted_axioms"])
    sections: dict[str, Any] = {
        "version": palomar.FORMALIZATION_VERSION,
        "project": {
            "name": str(record.get("title") or target_id),
            "description": str(record.get("informal") or "").strip()
            or f"The network's resolution of {target_id}.",
            "authors": names,
            "license": "Apache-2.0",
            "responsible_maintainers": [curator] if curator else names[:1],
        },
        "repository": {"role": "substantive-development"},
        "classification": {
            "arxiv": list(classification["arxiv"]),
            "msc2020": list(classification["msc2020"]),
        },
        "sources": sources,
        "status": {
            "scope": f"{decl} is proved in full; the development holds the "
            f"{len(closure.order) - 1} merged proof(s) its term rests on and nothing else "
            f"(F18).",
            "sorry_count": 0,
            "sorry_in_definitions": 0,
            "axioms": axioms,
            "main_results": [
                {
                    "declaration": decl,
                    "file": "Solution.lean",
                    "sorry_count": 0,
                    "axioms": axioms,
                    "comparator_config": "comparator.json",
                }
            ],
        },
        "automation": {
            "methods": methods,
            "spend_usd": "subscription-based usage where disclosed; "
            + (
                "every method declared at submission (D-23 v3.37)"
                if structured
                else NOT_RECONSTRUCTED
            ),
            "notes": f"Each method is one merged proof's disclosure as its submitter declared "
            f"it to the Open Proof Network (never verified, D-1); the ledger on the graph "
            f"at the exported commit is the record. The registering curator "
            f"({curator or 'unnamed'}) prepared this wrapper with the network's "
            f"export tool and wrote no Lean.",
        },
        "fidelity": {
            "divergences": f"The network's fidelity grade of the root statement is `{grade}` "
            f"(D-9); "
            + (
                "no human has read the formal statement against the informal one on the "
                "network's record."
                if grade == "mechanical-only"
                else f"signed by {', '.join(signers) or 'the record'}."
            )
            + " Challenge.lean is the graph's Statement.lean with its headers rewritten for the "
            "module system; the export checks the theorem text is identical.",
        },
        "review": {
            "status": "agent-reviewed" if grade == "mechanical-only" else "author-verified",
            "reviewers": signers,
            "notes": f"The gate checked the proof mechanically at {tg.spec['lean_toolchain']} "
            f"(kernel replay per module, the three standard axioms, the statement's type by "
            f"the kernel); fidelity grade {grade}. No independent human has reviewed "
            f"the proof unless named above.",
        },
        "alignment": {
            "namespace": package,
            "statements": [
                {
                    "source": str(record.get("title") or target_id),
                    "lean": decl,
                    "module": "Solution",
                    "status": "proved",
                    "note": "the root statement; the node's Statement.lean on the graph",
                }
            ]
            + [
                {
                    "source": f"node {n} on the graph",
                    "lean": _decl_name(tg, n) or n,
                    "module": node_module(package, n),
                    "status": "proved",
                    "note": "a statement the root's proof term rests on",
                }
                for n in closure.order
                if n != tg.root
            ],
        },
        "acknowledgements": "Mathlib and its authors; the Open Proof Network's contributors "
        "named above; the Formal Conjectures authors where the statement was inherited.",
    }
    if related:
        sections["related_formalizations"] = related
    return palomar.Formalization(sections)


# --- README ------------------------------------------------------------------------------------


def readme_text(  # noqa: PLR0913 — one argument per section the account draws on
    tg: graphmod.TargetGraph,
    record: dict[str, Any],
    closure: Closure,
    proof: graphmod.ProofRecord,
    meta: palomar.Formalization,
    *,
    decl: str,
    package: str,
    graph_commit: str,
    inline: list[tuple[str, str]],
    licence_source: str,
) -> str:
    template = (palomar.PALOMAR_DIR / "README.template.md").read_text(encoding="utf-8")
    rows = ["| module | graph node | theorem |", "|---|---|---|"]
    for n in closure.order:
        if n == tg.root:
            continue
        rows.append(f"| `{node_module(package, n)}` | `{n}` | `{_decl_name(tg, n) or '?'}` |")
    if len(rows) == 2:
        rows = ["(the proof rests on no other node)"]
    srcs = []
    for s in meta.sections.get("sources") or []:
        srcs.append(
            f"- {s.get('title')} "
            f"({s.get('relationship')})"
            f"{': ' + s['id'] if s.get('id') else ''}"
            f"{' — ' + s['note'] if s.get('note') else ''}"
        )
    for r in meta.sections.get("related_formalizations") or []:
        srcs.append(f"- related formalization ({r.get('relationship')}): {r.get('id')}")
    methods = meta.sections["automation"]["methods"]
    production = [
        f"- method `{m.get('method')}`"
        + (f", models {', '.join(m.get('models') or [])}" if m.get("models") else "")
        + (f", framework {m['framework']}" if m.get("framework") else "")
        + (f"; cost: {m['cost']}" if m.get("cost") else "")
        for m in methods
    ]
    production.append(f"- {meta.sections['automation']['notes']}")
    gaps = [f"- Fidelity: {meta.sections['fidelity']['divergences']}"]
    for node, deps in closure.pruned.items():
        for dep, why in deps.items():
            gaps.append(
                f"- `{node}` declares `{dep}` on the graph; it is not in this wrapper: {why}."
            )
    if closure.unmeasured:
        gaps.append(
            f"- Footprints not measured for: {', '.join(closure.unmeasured)}; the closure "
            f"followed their declared dependencies instead (wider, never narrower)."
        )
    gaps.append(
        "- `Witness.lean` files (the network's non-vacuity witnesses) are not exported; they "
        "are not part of the proof term."
    )
    if licence_source == "flag":
        gaps.append(
            "- The licence was supplied to the export by flag: the graph commit carried no root "
            "LICENSE file yet."
        )
    if not all(m.get("framework") for m in methods):
        gaps.append(f"- Cost and method for merges before D-23 v3.37: {NOT_RECONSTRUCTED}.")
    defs_sentence = (
        f", with the target's definitions ({', '.join(m for m, _ in inline)}) inlined verbatim"
        if inline
        else ""
    )
    filled = (
        template.replace("{{TITLE}}", str(record.get("title") or tg.target_id))
        .replace("{{SITE_URL}}", SITE_URL)
        .replace("{{GRAPH_COMMIT}}", graph_commit)
        .replace("{{TARGET_ID}}", tg.target_id)
        .replace("{{INFORMAL}}", str(record.get("informal") or "").strip())
        .replace("{{DECL}}", decl)
        .replace("{{DEFS_SENTENCE}}", defs_sentence)
        .replace("{{ROOT}}", tg.root)
        .replace("{{ATTESTATION}}", proof.attestation.removesuffix(".json"))
        .replace("{{PACKAGE}}", package)
        .replace("{{CLOSURE_TABLE}}", "\n".join(rows))
        .replace("{{SOURCES}}", "\n".join(srcs) or "(none on the record)")
        .replace("{{PRODUCTION}}", "\n".join(production))
        .replace("{{LEAN_TOOLCHAIN}}", str(tg.spec["lean_toolchain"]))
        .replace("{{MATHLIB_SHA}}", str(tg.spec.get("mathlib_sha") or "none (Lean core)"))
        .replace("{{GAPS}}", "\n".join(gaps))
    )
    return filled
