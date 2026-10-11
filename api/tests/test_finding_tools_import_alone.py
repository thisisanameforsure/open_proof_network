"""F22-T5 follow-up: every ``api/tools`` script starts on its own, as the deploy runs it.

The api-deploy of 2026-10-06 (ad6caf2) deployed the service, passed the HTTP smoke, and then went
red in ``smoke_mcp.py`` with ``No module named 'opn_site'``: F22-T5 made ``opn_api.glosses`` render
its dry-run preview with the site's prose module, the Lambda package and the deploy check learned
to carry ``site/``, and the tools that put ``api`` and ``gate`` on ``sys.path`` themselves did not.
The test suite could not see it, because pytest puts every package on the path. Each tool is run
here with ``--help`` in a fresh interpreter with no ``PYTHONPATH``, which is how the workflow runs
it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


@pytest.mark.parametrize("tool", sorted(p.name for p in TOOLS.glob("*.py")))
def test_the_tool_imports_with_no_path_set(tool: str) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run(
        [sys.executable, str(TOOLS / tool), "--help"],
        capture_output=True, text=True, check=False, env=env, timeout=120,
    )  # fmt: skip
    assert "ModuleNotFoundError" not in proc.stderr, proc.stderr[-800:]
