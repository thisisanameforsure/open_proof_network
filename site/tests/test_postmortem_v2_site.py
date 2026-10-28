"""postmortem/v2 on the site (D-23): a partial named by a v2 postmortem says what drafted the
record, as a literature record's "drafted with" does; a v1 postmortem reads as it always did."""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import samples
import yaml

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
PARENT = "and-swap-reassoc"
MODEL = "claude-opus-5-5 via opn-mcp"


def _label(root: Path) -> str:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = files[f"nodes/propositional/{PARENT}/index.html"]
    for block in re.findall(
        r'<div class="prose-block untrusted" data-block="partial">.*?</p>'
        r'<p class="label">(.*?)</p>',
        page,
        re.S,
    ):
        if "2026-09-01-a-partial.lean" in block:
            return str(block)
    msg = "no partial block"
    raise AssertionError(msg)


def _rewrite_record(root: Path, **overrides: object) -> None:
    path = fixture.nodes_dir(root) / PARENT / "attempts" / "2026-09-01-a.yaml"
    doc = samples.postmortem(
        node=PARENT,
        route_class="case-split",
        artifacts={"partial_proof": "attempts/2026-09-01-a-partial.lean"},
        **overrides,
    )
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_a_v2_postmortem_names_its_declared_model(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _rewrite_record(root, schema="postmortem/v2", model_and_tooling=MODEL)
    label = _label(root)
    assert "by thisisanameforsure, drafted with " + MODEL in label, label
    assert "route class case-split" in label, label


def test_a_v2_postmortem_declaring_no_model_says_nothing_of_one(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _rewrite_record(root, schema="postmortem/v2", model_and_tooling=None)
    label = _label(root)
    assert "by thisisanameforsure" in label and "drafted with" not in label, label


def test_a_v1_postmortem_reads_as_before(tmp_path: Path) -> None:
    label = _label(fixture.curated(tmp_path))
    assert "by thisisanameforsure" in label and "drafted with" not in label, label
    assert "route class case-split" in label, label
