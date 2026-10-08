"""F24-T4 / AC8 (F24-R4, R6, R7; D-32 v3.34): ``targets-index/v9`` publishes the panel.

The index carries the panel settings in force, each steward's last signed act and whether it has
lapsed, each target's panel (its unlapsed stewards) with every motion and its tally, and every
write-up with its stage and the one shown as official. A lapsed steward is not on the panel and
does not count for claimability (R4, Q5).

"Today", for lapse and for a motion's window, is the rendered commit's committer day (D-5: two
runs anywhere agree byte for byte), never the wall clock: ``products.render_day``.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from test_panel import D0, SIGNER, World, day

from opn_gate import policy, products, schemas, signed

TARGET = "euclid-primes"
TODAY = 19  # the rendered commit's day, as an offset from D0 (2026-10-20)
COMMIT_TIME = f"{day(TODAY)}T12:00:00Z"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("index-v9-keys") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path), "-C", "approval"],
        check=True,
    )
    return path


class TargetWorld(World):
    """``World``'s signed-record helpers, aimed at a target taken into a real fixture graph."""

    def __init__(self, root: Path, key: Path, target_id: str) -> None:
        self.root = root
        self.key = key
        self.target = root / "targets" / target_id
        self.target_id = target_id
        self.curators: list[str] = []

    def _write(self, sub: str, doc: dict[str, Any]) -> Path:
        directory = self.target / sub
        directory.mkdir(exist_ok=True)
        n = len(list(directory.glob("*.yaml"))) + 1
        doc = signed.sign(
            {**doc, "target": self.target_id, "via": "approval-key"}, self.key, SIGNER
        )
        path = directory / f"{n}.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return path

    def commit_by_motion(self, login: str, on: int, motion: int) -> Path:
        path = self.commit(login, on)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        doc.pop("signature", None)
        doc.pop("key", None)
        doc["admitted_by"] = f"motion:{motion}"
        doc = signed.sign(doc, self.key, SIGNER)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        return path

    def writeup(self, signer: str, on: int, **fields: Any) -> int:
        path = self._write(
            "writeup", {"schema": "writeup/v2", "signer": signer, "date": day(on), **fields}
        )
        return int(path.stem)


def panel_world(tmp_path: Path, key: Path, **take: Any) -> TargetWorld:
    root = copy_graph(tmp_path, publish=True)
    take_in(root, TARGET, **take)
    w = TargetWorld(root, key, TARGET)
    w.commit("olga", -200)  # never acts again: lapsed by TODAY under the default 183 days
    w.commit("ann", 0)
    w.commit("ben", 0)
    return w


def index_of(root: Path, commit_time: str = COMMIT_TIME) -> dict[str, Any]:
    prod = products.generate(root, rendered_from="5" * 40, commit_time=commit_time)
    return dict(json.loads(prod.files[Path("targets/index.json")]))


def row_of(index: dict[str, Any]) -> dict[str, Any]:
    return dict(next(t for t in index["targets"] if t["target_id"] == TARGET))


def test_render_day_is_the_commit_day_and_never_the_clock() -> None:
    assert products.render_day("2026-10-20T23:59:59Z") == dt.date(2026, 10, 20)
    assert products.render_day("2026-10-20T00:00:00Z") == dt.date(2026, 10, 20)
    acts = {"ann": [dt.date(2026, 3, 1), dt.date(2026, 5, 2)], "ben": [dt.date(2026, 4, 1)]}
    assert products.render_day("2026-10-20T00:00:00Z", acts=acts) == dt.date(2026, 10, 20)
    # A record dated ahead of the commit moves the day forward: the tree holds it.
    ahead = {"ann": [dt.date(2026, 10, 21)]}
    assert products.render_day("2026-10-20T23:00:00Z", acts=ahead) == dt.date(2026, 10, 21)
    # No commit time: the latest signed act on the target, else a fixed epoch.
    assert products.render_day(None, acts=acts) == dt.date(2026, 5, 2)
    assert products.render_day(None, acts={}) == products.EPOCH_DAY


def test_the_index_publishes_the_panel_its_motions_and_write_ups(tmp_path: Path, key: Path) -> None:
    w = panel_world(tmp_path, key)
    # Motion 1: ann invites newcomer; the panel (ann, ben; olga lapsed) passes it.
    m1 = w.motion("ann", 1, subject={"login": "newcomer", "note": "the lower bound"})
    w.vote("ann", m1, "yes", 1)
    w.vote("ben", m1, "yes", 1)
    # Write-up 1 by ann, verified by motion 2: released (ann is its only author).
    n1 = w.writeup("ann", 2, action="record", kind="paper", title="On t",
                   url="https://example.org/t.pdf", authors=["ann"])  # fmt: skip
    m2 = w.motion("ann", 2, kind="verify-writeup", subject={"writeup": n1})
    w.vote("ann", m2, "yes", 2)
    w.vote("ben", m2, "yes", 2)
    w.commit_by_motion("newcomer", 16, m1)
    # Write-up 2 by ben, steward-signed, with an open verify motion on it.
    n2 = w.writeup("ben", 17, action="record", kind="note", title="A note",
                   url="https://example.org/n.pdf", authors=["ben", "zed"])  # fmt: skip
    m3 = w.motion("ben", 17, kind="verify-writeup", subject={"writeup": n2})
    w.vote("ann", m3, "yes", 18)

    index = index_of(w.root)
    assert index["schema"] == "targets-index/v9"
    assert schemas.violations(index, "targets-index/v9") == []
    assert index["policy"]["panel"] == policy.load(w.root).panel.as_dict()
    row = row_of(index)
    seen = [(s["login"], s["last_act"], s["lapsed"], s["admitted_by"]) for s in row["stewards"]]
    assert seen == [
        ("olga", day(-200), True, "self"),
        ("ann", day(18), False, "self"),
        ("ben", day(17), False, "self"),
        ("newcomer", day(16), False, "motion:1"),
    ]
    assert row["panel"]["members"] == ["ann", "ben", "newcomer"]
    assert row["panel"]["motions"] == [
        {
            "n": 1, "kind": "invite", "subject": {"login": "newcomer", "note": "the lower bound"},
            "opened_by": "ann", "opened": day(1), "closes": day(15), "state": "passed",
            "yes": 2, "no": 0, "uncounted": [],
        },
        {
            "n": 2, "kind": "verify-writeup", "subject": {"writeup": 1}, "opened_by": "ann",
            "opened": day(2), "closes": day(16), "state": "passed", "yes": 2, "no": 0,
            "uncounted": [],
        },
        {
            "n": 3, "kind": "verify-writeup", "subject": {"writeup": 2}, "opened_by": "ben",
            "opened": day(17), "closes": day(31), "state": "open", "yes": 1, "no": 0,
            "uncounted": [],
        },
    ]  # fmt: skip
    writeups = row["writeups"]
    assert writeups["official"] == 1
    assert [(v["n"], v["kind"], v["stage"], v["signed"]) for v in writeups["items"]] == [
        (1, "paper", "released", ["ann"]),
        (2, "note", "steward-signed", ["ben"]),
    ]


def test_a_target_with_no_panel_records_publishes_empty_ones(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    take_in(root, TARGET)
    row = row_of(index_of(root))
    assert row["stewards"] == []
    assert row["panel"] == {"members": [], "motions": []}
    assert row["writeups"] == {"official": None, "items": []}


def enforce(root: Path) -> None:
    policy.write(root, policy.document(enforced=True, since="2026-09-16", evidence="e.md"))


def test_a_lapsed_steward_does_not_make_a_target_claimable(tmp_path: Path, key: Path) -> None:
    """F24-R4, Q5: under an enforced steward rule, a target whose only steward has lapsed is
    stewardless; one act inside the window brings them back."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root, TARGET, track="open")
    enforce(root)
    w = TargetWorld(root, key, TARGET)
    w.commit("olga", -200)
    row = row_of(index_of(root))
    assert [s["lapsed"] for s in row["stewards"]] == [True]
    assert row["panel"]["members"] == []
    assert row["claimable"] is False
    assert "no-steward" in row["not_claimable"]
    # A vote is a signed act: olga is back on the panel, and the target is claimable again.
    m = w.motion("olga", TODAY, subject={"login": "newcomer"})
    w.vote("olga", m, "yes", TODAY)
    row = row_of(index_of(root))
    assert row["panel"]["members"] == ["olga"]
    assert "no-steward" not in row["not_claimable"]


def test_two_generations_are_byte_identical(tmp_path: Path, key: Path) -> None:
    """D-5: the index is a function of the tree and the commit, never of when it ran."""
    w = panel_world(tmp_path, key)
    m = w.motion("ann", 17, subject={"login": "newcomer"})
    w.vote("ben", m, "no", 18)
    first = products.generate(w.root, rendered_from="5" * 40, commit_time=COMMIT_TIME)
    second = products.generate(w.root, rendered_from="5" * 40, commit_time=COMMIT_TIME)
    assert first.files[Path("targets/index.json")] == second.files[Path("targets/index.json")]
    # A later commit day, and only that, moves the motion from open to decided.
    later = index_of(w.root, f"{(D0 + dt.timedelta(days=40)).isoformat()}T00:00:00Z")
    assert [t["state"] for t in row_of(later)["panel"]["motions"]] == ["failed"]
    assert [t["state"] for t in row_of(index_of(w.root))["panel"]["motions"]] == ["open"]
