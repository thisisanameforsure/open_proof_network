"""F17-T7 / AC8, R9: the site serves the prover client with its checksum, read from the tooling
repository at build time (no copy in the site tree to drift), and the Docs page shows the
download, the check and the chain.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import fixture

from opn_site import model, render

REPO = "https://github.com/example/graph"


def rendered(tmp_path: Path) -> dict[str, str]:
    root = fixture.build(tmp_path)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_prove_client_hash(tmp_path: Path) -> None:
    files = rendered(tmp_path)
    served = files[render.PROVE_PATH]
    assert served == render.PROVE_CLIENT.read_text(encoding="utf-8")
    digest, name = files[render.PROVE_SUMS].split()
    assert name == "opn_prove.py"
    assert digest == hashlib.sha256(served.encode("utf-8")).hexdigest()


def test_no_copy_in_the_static_tree() -> None:
    assert not list(render.STATIC.rglob("opn_prove.py")), "the client must not be copied"


def test_docs_shows_the_chain(tmp_path: Path) -> None:
    docs = rendered(tmp_path)["docs/index.html"]
    card = docs[docs.index('id="connector-opn-prove"') :]
    card = card[: card.index("</section>")]
    for step in ("export", "run", "import", "submit", "sha256sum -c -"):
        assert step in card, step
    assert f'href="/{render.PROVE_PATH}"' in card
    assert f'href="/{render.PROVE_SUMS}"' in card
    assert "https://" not in card, "the site names no host of its own"
