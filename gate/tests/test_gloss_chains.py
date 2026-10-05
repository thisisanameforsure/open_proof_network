"""F20-T4 / AC2, AC5, AC6, AC7: versions of glosses and explainers (R6 to R9; D-3 v3.30, D-33).

A gloss or an explainer is corrected by a new version that supersedes the head of its chain, never
by an edit: the chain is linear, so the current version needs no clock (F20-Q3). Superseding
anything but the head is ``record-not-head``, naming the head. Anyone may supersede a signed
version: F20's ``signed-supersede`` is withdrawn (F21-R13), and a person's change to verified
words is pending until a steward or curator signs it (``opn_gate.sections``). A version is
withdrawn by a ``withdrawal/v2`` record from its author, an active steward or a listed curator,
and every reader reads it as absent while the file stays.
A gloss signature is a steward's or curator's affirmation that the words say what the Lean says;
it changes nothing else. Digestion counts a node while every section an explainer chain on its
first proof shows is verified (D-33 v3.31, F21-R15). The products publish every chain per subject
in ``targets/<id>/glosses.json`` (``glosses/v2`` since F21), ranked by nothing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph
from test_modes import CURATOR, write_curators
from test_products import ROOT_NODE, attest, generate, loads

from opn_gate import cli, config, explainers, glosses, modes, schemas, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner

NODE = "and-reassoc"
STEWARD = "alice-steward"
STRANGER = "mallory"
SIGNER = SshKeygenSigner()


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("gloss-keys")
    out: dict[str, Path] = {}
    for who in (CURATOR, STEWARD, STRANGER):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


@pytest.fixture
def root(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The propositional fixture, products published, a curator listed and a steward
    committed on its one target."""
    graph = copy_graph(tmp_path, publish=True)
    write_curators(graph, CURATOR)
    steward.write(
        graph / "targets" / TARGET,
        action=steward.COMMIT,
        login=STEWARD,
        name="Alice",
        link="https://orcid.org/0000-0002-1825-0097",
        date="2026-10-04",
        key_path=keys[STEWARD],
        signer=SIGNER,
    )
    return graph


def node_dir(root: Path, node: str = NODE) -> Path:
    return root / "targets" / TARGET / "nodes" / node


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def front(doc: dict[str, Any], body: str) -> str:
    return "---\n" + str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)) + "---\n" + body


def put(directory: Path, text: str) -> Path:
    digest = schemas.content_hash(text.encode("utf-8"))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.md"
    path.write_text(text, encoding="utf-8")
    return path


def gloss(
    root: Path,
    body: str,
    *,
    supersedes: str | None = None,
    author: str | None = "carol",
    node: str = NODE,
    kind: str = "statement",
) -> tuple[str, Change]:
    file = node_dir(root, node) / glosses.KIND_FILES[kind]
    doc = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {
            "kind": kind,
            "node": node,
            "module": None,
            "lean_hash": schemas.content_hash(file.read_bytes()),
        },
        "supersedes": supersedes,
        "author": author,
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    path = put(node_dir(root, node) / "gloss", front(doc, body))
    return path.stem, Change("A", rel(root, path))


def explainer(
    root: Path,
    body: str,
    *,
    supersedes: str | None = None,
    author: str | None = "carol",
    node: str = NODE,
) -> tuple[str, Change]:
    proof = schemas.content_hash((node_dir(root, node) / "Proof.lean").read_bytes())
    doc = {
        "schema": "explainer/v1",
        "target": TARGET,
        "node": node,
        "proof": proof,
        "supersedes": supersedes,
        "author": author,
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    path = put(node_dir(root, node) / "explainer", front(doc, f"## The idea\n{body}\n"))
    return path.stem, Change("A", rel(root, path))


def codes(root: Path, *changes: Change, author: str = STRANGER) -> list[str]:
    classification = modes.classify(list(changes), author=author, graph_root=root)
    if not classification.ok:
        return [d.code for d in classification.problems]
    assert classification.mode == "explainer", classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


def problems(root: Path, change: Change, author: str = STRANGER) -> list[Any]:
    classification = modes.classify([change], author=author, graph_root=root)
    assert classification.mode == "explainer", classification.as_dict()
    return modes.check(root, classification)


def sign_gloss(root: Path, digest: str, by: str, key: Path, node: str | None = NODE) -> Change:
    parent = node_dir(root, node) if node is not None else root / "targets" / TARGET
    path = glosses.sign(
        parent,
        digest,
        target_id=TARGET,
        node_id=node,
        signer_login=by,
        date="2026-10-04",
        key_path=key,
        signer=SIGNER,
    )
    return Change("A", rel(root, path))


def sign_explainer(root: Path, digest: str, by: str, key: Path, node: str = NODE) -> Change:
    path = explainers.sign(
        node_dir(root, node), digest, target_id=TARGET, signer_login=by, date="2026-10-04",
        key_path=key, signer=SIGNER,
    )  # fmt: skip
    return Change("A", rel(root, path))


def withdraw(root: Path, record: str, author: str, *, n: int, node: str | None = NODE) -> Change:
    parent = node_dir(root, node) if node is not None else root / "targets" / TARGET
    doc = {
        "schema": "withdrawal/v2",
        "withdraws": record,
        "reason": "It misreads the hypothesis.",
        "author": author,
        "date": "2026-10-04",
    }
    path = parent / "withdrawals" / f"2026-10-04T00-00-0{n}Z-{author}.yaml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return Change("A", rel(root, path))


def chains_of(root: Path, kind: str, node: str = NODE) -> list[dict[str, Any]]:
    doc = loads(generate(root), f"targets/{TARGET}/glosses.json")
    assert doc["schema"] == "glosses/v2" and schemas.violations(doc) == []
    [subject] = [s for s in doc["subjects"] if s["kind"] == kind and s["node"] == node]
    return list(subject["chains"])


# --- AC2 ---------------------------------------------------------------------------------------


def test_a_gloss_of_changed_text_is_marked(root: Path) -> None:
    """AC2 (gate half): a gloss of a hole's stub witness describes the current text until the
    witness is filled; then the products mark it as describing an earlier version, and keep it."""
    witness = node_dir(root) / "Witness.lean"
    filled = witness.read_text(encoding="utf-8")
    witness.write_text("theorem witness : True := sorry\n", encoding="utf-8")
    digest, change = gloss(root, "The slot asks for three propositions.\n", kind="witness")
    assert codes(root, change) == []
    [chain] = chains_of(root, "witness")
    [version] = chain["versions"]
    assert chain["current"] == digest and version["describes_current"] is True
    witness.write_text(filled, encoding="utf-8")  # the witness is filled
    [chain] = chains_of(root, "witness")
    [version] = chain["versions"]
    assert version["hash"] == digest and version["describes_current"] is False
    assert chain["current"] == digest  # still the chain's current version, of earlier text


# --- AC5 ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_linear_chains_and_signed_supersede(root: Path, keys: dict[str, Path], record: str) -> None:
    """AC5, restated by F21-R13: a chain A<-B; C superseding A is refused ``record-not-head``
    naming B and D superseding B passes. With B signed, E superseding it is accepted from anyone
    — a third party, a steward or a curator — since F20's ``signed-supersede`` is withdrawn; E's
    change to B's verified words is pending, and the chain goes on showing B's. The same for
    explainers."""
    make = gloss if record == "gloss" else explainer
    sign = sign_gloss if record == "gloss" else sign_explainer
    a, _ = make(root, "First reading.")
    b, _ = make(root, "Second reading.", supersedes=a)
    _c, c_change = make(root, "A fork.", supersedes=a)
    found = problems(root, c_change)
    assert [d.code for d in found] == ["record-not-head"]
    assert found[0].details["head"] == b and b in found[0].message
    (root / c_change.path).unlink()  # refused, so never merged: the tree is as it was
    _, d_change = make(root, "Third reading.", supersedes=b)
    # carol's edit of carol's own written words shows at once (F21-Q10), so it is opened by carol:
    # opened by anyone else it would be refused author-not-opener (F21-Q14)
    assert codes(root, d_change, author="carol") == []
    (root / d_change.path).unlink()  # D was a probe; B stays the head

    sign(root, b, STEWARD, keys[STEWARD])
    e, e_change = make(root, "A correction of the signed text.", supersedes=b)
    assert codes(root, e_change, author=STRANGER) == []
    assert codes(root, e_change, author=STEWARD) == []
    assert codes(root, e_change, author=CURATOR) == []
    kind = "statement" if record == "gloss" else "proof"
    [chain] = [c for c in chains_of(root, kind) if c["current"] == e]
    key = "whole" if record == "gloss" else "overview"
    assert chain["shown"] == [{"key": key, "version": b, "state": "verified"}]
    assert chain["pending"] == [{"key": key, "version": e, "state": "pending"}]
    (root / e_change.path).unlink()
    # Anyone may start a chain of their own instead.
    _, fresh = make(root, "My own account.")
    assert codes(root, fresh, author=STRANGER) == []


def test_a_version_supersedes_its_own_subject_only(root: Path) -> None:
    """R6: a gloss superseding a gloss of another file, or an unknown hash, is not the head of
    anything on its subject."""
    witness, _ = gloss(root, "The witness.", kind="witness")
    _, change = gloss(root, "The statement.", supersedes=witness)
    assert codes(root, change) == ["record-not-head"]
    _, unknown = gloss(root, "The statement.", supersedes="e" * 64)
    assert codes(root, unknown) == ["record-not-head"]


# --- AC6 ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "author", "opened_by", "expected"),
    [
        ("gloss", "carol", "carol", []),
        ("gloss", STEWARD, STEWARD, []),
        ("gloss", CURATOR, CURATOR, []),
        ("gloss", STRANGER, STRANGER, ["withdrawal-unauthorized"]),
        ("explainer", "carol", "carol", []),
        ("explainer", STRANGER, STRANGER, ["withdrawal-unauthorized"]),
    ],
)
def test_withdrawal_and_current_version(
    root: Path, record: str, author: str, opened_by: str, expected: list[str]
) -> None:
    """AC6: a chain A<-B<-C with C withdrawn by its author, a steward or a curator passes and
    the current version is B; by a third party it is refused."""
    make = gloss if record == "gloss" else explainer
    a, _ = make(root, "First.")
    b, _ = make(root, "Second.", supersedes=a)
    c, _ = make(root, "Third.", supersedes=b)
    change = withdraw(root, f"{record}/{c}.md", author, n=1)
    assert codes(root, change, author=opened_by) == expected
    if expected:
        return
    kind = "statement" if record == "gloss" else "proof"
    [chain] = chains_of(root, kind)
    assert chain["current"] == b
    assert [(v["hash"], v["withdrawn"]) for v in chain["versions"]] == [
        (a, False),
        (b, False),
        (c, True),
    ]
    # The head is B again: a fourth version supersedes it, and C cannot be superseded.
    _, d_change = make(root, "Fourth.", supersedes=b)
    # carol's own edit, so opened by carol (F21-Q10, Q14)
    assert [d.message for d in problems(root, d_change, author="carol")] == []
    _, after_c = make(root, "After the withdrawn one.", supersedes=c)
    assert codes(root, after_c) == ["record-not-head"]


def test_a_withdrawal_names_a_version_on_the_record(root: Path) -> None:
    change = withdraw(root, f"gloss/{'f' * 64}.md", "carol", n=1)
    assert codes(root, change, author=CURATOR) == ["withdrawal-unknown-record"]


def test_a_status_withdrawal_stays_a_curator_record(root: Path) -> None:
    """F08-T31 unchanged: a withdrawal of a status record is classified as before, by curator."""
    change = withdraw(root, "status/2026-09-09-1.yaml", STRANGER, n=1)
    classification = modes.classify([change], author=STRANGER, graph_root=root)
    assert [d.code for d in classification.problems] == ["curator-unlisted"]


def test_a_definition_gloss_chain_lives_at_the_target(root: Path, keys: dict[str, Path]) -> None:
    """R1, R7, R8 at the target level: a definition module's gloss, its signature and its
    withdrawal sit under targets/<id>/."""
    defs = root / "targets" / TARGET / "defs"
    (defs / "Prime.lean").write_text("def Opn.P (n : Nat) : Prop := 2 ≤ n\n", encoding="utf-8")
    doc = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {
            "kind": "definition",
            "node": None,
            "module": "Prime.lean",
            "lean_hash": schemas.content_hash((defs / "Prime.lean").read_bytes()),
        },
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    path = put(root / "targets" / TARGET / "gloss", front(doc, "A number at least two.\n"))
    assert codes(root, Change("A", rel(root, path))) == []
    signature = sign_gloss(root, path.stem, CURATOR, keys[CURATOR], node=None)
    assert codes(root, signature, author=CURATOR) == []
    gone = withdraw(root, f"gloss/{path.stem}.md", "carol", n=1, node=None)
    assert codes(root, gone, author="carol") == []
    out = loads(generate(root), f"targets/{TARGET}/glosses.json")
    [subject] = [s for s in out["subjects"] if s["kind"] == "definition"]
    assert subject["module"] == "Prime.lean" and subject["file"] == "defs/Prime.lean"
    [chain] = subject["chains"]
    assert chain["current"] is None
    [version] = chain["versions"]
    assert version["withdrawn"] is True and version["signatures"][0]["signer"] == CURATOR


# --- R8: gloss signatures ----------------------------------------------------------------------


def test_a_gloss_signature_is_a_stewards_or_curators(root: Path, keys: dict[str, Path]) -> None:
    """R8: a steward's or a curator's signature on a gloss passes; a stranger's is
    ``signer-unlisted``; one on a gloss not there is ``gloss-absent``; an altered sentence is
    ``affirmation-differs``."""
    digest, _ = gloss(root, "Words.")
    assert codes(root, sign_gloss(root, digest, STEWARD, keys[STEWARD])) == []
    assert codes(root, sign_gloss(root, digest, CURATOR, keys[CURATOR])) == []
    assert codes(root, sign_gloss(root, digest, STRANGER, keys[STRANGER])) == ["signer-unlisted"]
    with pytest.raises(glosses.GlossError):
        glosses.sign(
            node_dir(root), "f" * 64, target_id=TARGET, node_id=NODE, signer_login=CURATOR,
            date="2026-10-04", key_path=keys[CURATOR], signer=SIGNER,
        )  # fmt: skip
    change = sign_gloss(root, digest, CURATOR, keys[CURATOR])
    path = root / change.path
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["affirmation"] = "I skimmed it."
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert codes(root, change) == ["affirmation-differs", "signature-invalid"]
    assert glosses.AFFIRMATION == (
        "I have read this against the Lean it names, and it says what the Lean says."
    )


# --- AC7 ---------------------------------------------------------------------------------------


def test_digestion_counts_explainers_only(root: Path, keys: dict[str, Path]) -> None:
    """AC7, restated by F21-R15 (per section): a resolved target whose closure nodes all carry
    signed explainers is ``explained``. A person's newer version leaves it ``explained`` — the
    change to verified words is pending and the verified words stay shown. Withdrawing the signed
    version shows the newer words as written, which makes it ``undigested``; signing the newer
    version makes it ``explained`` again. Signing every gloss changes no status, grade or
    digestion state."""
    for n, node in enumerate(("tutorial-and-swap", "and-reassoc", ROOT_NODE), start=1):
        attest(root, node, n=n)
    heads: dict[str, str] = {}
    for node in ("tutorial-and-swap", "and-reassoc", ROOT_NODE):
        heads[node], _ = explainer(root, f"Why {node} holds.", node=node)
        sign_explainer(root, heads[node], STEWARD, keys[STEWARD], node=node)

    def row() -> dict[str, Any]:
        return dict(loads(generate(root), "targets/index.json")["targets"][0])

    assert row()["status"] == "resolved"
    assert row()["digestion"]["state"] == "explained"
    newer, _ = explainer(root, "A clearer account.", supersedes=heads[NODE], node=NODE)
    assert row()["digestion"]["state"] == "explained"  # the edit is pending (F21-R11)
    withdraw(root, f"explainer/{heads[NODE]}.md", STEWARD, n=1, node=NODE)
    assert row()["digestion"]["state"] == "undigested"
    assert row()["digestion"]["closure_explained"] == 2
    sign_explainer(root, newer, CURATOR, keys[CURATOR], node=NODE)
    assert row()["digestion"]["state"] == "explained"

    before = generate(root)
    for node in ("tutorial-and-swap", "and-reassoc", ROOT_NODE):
        for kind in ("statement", "witness"):
            digest, _ = gloss(root, f"The {kind} of {node}.", node=node, kind=kind)
            sign_gloss(root, digest, CURATOR, keys[CURATOR], node=node)
    after = generate(root)
    for rel_path in ("targets/index.json", f"targets/{TARGET}/graph.json", "frontier.json"):
        assert after.files[Path(rel_path)] == before.files[Path(rel_path)], rel_path
    assert after.meta_status == before.meta_status
    glossed = json.loads(after.files[Path(f"targets/{TARGET}/glosses.json")])
    signed = [
        v
        for s in glossed["subjects"]
        for c in s["chains"]
        for v in c["versions"]
        if s["kind"] in ("statement", "witness") and v["signatures"]
    ]
    assert len(signed) == 6


def test_a_pre_f20_explainer_is_a_chain_of_one(root: Path, keys: dict[str, Path]) -> None:
    """Q: an explainer filed before F20 names no proof; it is read as a one-version chain on the
    node's Proof.lean, so a signed one still counts, and a v1 version may supersede it — since
    F21-R13 from anyone, its change to the signed words pending."""
    text = "---\nauthor: someone\ndate: 2026-09-16\n---\nWhy it holds.\n"
    legacy = put(node_dir(root) / "explainer", text).stem
    sign_explainer(root, legacy, STEWARD, keys[STEWARD])
    [chain] = chains_of(root, "proof")
    assert chain["current"] == legacy
    assert chain["versions"][0]["schema"] is None and chain["versions"][0]["author"] == "someone"
    _, change = explainer(root, "Anchored now.", supersedes=legacy)
    assert codes(root, change, author=STEWARD) == []
    assert codes(root, change, author=STRANGER) == []


def test_the_product_lists_every_lean_file(root: Path) -> None:
    """R9: every statement, witness and relation of every node, and every merged proof artifact,
    is a subject, with or without chains, in the target's structural order."""
    doc = loads(generate(root), f"targets/{TARGET}/glosses.json")
    assert doc["schema"] == "glosses/v2" and doc["target"] == TARGET
    seen = {(s["kind"], s["node"]) for s in doc["subjects"]}
    for node in ("tutorial-and-swap", "and-reassoc", ROOT_NODE):
        assert {("statement", node), ("witness", node), ("proof", node)} <= seen
    assert all(s["chains"] == [] for s in doc["subjects"])


# --- F20-T6: who is acting when the service opened the pull request ----------------------------
#
# Every pull request the service opens is authored by its GitHub App, so the host's author names
# nobody. The service writes the identity it authenticated into the record's own ``author`` (as
# F18-Q7(a): the service writes only the authenticated pseudonym), so a pull request opened by the
# service's login is judged by that field; a hand-opened one stays judged by its opener, whatever
# its record claims.

SERVICE = config.DEFAULT_SERVICE_LOGIN


def codes_by(root: Path, change: Change, opened_by: str, **kwargs: Any) -> list[str]:
    classification = modes.classify([change], author=opened_by, graph_root=root, **kwargs)
    if not classification.ok:
        return [d.code for d in classification.problems]
    return [d.code for d in modes.check(root, classification)]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize(
    ("record_author", "expected"),
    [
        ("carol", []),  # the version's author, through the service
        (STEWARD, []),  # an active steward, through the service
        (f"{CURATOR}-pseudonym", []),  # a listed curator, by the pseudonym the service writes
        (STRANGER, ["withdrawal-unauthorized"]),
    ],
)
def test_a_service_withdrawal_acts_for_its_records_author(
    root: Path, record: str, record_author: str, expected: list[str]
) -> None:
    make = gloss if record == "gloss" else explainer
    a, _ = make(root, "First.")
    change = withdraw(root, f"{record}/{a}.md", record_author, n=1)
    assert codes_by(root, change, SERVICE) == expected


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_hand_opened_withdrawal_is_judged_by_its_opener(root: Path, record: str) -> None:
    """A record that names the version's author proves nothing in a pull request someone else
    opened by hand: the stranger is judged, and a steward opening it by hand passes."""
    make = gloss if record == "gloss" else explainer
    a, _ = make(root, "First.")
    change = withdraw(root, f"{record}/{a}.md", "carol", n=1)
    assert codes_by(root, change, STRANGER) == ["withdrawal-unauthorized"]
    assert codes_by(root, change, STEWARD) == []
    assert codes_by(root, change, "carol") == []


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_service_supersede_of_a_signed_version_acts_for_its_author(
    root: Path, keys: dict[str, Path], record: str
) -> None:
    """R6 through the service, restated by F21-R13: a version superseding a signed one passes
    whoever acts for it — a steward, a curator, a stranger, through the service or by hand — since
    F20's ``signed-supersede`` is withdrawn; a person's change to the signed words is pending."""
    make = gloss if record == "gloss" else explainer
    sign = sign_gloss if record == "gloss" else sign_explainer
    b, _ = make(root, "Signed reading.")
    sign(root, b, CURATOR, keys[CURATOR])
    _, by_steward = make(root, "The steward's correction.", supersedes=b, author=STEWARD)
    assert codes_by(root, by_steward, SERVICE) == []
    assert codes_by(root, by_steward, STRANGER) == []
    (root / by_steward.path).unlink()
    _, by_curator = make(root, "The curator's.", supersedes=b, author=f"{CURATOR}-pseudonym")
    assert codes_by(root, by_curator, SERVICE) == []
    (root / by_curator.path).unlink()
    _, by_stranger = make(root, "A stranger's correction.", supersedes=b, author=STRANGER)
    assert codes_by(root, by_stranger, SERVICE) == []


def test_the_service_login_is_configuration(root: Path) -> None:
    """``OPN_SERVICE_LOGIN`` names the App; any other login is a person opening by hand."""
    a, _ = gloss(root, "First.")
    change = withdraw(root, f"gloss/{a}.md", "carol", n=1)
    assert codes_by(root, change, "opn-app[bot]", service_login="opn-app[bot]") == []
    assert codes_by(root, change, "opn-app[bot]") == ["withdrawal-unauthorized"]
    assert config.load({}).service_login == SERVICE == "open-proof-network[bot]"
    assert config.load({"OPN_SERVICE_LOGIN": "opn-app[bot]"}).service_login == "opn-app[bot]"


def test_the_classify_command_reads_what_a_withdrawal_withdraws(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The workflow's entry point gives ``classify`` the checkout, so a steward's withdrawal of a
    gloss version is the explainer mode and not a curator record (F20-R7)."""
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(root.parent),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    a, _ = gloss(root, "First.")
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    withdraw(root, f"gloss/{a}.md", STEWARD, n=1)
    git("add", "-A")
    git("commit", "-q", "-m", "withdraw")
    code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1", "--author", STEWARD])
    out = json.loads(capsys.readouterr().out)
    assert [p["code"] for p in out["problems"]] == []
    assert out["mode"] == "explainer" and code == 0
