"""F08-T36 (D-16 v3.28): a statement's page shows every open defect claim against it.

The page names each standing claim's class, links its file on the graph at the rendered commit
(``file_link``, never a literal hostname) and says "claim open"; a claim a curator has accepted
for adjudication by a ``disputed`` record (D-18 v3.28, F08-T35) also says "disputed". A withdrawn
claim is not open, so the page does not show it (``graph.json`` still lists it). A node with no
claim renders exactly as before.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import samples
import yaml
from fixture import COMMIT, NOW, curated, nodes_dir

from opn_gate import curator, products
from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
NODE = "and-swap-reassoc"
OPEN = "20261003T120000Z-alice.yaml"
GONE = "20261002T120000Z-bob.yaml"
PAGE = f"nodes/{TARGET}/{NODE}/index.html"


def claimed(tmp_path: Path, *, accept: bool = False) -> dict[str, str]:
    root = curated(tmp_path)
    defects = nodes_dir(root) / NODE / "defects"
    defects.mkdir(parents=True)
    doc = samples.defect_claim(stmt_ref=NODE, **{"class": "wrong-domain"})
    (defects / OPEN).write_text(yaml.safe_dump(doc), encoding="utf-8")
    (defects / GONE).write_text(yaml.safe_dump(samples.defect_claim(stmt_ref=NODE)), "utf-8")
    withdrawals = nodes_dir(root) / NODE / "withdrawals"
    withdrawals.mkdir()
    (withdrawals / "20261004T110000Z-founder.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "withdrawal/v1",
                "withdraws": f"defects/{GONE}",
                "reason": "never reached",
                "author": "founder",
                "date": "2026-10-04",
            }
        ),
        encoding="utf-8",
    )
    if accept:
        curator.declare_status(
            root,
            TARGET,
            NODE,
            "disputed",
            "ground (i) accepted",
            author="founder",
            date="2026-10-04T12:00:00Z",
            now=datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC),
            reference=f"defects/{OPEN}",
        )
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO)


def test_an_open_claim_is_shown_with_its_class_and_file(tmp_path: Path) -> None:
    page = claimed(tmp_path)[PAGE]
    link = f"{REPO}/blob/{COMMIT}/targets/{TARGET}/nodes/{NODE}/defects/{OPEN}"
    assert "claim open" in page
    assert "wrong-domain" in page
    assert f'href="{link}"' in page
    assert GONE not in page  # withdrawn: not open
    assert "disputed" not in page.split('<pre class="lean statement', 1)[0]


def test_an_accepted_claim_says_disputed(tmp_path: Path) -> None:
    page = claimed(tmp_path, accept=True)[PAGE]
    section = page.split('class="defect-claims"', 1)
    assert len(section) == 2, "no defect-claims section on the page"
    assert "claim open" in section[1] and "disputed" in section[1]
