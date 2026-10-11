"""F21-T4 / AC3: credit on approval (R3, R4; D-19 v3.31, Q3).

A gloss or explainer version earns its author one ``write-up`` line when a steward of its target
or a listed curator signs it, and the post-merge ``opn-gate ledger`` step is what writes it. The
line credits the version's ``author`` — never the git author of the merge, who is the *signer* —
once per version, however many signatures follow; a draft (no author), a signature on one's own
version and an unsigned merge earn nothing. Every case runs on a real repository: the version
merged in an earlier commit and the signature as the merge under test, the shape the record has.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from test_cli_sandboxed import run
from test_modes import CURATOR, write_curators

from opn_gate import cli, explainers, glosses, ledger, schemas, signed, steward
from opn_gate.signer import SshKeygenSigner

TARGET = "euclid-primes"
NODE = "and-reassoc"  # take_in's root, which carries the fixture's proof
STEWARD = "alice-steward"
CURATOR_PSEUDONYM = f"{CURATOR}-pseudonym"  # write_curators pairs each login with this
MODULE = "Primes.lean"
DEFS = {MODULE: "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
SIGNER = SshKeygenSigner()
DRAFTER = {
    "name": "opn-drafter",
    "model": "a-model",
    "model_version": "1",
    "input_commit": "a" * 40,
}


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("writeup-keys")
    out: dict[str, Path] = {}
    for who in (CURATOR, STEWARD):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Repo:
    """A curated target with a definition module, its curator listed and a steward committed,
    as a git repository; each ``merge`` is one commit authored by whoever opened it."""

    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        self.root = copy_graph(tmp_path)
        take_in(self.root, TARGET, defs=DEFS)
        write_curators(self.root, CURATOR)
        steward.write(
            self.root / "targets" / TARGET,
            action=steward.COMMIT,
            login=STEWARD,
            name="Alice",
            link="https://orcid.org/0000-0002-1825-0097",
            date="2026-09-16",
            key_path=keys[STEWARD],
            signer=SIGNER,
        )
        self.keys = keys
        self.env = {
            "GIT_COMMITTER_NAME": "committer",
            "GIT_COMMITTER_EMAIL": "c@x",
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        }
        self.git("init", "-q")
        self.merge("seed", by="seed")

    @property
    def target_dir(self) -> Path:
        return self.root / "targets" / TARGET

    @property
    def node_dir(self) -> Path:
        return self.target_dir / "nodes" / NODE

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            env=self.env,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def merge(self, message: str, *, by: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--author", f"{by} <{by}@x>", "-m", message)
        return self.git("rev-parse", "HEAD")

    def file(self, parent: Path, directory: str, text: str) -> str:
        digest = str(schemas.content_hash(text.encode("utf-8")))
        (parent / directory).mkdir(parents=True, exist_ok=True)
        (parent / directory / f"{digest}.md").write_text(text, encoding="utf-8")
        return digest

    def explainer(self, author: str | None, *, drafter: dict[str, Any] | None = None) -> str:
        proof = explainers.first_proof(self.node_dir)
        doc = {
            "schema": "explainer/v1",
            "target": TARGET,
            "node": NODE,
            "proof": proof,
            "supersedes": None,
            "author": author,
            "drafter": drafter,
            "date": "2026-10-04",
            "licence": "CC-BY-4.0",
        }
        body = f"Reassociate the conjunction, as {author or 'the drafter'} tells it.\n"
        text = "---\n" + str(yaml.safe_dump(doc, sort_keys=False)) + "---\n" + body
        return self.file(self.node_dir, "explainer", text)

    def gloss(self, author: str | None, *, node: str | None = NODE) -> str:
        if node is None:
            parent, kind, module = self.target_dir, "definition", MODULE
            lean = self.target_dir / "defs" / MODULE
        else:
            parent, kind, module = self.node_dir, "statement", None
            lean = self.node_dir / "Statement.lean"
        doc = {
            "schema": "gloss/v1",
            "target": TARGET,
            "subject": {
                "kind": kind,
                "node": node,
                "module": module,
                "lean_hash": schemas.content_hash(lean.read_bytes()),
            },
            "supersedes": None,
            "author": author,
            "drafter": None if author else DRAFTER,
            "date": "2026-10-04",
            "licence": "CC-BY-4.0",
        }
        text = "---\n" + str(yaml.safe_dump(doc, sort_keys=False)) + "---\nWhat it says.\n"
        return self.file(parent, "gloss", text)

    def sign_explainer(self, digest: str, by: str) -> Path:
        return explainers.sign(
            self.node_dir, digest, target_id=TARGET, signer_login=by, date="2026-10-05",
            key_path=self.keys[by], signer=SIGNER,
        )  # fmt: skip

    def sign_gloss(self, digest: str, by: str, *, node: str | None = NODE) -> Path:
        parent = self.node_dir if node is not None else self.target_dir
        return glosses.sign(
            parent, digest, target_id=TARGET, node_id=node, signer_login=by, date="2026-10-05",
            key_path=self.keys[by], signer=SIGNER,
        )  # fmt: skip

    def sign_explainer_v2(self, digest: str, by: str, sections: list[str]) -> Path:
        """An ``explainer-signature/v2`` naming the sections it approves (F21-R13)."""
        doc = {
            "schema": "explainer-signature/v2",
            "target": TARGET,
            "node": NODE,
            "explainer": digest,
            "affirmation": explainers.AFFIRMATION,
            "signer": by,
            "date": "2026-10-05",
            "sections": sections,
        }
        doc = schemas.validate(signed.sign(doc, self.keys[by], SIGNER), "explainer-signature/v2")
        path = explainers.next_path(self.node_dir, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return path

    def ledger(self, capsys: pytest.CaptureFixture[str], commit: str) -> dict[str, Any]:
        code, out, err = run(capsys, "ledger", "--graph", str(self.root), "--commit", commit)
        assert code == cli.EXIT_PASS, err
        return out

    def entries(self, identity: str) -> list[dict[str, Any]]:
        return ledger.entries_of(ledger.load(self.root, identity))

    def ledger_files(self) -> dict[str, bytes]:
        directory = self.root / "ledger"
        if not directory.is_dir():
            return {}
        return {p.name: p.read_bytes() for p in sorted(directory.iterdir())}


@pytest.fixture
def repo(tmp_path: Path, keys: dict[str, Path]) -> Repo:
    return Repo(tmp_path, keys)


# --- explainers ---------------------------------------------------------------------------------


def test_a_curators_signature_credits_the_explainers_author_once(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: one write-up entry for the author (not the signer, who is the merge's git author),
    naming the version's path under its node; a replay of the same merge writes nothing, and a
    second signature on the same version — by the steward — adds no second entry (Q3)."""
    digest = repo.explainer("bob")
    repo.merge("bob's explainer", by="bob")
    assert repo.ledger_files() == {}  # R4: the unsigned merge itself earned nothing

    repo.sign_explainer(digest, CURATOR)
    commit = repo.merge("curator signs", by=CURATOR)
    out = repo.ledger(capsys, commit)
    assert out["earned"] is True, out
    [entry] = repo.entries("bob")
    assert entry["line"] == "write-up"
    assert entry["target"] == TARGET and entry["node"] == NODE
    assert entry["artifact"] == f"explainer/{digest}.md"
    assert entry["merge_commit"] == commit and entry["status"] == "active"
    assert set(repo.ledger_files()) == {"bob.json"}  # the signer is never credited

    before = repo.ledger_files()
    out = repo.ledger(capsys, commit)
    assert out["earned"] is False and repo.ledger_files() == before

    repo.sign_explainer(digest, STEWARD)
    second = repo.merge("steward signs too", by=STEWARD)
    out = repo.ledger(capsys, second)
    assert out["earned"] is False, out
    assert "already" in out["reason"]
    assert repo.ledger_files() == before


def test_a_signature_on_a_draft_credits_nobody(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: a draft has no author, so its signature earns nothing (R3)."""
    digest = repo.explainer(None, drafter=DRAFTER)
    repo.merge("a merged draft", by="opn-service")
    repo.sign_explainer(digest, CURATOR)
    out = repo.ledger(capsys, repo.merge("curator signs the draft", by=CURATOR))
    assert out["earned"] is False and "draft" in out["reason"], out
    assert repo.ledger_files() == {}


def test_a_steward_signing_their_own_version_earns_once_as_written_work(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-3 v3.33 (F23-R11, AC8), restating F21-AC3's rule of 2026-10-04 ("a signature on one's
    own version earns nothing"), which v3.33 keeps for the *signature*: a steward's or curator's
    own version signed by them earns once, on the write-up line, as their written work, and a
    second signature adds nothing. The author is recognised whether spelled as the signer's login
    or, for a listed curator, as the pseudonym ``curators.json`` pairs it with."""
    own = repo.explainer(STEWARD)
    repo.merge("the steward's explainer", by=STEWARD)
    repo.sign_explainer(own, STEWARD)
    out = repo.ledger(capsys, repo.merge("steward signs own", by=STEWARD))
    assert out["earned"] is True, out
    [entry] = repo.entries(STEWARD)
    assert entry["line"] == "write-up" and entry["artifact"] == f"explainer/{own}.md"
    repo.sign_explainer(own, CURATOR)
    out = repo.ledger(capsys, repo.merge("the curator signs it too", by=CURATOR))
    assert out["earned"] is False and "already" in out["reason"], out

    by_pseudonym = repo.gloss(CURATOR_PSEUDONYM)
    repo.merge("the curator's gloss, through the service", by="opn-service")
    repo.sign_gloss(by_pseudonym, CURATOR)
    out = repo.ledger(capsys, repo.merge("curator signs own", by=CURATOR))
    assert out["earned"] is True, out
    assert len(repo.entries(CURATOR_PSEUDONYM)) == 1
    assert set(repo.ledger_files()) == {f"{STEWARD}.json", f"{CURATOR_PSEUDONYM}.json"}


def test_an_unsigned_explainer_or_gloss_merge_earns_nothing(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """R4: a merged gloss or explainer that is not a signature earns no ledger line."""
    repo.explainer("bob")
    out = repo.ledger(capsys, repo.merge("bob's explainer", by="bob"))
    assert out["earned"] is False, out
    repo.gloss("carol")
    out = repo.ledger(capsys, repo.merge("carol's gloss", by="carol"))
    assert out["earned"] is False, out
    assert repo.ledger_files() == {}


def test_a_v2_signature_naming_some_sections_credits_once(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """R13 with Q3: a signature approves the sections it names, and credit is still once per
    version — a second v2 signature on other sections adds nothing."""
    digest = repo.explainer("bob")
    repo.merge("bob's explainer", by="bob")
    repo.sign_explainer_v2(digest, CURATOR, ["overview"])
    commit = repo.merge("curator approves the overview", by=CURATOR)
    out = repo.ledger(capsys, commit)
    assert out["earned"] is True, out
    [entry] = repo.entries("bob")
    assert entry["artifact"] == f"explainer/{digest}.md" and entry["merge_commit"] == commit

    repo.sign_explainer_v2(digest, STEWARD, ["steps:h1"])
    out = repo.ledger(capsys, repo.merge("steward approves a step", by=STEWARD))
    assert out["earned"] is False, out
    assert len(repo.entries("bob")) == 1


# --- glosses ------------------------------------------------------------------------------------


def test_a_signed_node_gloss_credits_its_author(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3 for glosses: a statement gloss signed by the curator credits its author once."""
    digest = repo.gloss("carol")
    repo.merge("carol's gloss", by="carol")
    repo.sign_gloss(digest, CURATOR)
    commit = repo.merge("curator signs", by=CURATOR)
    out = repo.ledger(capsys, commit)
    assert out["earned"] is True, out
    [entry] = repo.entries("carol")
    assert entry["line"] == "write-up" and entry["node"] == NODE
    assert entry["artifact"] == f"gloss/{digest}.md" and entry["merge_commit"] == commit
    assert set(repo.ledger_files()) == {"carol.json"}

    repo.sign_gloss(digest, STEWARD)
    out = repo.ledger(capsys, repo.merge("steward signs too", by=STEWARD))
    assert out["earned"] is False, out
    assert len(repo.entries("carol")) == 1


def test_a_signed_definition_gloss_credits_its_author(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3 for a definition module's gloss, which sits under the target, not a node. ledger/v1
    has no null node, so the entry carries the target's id there (F21-T4; see the report)."""
    digest = repo.gloss("dave", node=None)
    repo.merge("dave's definition gloss", by="dave")
    repo.sign_gloss(digest, STEWARD, node=None)
    commit = repo.merge("steward signs", by=STEWARD)
    out = repo.ledger(capsys, commit)
    assert out["earned"] is True, out
    [entry] = repo.entries("dave")
    assert entry["line"] == "write-up" and entry["target"] == TARGET
    assert entry["node"] == TARGET
    assert entry["artifact"] == f"gloss/{digest}.md"

    repo.sign_gloss(digest, CURATOR, node=None)
    out = repo.ledger(capsys, repo.merge("curator signs too", by=CURATOR))
    assert out["earned"] is False, out
    assert len(repo.entries("dave")) == 1


def test_a_signed_draft_gloss_credits_nobody(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    digest = repo.gloss(None)
    repo.merge("a merged draft gloss", by="opn-service")
    repo.sign_gloss(digest, CURATOR)
    out = repo.ledger(capsys, repo.merge("curator signs the draft", by=CURATOR))
    assert out["earned"] is False and "draft" in out["reason"], out
    assert repo.ledger_files() == {}
