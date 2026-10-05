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
#: F21-R6, R7: what a contributor says drafted their words — markup in it, so the tests see it
#: escaped.
DRAFTED_WITH = 'anthropic/claude-opus-5.5 via "Claude Code" <cli> & tools'
HOLE_STATEMENT_GLOSS = "The hole's obligation, as its parent's skeleton left it open."

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
    drafted_with: str | None = None,
    v2: bool = False,
) -> str:
    """A ``gloss/v1`` record of the file as it stands now; ``gloss/v2`` when it names
    ``drafted_with`` or ``v2`` is set (F21-R6)."""
    parent = node_dir(root, node, target) if node is not None else target_dir(root, target)
    file = (
        target_dir(root, target) / "defs" / str(module)
        if kind == "definition"
        else parent / glosses.KIND_FILES[kind]
    )
    doc: dict[str, Any] = {
        "schema": "gloss/v2" if v2 or drafted_with is not None else "gloss/v1",
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
    if drafted_with is not None:
        doc["drafted_with"] = drafted_with
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
    drafted_with: str | None = None,
    v2: bool = False,
) -> str:
    """An ``explainer/v1`` record of the node's proof; ``explainer/v2`` when it names
    ``drafted_with`` or ``v2`` is set (F21-R6)."""
    proof = schemas.content_hash((node_dir(root, node) / "Proof.lean").read_bytes())
    doc: dict[str, Any] = {
        "schema": "explainer/v2" if v2 or drafted_with is not None else "explainer/v1",
        "target": TARGET,
        "node": node,
        "proof": proof,
        "supersedes": supersedes,
        "author": author,
        "drafter": drafter,
        "date": date,
        "licence": "CC-BY-4.0",
    }
    if drafted_with is not None:
        doc["drafted_with"] = drafted_with
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
    # F21-R7: a person's words their agent drafted, saying so in ``drafted_with`` (gloss/v2).
    gloss(
        root,
        HOLE_STATEMENT_GLOSS,
        kind="statement",
        node=HOLE,
        author="dana",
        drafted_with=DRAFTED_WITH,
    )
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


# -- F21-T12 (R14; AC11): words by section, with an edit awaiting review ---------------------------

#: The explainer chain of ``sectioned_tree`` on the tutorial's proof, three sections each. Dana's
#: agent drafts all three; Alice rewrites the first anchored one (written); a curator signs the
#: second in Alice's version (verified); Bob then edits the verified one (pending).
SECTION_DRAFT = (
    "## The idea\nSwap the two halves of the hypothesis.\n\n"
    "## Getting q {steps: hq}\nThe right half is h.2.\n\n"
    "## Getting p, and closing {steps: hp s3}\nThe left half is h.1; pair them the other way.\n"
)
SECTION_WRITTEN = (
    "## The idea\nSwap the two halves of the hypothesis.\n\n"
    "## Getting q {steps: hq}\nTake the hypothesis apart and keep its right half, which is "
    "$q$.\n\n"
    "## Getting p, and closing {steps: hp s3}\nThe left half is h.1; pair them the other way.\n"
)
SECTION_EDIT = (
    "## The idea\nSwap the two halves of the hypothesis.\n\n"
    "## Getting q {steps: hq}\nTake the hypothesis apart and keep its right half, which is "
    "$q$.\n\n"
    "## Getting p, and closing {steps: hp s3}\nThe left half is $p$, read off the hypothesis; "
    "the anonymous constructor then builds $q \\land p$.\n"
)
KEY_OVERVIEW, KEY_Q, KEY_P = "overview", "steps:hq", "steps:hp,s3"
#: The gloss chain of ``sectioned_tree`` on the tutorial's statement: Alice's words, signed by a
#: curator, then Bob's edit of them.
GLOSS_VERIFIED = "From p and q together, one gets q and p."
GLOSS_EDIT = "If both p and q hold, then q and p hold: the order of a conjunction does not matter."


def sectioned_tree(tmp_path: Path, *, approve_edit: bool = False) -> tuple[Path, dict[str, str]]:
    """F21-T12's tree: the tutorial's explainer shows one section drafted, one written and one
    verified, with Bob's edit of the verified one awaiting review; its statement's gloss shows
    Alice's verified words with Bob's edit awaiting review. With ``approve_edit`` a curator then
    signs the edited section of Bob's explainer and Bob's gloss. Products written by the gate.
    Returns the root and the record hashes by name."""
    root = rf.chain_tree(tmp_path)
    signer = SshKeygenSigner()
    curator_key = keypair(tmp_path, CURATOR)
    node = node_dir(root, TUTORIAL)
    h: dict[str, str] = {}
    h["draft"] = explainer(
        root, TUTORIAL, SECTION_DRAFT, author="dana", drafted_with=DRAFTED_WITH, date="2026-10-04"
    )
    h["written"] = explainer(
        root, TUTORIAL, SECTION_WRITTEN, author="alice", supersedes=h["draft"], v2=True,
        date="2026-10-05",
    )  # fmt: skip
    explainers.sign(
        node, h["written"], target_id=TARGET, signer_login=CURATOR, date="2026-10-05",
        key_path=curator_key, signer=signer, approves=[KEY_P],
    )  # fmt: skip
    h["edit"] = explainer(
        root, TUTORIAL, SECTION_EDIT, author="bob", supersedes=h["written"], v2=True,
        date="2026-10-06",
    )  # fmt: skip
    h["gloss"] = gloss(
        root, GLOSS_VERIFIED, kind="statement", node=TUTORIAL, author="alice", v2=True
    )
    glosses.sign(
        node, h["gloss"], target_id=TARGET, node_id=TUTORIAL, signer_login=CURATOR,
        date="2026-10-05", key_path=curator_key, signer=signer,
    )  # fmt: skip
    h["gloss_edit"] = gloss(
        root, GLOSS_EDIT, kind="statement", node=TUTORIAL, author="bob", supersedes=h["gloss"],
        v2=True, date="2026-10-06",
    )  # fmt: skip
    if approve_edit:
        explainers.sign(
            node, h["edit"], target_id=TARGET, signer_login=CURATOR, date="2026-10-07",
            key_path=curator_key, signer=signer, approves=[KEY_P],
        )  # fmt: skip
        glosses.sign(
            node, h["gloss_edit"], target_id=TARGET, node_id=TUTORIAL, signer_login=CURATOR,
            date="2026-10-07", key_path=curator_key, signer=signer, approves=["whole"],
        )  # fmt: skip
    rf.write_products(root)
    return root, h
