"""F23-R14 (D-32 v3.33): ``targets-index/v8`` — each active steward says how they were admitted.

A steward made through the site may carry no identity link, and the site labels each steward
self-admitted or admitted by a curator (R14). ``targets-index/v7`` could hold neither: its
``link`` was a required https string and it had no ``admitted_by``. v8 carries ``admitted_by``
(``self``, a curator's login, or ``null`` for a v1 record, which predates the field and was merged
by a curator under the old rule), ``via`` (``ssh`` or ``approval-key``) and a nullable ``link``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import products, schemas, signed, steward
from opn_gate.signer import SshKeygenSigner

TARGET = "euclid-primes"
LINK = "https://orcid.org/0000-0002-1825-0097"
SIGNER = SshKeygenSigner()


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("index-v8-keys")
    out: dict[str, Path] = {}
    for who in ("approval", "bob"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


def test_index_v8_names_how_each_steward_was_admitted(
    tmp_path: Path, keys: dict[str, Path]
) -> None:
    root = copy_graph(tmp_path, publish=True)
    take_in(root, TARGET)
    target = root / "targets" / TARGET
    steward.write(
        target, action=steward.COMMIT, login="bob", name="Bob", link=LINK, date="2026-09-16",
        key_path=keys["bob"], signer=SIGNER,
    )  # fmt: skip
    doc = steward.document_v2(
        target_id=TARGET, action=steward.COMMIT, login="alice", name="Alice", link=None,
        date="2026-10-07", admitted_by=steward.SELF,
    )  # fmt: skip
    doc = schemas.validate(signed.sign(doc, keys["approval"], SIGNER), steward.SCHEMA_V2)
    path = steward.next_path(target)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    prod = products.generate(root, rendered_from="5" * 40, commit_time="2026-10-07T12:00:00Z")
    index = json.loads(prod.files[Path("targets/index.json")])
    assert index["schema"] == "targets-index/v8"
    assert schemas.violations(index, "targets-index/v8") == []
    row = next(t for t in index["targets"] if t["target_id"] == TARGET)
    assert row["stewards"] == [
        {
            "login": "bob",
            "name": "Bob",
            "link": LINK,
            "since": "2026-09-16",
            "admitted_by": None,
            "via": "ssh",
        },
        {
            "login": "alice",
            "name": "Alice",
            "link": None,
            "since": "2026-10-07",
            "admitted_by": "self",
            "via": "approval-key",
        },
    ]
