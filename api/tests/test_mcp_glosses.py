"""F20-T6 / AC9: ``submit_gloss``, ``withdraw_gloss`` and ``get_node``'s chains (R11; D-28 v3.30).

The two write tools are their routes, body for body (D-28: no MCP-only capability): a receipt
is the route's 201 and a refusal the route's own, before anything opens. ``get_node`` returns
the node's outlines, each gloss chain of its Lean files and each explainer chain of its merged
proofs, with every version's prose served as demarcated untrusted data. Where the graph carries
no ``glosses.json`` yet, the chains are derived from the node's files by the gate's own function,
and they equal what the committed product says (F10-Q7's twin).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_explainer_schema import step
from test_glosses_route import (
    CURATOR,
    INJECTION,
    NODE,
    NODE_DIR,
    SIGNER,
    TARGET,
    make_h,
    make_keys,
    make_tree,
    proof_hash,
    put_version,
    serve,
    statement_gloss,
    write_outline,
)
from test_mcp_demarcation import bare_hits, wrapped_hits

from opn_api import routes
from opn_api.mcp import bijection, demarcate, results
from opn_gate import glosses, products, schemas
from opn_gate import graph as graphmod

TOOLS = {"submit_gloss": "POST /glosses", "withdraw_gloss": "POST /glosses/withdrawals"}


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def test_the_tools_are_listed_and_paired_with_their_routes(h: Harness) -> None:
    listed = {t.name: t for t in McpClient(h).list_tools()}
    labels = {r.label for r in routes.ROUTES}
    for tool, route in TOOLS.items():
        assert tool in listed, sorted(listed)
        assert listed[tool].outputSchema == results.load(tool)
        row = bijection.BY_TOOL[tool]
        assert row.kind == "write" and row.plain == (route,)
        assert route in labels


def test_submit_gloss_is_the_route(h: Harness, tree: Path) -> None:
    token = h.token_for("code_bob", "bob")
    client = McpClient(h)
    out = client.ok("submit_gloss", statement_gloss(), token=token)
    assert out["status"] == 201, out
    [(path, content)] = h.githost.pushes[-1].files.items()
    assert path == out["body"]["path"] == f"{NODE_DIR}/gloss/{out['body']['hash']}.md"
    assert schemas.content_hash(content.encode()) == out["body"]["hash"]
    assert results.violations("submit_gloss", out) == []
    stale = statement_gloss()
    stale["subject"]["lean_hash"] = "a" * 64
    refused = client.failed("submit_gloss", stale, token=token)
    assert refused["status"] == 400 and refused["body"]["error"] == "gloss-subject-mismatch"
    assert len(h.githost.pushes) == 1  # nothing more opened
    assert results.violations("submit_gloss", refused) == []
    assert client.failed("submit_gloss", statement_gloss())["status"] == 401  # writes need one


def test_submit_gloss_carries_drafted_with(h: Harness) -> None:
    """F21-R6 through the tool, body for body: ``drafted_with`` reaches the route, which writes
    it into the v2 record."""
    model = "anthropic/claude-opus-5.5 via Claude Code"
    args = statement_gloss() | {"drafted_with": model}
    out = McpClient(h).ok("submit_gloss", args, token=h.token_for("code_bob", "bob"))
    assert out["status"] == 201, out
    doc, _ = glosses.split_front_matter(next(iter(h.githost.pushes[-1].files.values())))
    assert doc is not None and doc["schema"] == "gloss/v2" and doc["drafted_with"] == model


def test_withdraw_gloss_is_the_route(h: Harness, tree: Path) -> None:
    digest = put_version(tree, "gloss", "Mine.", author="bob")
    serve(h, tree)
    token = h.token_for("code_bob", "bob")
    args = {"record": f"{NODE_DIR}/gloss/{digest}.md", "reason": "It misreads the bound."}
    out = McpClient(h).ok("withdraw_gloss", args, token=token)
    assert out["status"] == 201, out
    [(path, _)] = h.githost.pushes[-1].files.items()
    assert path.startswith(f"{NODE_DIR}/withdrawals/")
    assert results.violations("withdraw_gloss", out) == []


# --- get_node ------------------------------------------------------------------------------------


def seeded(tree: Path, keys: dict[str, Path]) -> dict[str, str]:
    """A gloss chain A<-B on the statement (B signed), an explainer of Proof.lean, and the
    proof's outline, each version's prose carrying the planted injection."""
    a = put_version(tree, "gloss", f"First reading. {INJECTION}.")
    b = put_version(tree, "gloss", f"Second reading. {INJECTION}.", supersedes=a)
    glosses.sign(
        tree / NODE_DIR, b, target_id=TARGET, node_id=NODE, signer_login=CURATOR,
        date="2026-10-04", key_path=keys[CURATOR], signer=SIGNER,
    )  # fmt: skip
    e = put_version(tree, "explainer", f"Regroup the conjuncts. {INJECTION}.")
    write_outline(tree, [step("s1")])
    return {"a": a, "b": b, "e": e}


def chain_parts(bundle: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    return bundle["gloss_chains"], bundle["explainer_chains"]


def test_get_node_serves_outlines_and_chains_demarcated(
    h: Harness, tree: Path, keys: dict[str, Path]
) -> None:
    made = seeded(tree, keys)
    serve(h, tree)
    bundle = McpClient(h).ok("get_node", {"node_id": NODE})
    assert {"outlines", "gloss_chains", "explainer_chains", "chains_source"} <= set(bundle)
    assert bundle["chains_source"] == "derived"
    [outline] = bundle["outlines"]
    assert outline["proof"] == proof_hash(tree) and outline["file"] == f"nodes/{NODE}/Proof.lean"
    assert outline["outline"]["steps"][0]["id"] == "s1"
    gloss_chains, explainer_chains = chain_parts(bundle)
    [statement] = [s for s in gloss_chains if s["kind"] == "statement"]
    [chain] = statement["chains"]
    assert chain["current"] == made["b"]
    assert [v["hash"] for v in chain["versions"]] == [made["a"], made["b"]]
    # F21-R13, R14 (glosses/v2): a signature names the sections it approves (None: all of them,
    # as this v1 signature does), and the chain says what it shows, section by section.
    assert chain["versions"][1]["signatures"] == [
        {"signer": CURATOR, "date": "2026-10-04", "sections": None}
    ]
    assert chain["shown"] == [{"key": "whole", "version": made["b"], "state": "verified"}]
    assert chain["pending"] == []
    assert {s["kind"] for s in gloss_chains} == {"statement", "witness"}  # every file listed
    [proof] = [s for s in explainer_chains if s["kind"] == "proof"]
    assert proof["chains"][0]["current"] == made["e"]
    # Every version's prose is untrusted data; nothing of it is a bare string.
    assert bare_hits(bundle, INJECTION) == []
    sources = {w["source"] for w in wrapped_hits(bundle, INJECTION)}
    for digest, record in ((made["a"], "gloss"), (made["b"], "gloss"), (made["e"], "explainer")):
        assert f"{NODE_DIR}/{record}/{digest}.md" in sources
    assert bundle["untrusted_note"] == demarcate.UNTRUSTED_NOTE
    assert results.violations("get_node", bundle) == []


def test_the_derived_chains_equal_the_committed_product(
    h: Harness, tree: Path, keys: dict[str, Path]
) -> None:
    """F10-Q7's rule for a twin: the chains derived from the host equal what the post-merge
    job commits, signatures verified by the service's own reader included."""
    seeded(tree, keys)
    serve(h, tree)
    client = McpClient(h)
    derived = client.ok("get_node", {"node_id": NODE})
    doc = products.glosses_doc(graphmod.load_target(tree, TARGET), "5" * 40, signer=SIGNER)
    product = tree / "targets" / TARGET / products.GLOSSES_FILE
    product.write_bytes(schemas.canonical_json(schemas.validate(doc, products.GLOSSES_SCHEMA)))
    serve(h, tree)
    committed = client.ok("get_node", {"node_id": NODE})
    assert committed["chains_source"] == "file" and derived["chains_source"] == "derived"
    assert chain_parts(committed) == chain_parts(derived)
    assert committed["outlines"] == derived["outlines"]
    # And what is served is the product's own subjects for the node, plus each version's prose.
    mine = [s for s in json.loads(product.read_bytes())["subjects"] if s["node"] == NODE]
    served = [s for part in chain_parts(committed) for s in part]
    for subject in served:
        for chain in subject["chains"]:
            for version in chain["versions"]:
                assert demarcate.is_wrapped(version.pop("text"))
    assert sorted(served, key=json.dumps) == sorted(mine, key=json.dumps)


def as_v1(doc: dict[str, Any]) -> dict[str, Any]:
    """A ``glosses/v2`` product as the gate before F21 wrote it: no sections, no shown or pending
    words, no ``drafted_with``, signatures without ``sections``."""
    old: dict[str, Any] = json.loads(json.dumps(doc))
    old["schema"] = "glosses/v1"
    for subject in old["subjects"]:
        for chain in subject["chains"]:
            chain.pop("shown"), chain.pop("pending")
            for version in chain["versions"]:
                version.pop("sections"), version.pop("drafted_with")
                for sig in version["signatures"]:
                    sig.pop("sections")
    assert schemas.violations(old, "glosses/v1") == []
    return old


def test_a_committed_v1_product_is_still_served(
    h: Harness, tree: Path, keys: dict[str, Path]
) -> None:
    """The changeover (F21-R6): until the re-pin the live graph holds ``glosses/v1``; get_node
    validates the committed product against the version it declares, and serves either."""
    seeded(tree, keys)
    doc = products.glosses_doc(graphmod.load_target(tree, TARGET), "5" * 40, signer=SIGNER)
    product = tree / "targets" / TARGET / products.GLOSSES_FILE
    client = McpClient(h)
    for written in (as_v1(doc), doc):
        product.write_bytes(schemas.canonical_json(written))
        serve(h, tree)
        bundle = client.ok("get_node", {"node_id": NODE})
        assert bundle["chains_source"] == "file", written["schema"]
        [statement] = [s for s in bundle["gloss_chains"] if s["kind"] == "statement"]
        assert len(statement["chains"][0]["versions"]) == 2
        assert results.violations("get_node", bundle) == []
    product.write_bytes(schemas.canonical_json(as_v1(doc) | {"schema": "glosses/v9"}))
    serve(h, tree)
    assert client.failed("get_node", {"node_id": NODE})["error"] == "glosses-invalid"


def test_a_node_with_no_words_has_empty_chains(h: Harness) -> None:
    bundle = McpClient(h).ok("get_node", {"node_id": NODE})
    gloss_chains, explainer_chains = chain_parts(bundle)
    assert all(s["chains"] == [] for s in gloss_chains + explainer_chains)
    assert [o["outline"] for o in bundle["outlines"]] == [None]  # Proof.lean, not yet outlined
