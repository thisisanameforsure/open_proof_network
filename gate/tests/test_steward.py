"""F15-T3: steward records — signed with the steward's own key, append-only, the active set
(R1, R2; AC1, AC2; D-32 v3.17).

Every record here is signed by a real ``ssh-keygen`` through the ``Signer`` seam, because the
rule under test is about signatures: a tampered body, a foreign key on a step-down and an
altered sentence each have to count for nothing, and only a real signature can show that a real
one counts. The keys are throwaway ed25519 pairs made per module.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import cli, schemas, signed, steward
from opn_gate.signer import SshKeygenSigner
from opn_gate.steward import StewardError

TARGET = "euclid-primes"
ALICE = "alice-steward"
BOB = "bob-steward"
LINK = "https://orcid.org/0000-0002-1825-0097"
DATE = "2026-09-16T10:00:00Z"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """One ed25519 private key per login, plus a stranger's."""
    d = tmp_path_factory.mktemp("steward-keys")
    out: dict[str, Path] = {}
    for who in (ALICE, BOB, "stranger"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root)
    return root / "targets" / TARGET


SIGNER = SshKeygenSigner()


def commit(target: Path, keys: dict[str, Path], login: str, date: str = DATE) -> Path:
    return steward.write(
        target,
        action=steward.COMMIT,
        login=login,
        name=f"{login} (name)",
        link=LINK,
        date=date,
        key_path=keys[login],
        signer=SIGNER,
    )


def step_down(target: Path, keys: dict[str, Path], login: str, *, key: str | None = None) -> Path:
    return steward.write(
        target, action=steward.STEP_DOWN, login=login, date=DATE, key_path=keys[key or login],
        signer=SIGNER,
    )  # fmt: skip


def active_logins(target: Path) -> list[str]:
    return [s.login for s in steward.active(target, SIGNER)]


def files(target: Path) -> list[str]:
    directory = target / "stewards"
    return sorted(p.name for p in directory.iterdir()) if directory.is_dir() else []


# --- AC1: the record round trip, and the refusals that write nothing ------------------------------


def test_record_round_trip(target: Path, keys: dict[str, Path]) -> None:
    """AC1: ``steward commit`` writes one ``steward/v1`` record that verifies under its own key
    and makes the login active, with the commitment sentence verbatim."""
    path = commit(target, keys, ALICE)
    assert path == target / "stewards" / "1.yaml"
    doc = schemas.load_yaml(path, "steward/v1")
    assert doc["login"] == ALICE and doc["action"] == "commit"
    assert doc["commitment"] == steward.COMMITMENT
    assert doc["key"].startswith("ssh-ed25519 ")
    assert signed.verifies(doc, SIGNER)
    assert steward.active(target, SIGNER) == [
        steward.Steward(ALICE, f"{ALICE} (name)", LINK, "2026-09-16")
    ]
    # A second act appends: the file is numbered, never rewritten.
    assert commit(target, keys, BOB) == target / "stewards" / "2.yaml"
    assert active_logins(target) == [ALICE, BOB]


def test_refusals_write_nothing(target: Path, keys: dict[str, Path]) -> None:
    """AC1: a tampered body, a different key on the step-down and an altered sentence each
    count for nothing, by name; a refused write leaves the directory as it was."""
    commit(target, keys, ALICE)
    before = files(target)

    # A step-down signed with a key other than the commitment's is refused before it is written.
    with pytest.raises(StewardError, match="not the key"):
        step_down(target, keys, ALICE, key="stranger")
    assert files(target) == before and active_logins(target) == [ALICE]
    # Nobody steps down from a commitment they never made.
    with pytest.raises(StewardError, match="not an active steward"):
        step_down(target, keys, BOB)
    assert files(target) == before
    # The inputs are checked before anything is signed.
    for bad in (
        {"login": "-not-a-login"},
        {"link": "http://insecure.example"},
        {"name": " "},
    ):
        with pytest.raises(StewardError):
            steward.write(
                target,
                action=steward.COMMIT,
                **{"login": BOB, "name": "B", "link": LINK, **bad},
                date=DATE,
                key_path=keys[BOB],
                signer=SIGNER,
            )
    assert files(target) == before

    # A merged record whose body was tampered with counts for nothing and is named.
    path = target / "stewards" / "1.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["name"] = "Somebody Else"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    [checked] = steward.check(steward.load(target), SIGNER)
    assert not checked.counts and checked.problems[0].startswith("steward-signature")
    assert active_logins(target) == []

    # A record whose sentence is not the fixed one counts for nothing even when signed.
    signed_doc = signed.sign(
        {
            **steward.document(
                target_id=TARGET, action=steward.COMMIT, login=BOB, name="B", link=LINK, date=DATE
            ),
            "commitment": "I promise to try.",
        },
        keys[BOB],
        SIGNER,
    )
    (target / "stewards" / "2.yaml").write_text(yaml.safe_dump(signed_doc), encoding="utf-8")
    verdicts = steward.check(steward.load(target), SIGNER)
    assert [c.record.login for c in verdicts if not c.counts] == [ALICE, BOB]
    assert verdicts[1].problems == (
        "steward-sentence: the commit sentence is not the fixed one (F15-R1)",
    )
    assert active_logins(target) == []


# --- AC2: the active set --------------------------------------------------------------------------


def test_step_down_leaves_the_other_steward(target: Path, keys: dict[str, Path]) -> None:
    """AC2: commits for two logins and a step-down for one leave the other active; a step-down
    written under a foreign key is flagged and the login stays active."""
    commit(target, keys, ALICE, date="2026-09-16T00:00:00Z")
    commit(target, keys, BOB, date="2026-09-17T00:00:00Z")
    step_down(target, keys, ALICE)
    assert active_logins(target) == [BOB]
    assert steward.commit_key_of(target, ALICE, SIGNER) is None

    # A step-down for Bob signed by a stranger, written by hand as a merged file would be.
    forged = signed.sign(
        steward.document(
            target_id=TARGET, action=steward.STEP_DOWN, login=BOB, name="B", link=LINK, date=DATE
        ),
        keys["stranger"],
        SIGNER,
    )
    (target / "stewards" / "4.yaml").write_text(yaml.safe_dump(forged), encoding="utf-8")
    checked = steward.check(steward.load(target), SIGNER)
    assert checked[-1].problems and checked[-1].problems[0].startswith("steward-key")
    assert active_logins(target) == [BOB]
    assert steward.active(target, SIGNER)[0].since == "2026-09-17"

    # Alice commits again: active once more, since the new commitment's date.
    commit(target, keys, ALICE, date="2026-09-18T00:00:00Z")
    assert [(s.login, s.since) for s in steward.active(target, SIGNER)] == [
        (BOB, "2026-09-17"),
        (ALICE, "2026-09-18"),
    ]


def test_a_malformed_record_is_a_graph_defect(target: Path, keys: dict[str, Path]) -> None:
    """A file under stewards/ that is not a numbered, valid record raises rather than being
    skipped: the directory reaches the tree only through a merge the gate checked (C9)."""
    commit(target, keys, ALICE)
    (target / "stewards" / "notes.yaml").write_text("login: x\n", encoding="utf-8")
    with pytest.raises(schemas.SchemaError, match=r"stewards/<n>\.yaml"):
        steward.load(target)
    (target / "stewards" / "notes.yaml").unlink()
    (target / "stewards" / "2.yaml").write_text("login: x\n", encoding="utf-8")
    with pytest.raises(schemas.SchemaError):
        steward.load(target)


# --- R2: the commands -----------------------------------------------------------------------------


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return code, out, captured.err


def test_commands(
    tmp_path: Path, keys: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """R2: ``steward commit`` and ``step-down`` write and sign with the given key; ``check``
    reports whether the signature verifies and whether the key is one the login publishes
    (from a file here — the fetch is the curator's, never the gate's)."""
    root = copy_graph(tmp_path)
    take_in(root)
    target = root / "targets" / TARGET
    code, out, _ = run(
        capsys,
        "steward",
        "commit",
        TARGET,
        "--graph",
        str(root),
        "--login",
        ALICE,
        "--name",
        "Alice",
        "--link",
        LINK,
        "--key",
        str(keys[ALICE]),
        "--date",
        DATE,
    )
    assert code == cli.EXIT_PASS, out
    assert out["written"] == [f"targets/{TARGET}/stewards/1.yaml"]
    assert [s["login"] for s in out["active"]] == [ALICE]

    record = target / "stewards" / "1.yaml"
    published = tmp_path / "alice.keys"
    published.write_text(Path(f"{keys[ALICE]}.pub").read_text(encoding="utf-8"))
    code, out, _ = run(capsys, "steward", "check", str(record), "--keys-from", str(published))
    assert code == cli.EXIT_PASS and out["verifies"] and out["published"] is True
    assert out["key_id"].startswith("SHA256:") and out["sentence_fixed"]
    strangers = tmp_path / "other.keys"
    strangers.write_text(Path(f"{keys['stranger']}.pub").read_text(encoding="utf-8"))
    code, out, _ = run(capsys, "steward", "check", str(record), "--keys-from", str(strangers))
    assert code == cli.EXIT_FAIL and out["verifies"] and out["published"] is False
    code, out, _ = run(capsys, "steward", "check", str(record), "--offline")
    assert code == cli.EXIT_PASS and out["published"] is None

    # A step-down with the wrong key is a refusal, not a traceback, and writes nothing.
    code, out, _err = run(
        capsys,
        "steward",
        "step-down",
        TARGET,
        "--graph",
        str(root),
        "--login",
        ALICE,
        "--key",
        str(keys["stranger"]),
        "--date",
        DATE,
    )
    assert code == cli.EXIT_FAIL and out["ok"] is False and "not the key" in out["refused"]
    assert files(target) == ["1.yaml"]
    code, out, _ = run(
        capsys,
        "steward",
        "step-down",
        TARGET,
        "--graph",
        str(root),
        "--login",
        ALICE,
        "--key",
        str(keys[ALICE]),
        "--date",
        DATE,
    )
    assert code == cli.EXIT_PASS and out["active"] == []
    assert files(target) == ["1.yaml", "2.yaml"]
    doc = schemas.load_yaml(target / "stewards" / "2.yaml", "steward/v1")
    assert doc["action"] == "step-down" and doc["name"] == "Alice"  # carried from the commit
