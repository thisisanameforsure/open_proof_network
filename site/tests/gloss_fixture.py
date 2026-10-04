"""F20-T8 fixture trees: glosses and explainer versions on the site (R13, R14; AC2, AC11, AC12).

Every record here is written the way a pull request adds it — Markdown with ``gloss/v1`` or
``explainer/v1`` front matter, named by its own sha256 — and every signature is made with a test
key through the gate's own signers (``glosses.sign``, ``explainers.sign``), so the site verifies
real signatures at render. ``targets/<id>/glosses.json`` is then written by the gate's own
``products.generate``: the tests read the shape that lands, never a hand-made product.

The tree is F19's ``chain_tree`` (the tutorial's proof outlined: steps ``hq``, ``hq.s1``, ``hp``,
``s3``) plus a definition module, a hole whose stub witness was glossed and then filled, a
``resolves`` variant with its relation, and a second, curated target whose root has an informal
statement and a steward's gloss.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import fixture
import reading_fixture as rf
import yaml
from harness import TARGET, take_in
from test_finding_hole_frontier import write_hole

from opn_gate import explainers, glosses, scaffold, schemas
from opn_gate.signer import SshKeygenSigner

COMMIT = fixture.COMMIT
TUTORIAL, MIDDLE, ROOT = rf.TUTORIAL, rf.MIDDLE, rf.ROOT
HOLE = "and-swap-reassoc--h1"
VARIANT = "variant-resolves"
MODULE = "Fact.lean"
CURATED = "curated-target"
CURATED_ROOT = "and-reassoc"  # take_in's default source node keeps its id
CURATOR = "curator-one"
STEWARD = "alice-steward"
INFORMAL = "Reassociating a conjunction of three propositions changes nothing, $p \\land q$."
DRAFTER = {
    "name": "opn-drafter",
    "model": "claude-fable-5-1",
    "model_version": "claude-fable-5-1-20260901",
    "input_commit": "8" * 40,
}
STUB_WITNESS = "theorem witness : True := by\n  sorry\n"
FILLED_WITNESS = "theorem witness : True := trivial\n"
RELATION = "theorem relation : True := trivial\n"

#: The words each gloss carries, so the tests can find them on the page.
TUTORIAL_DRAFT = "For all propositions p and q, from p and q together one gets q and p."
TUTORIAL_REVISED = (
    "For any two propositions $p$ and $q$, if both hold then both hold in the other order. "
    "Nothing else is assumed."
)
TUTORIAL_SECOND_CHAIN = "Conjunction is symmetric: swapping the two sides keeps it true."
WITNESS_OF_STUB = "The witness slot is open: it still holds sorry."
RELATION_GLOSS = "The variant's relation: a proof of True, which is all the label asks."
DEFINITION_GLOSS = "The factorial of a natural number, defined by recursion on it."
ROOT_GLOSS = "Reassociation, read by a steward: the grouping of three conjuncts does not matter."

#: The explainer chain on the tutorial's proof: a draft, a person's revision (signed), and a
#: third version that was withdrawn, so the revision is current again (D-3 v3.30).
EXPLAINER_DRAFT = (
    "## The idea\nSplit the hypothesis and rebuild it the other way round.\n\n"
    "## The two halves {steps: hq hp}\nEach half is read off the hypothesis.\n"
)
EXPLAINER_REVISED = (
    "## The idea\nThe hypothesis $p \\land q$ already holds both halves; the proof only "
    "reorders them.\n\n"
    "## Getting q {steps: hq}\nTake the hypothesis apart and keep its right half, `h.2`.\n\n"
    "## Getting p, and closing {steps: hp s3}\nThe left half is routine; then the pair is "
    "rebuilt as $q \\land p$.\n"
)
EXPLAINER_WITHDRAWN = "## The idea\nA third reading that misread the hypothesis.\n"


def front(doc: dict[str, Any], body: str) -> str:
    return "---\n" + str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)) + "---\n" + body


def put(directory: Path, text: str) -> str:
    """The record, named by its own sha256 as a pull request files it; returns the hash."""
    digest = str(schemas.content_hash(text.encode("utf-8")))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{digest}.md").write_text(text, encoding="utf-8")
    return digest


def target_dir(root: Path, target: str = TARGET) -> Path:
    return root / "targets" / target


def node_dir(root: Path, node: str, target: str = TARGET) -> Path:
    return target_dir(root, target) / "nodes" / node


def gloss(
    root: Path,
    body: str,
    *,
    kind: str,
    node: str | None,
    module: str | None = None,
    author: str | None = None,
    drafter: dict[str, Any] | None = None,
    supersedes: str | None = None,
    target: str = TARGET,
    date: str = "2026-10-04",
) -> str:
    """A ``gloss/v1`` record of the file as it stands now."""
    parent = node_dir(root, node, target) if node is not None else target_dir(root, target)
    file = (
        target_dir(root, target) / "defs" / str(module)
        if kind == "definition"
        else parent / glosses.KIND_FILES[kind]
    )
    doc = {
        "schema": "gloss/v1",
        "target": target,
        "subject": {
            "kind": kind,
            "node": node,
            "module": module,
            "lean_hash": schemas.content_hash(file.read_bytes()),
        },
        "supersedes": supersedes,
        "author": author,
        "drafter": drafter,
        "date": date,
        "licence": "CC-BY-4.0",
    }
    return put(parent / "gloss", front(doc, body + "\n"))


def explainer(
    root: Path,
    node: str,
    body: str,
    *,
    author: str | None = None,
    drafter: dict[str, Any] | None = None,
    supersedes: str | None = None,
    date: str = "2026-10-04",
) -> str:
    proof = schemas.content_hash((node_dir(root, node) / "Proof.lean").read_bytes())
    doc = {
        "schema": "explainer/v1",
        "target": TARGET,
        "node": node,
        "proof": proof,
        "supersedes": supersedes,
        "author": author,
        "drafter": drafter,
        "date": date,
        "licence": "CC-BY-4.0",
    }
    return put(node_dir(root, node) / "explainer", front(doc, body))


def withdraw(parent: Path, record: str, author: str) -> None:
    doc = {
        "schema": "withdrawal/v2",
        "withdraws": record,
        "reason": "It misreads the hypothesis.",
        "author": author,
        "date": "2026-10-04",
    }
    path = parent / "withdrawals" / f"2026-10-04T00-00-01Z-{author}.yaml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def keypair(tmp_path: Path, who: str) -> Path:
    key = tmp_path / f"key-{who}"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who], check=True
    )
    return key


def add_variant(root: Path) -> None:
    """A ``resolves`` variant with its ``Relation.lean``, as the scaffold writes one; its root is
    already declared by ``write_hole`` (a variant has no dependents, F08-Q19)."""
    proposal = scaffold.Proposal(
        node_id=VARIANT,
        target_id=TARGET,
        statement="theorem OpnProp.variant_one : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="resolves",
        relation_proof=RELATION,
        date="2026-10-01T00:00:00Z",
    )
    scaffold.validate(proposal)
    scaffold.write(fixture.nodes_dir(root), proposal)


def glossed_tree(tmp_path: Path) -> Path:
    """The tree the AC2, AC11 and AC12 tests and the evidence script render; products written."""
    root = rf.chain_tree(tmp_path)
    signer = SshKeygenSigner()
    curator_key = keypair(tmp_path, CURATOR)
    steward_key = keypair(tmp_path, STEWARD)

    # A definition module and its gloss (targets/<id>/gloss/).
    defs = target_dir(root) / "defs"
    (defs / MODULE).write_text(
        "def Opn.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 => (n + 1) * Opn.fact n\n",
        encoding="utf-8",
    )
    gloss(root, DEFINITION_GLOSS, kind="definition", node=None, module=MODULE, author="carol")

    # The tutorial's statement: a draft, a person's revision of it (signed), and a second chain.
    draft = gloss(root, TUTORIAL_DRAFT, kind="statement", node=TUTORIAL, drafter=DRAFTER)
    revised = gloss(
        root,
        TUTORIAL_REVISED,
        kind="statement",
        node=TUTORIAL,
        author="alice",
        supersedes=draft,
        date="2026-10-05",
    )
    glosses.sign(
        node_dir(root, TUTORIAL),
        revised,
        target_id=TARGET,
        node_id=TUTORIAL,
        signer_login=CURATOR,
        date="2026-10-06",
        key_path=curator_key,
        signer=signer,
    )
    gloss(root, TUTORIAL_SECOND_CHAIN, kind="statement", node=TUTORIAL, author="bob")

    # A hole whose stub witness was glossed, then filled: the gloss describes an earlier text.
    write_hole(root, witness=STUB_WITNESS, node_id=HOLE)
    gloss(root, WITNESS_OF_STUB, kind="witness", node=HOLE, drafter=DRAFTER)
    (node_dir(root, HOLE) / "Witness.lean").write_text(FILLED_WITNESS, encoding="utf-8")

    # A resolves variant and a draft of its relation.
    add_variant(root)
    gloss(root, RELATION_GLOSS, kind="relation", node=VARIANT, drafter=DRAFTER)

    # The explainer chain on the tutorial's proof.
    e1 = explainer(root, TUTORIAL, EXPLAINER_DRAFT, drafter=DRAFTER, date="2026-10-04")
    e2 = explainer(
        root, TUTORIAL, EXPLAINER_REVISED, author="alice", supersedes=e1, date="2026-10-05"
    )
    explainers.sign(
        node_dir(root, TUTORIAL),
        e2,
        target_id=TARGET,
        signer_login=CURATOR,
        date="2026-10-06",
        key_path=curator_key,
        signer=signer,
    )
    e3 = explainer(
        root, TUTORIAL, EXPLAINER_WITHDRAWN, author=CURATOR, supersedes=e2, date="2026-10-07"
    )
    withdraw(node_dir(root, TUTORIAL), f"explainer/{e3}.md", CURATOR)

    # A curated target: its root has an informal statement of record and a steward's gloss.
    take_in(root, CURATED, informal=INFORMAL, title="A curated target")
    gloss(
        root,
        ROOT_GLOSS,
        kind="statement",
        node=CURATED_ROOT,
        author=STEWARD,
        target=CURATED,
    )
    del steward_key  # the steward writes; only a signature needs a key, and this one is unsigned
    rf.write_products(root)
    return root


def shoot_paths(root: Path) -> list[str]:
    """The site paths the evidence script captures (engineering/evidence/F20/shoot.py)."""
    proof = node_dir(root, ROOT) / "Proof.lean"
    reading = rf.reading_path(TARGET, schemas.content_hash(proof.read_bytes()))
    return [
        f"/nodes/{TARGET}/{TUTORIAL}/",
        f"/nodes/{TARGET}/{HOLE}/",
        "/problems/",
        "/" + reading.removesuffix("index.html"),
        f"/problems/{TARGET}/",
    ]
