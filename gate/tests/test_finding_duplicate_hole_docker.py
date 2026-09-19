"""Finding "record: duplicate hole", docker tier: the post-merge job in the step-3 sandbox (F07-T7).

The lean tier proves the extractor names the sibling when it can read the probes; this proves it
can read them where the gate runs. The sandbox holds the node under check and the work directory
and nothing else (three sandbox-only failures in the Log), so the probes are staged under the work
directory — and only a run through the container shows the staging reaches it. The shape is the
2026-09-13 live contribution's: a variant beside the tutorial, and a skeleton on the variant whose
first hole is the tutorial's own theorem.

Revised 2026-09-19 (F07-T21, D-12 v3.19): the restated hole is still no ``--h1`` node and the
verdict still names the tutorial as its placement, but it is no edge either. F07-T7 made it a
dependency of the variant; a dependency is what the variant would then wait on, and a decomposition
must not add one (F07-R22, Q29). The edge gave way; the placement and the sandbox staging it proves
did not.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import TARGET, TUTORIAL
from test_cli_sandboxed import NODES, git_repo, run
from test_finding_duplicate_hole import declare_root
from test_finding_duplicate_hole_lean import SKELETON, VARIANT, write_variant_with_skeleton

from opn_gate import cli

pytestmark = pytest.mark.docker


def test_the_sandboxed_post_merge_places_the_restated_hole_on_the_tutorial_without_an_edge(
    sandbox_image: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    write_variant_with_skeleton(root)
    attempt = root / NODES / VARIANT / "attempts" / SKELETON
    skeleton = attempt.read_text(encoding="utf-8")
    attempt.unlink()
    declare_root(root)  # the variant is a second sink until something depends on it (F08-Q19)
    git("add", "-A")
    git("commit", "-q", "-m", "the variant, unproved")
    attempt.write_text(skeleton, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", f"partial: {VARIANT}")

    code, out, err = run(
        capsys,
        "postmerge", "--graph", str(root), "--commit", "HEAD", "--pr", "33", "--target", TARGET,
        "--node", VARIANT, "--review-kind", "pr-approval", "--reviewer", "rev",
        "--out", str(tmp_path / "o"), "--image", sandbox_image,
        "--apply-partial", "--author", "tester",
    )  # fmt: skip
    assert code == cli.EXIT_PASS, (err, out)
    assert out["partial"]["holes"] == [
        {"name": "h₁", "child": None, "reused_node": TUTORIAL},
        {"name": "h₂", "child": f"{VARIANT}--h2", "reused_node": None},
    ]
    nodes = root / NODES
    assert not (nodes / f"{VARIANT}--h1").exists()
    meta = yaml.safe_load((nodes / VARIANT / "META.yaml").read_text(encoding="utf-8"))
    assert meta["deps"] == [f"{VARIANT}--h2"]  # the tutorial is placed, not depended on (T21)
