"""F19 fixture trees for the outline and reading-view tests and for the evidence script.

``outlined_tutorial`` rewrites the tutorial node's proof into ``site_outlines.TUTORIAL_PROOF``,
attests it and files its hand-written outline. ``shoot_tree`` adds prose carrying TeX, for the
screenshots (engineering/evidence/F19/shoot.py).
"""

from __future__ import annotations

from pathlib import Path

import fixture
import samples
import site_outlines as so
from harness import TARGET, copy_graph

from opn_gate import products, schemas

COMMIT = fixture.COMMIT
REPO = "https://github.com/example/graph"
TUTORIAL = "tutorial-and-swap"
EXPLAINER_WITH_MATH = (
    "---\nauthor: alice\nmodel: claude-fable-5-1\ndate: 2026-10-04\n---\n"
    "The statement swaps a conjunction: from $p \\land q$ it builds $q \\land p$.\n\n"
    "Both halves come from the hypothesis, so $$\\frac{p \\land q}{q \\land p}$$ is one rule.\n\n"
    "The Lean names them `h.1` and `h.2`; a dollar in code, `$x$`, stays text.\n"
)
ANNEX_WITH_MATH = "An informal sketch: $p \\land q \\to q \\land p$ by cases.\n"


def outlined_tutorial(tmp_path: Path) -> tuple[Path, str]:
    """The fixture graph with the tutorial's proof rewritten and attested, and its outline filed;
    returns the root and the proof's sha256 (its ``artifact_hash``). Products are not written."""
    root = copy_graph(tmp_path, publish=True)
    proof = fixture.nodes_dir(root) / TUTORIAL / "Proof.lean"
    proof.write_text(so.TUTORIAL_PROOF, encoding="utf-8")
    fixture.attest(root, TUTORIAL, 1, steps=[*samples.attestation()["steps"], fixture.WITNESS_STEP])
    digest = schemas.content_hash(proof.read_bytes())
    so.write(root, so.document(TUTORIAL, "Proof.lean", digest, so.tutorial_steps()))
    return root, digest


def write_products(root: Path) -> None:
    products.generate(root, rendered_from=COMMIT, commit_time=fixture.NOW).write(root)


def shoot_tree(tmp_path: Path) -> tuple[Path, list[str]]:
    """The tree the evidence script renders, and the site paths it captures."""
    root, _ = outlined_tutorial(tmp_path)
    node = fixture.nodes_dir(root) / TUTORIAL
    (node / "explainer" / "why.md").write_text(EXPLAINER_WITH_MATH, encoding="utf-8")
    (node / "annex" / "sketch.md").write_text(ANNEX_WITH_MATH, encoding="utf-8")
    write_products(root)
    return root, [f"/nodes/{TARGET}/{TUTORIAL}/"]
