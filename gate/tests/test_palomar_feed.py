"""F25-T13 / R14, AC13: the Palomar feed matcher, the proposal writer and the drift check.

Over the fixture feed (``fixtures/palomar/recent-2026-10-10.json``, trimmed from the live
``recent.json`` of 2026-10-10) and a fixture graph carrying the network's live target ids:
E257 is an *inferred* candidate for erdos-257 and nothing else in the feed matches it; every
other target has no candidate; a bare ``257`` inside ``1257`` or ``2570`` is never a match;
``propose`` writes a ``literature/v1`` proposal into the output directory and nothing without the
flag; ``drift`` reports a changed hash and a changed status and nothing for an identical record;
an unreachable host writes nothing and the command exits 1.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml

from opn_gate import cli, intake, literature, palomar_feed, registrations, schemas
from opn_gate.palomar_host import FakePalomarHost, PalomarError

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "palomar" / "recent-2026-10-10.json"
FC = "https://github.com/google-deepmind/formal-conjectures/blob/c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae"
#: The live graph's targets on 2026-10-11 (``targets/*/target.yaml``; the tutorial has none).
ERDOS_IDS = (
    1003, 1050, 1065, 1094, 172, 212, 251, 257, 324, 376, 402, 406, 410, 412, 417,
    51, 52, 68, 69, 727, 849, 850, 931, 952,
)  # fmt: skip
LIVE_IDS = (*(f"erdos-{n}" for n in ERDOS_IDS), "euclid-primes", "riemann-hypothesis", "tutorial")
E257 = "PALOMAR-2026-09-25-000009"
WHEN = "2026-10-11T09:00:00Z"


# --- fixtures ---------------------------------------------------------------------------------


def erdos_record(n: int) -> dict[str, Any]:
    return samples.target_record(
        id=f"erdos-{n}",
        title=f"Erdős problem {n}",
        track="open",
        source={
            "kind": "formal-conjectures",
            "ref": f"FormalConjectures/ErdosProblems/{n}.lean",
            "url": f"{FC}/FormalConjectures/ErdosProblems/{n}.lean",
        },
        prior_art={
            "arxiv_query": None,
            "forum_url": f"https://www.erdosproblems.com/{n}",
            "summary": "From the registry.",
        },
    )


def live_graph(root: Path) -> Path:
    """A graph whose target records carry the live ids; erdos-257 declares its root."""
    for n in ERDOS_IDS:
        intake.write_doc(root / "targets" / f"erdos-{n}", erdos_record(n))
    intake.write_doc(root / "targets" / "euclid-primes", samples.target_record())
    intake.write_doc(
        root / "targets" / "riemann-hypothesis",
        samples.target_record(
            id="riemann-hypothesis",
            title="The Riemann hypothesis",
            track="open",
            source={
                "kind": "formal-conjectures",
                "ref": "FormalConjectures/Millenium/RiemannHypothesis.lean",
                "url": f"{FC}/FormalConjectures/Millenium/RiemannHypothesis.lean",
            },
        ),
    )
    (root / "targets" / "tutorial" / "nodes" / "tutorial").mkdir(parents=True)  # no target.yaml
    status = root / "targets" / "erdos-257" / "status"
    status.mkdir()
    (status / "20260914T172138Z-thisisanameforsure.yaml").write_text(
        yaml.safe_dump(samples.target_status(status="listed", root="erdos-257"), sort_keys=False)
    )
    (root / "targets" / "erdos-257" / "nodes" / "erdos-257").mkdir(parents=True)
    return root


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    return live_graph(tmp_path / "graph")


@pytest.fixture
def feed() -> list[dict[str, Any]]:
    return palomar_feed.load_snapshot(FIXTURE)


def entry(**overrides: Any) -> dict[str, Any]:
    """A feed entry in the live shape, saying nothing of any Erdős problem unless told to."""
    doc: dict[str, Any] = {
        "id": "PALOMAR-2026-10-10-000099",
        "version": 1,
        "title": "A theorem",
        "abstract": "Nothing about any numbered problem.",
        "status": "registered",
        "source": {"repository": "someone/some-lean", "commit": "a" * 40, "project_path": None},
        "formalization": {"theorem_names": ["Some.theorem"]},
        "classification": {"primary": "number-theory"},
        "authors": [{"name": "A. Author"}],
        "published_at": "2026-10-10T00:00:00Z",
    }
    doc.update(overrides)
    return doc


# --- the index --------------------------------------------------------------------------------


def test_targets_index_derives_each_erdos_number_and_skips_a_target_with_no_record(
    graph: Path,
) -> None:
    keys = palomar_feed.targets_index(graph)
    assert set(keys) == set(LIVE_IDS) - {"tutorial"}
    assert keys["erdos-257"].number == 257
    assert keys["erdos-1050"].number == 1050
    assert keys["euclid-primes"].number is None
    assert keys["riemann-hypothesis"].number is None


@pytest.mark.parametrize(
    ("source", "prior_art", "number"),
    [
        (
            {"kind": "formal-conjectures", "ref": "FormalConjectures/ErdosProblems/69.lean"},
            {"summary": "s", "forum_url": None, "arxiv_query": None},
            69,
        ),
        (
            {
                "kind": "erdos",
                "ref": "erdosproblems.com",
                "url": "https://www.erdosproblems.com/402",
            },
            {"summary": "s", "forum_url": None, "arxiv_query": None},
            402,
        ),
        (
            {"kind": "other", "ref": "a paper", "url": None},
            {
                "summary": "s",
                "forum_url": "https://www.erdosproblems.com/1050",
                "arxiv_query": None,
            },
            1050,
        ),
        (
            {"kind": "other", "ref": "Euclid, Elements IX.20", "url": None},
            {"summary": "s", "forum_url": None, "arxiv_query": None},
            None,
        ),
    ],
)
def test_the_number_comes_from_the_url_or_the_registry_path(
    source: dict[str, Any], prior_art: dict[str, Any], number: int | None
) -> None:
    doc = samples.target_record(id="t", source=source, prior_art=prior_art)
    assert palomar_feed.number_of(doc) == number


# --- the matcher ------------------------------------------------------------------------------


def test_e257_is_an_inferred_candidate_for_erdos_257_and_nothing_else_matches_it(
    graph: Path, feed: list[dict[str, Any]]
) -> None:
    """AC13: the fixture feed names thirteen Erdős problems the network does not list and one
    corpus namespace, ``E257``; that namespace is the one candidate, and it is inference."""
    found = palomar_feed.match(feed, palomar_feed.targets_index(graph))
    assert [(c.target_id, c.registry_id, c.confidence) for c in found] == [
        ("erdos-257", E257, "inferred")
    ]
    only = found[0]
    assert only.version == 1
    assert "E257" in only.evidence and "theorem_names" in only.evidence
    assert only.title.startswith("Weighted support criteria")


def test_erdos_1050_and_every_other_target_has_no_candidate(
    graph: Path, feed: list[dict[str, Any]]
) -> None:
    found = palomar_feed.match(feed, palomar_feed.targets_index(graph))
    by_target = {c.target_id for c in found}
    assert "erdos-1050" not in by_target
    assert by_target == {"erdos-257"}


def test_the_fixture_feed_names_the_problems_the_brief_counted(
    feed: list[dict[str, Any]],
) -> None:
    """Guard on the fixture: the numbers the matcher must *not* confuse with the live targets."""
    named = {n for e in feed for n in palomar_feed.numbers_named(e)}
    assert {2, 274, 374, 546, 575, 809, 956, 958, 1007, 1054, 1139, 1219, 1220} <= named
    assert 257 in named
    assert 1050 not in named


@pytest.mark.parametrize(
    ("text", "field"),
    [
        ("Erdős problem 1257 in Lean", "title"),
        ("Erdős 2570: a bound", "title"),
        ("see erdos-1257 and erdos_2570", "abstract"),
        ("E1257 and E2570, but not the one in between", "abstract"),
    ],
)
def test_a_bare_257_inside_a_longer_number_is_not_a_match(
    graph: Path, text: str, field: str
) -> None:
    keys = {"erdos-257": palomar_feed.targets_index(graph)["erdos-257"]}
    assert palomar_feed.match([entry(**{field: text})], keys) == []


@pytest.mark.parametrize(
    ("overrides", "confidence", "where"),
    [
        ({"title": "Erdős Problem 257: a new bound"}, "number", "title"),
        ({"title": "Erdős 257 settled"}, "number", "title"),
        ({"abstract": "This answers Erdős problem #257 in full."}, "number", "abstract"),
        ({"abstract": "See https://www.erdosproblems.com/257 for it."}, "number", "abstract"),
        ({"source": {"repository": "x/erdos-257-lean", "commit": "a"}}, "inferred", "repository"),
        ({"formalization": {"theorem_names": ["Erdos257.main"]}}, "inferred", "theorem_names"),
        ({"formalization": {"theorem_names": ["erdos_257"]}}, "inferred", "theorem_names"),
        ({"formalization": {"theorem_names": ["Corpus.E257.claim"]}}, "inferred", "theorem_names"),
        ({"source": {"repository": "x/y", "project_path": "p/257.lean"}}, "inferred", "project"),
        ({"abstract": "Problem #257 of the list."}, "inferred", "abstract"),
    ],
)  # fmt: skip
def test_each_token_shape_matches_with_its_confidence(
    graph: Path, overrides: dict[str, Any], confidence: str, where: str
) -> None:
    keys = {"erdos-257": palomar_feed.targets_index(graph)["erdos-257"]}
    found = palomar_feed.match([entry(**overrides)], keys)
    assert [(c.target_id, c.confidence) for c in found] == [("erdos-257", confidence)]
    assert where in found[0].evidence


def test_an_explicit_name_outranks_a_namespace_hit_on_the_same_entry(graph: Path) -> None:
    keys = {"erdos-257": palomar_feed.targets_index(graph)["erdos-257"]}
    e = entry(title="Erdős 257", formalization={"theorem_names": ["Erdos257.main"]})
    found = palomar_feed.match([e], keys)
    assert len(found) == 1 and found[0].confidence == "number"


def test_a_target_without_a_number_never_matches(graph: Path) -> None:
    keys = palomar_feed.targets_index(graph)
    e = entry(title="Euclid primes and the Riemann hypothesis", abstract="erdos-257")
    found = palomar_feed.match([e], keys)
    assert [c.target_id for c in found] == ["erdos-257"]


def test_the_report_is_json_with_the_candidates_and_the_counts(
    graph: Path, feed: list[dict[str, Any]]
) -> None:
    keys = palomar_feed.targets_index(graph)
    found = palomar_feed.match(feed, keys)
    doc = json.loads(palomar_feed.report(found, entries=len(feed), targets=len(keys)))
    assert doc["ok"] is True
    assert doc["entries"] == 25 and doc["targets"] == 26
    assert doc["candidates"] == [
        {
            "target": "erdos-257",
            "registry_id": E257,
            "version": 1,
            "url": f"https://palomar-registry.org/entries/{E257}-v1",
            "title": found[0].title,
            "confidence": "inferred",
            "evidence": found[0].evidence,
        }
    ]


# --- proposals --------------------------------------------------------------------------------


def test_propose_writes_a_literature_proposal_that_validates_with_the_id_and_url(
    graph: Path, feed: list[dict[str, Any]], tmp_path: Path
) -> None:
    (cand,) = palomar_feed.match(feed, palomar_feed.targets_index(graph))
    out = tmp_path / "out"
    path = palomar_feed.propose(graph, cand, contributor="opn-feed", out=out, date=WHEN)
    assert path.is_relative_to(out)
    assert path.relative_to(out).as_posix() == (
        "targets/erdos-257/nodes/erdos-257/literature/20261011T090000Z-opn-feed.yaml"
    )
    doc = schemas.load_yaml(path, literature.SCHEMA)
    assert doc["node"] == "erdos-257"
    assert doc["status"] == "known"
    assert doc["contributor"] == "opn-feed"
    assert doc["date"] == WHEN
    assert doc["via"] is None and doc["key"] is None and doc["signature"] is None
    (ref,) = doc["references"]
    assert ref["url"] == f"https://palomar-registry.org/entries/{E257}-v1"
    assert E257 in ref["title"]
    assert "E257" in doc["summary"] and "inferred" in doc["summary"]
    # The graph itself was not written.
    assert not list((graph / "targets" / "erdos-257").rglob("literature"))


def test_propose_refuses_a_target_whose_root_is_not_declared(graph: Path, tmp_path: Path) -> None:
    cand = palomar_feed.Candidate(
        target_id="erdos-69",
        registry_id=E257,
        version=1,
        title="t",
        evidence="e",
        confidence="inferred",
    )
    with pytest.raises(palomar_feed.FeedError, match="root"):
        palomar_feed.propose(graph, cand, contributor="x", out=tmp_path / "out")
    assert not (tmp_path / "out").exists()


# --- drift ------------------------------------------------------------------------------------


def registered(graph: Path, target: str, rid: str | None, **overrides: Any) -> dict[str, Any]:
    where = registrations.directory(graph / "targets" / target)
    where.mkdir(exist_ok=True)
    doc = samples.registration(target=target, registry_id=rid, **overrides)
    (where / f"2026-10-12-{len(list(where.iterdir())) + 1}.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False)
    )
    return doc


def palomar_entry(rid: str, **overrides: Any) -> dict[str, Any]:
    """An ``entries/<id>-v<n>.json`` record in the observed shape, from a corpus fixture."""
    doc: dict[str, Any] = json.loads(
        (FIXTURE.parent / "PALOMAR-2026-09-25-000003" / "entry.json").read_text(encoding="utf-8")
    )
    doc["id"] = rid
    doc["version"] = 1
    doc["status"] = "registered"
    doc["verification"]["challenge_sha256"] = "c" * 64
    doc["verification"]["solution_sha256"] = "d" * 64
    doc.update(overrides)
    return doc


def test_drift_reports_a_changed_hash_and_a_changed_status_and_nothing_identical(
    graph: Path,
) -> None:
    same, hashed, status = (f"PALOMAR-2026-10-12-00000{i}" for i in (1, 2, 3))
    registered(graph, "erdos-257", same)
    registered(graph, "erdos-69", hashed)
    registered(graph, "erdos-1050", status)
    host = FakePalomarHost(
        entries={
            (same, 1): palomar_entry(same),
            (hashed, 1): palomar_entry(hashed, verification={
                "challenge_sha256": "e" * 64, "solution_sha256": "d" * 64}),
            (status, 1): palomar_entry(status, status="withdrawn"),
        }
    )  # fmt: skip
    before = sorted(p.as_posix() for p in graph.rglob("*"))
    found = palomar_feed.drift(graph, host)
    assert sorted(p.as_posix() for p in graph.rglob("*")) == before
    assert [(d["target"], d["registry_id"], d["kind"]) for d in found] == [
        ("erdos-1050", status, "changed"),
        ("erdos-69", hashed, "changed"),
    ]
    assert found[0]["differences"] == [
        {"field": "status", "record": "registered", "registry": "withdrawn"}
    ]
    assert found[1]["differences"] == [
        {"field": "challenge_sha256", "record": "c" * 64, "registry": "e" * 64}
    ]
    assert sorted(host.calls) == sorted(
        [("entry", (same, 1)), ("entry", (hashed, 1)), ("entry", (status, 1))]
    )


def test_drift_reports_an_entry_the_registry_no_longer_serves(graph: Path) -> None:
    gone = "PALOMAR-2026-10-12-000004"
    registered(graph, "erdos-257", gone)
    found = palomar_feed.drift(graph, FakePalomarHost())
    assert [(d["registry_id"], d["kind"]) for d in found] == [(gone, "missing")]


def test_drift_reads_the_latest_record_and_skips_withdrawn_and_pending_ones(graph: Path) -> None:
    rid = "PALOMAR-2026-10-12-000005"
    registered(graph, "erdos-257", rid, status="submitted", date="2026-10-11")
    registered(graph, "erdos-257", rid, status="withdrawn", date="2026-10-12")
    registered(
        graph, "erdos-69", None, version=None, status="submitted", url=None,
        challenge_sha256=None, solution_sha256=None,
    )  # fmt: skip
    host = FakePalomarHost(entries={(rid, 1): palomar_entry(rid)})
    assert palomar_feed.drift(graph, host) == []
    assert host.calls == []


# --- the run, unreachable hosts, the command line ---------------------------------------------


def test_an_unreachable_feed_writes_nothing_and_exits_1(graph: Path, tmp_path: Path) -> None:
    class Down(FakePalomarHost):
        def recent(self) -> dict[str, Any]:
            raise PalomarError("GET recent.json failed: URLError")

    out = tmp_path / "out"
    before = sorted(p.as_posix() for p in graph.rglob("*"))
    result = palomar_feed.run(graph, Down(), propose=True, contributor="opn-feed", out=out)
    assert result.exit_code == 1
    assert result.report["ok"] is False
    assert "unreachable" in result.report["warning"]
    assert result.report["candidates"] == []
    assert not out.exists()
    assert sorted(p.as_posix() for p in graph.rglob("*")) == before


def test_a_refused_drift_lookup_is_a_warning_and_exit_1(graph: Path) -> None:
    rid = "PALOMAR-2026-10-12-000006"
    registered(graph, "erdos-257", rid)
    host = FakePalomarHost(feed=[], entries={(rid, 1): palomar_entry(rid)})
    from opn_gate.palomar_host import PalomarRefusedError  # noqa: PLC0415

    host.refuse_next = PalomarRefusedError(500, "boom")
    result = palomar_feed.run(graph, host, drift=True)
    assert result.exit_code == 1 and result.report["ok"] is False
    assert "500" in result.report["warning"]


def test_run_over_the_fake_host_reports_the_candidate_and_proposes_only_with_the_flag(
    graph: Path, feed: list[dict[str, Any]], tmp_path: Path
) -> None:
    host = FakePalomarHost(feed=feed)
    out = tmp_path / "out"
    plain = palomar_feed.run(graph, host)
    assert plain.exit_code == 0
    assert [c["target"] for c in plain.report["candidates"]] == ["erdos-257"]
    assert plain.report["proposals"] == []
    assert not out.exists()
    proposed = palomar_feed.run(
        graph, host, propose=True, contributor="opn-feed", out=out, date=WHEN
    )
    assert proposed.exit_code == 0
    (written,) = proposed.report["proposals"]
    assert Path(written).is_file() and Path(written).is_relative_to(out)
    assert host.calls == [("recent", ()), ("recent", ())]


def test_the_cli_with_a_snapshot_prints_the_candidate_and_asks_the_host_nothing(
    graph: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_host(*_: Any, **__: Any) -> FakePalomarHost:
        raise AssertionError("the host must not be built when --snapshot is given")

    monkeypatch.setattr(palomar_feed, "default_host", no_host)
    code = cli.main(["palomar-feed", "--graph", str(graph), "--snapshot", str(FIXTURE)])
    assert code == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True and doc["source"] == str(FIXTURE)
    assert [(c["target"], c["registry_id"], c["confidence"]) for c in doc["candidates"]] == [
        ("erdos-257", E257, "inferred")
    ]


def test_the_cli_exits_1_on_an_unreachable_host_and_2_on_bad_arguments(
    graph: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class Down(FakePalomarHost):
        def recent(self) -> dict[str, Any]:
            raise PalomarError("GET recent.json failed: URLError")

    monkeypatch.setattr(palomar_feed, "default_host", Down)
    assert cli.main(["palomar-feed", "--graph", str(graph)]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False
    # --propose needs both --contributor and --out.
    assert cli.main(["palomar-feed", "--graph", str(graph), "--propose"]) == 2
    assert cli.main(["palomar-feed", "--graph", str(tmp_path / "nowhere")]) == 2
    assert (
        cli.main(["palomar-feed", "--graph", str(graph), "--snapshot", str(tmp_path / "no.json")])
        == 2
    )


def test_the_tool_delegates_to_the_same_run(
    graph: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    tool = Path(__file__).resolve().parents[1] / "tools" / "watch_palomar.py"
    spec = importlib.util.spec_from_file_location("watch_palomar", tool)
    assert spec is not None and spec.loader is not None
    watch_palomar: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(watch_palomar)
    report = tmp_path / "report.json"
    code = watch_palomar.main(
        ["--graph", str(graph), "--snapshot", str(FIXTURE), "--out-report", str(report)]
    )
    assert code == 0
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc == json.loads(capsys.readouterr().out)
    assert [c["target"] for c in doc["candidates"]] == ["erdos-257"]
    assert watch_palomar.main(["--graph", str(tmp_path / "nowhere")]) == 2


def test_the_workflow_is_a_weekly_dry_run_with_read_only_contents() -> None:
    text = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "watch-palomar.yml"
    ).read_text(encoding="utf-8")
    wf = yaml.safe_load(text)
    on = wf.get("on") or wf.get(True)  # PyYAML reads a bare `on:` as the boolean True
    assert "workflow_dispatch" in on
    (cron,) = [c["cron"] for c in on["schedule"]]
    fields = cron.split()
    assert len(fields) == 5 and fields[2] == "*" and fields[3] == "*" and fields[4] != "*", (
        "weekly: a day of the week, every month"
    )
    assert wf["permissions"] == {"contents": "read"}
    assert "--propose" not in text, "the workflow is a dry run: it reports, a person proposes"
    assert "watch_palomar.py" in text and "upload-artifact" in text
