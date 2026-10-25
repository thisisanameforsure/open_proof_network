"""F31 (D-14 v3.47): the fixture tree the shelving tests share.

The propositional fixture, curated: ``and-swap-reassoc`` is the root, ``and-reassoc`` (``A``)
and ``tutorial-and-swap`` (``T``) its deps. The owner is listed as curator, Alice is an active
steward under her own SSH key, and the approval key is published; ``base`` is the pull request's
parent tree. Holes are written the way the post-merge job writes them, partials the way a merge
leaves them (file plus attestation), proofs with the footprint step 8 measured.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph
from test_modes import CURATOR, write_curators

from opn_gate import context, graph, modes, postmerge, products, schemas, signed, steward
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner, public_key_for

ROOT = "and-swap-reassoc"
A = "and-reassoc"
T = "tutorial-and-swap"
ALICE = "alice-steward"
STRANGER = "mallory"
SERVICE = "open-proof-network[bot]"
SIGNER = SshKeygenSigner()
RENDERED = "5" * 40
NOW = "2026-10-24T12:00:00Z"
MERGE = "4" * 40
ANNEX = "a" * 64


def make_keys(directory: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for who in ("approval", ALICE, CURATOR, STRANGER):
        key = directory / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


class Tree:
    def __init__(self, tmp_path: Path, keys: dict[str, Path]) -> None:
        self.root = copy_graph(tmp_path, publish=True)
        write_curators(self.root, CURATOR)
        self.keys = keys
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / signed.APPROVAL_KEY_PATH).write_text(
            public_key_for(keys["approval"]) + "\n", encoding="utf-8"
        )
        steward.write(
            self.target, action=steward.COMMIT, login=ALICE, name="Alice",
            link="https://orcid.org/0000-0002-1825-0097", date="2026-10-01",
            key_path=keys[ALICE], signer=SIGNER,
        )  # fmt: skip
        self.base_files = {
            signed.APPROVAL_KEY_PATH: (self.root / signed.APPROVAL_KEY_PATH).read_bytes(),
            modes.CURATORS_FILE: (self.root / modes.CURATORS_FILE).read_bytes(),
        }
        self.attested = 0

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET

    @property
    def nodes_dir(self) -> Path:
        return self.target / "nodes"

    def node_dir(self, node_id: str) -> Path:
        return self.nodes_dir / node_id

    def base(self, path: str) -> bytes | None:
        return self.base_files.get(path)

    # --- the tree ---------------------------------------------------------------------------

    def hole(self, child: str, name: str, *, parent: str) -> None:
        """A hole child as the post-merge job writes one, recorded as a dep of ``parent``."""
        node = self.node_dir(child)
        node.mkdir()
        for sub in ("attempts", "annex", "explainer"):
            (node / sub).mkdir()
        obligation = SimpleNamespace(name=name, closed_type="True")
        (node / "Statement.lean").write_text(
            postmerge.child_statement(child, obligation), encoding="utf-8"
        )
        (node / "Context.lean").write_text("/-! no deps -/\n", encoding="utf-8")
        (node / "Witness.lean").write_text("theorem witness : True := trivial\n", encoding="utf-8")
        meta = samples.meta(
            id=child,
            schema="meta/v3",
            origin="skeleton-hole",
            tutorial=False,
            **{"statement-hash": schemas.content_hash((node / "Statement.lean").read_bytes())},
        )
        (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
        parent_meta = self.node_dir(parent) / "META.yaml"
        doc = yaml.safe_load(parent_meta.read_text())
        doc["deps"] = [*doc["deps"], child]
        parent_meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    def lemmas(self, node_id: str, lemmas: list[dict[str, str]]) -> None:
        """``META.yaml``'s ``lemmas`` as the post-merge job writes them (``meta/v6``)."""
        path = self.node_dir(node_id) / "META.yaml"
        doc = yaml.safe_load(path.read_text())
        doc.update(schema="meta/v6", lemmas=lemmas)
        assert schemas.violations(doc, "meta/v6") == [], "the hand-written META is not meta/v6"
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    def _statement_hash(self, node_id: str) -> str:
        return schemas.content_hash((self.node_dir(node_id) / "Statement.lean").read_bytes())

    def _attest(self, doc: dict[str, Any]) -> None:
        self.attested += 1
        (self.root / "attestations").mkdir(exist_ok=True)
        (self.root / "attestations" / f"{self.attested:06d}.json").write_bytes(
            schemas.canonical_json(doc)
        )

    def partial(self, holder: str, holes: list[str], *, path: str) -> str:
        """A merged partial of ``holder``: its file under ``attempts/`` and its passing
        attestation naming the file (step 2) and the holes it made (step 4)."""
        file = self.node_dir(holder) / path
        file.parent.mkdir(exist_ok=True)
        file.write_text(f"theorem x : True := by\n  -- annex: {ANNEX}\n  sorry\n", encoding="utf-8")
        (self.node_dir(holder) / "annex").mkdir(exist_ok=True)
        (self.node_dir(holder) / "annex" / f"{ANNEX}.md").write_text("an outline\n")
        steps = [
            {"step": 1, "name": "toolchain", "result": "pass", "diagnostic": None},
            {
                "step": 2,
                "name": "paths",
                "result": "pass",
                "diagnostic": {
                    "code": "partial-submission",
                    "message": f"a partial proof: {path} (D-12 #5)",
                    "details": {"path": path},
                },
            },
            {
                "step": 4,
                "name": "kernel-replay",
                "result": "pass",
                "diagnostic": {
                    "code": "artifact-partial",
                    "message": "partial",
                    "details": {"holes": holes, "kind": "partial"},
                },
            },
        ]
        self._attest(
            samples.attestation(
                node_id=holder,
                statement_hash=self._statement_hash(holder),
                merge_commit=MERGE,
                artifact_hash=None,
                steps=steps,
            )
        )
        return path

    def prove(self, node_id: str, *, used: list[str] | None = None) -> None:
        """A merged ``Proof.lean`` for ``node_id`` with the footprint step 8 measured."""
        node = self.node_dir(node_id)
        statement = (node / "Statement.lean").read_text(encoding="utf-8")
        proof = node / "Proof.lean"
        if not proof.is_file():  # the fixture's authored nodes carry one; a hole does not
            proof.write_text(statement.replace("sorry", "trivial"), encoding="utf-8")
        self._attest(
            samples.attestation(
                node_id=node_id,
                statement_hash=self._statement_hash(node_id),
                merge_commit=MERGE,
                artifact_hash=schemas.content_hash(proof.read_bytes()),
                footprint={"nodes": list(used or [])},
            )
        )

    def revise(self, node_id: str) -> str:
        """A D-8 revision of ``node_id`` with the statement unchanged: the ``-v2`` node that says
        what it supersedes, and the ``superseded`` status record on the original naming it."""
        new = f"{node_id}-v2"
        revised = self.node_dir(new)
        revised.mkdir()
        for sub in ("attempts", "annex", "explainer"):
            (revised / sub).mkdir()
        for name in ("Statement.lean", "Context.lean", "Witness.lean"):
            text = (self.node_dir(node_id) / name).read_text(encoding="utf-8")
            (revised / name).write_text(text.replace(f"«{node_id}»", f"«{new}»"), encoding="utf-8")
        meta = yaml.safe_load((self.node_dir(node_id) / "META.yaml").read_text())
        meta.update({"id": new, "schema": "meta/v4", "supersedes": node_id})
        meta["statement-hash"] = schemas.content_hash((revised / "Statement.lean").read_bytes())
        (revised / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
        status = self.node_dir(node_id) / "status"
        status.mkdir()
        (status / "2026-10-24-1.yaml").write_text(
            yaml.safe_dump(samples.node_status(status="superseded", reference=new)),
            encoding="utf-8",
        )
        return new

    # --- the record -------------------------------------------------------------------------

    def document(self, node_id: str, **overrides: Any) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema": "shelving/v1",
            "node": node_id,
            "action": "shelved",
            "scope": "node",
            "route": None,
            "cause": "This branch does not serve the root.",
            "contributor": ALICE,
            "date": "2026-10-24T10:00:00Z",
            "via": signed.VIA_SSH,
            "key": None,
            "signature": None,
        }
        doc.update(overrides)
        return doc

    def write(self, doc: dict[str, Any], stamp: str | None = None) -> Change:
        """The record under ``nodes/<node>/shelving/<stamp>-<login>.yaml``."""
        stamp = stamp or str(doc["date"]).replace("-", "").replace(":", "")
        name = f"{stamp}-{doc['contributor']}.yaml"
        path = self.node_dir(str(doc["node"])) / "shelving" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return Change("A", path.relative_to(self.root).as_posix())

    def signed_by(
        self,
        who: str,
        node_id: str,
        *,
        key: str | None = None,
        via: str = signed.VIA_SSH,
        date: str = "2026-10-24T10:00:00Z",
        **overrides: Any,
    ) -> Change:
        """A record by ``who``, signed with ``key``'s private half (their own by default)."""
        doc = self.document(node_id, contributor=who, date=date, via=via, **overrides)
        doc = signed.sign(doc, self.keys[key or who], SIGNER)
        return self.write(doc)

    def shelve(self, who: str, node_id: str, **overrides: Any) -> Change:
        """An approval-key record through the service for ``who``, the live shape."""
        return self.signed_by(
            who, node_id, key="approval", via=signed.VIA_APPROVAL_KEY, **overrides
        )

    # --- the gate and the products ----------------------------------------------------------

    def classify(self, change: Change, *, opened_by: str = SERVICE) -> modes.Classification:
        return modes.classify([change], author=opened_by, graph_root=self.root)

    def codes(self, change: Change, *, opened_by: str = SERVICE) -> list[str]:
        classification = self.classify(change, opened_by=opened_by)
        assert classification.ok, classification.as_dict()
        assert classification.mode == "append", classification.as_dict()
        return [d.code for d in modes.check(self.root, classification, base=self.base)]

    def check(
        self,
        changes: list[Change],
        *,
        opened_by: str = SERVICE,
        base: Any = None,
    ) -> tuple[str | None, list[str]]:
        """The mode and the codes of a pull request of any mode, with ``base`` (default: this
        tree's) as the merge's parent."""
        classification = modes.classify(changes, author=opened_by, graph_root=self.root)
        if not classification.ok:
            return None, [d.code for d in classification.problems]
        found = modes.check(self.root, classification, base=base or self.base)
        return classification.mode, [d.code for d in found]

    def load(self) -> graph.TargetGraph:
        return graph.load_target(self.root, TARGET)

    def render(self) -> products.Products:
        return products.generate(self.root, rendered_from=RENDERED, commit_time=NOW)

    def rows(self, prod: products.Products) -> dict[str, dict[str, Any]]:
        doc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
        return {n["node_id"]: dict(n) for n in doc["nodes"]}

    def frontier(self, prod: products.Products) -> set[str]:
        doc = json.loads(prod.files[Path("frontier.json")])
        return {e["node_id"] for e in doc["entries"] if e["target_id"] == TARGET}

    def bundle(self, prod: products.Products, node_id: str) -> dict[str, Any]:
        return dict(json.loads(prod.files[Path(context.context_path(TARGET, node_id))]))
