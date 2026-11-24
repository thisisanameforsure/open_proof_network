"""F14-T33: a signed-in ``GET /session`` costs the host the same reads at any graph size.

After the bulk load (443 targets) the roles walk — the targets a login stewards, the motions
awaiting its vote, the reviews awaiting its answer — listed three directories per target, one
Contents-API call each, in series: about 1300 calls, past API Gateway's 29-second window, so the
signed-in header, the review page's answer and sign forms and ``/me/`` all went blank. Listings
are now answered from one recursive tree per head, with the directory walk kept as the fallback
for a tree the host truncates.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_glosses_route import TARGET, make_keys, make_tree
from test_session_roles import harness_over, session
from test_web_session import sign_in

from opn_api.mcp import reads


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness_over(tree)


def grow(h: Harness, extra: int) -> None:
    """The index lists ``extra`` more targets beside the fixture's; none of them has a steward,
    motion or review directory, as most of the live graph's targets have none."""
    index = json.loads(h.githost.files["targets/index.json"])
    index["targets"] = list(index["targets"]) + [
        {**index["targets"][0], "target_id": f"bulk-{i:04d}"} for i in range(extra)
    ]
    h.githost.files["targets/index.json"] = json.dumps(index).encode()
    h.context.files.clear()
    h.context.listings.clear()


def host_listings(h: Harness) -> int:
    """Directory reads the host was asked for: Contents listings plus whole-tree reads."""
    return sum(1 for path, _ in h.githost.fetches if path.endswith("/")) + len(h.githost.tree_calls)


def signed_in_reads(h: Harness, extra: int) -> tuple[int, dict[str, Any]]:
    grow(h, extra)
    cookie = sign_in(h, "code_alice")
    before = host_listings(h)
    r = session(h, cookie)
    assert r.status_code == 200, r.text
    return host_listings(h) - before, r.json()


def test_a_signed_in_session_costs_the_same_listings_at_any_graph_size(tree: Path) -> None:
    """The red case: with 200 more targets the walk asked for 600 more listings."""
    counts = []
    for extra in (5, 200):
        for h in harness_over(tree):  # one harness, closed when the loop ends
            n, doc = signed_in_reads(h, extra)
            assert doc["stewards"] == [TARGET]
            counts.append(n)
    assert counts[0] == counts[1], counts
    assert counts[1] <= 2, counts


def test_a_second_session_at_the_same_head_reads_no_listing_again(h: Harness) -> None:
    grow(h, 20)
    cookie = sign_in(h, "code_alice")
    session(h, cookie)
    before = host_listings(h)
    assert session(h, cookie).json()["stewards"] == [TARGET]
    assert host_listings(h) == before


def test_a_truncated_tree_falls_back_to_listing_each_directory(h: Harness) -> None:
    """A tree too large for the host is read directory by directory, as before: slower, and the
    same answer."""
    h.githost.tree_truncated = True
    n, doc = signed_in_reads(h, 5)
    assert doc["stewards"] == [TARGET]
    assert n > 2  # the walk, one listing per directory


def test_a_failed_tree_read_falls_back_to_listing_each_directory(h: Harness) -> None:
    """The tree read failing is no outage: the directory walk answers, as it did before."""
    original = h.githost.list_tree

    def failing(repo: str, ref: str) -> dict[str, list[str]] | None:
        h.githost.unreachable = True
        try:
            return original(repo, ref)
        finally:
            h.githost.unreachable = False

    h.githost.list_tree = failing  # type: ignore[method-assign]
    n, doc = signed_in_reads(h, 5)
    assert doc["stewards"] == [TARGET]
    assert n > 2


def test_every_listing_from_the_tree_equals_the_contents_listing(h: Harness) -> None:
    """Parity at the seam: each directory of the fixture graph, and one that does not exist,
    reads the same through the tree as through the Contents API."""
    dirs = {p.rpartition("/")[0] for p in h.githost.files} | {
        f"targets/{TARGET}/motions",
        f"targets/{TARGET}",  # holds only directories at the top: an empty listing either way
        "nowhere/at/all",
    }
    via_tree = {d: reads.listing(h.context, d) for d in sorted(dirs)}
    h.context.listings.clear()
    h.githost.tree_truncated = True
    via_contents = {d: reads.listing(h.context, d) for d in sorted(dirs)}
    assert via_tree == via_contents
