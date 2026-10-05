"""F21-T7 / AC8: the Problems page's "needs words" filter (R9).

Words are contributors' work (D-3 v3.31), so the page that lists the problems also says, per
problem, how many of its Lean files and merged proofs have no words yet, and offers a filter
that keeps exactly the problems with some. The count is computed by the gate's own
``glosses.needed`` from the ``glosses.json`` the site already loads and the target's
``target.yaml`` — the same rows ``list_words_needed`` serves (F21-Q6).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
import yaml
from harness import TARGET, take_in

from opn_gate import glosses, products, schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
WORDED = "euclid-primes"  # every file has words
PROBLEMS = "problems/index.html"


def needed_of(root: Path, target_id: str) -> list[dict[str, Any]]:
    target_dir = root / "targets" / target_id
    doc = json.loads((target_dir / products.GLOSSES_FILE).read_text(encoding="utf-8"))
    record = target_dir / "target.yaml"
    curated = glosses.curated_words(
        yaml.safe_load(record.read_text(encoding="utf-8")) if record.is_file() else None
    )
    root_id = json.loads((target_dir / "graph.json").read_text(encoding="utf-8"))["root"]
    return glosses.needed(doc, root=root_id, curated=curated)


def put(directory: Path, doc: dict[str, Any], body: str) -> None:
    text = "---\n" + str(yaml.safe_dump(doc, sort_keys=False)) + "---\n" + body
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{schemas.content_hash(text.encode('utf-8'))}.md").write_text(text, "utf-8")


def give_words(root: Path, target_id: str) -> None:
    """A gloss or an explainer for every subject that lacks one, as a merged one is filed."""
    target_dir = root / "targets" / target_id
    for row in needed_of(root, target_id):
        file = root / row["file"]
        common = {"supersedes": None, "author": "carol", "drafter": None, "date": "2026-10-06"}
        if row["kind"] in glosses.ARTIFACT_KINDS:
            doc = {
                "schema": "explainer/v1",
                "target": target_id,
                "node": row["node"],
                "proof": schemas.content_hash(file.read_bytes()),
                **common,
                "licence": "CC-BY-4.0",
            }
            put(target_dir / "nodes" / row["node"] / "explainer", doc, "## The idea\nIt holds.\n")
            continue
        parent = target_dir if row["node"] is None else target_dir / "nodes" / row["node"]
        doc = {
            "schema": "gloss/v1",
            "target": target_id,
            "subject": {
                "kind": row["kind"],
                "node": row["node"],
                "module": row["module"],
                "lean_hash": schemas.content_hash(file.read_bytes()),
            },
            **common,
            "licence": "CC-BY-4.0",
        }
        put(parent / "gloss", doc, f"What the {row['kind']} says.\n")


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, str]]:
    """Two problems: the propositional one with files lacking words, and a second whose every
    file and proof has them."""
    root = fixture.curated(tmp_path_factory.mktemp("words"))
    take_in(root, WORDED)
    render_products(root)
    give_words(root, WORDED)
    render_products(root)
    site = model.load_site(root, fixture.COMMIT)
    return root, render.render_site(site, repo_url=REPO)


def render_products(root: Path) -> None:
    prod = products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW)
    prod.write(root)


def card(page: str, target_id: str) -> str:
    [found] = re.findall(
        rf'<article class="card problem"[^>]*id="p-{target_id}">.*?</article>', page, flags=re.S
    )
    return str(found)


def test_each_problem_shows_its_count(built: tuple[Path, dict[str, str]]) -> None:
    """R9: each problem's card carries its count of subjects without words, the gate's own
    count, as an attribute the filter reads and as words a reader sees."""
    root, pages = built
    page = pages[PROBLEMS]
    lacking = len(needed_of(root, TARGET))
    assert lacking > 0 and needed_of(root, WORDED) == [], "guard: one of each"
    mine = card(page, TARGET)
    assert f'data-words="{lacking}"' in mine
    assert f"{lacking} files need words" in mine
    done = card(page, WORDED)
    assert 'data-words="0"' in done
    assert "need words" not in done


def test_the_filter_keeps_exactly_the_problems_with_some(
    built: tuple[Path, dict[str, str]],
) -> None:
    """AC8: the segment is offered with the number of problems it keeps, and the script's
    filter keeps a card exactly when its count is above zero."""
    _root, pages = built
    page = pages[PROBLEMS]
    segments = re.findall(r'<a class="seg-opt"[^>]*data-filter="words"[^>]*>.*?</a>', page)
    assert len(segments) == 1, "one 'needs words' segment"
    segment = segments[0]
    assert 'href="/problems/?filter=words"' in segment
    assert "Needs words" in segment and '<span class="n">1</span>' in segment
    counts = {
        tid: int(n) for n, tid in re.findall(r'data-words="(\d+)"[^>]*id="p-([a-z0-9-]+)"', page)
    }
    assert set(counts) == {TARGET, WORDED}
    kept = {tid for tid, n in counts.items() if n > 0}
    assert kept == {TARGET}
    script = pages["problems.js"]
    assert re.search(
        r'filter === "words"\)\s*\{\s*return parseInt\(card\.getAttribute\("data-words"\)', script
    ), "matchesFilter keeps a card by its data-words count"
