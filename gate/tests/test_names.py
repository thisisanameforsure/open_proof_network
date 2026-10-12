"""F25-T4 / AC5: display names are read, never rewritten (F25-R6; D-3, D-19 v3.37).

``names/<pseudonym>.yaml`` is one file per pseudonym at the graph root, beside ``policy.json``
(the one other graph-root file a pull request may touch); a later record replaces it and git
history is the trail (F25-Q6). ``opn_gate.names`` is the one reader: ``display_name`` answers the
pseudonym's name, ``None`` when there is no record or the latest record withdrew it (``name:
null``), and a file that does not validate or is not named for its own pseudonym is passed over.
F25-T7's ``palomar.authors`` will call it; the admission half (who may write one) is
``test_modes_registration.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import samples
import yaml

from opn_gate import names, paths

BOB = "bob-prover"
ALICE = "alice-steward"


def write(root: Path, pseudonym: str, stem: str | None = None, **overrides: Any) -> Path:
    where = root / names.DIR
    where.mkdir(exist_ok=True)
    doc = samples.display_name(pseudonym=pseudonym, **overrides)
    path = where / f"{stem or pseudonym}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def test_the_record_lives_at_the_graph_root_beside_policy_json() -> None:
    assert names.path_for(Path("/g"), BOB) == Path("/g") / "names" / f"{BOB}.yaml"
    located = paths.locate(f"names/{BOB}.yaml")
    policy = paths.locate(paths.POLICY_FILE)
    assert located is not None and policy is not None
    assert located.target_id == policy.target_id == paths.GRAPH_SCOPE
    assert located.role == "display-name"


def test_no_record_is_no_name(tmp_path: Path) -> None:
    assert names.display_name(tmp_path, BOB) is None
    assert names.load(tmp_path) == []
    assert names.latest(tmp_path) == {}


def test_the_record_names_its_pseudonym_and_nobody_else(tmp_path: Path) -> None:
    write(tmp_path, BOB, name="Robert Prover", link=None)
    assert names.display_name(tmp_path, BOB) == "Robert Prover"
    assert names.display_name(tmp_path, ALICE) is None
    (record,) = names.load(tmp_path)
    assert (record.pseudonym, record.name, record.link) == (BOB, "Robert Prover", None)
    assert names.latest(tmp_path) == {BOB: record}


def test_a_later_null_record_withdraws_the_name(tmp_path: Path) -> None:
    write(tmp_path, BOB, name="Robert Prover")
    assert names.display_name(tmp_path, BOB) == "Robert Prover"
    write(tmp_path, BOB, name=None, link=None, date="2026-10-13")
    assert names.display_name(tmp_path, BOB) is None
    assert names.latest(tmp_path)[BOB].name is None, "the record stands; the name is withdrawn"


def test_the_link_rides_with_the_name(tmp_path: Path) -> None:
    write(tmp_path, ALICE, name="Alice", link="https://orcid.org/0000-0002-1825-0097")
    assert names.latest(tmp_path)[ALICE].link == "https://orcid.org/0000-0002-1825-0097"


def test_a_file_not_named_for_its_pseudonym_is_passed_over(tmp_path: Path) -> None:
    write(tmp_path, BOB, stem=ALICE, name="Robert Prover")
    assert names.display_name(tmp_path, BOB) is None
    assert names.display_name(tmp_path, ALICE) is None
    assert names.load(tmp_path) == []


def test_a_file_that_does_not_validate_is_passed_over(tmp_path: Path) -> None:
    write(tmp_path, BOB, name="x" * 201)
    assert names.display_name(tmp_path, BOB) is None
    (tmp_path / names.DIR / f"{ALICE}.yaml").write_text("schema: display-name/v1\n: :\n")
    (tmp_path / names.DIR / "notes.txt").write_text("ignored\n")
    assert names.load(tmp_path) == []


def test_only_the_approval_key_and_ssh_are_ways_to_sign(tmp_path: Path) -> None:
    write(tmp_path, BOB, via="password")
    assert names.display_name(tmp_path, BOB) is None
