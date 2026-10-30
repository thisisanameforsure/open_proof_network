"""F32-T6 (R8, Q13; AC11): a born-proved hole's page reads proved, and every link to its
``Proof.lean`` names a commit at which the file exists.

The site links a proved node's file at ``proof_commit``, its attestation's merge commit. For a
hole whose proof was carried by a partial, that commit predates the file: the merge commit holds
the assembly and the carried ``.proof`` file, and the post-merge job's bot commit, after it,
writes the hole's node and its ``Proof.lean`` (F32-R4). The products cannot name the bot commit
(it is being made when they are rendered), so the page names its own rendered commit for such a
node: the commit the products derived the hole proved from, which by F03-Q7 holds the file, and
whose bytes are the born ones because no submission may modify a ``Proof.lean``. An ordinary
proof still links at the merge commit that brought it.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
from pathlib import Path

import pytest
from test_cli_sandboxed import Seam
from test_cli_sandboxed import seam as seam  # noqa: PLC0414 — the scripted-docker fixture
from test_finding_carried_proof_postmerge import H1, recorded
from test_partial import ROOT

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
BLOB = re.compile(r'href="' + re.escape(REPO) + r'/blob/(?P<commit>[0-9a-f]{40})/(?P<path>[^"#]+)')


def _exists(root: Path, commit: str, path: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{commit}:{path}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _links(page: str, path: str) -> list[str]:
    return [m["commit"] for m in BLOB.finditer(page) if m["path"] == path]


def test_the_holes_proof_link_names_a_commit_where_the_file_exists(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, merge, bot = recorded(tmp_path, seam, capsys)
    files = render.render_site(model.load_site(root, bot), repo_url=REPO)
    page = files[f"nodes/{TARGET}/{H1}/index.html"]
    assert "Proved by" in page
    proof = f"targets/{TARGET}/nodes/{H1}/Proof.lean"
    commits = _links(page, proof)
    assert commits, "the page links the hole's Proof.lean"
    assert not _exists(root, merge, proof)  # Q13: the merge commit predates the file
    for commit in commits:
        assert _exists(root, commit, proof), commit
    assert set(commits) == {bot}
    # The facts row still says which merge proved it, beside the parent that carried it.
    assert f"<code>{merge[:12]}</code>" in page
    assert f'href="/nodes/{TARGET}/{ROOT}/"' in page


def test_an_ordinary_proof_still_links_at_its_merge_commit(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The rule is for a record whose proof was carried (``carried_by`` set) and nothing else:
    with the hole's record restated as an ordinary proof's, the link is the merge commit's."""
    root, merge, bot = recorded(tmp_path, seam, capsys)
    site = model.load_site(root, bot)
    nv = site.targets[TARGET].nodes[H1]
    assert nv.attestation is not None and nv.attestation["carried_by"]["node_id"] == ROOT
    plain = dataclasses.replace(nv, attestation={**nv.attestation, "carried_by": None})
    renderer = render.Renderer(site, repo_url=REPO)
    assert renderer.proof_file_commit(plain) == merge
    assert renderer.proof_file_commit(nv) == bot
