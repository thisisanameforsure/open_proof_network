"""F24-T2 / AC6: a write-up's stage, the official pick and the coauthors (F24-R5, R7).

D-32 v3.34.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_panel import D0, SIGNER, World, day

from opn_gate import writeup


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("keys") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path), "-C", "approval"],
        check=True,
    )
    return path


@pytest.fixture
def world(tmp_path: Path, key: Path) -> World:
    w = World(tmp_path / "graph", key)
    w.commit("ann", 0)
    w.commit("ben", 0, admitted_by="carol")
    return w


def act(w: World, signer: str, on: int, **fields: Any) -> int:
    path = w._write(
        "writeup", {"schema": "writeup/v2", "signer": signer, "date": day(on), **fields}
    )
    return int(path.stem)


def record(w: World, signer: str, *, authors: list[str], on: int = 1, **extra: Any) -> int:
    return act(w, signer, on, action="record", kind="paper", title="On t",
               url="https://example.org/t.pdf", authors=authors, **extra)  # fmt: skip


def verify(w: World, n: int, on: int = 2) -> None:
    """A verify-writeup motion on ``n`` that the two-member panel passes."""
    m = w.motion("ann", on, kind="verify-writeup", subject={"writeup": n})
    w.vote("ann", m, "yes", on)
    w.vote("ben", m, "yes", on)


def views(w: World, today: int = 40) -> dict[int, writeup.View]:
    found = writeup.views(
        w.root, "t", today=D0 + dt.timedelta(days=today), signer=SIGNER,
        curators=frozenset(w.curators),
    )  # fmt: skip
    return {v.n: v for v in found}


def stage(w: World, n: int, today: int = 40) -> str:
    return views(w, today)[n].stage


def test_a_model_drafted_record_by_a_contributor_is_drafted(world: World) -> None:
    n = record(world, "zed", authors=["zed"], model="claude-opus-5-5")
    assert stage(world, n) == "drafted"


def test_a_contributors_own_record_is_written(world: World) -> None:
    n = record(world, "zed", authors=["zed", "yan"])
    assert stage(world, n) == "written"


def test_a_stewards_record_is_steward_signed(world: World) -> None:
    n = record(world, "ann", authors=["ann", "zed"])
    assert stage(world, n) == "steward-signed"


def test_a_curators_record_is_steward_signed(world: World) -> None:
    world.curators = ["carol"]
    n = record(world, "carol", authors=["carol", "zed"])
    assert stage(world, n) == "steward-signed"


def test_a_steward_author_signing_makes_it_steward_signed(world: World) -> None:
    n = record(world, "zed", authors=["zed", "ann"], model="m")
    act(world, "ann", 2, action="author-sign", writeup=n)
    assert stage(world, n) == "steward-signed"


def test_a_passed_verify_motion_makes_it_panel_verified(world: World) -> None:
    n = record(world, "ann", authors=["ann", "zed"])
    m = world.motion("ann", 2, kind="verify-writeup", subject={"writeup": n})
    world.vote("ann", m, "yes", 3)
    world.vote("ben", m, "yes", 3)
    assert stage(world, n, today=10) == "steward-signed"  # still open
    assert stage(world, n, today=20) == "panel-verified"


def test_every_author_signing_releases_it_once_verified(world: World) -> None:
    n = record(world, "ann", authors=["ann", "zed"])
    act(world, "zed", 2, action="author-sign", writeup=n)
    assert stage(world, n) == "steward-signed"  # each rung needs the one below it
    verify(world, n)
    v = views(world)[n]
    assert (v.stage, v.signed) == ("released", ("ann", "zed"))


def test_a_signature_by_someone_not_listed_is_ignored(world: World) -> None:
    n = record(world, "ann", authors=["ann", "zed"])
    act(world, "mallory", 2, action="author-sign", writeup=n)
    act(world, "mallory", 3, action="arxiv", writeup=n, arxiv="2610.01234")
    assert stage(world, n) == "steward-signed"


def test_a_solo_note_by_a_contributor_never_climbs_past_written(world: World) -> None:
    n = record(world, "zed", authors=["zed"])
    act(world, "zed", 2, action="arxiv", writeup=n, arxiv="2610.01234")
    act(world, "zed", 3, action="accepted", writeup=n, journal="Annals")
    v = views(world)[n]
    assert (v.stage, v.arxiv, v.journal) == ("written", "2610.01234", "Annals")


def test_the_journal_ladder(world: World) -> None:
    n = record(world, "ann", authors=["ann"])
    assert stage(world, n) == "steward-signed"
    verify(world, n)
    assert stage(world, n) == "released"  # the signer is the only author
    act(world, "ann", 2, action="arxiv", writeup=n, arxiv="2610.01234")
    assert stage(world, n) == "on-arxiv"
    act(world, "ann", 3, action="submitted", writeup=n, journal="Annals")
    assert stage(world, n) == "submitted"
    act(world, "ann", 4, action="rejected", writeup=n, journal="Annals")
    assert stage(world, n) == "on-arxiv"
    act(world, "ann", 5, action="submitted", writeup=n, journal="Acta")
    act(world, "ann", 6, action="accepted", writeup=n, journal="Acta", doi="10.1000/acta.1")
    v = views(world)[n]
    assert (v.stage, v.arxiv, v.journal, v.doi) == (
        "accepted",
        "2610.01234",
        "Acta",
        "10.1000/acta.1",
    )


def test_a_rejection_without_arxiv_returns_to_released(world: World) -> None:
    n = record(world, "ann", authors=["ann"])
    verify(world, n)
    act(world, "ann", 3, action="submitted", writeup=n, journal="Annals")
    act(world, "ann", 4, action="rejected", writeup=n, journal="Annals")
    v = views(world)[n]
    assert (v.stage, v.journal) == ("released", None)


def test_withdrawal_is_final_and_never_official(world: World) -> None:
    first = record(world, "ann", authors=["ann"])
    act(world, "ann", 2, action="arxiv", writeup=first, arxiv="2610.01234")
    second = record(world, "zed", authors=["zed"], on=3)
    assert writeup.official(list(views(world).values())) == first
    act(world, "ann", 4, action="withdrawn", writeup=first)
    assert stage(world, first) == "withdrawn"
    assert writeup.official(list(views(world).values())) == second


def test_the_official_write_up_is_the_highest_stage_then_the_newest(world: World) -> None:
    a = record(world, "ann", authors=["ann", "zed"])  # steward-signed
    b = record(world, "ben", authors=["ben", "zed"], on=2)  # steward-signed, newer
    record(world, "zed", authors=["zed"], on=3)  # written
    assert writeup.official(list(views(world).values())) == b
    act(world, "zed", 4, action="author-sign", writeup=a)
    verify(world, a, on=5)  # released
    assert writeup.official(list(views(world).values())) == a
    assert writeup.official([]) is None


def test_coauthors_are_stewards_who_signed_it_or_a_words_section(world: World) -> None:
    n = record(world, "zed", authors=["zed", "ann"])
    act(world, "ann", 2, action="author-sign", writeup=n)
    world.words_signature("explainer", "ben", 3)
    assert views(world)[n].coauthors == ("ann", "ben")


def test_a_v1_record_reads_as_its_signers_steward_signed_paper(world: World) -> None:
    """Whoever signed it: v1 admitted only stewards and curators (F15-R6)."""
    doc = {
        "schema": "writeup/v1",
        "target": "t",
        "kind": "paper",
        "title": "Old",
        "url": "https://example.org/old.pdf",
        "date": day(1),
        "signer": "a-former-curator",
    }
    from opn_gate import signed  # noqa: PLC0415

    (world.target / "writeup").mkdir()
    (world.target / "writeup" / "1.yaml").write_text(
        yaml.safe_dump(signed.sign(doc, world.key, SIGNER), sort_keys=False), encoding="utf-8"
    )
    v = views(world)[1]
    assert (v.stage, v.authors, v.signed) == (
        "steward-signed",
        ("a-former-curator",),
        ("a-former-curator",),
    )


def test_has_paper_needs_a_paper_at_steward_signed_or_above(world: World) -> None:
    record(world, "zed", authors=["zed"])
    assert not writeup.has_paper(world.target, SIGNER)
    record(world, "ann", authors=["ann"], on=2)
    assert writeup.has_paper(world.target, SIGNER)
