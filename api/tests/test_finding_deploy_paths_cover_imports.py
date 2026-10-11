"""A gate module the service imports redeploys the service when it changes (the audit's
follow-up, 2026-10-04).

``api-deploy.yml`` runs on a push that touches one of its listed paths. The list named gate files
one by one, so a change to a module the service reads — ``layout.py`` since F08-T37,
``exhibits.py`` since F13-T31, ``codes.py`` since F13-T29 — would merge and never reach the
running service. This holds the list to the service's actual imports: every ``opn_gate`` module
the ``opn_api`` package reaches, directly or through other gate modules, must match a path.
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "api-deploy.yml"


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module == "opn_gate":
                found |= {f"opn_gate.{a.name}" for a in node.names}
            elif node.module.startswith("opn_gate."):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {a.name for a in node.names if a.name.startswith("opn_gate.")}
    return found


def gate_modules_the_service_reaches() -> set[Path]:
    """Every gate source file reachable from ``opn_api``'s imports, transitively."""
    pending = set().union(*(_imports(p) for p in (ROOT / "api" / "opn_api").rglob("*.py")))
    files: set[Path] = set()
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        rel = Path("gate", *name.split("."))
        for candidate in (ROOT / rel.with_suffix(".py"), ROOT / rel / "__init__.py"):
            if candidate.is_file():
                files.add(candidate.relative_to(ROOT))
                pending |= _imports(candidate)
    return files


def test_every_gate_module_the_service_imports_redeploys_it() -> None:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True))  # YAML reads a bare `on:` key as True
    patterns = on["push"]["paths"]
    uncovered = sorted(
        str(f)
        for f in gate_modules_the_service_reaches()
        if not any(fnmatch.fnmatch(str(f), p.replace("**", "*")) for p in patterns)
    )
    assert not uncovered, uncovered
