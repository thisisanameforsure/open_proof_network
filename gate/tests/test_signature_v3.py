"""F23-T2 / AC7 (gate half), AC8: ``gloss-signature/v3`` and ``explainer-signature/v3`` (R10, R11;
D-3 v3.33).

A v3 signature made through the service is signed with the network's approval key for a signed-in
steward of the target or a curator, and means what an SSH signature means. At the gate it is the
signer's own act when its key is ``keys/approval.pub`` in the merge's parent tree — the service
opened the pull request and is the only holder of that key — and refused ``signature-invalid``
when the key is any other. After its merge it is read exactly as v2: the sections it names are
verified, the version's author earns the write-up line once, and the signer earns nothing.

D-3 v3.33: a version a steward or curator wrote may be signed by that same author. Its sections
are verified, and it earns once, on the write-up line, as the author's work; the signature earns
nothing beyond that.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_modes import CURATOR
from test_writeup_credit import STEWARD, Repo

from opn_gate import config, explainers, glosses, modes, schemas, sections, signed
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

SIGNER = SshKeygenSigner()
SERVICE = config.DEFAULT_SERVICE_LOGIN
TARGET = "euclid-primes"
NODE = "and-reassoc"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("signature-v3-keys")
    out: dict[str, Path] = {}
    for who in (CURATOR, STEWARD, "approval", "stranger"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Graph(Repo):
    """``test_writeup_credit``'s repository, with the approval key published on its base."""

    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        super().__init__(tmp_path, keys)
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / signed.APPROVAL_KEY_PATH).write_text(
            public_key_for(keys["approval"]) + "\n", encoding="utf-8"
        )
        self.merge("publish the approval key", by=CURATOR)

    def base(self, path: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "show", f"HEAD:{path}"],
            capture_output=True, check=False, env=self.env,
        )  # fmt: skip
        return proc.stdout if proc.returncode == 0 else None

    def _write(self, doc: dict[str, Any], key: str, path: Path) -> Change:
        doc = schemas.validate(signed.sign(doc, self.keys[key], SIGNER), str(doc["schema"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return Change("A", path.relative_to(self.root).as_posix())

    def approve_gloss(self, digest: str, by: str, *, key: str = "approval") -> Change:
        doc = glosses.signature_document_v3(
            target_id=TARGET, node_id=NODE, gloss=digest, signer_login=by, date="2026-10-07",
            sections=[sections.WHOLE],
        )  # fmt: skip
        return self._write(doc, key, glosses.next_signature_path(self.node_dir, digest))

    def approve_explainer(self, digest: str, by: str, *, key: str = "approval") -> Change:
        doc = explainers.signature_document_v3(
            target_id=TARGET, node_id=NODE, explainer_hash=digest, signer_login=by,
            date="2026-10-07", sections=None,
        )  # fmt: skip
        return self._write(doc, key, explainers.next_path(self.node_dir, digest))

    def codes(self, change: Change, *, opened_by: str = SERVICE) -> list[str]:
        classification = modes.classify([change], author=opened_by, graph_root=self.root)
        assert classification.mode == "explainer", classification.as_dict()
        return [d.code for d in modes.check(self.root, classification, base=self.base)]


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


# --- at the gate --------------------------------------------------------------------------------


def test_a_stewards_approval_through_the_service_is_admitted(graph: Graph) -> None:
    """AC7: the service opens the signature for a signed-in steward; it is their act."""
    gloss = graph.gloss("bob")
    graph.merge("bob's gloss", by="bob")
    assert graph.codes(graph.approve_gloss(gloss, STEWARD)) == []
    explainer = graph.explainer("bob")
    graph.merge("bob's explainer", by="bob")
    assert graph.codes(graph.approve_explainer(explainer, CURATOR)) == []


def test_an_approval_signed_by_another_key_is_refused(graph: Graph) -> None:
    """A ``via: approval-key`` signature that verifies under a key other than the parent tree's
    approval key is not the service's, whoever it names."""
    gloss = graph.gloss("bob")
    graph.merge("bob's gloss", by="bob")
    found = graph.codes(graph.approve_gloss(gloss, STEWARD, key="stranger"))
    assert "signature-invalid" in found
    explainer = graph.explainer("bob")
    graph.merge("bob's explainer", by="bob")
    found = graph.codes(graph.approve_explainer(explainer, STEWARD, key="stranger"))
    assert "signature-invalid" in found


def test_an_approval_for_a_login_with_no_role_is_refused(graph: Graph) -> None:
    gloss = graph.gloss("bob")
    graph.merge("bob's gloss", by="bob")
    assert "signer-unlisted" in graph.codes(graph.approve_gloss(gloss, "someone-else"))


# --- after the merge: read as v2 ----------------------------------------------------------------


def test_an_approval_verifies_the_sections_and_credits_the_author(
    graph: Graph, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC7: after the merge the sections are verified and the author, never the signer, is
    credited once."""
    explainer = graph.explainer("bob")
    graph.merge("bob's explainer", by="bob")
    assert not explainers.explained(graph.node_dir, SIGNER)
    graph.approve_explainer(explainer, STEWARD)
    commit = graph.merge("the steward approves", by=SERVICE)
    assert explainers.explained(graph.node_dir, SIGNER)
    out = graph.ledger(capsys, commit)
    assert out["earned"] is True, out
    [entry] = graph.entries("bob")
    assert entry["line"] == "write-up" and entry["artifact"] == f"explainer/{explainer}.md"
    assert set(graph.ledger_files()) == {"bob.json"}

    gloss = graph.gloss("carol")
    graph.merge("carol's gloss", by="carol")
    graph.approve_gloss(gloss, CURATOR)
    graph.merge("the curator approves", by=SERVICE)
    assert [s.signer for s in glosses.valid_signatures(graph.node_dir, SIGNER)[gloss]] == [CURATOR]


# --- D-3 v3.33: one's own version ---------------------------------------------------------------


def test_a_stewards_own_version_signed_by_them_is_verified_and_earns_once(
    graph: Graph, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC8: the steward wrote the explainer and approves it through the site: its sections are
    verified, the write-up line carries one entry for them, and a second signature (a curator's)
    adds nothing."""
    own = graph.explainer(STEWARD)
    graph.merge("the steward's explainer", by=SERVICE)
    change = graph.approve_explainer(own, STEWARD)
    assert graph.codes(change) == []
    out = graph.ledger(capsys, graph.merge("the steward approves their own", by=SERVICE))
    assert out["earned"] is True, out
    assert explainers.explained(graph.node_dir, SIGNER)
    [entry] = graph.entries(STEWARD)
    assert entry["line"] == "write-up" and entry["artifact"] == f"explainer/{own}.md"

    graph.approve_explainer(own, CURATOR)
    out = graph.ledger(capsys, graph.merge("the curator approves too", by=SERVICE))
    assert out["earned"] is False and "already" in out["reason"], out
    assert len(graph.entries(STEWARD)) == 1
