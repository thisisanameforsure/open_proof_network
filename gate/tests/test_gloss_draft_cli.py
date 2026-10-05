"""F20-T10: ``opn-gate gloss draft`` — the drafter's run (R15-R18, R20, R21; Q6-Q9; AC13, AC14).

The library (``drafter``, T9) builds prompts, checks drafts and reports; this command is what
drives it over a graph checkout: it reads the coverage report for the subjects, builds each from
files alone, drafts them with the configured caps, checks each with the gate's own rules over a
scratch copy of the checkout, and posts each to the service's ``POST /glosses`` with the
drafter's token, writing its report as it goes.

Every model and the service here are fakes: no test makes a network call. The fixture is the
propositional graph committed as a git repository (a draft names the commit its input was read
at): three nodes, the root ``and-swap-reassoc`` with no curated words (so its statement is offered
and skipped by rule, F20-Q11), and an outline for one of the three proofs.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest
from harness import copy_graph
from test_drafter import ScriptedModel

from opn_gate import cli, draft_run, drafter, glosses, schemas

TARGET = "propositional"
ROOT = "and-swap-reassoc"
OUTLINED = "and-reassoc"  # its Proof.lean has an outline; the other two proofs do not
TOKEN = "opn-test-drafter-token-0f9e8d"  # noqa: S105 — a fake, asserted never to be printed
SERVICE = "https://service.invalid"
GLOSS = "For all propositions $p$ and $q$, from $p$ and $q$ together one has $q$ and $p$."
EXPLAINER = "## The idea\n\nRegroup the conjuncts.\n\n## The regrouping {steps: s1}\n\nRoutine.\n"
INVENTED = "By `Nat.Coprime.symm` the conjunction swaps."


def nodes(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def key(node: str, name: str) -> str:
    return f"targets/{TARGET}/nodes/{node}/{name}"


def git(root: Path, *args: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(root.parent),
    }
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
    ).stdout.strip()


def write_outline(root: Path, node: str) -> str:
    """F19's committed outline of the node's Proof.lean, with one routine step ``s1``."""
    digest = schemas.content_hash((nodes(root) / node / "Proof.lean").read_bytes())
    step: dict[str, Any] = {
        "id": "s1",
        "kind": "have",
        "name": "s1",
        "claim": {"text": "q ∧ p", "printed": "reliable", "truncated": False},
        "goal": None,
        "span": {"start_line": 1, "end_line": 2},
        "uses": {"nodes": [], "defs": [], "mathlib": []},
        "closed_by": {"kind": "automation", "tactics": ["simp"]},
        "child_node": None,
        "children": [],
    }
    doc = {
        "schema": "outline/v1",
        "target": TARGET,
        "node": node,
        "artifact": {"path": "Proof.lean", "hash": digest, "kind": "proof"},
        "gate": "9" * 40,
        "steps": [step],
    }
    assert schemas.violations(doc, "outline/v1") == []
    out = root / "targets" / TARGET / "outlines" / f"{digest}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(schemas.canonical_json(doc))
    return digest


@pytest.fixture
def graph(tmp_path: Path) -> tuple[Path, str]:
    root = copy_graph(tmp_path)
    write_outline(root, OUTLINED)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "seed")
    return root, git(root, "rev-parse", "HEAD")


@dataclass
class FakeService:
    """``POST /glosses`` as the service answers it: 201 with a path and a pull request unless an
    answer is scripted for that call (a status, or an exception to raise). Every body is kept."""

    answers: dict[int, int | Exception] = field(default_factory=dict)
    bodies: list[dict[str, Any]] = field(default_factory=list)
    report_path: Path | None = None
    seen_on_disk: list[dict[str, Any]] = field(default_factory=list)

    def post(self, body: Mapping[str, Any]) -> draft_run.Answer:
        n = len(self.bodies)
        self.bodies.append(dict(body))
        if self.report_path is not None and self.report_path.is_file():
            self.seen_on_disk.append(json.loads(self.report_path.read_text(encoding="utf-8")))
        answer = self.answers.get(n, 201)
        if isinstance(answer, Exception):
            raise answer
        if answer == 201:
            digest = f"{n:064x}"
            return draft_run.Answer(
                201,
                {"path": f"x/{digest}.md", "hash": digest, "pr_url": f"https://pr.invalid/{n}"},
            )
        return draft_run.Answer(answer, {"error": "rate-limited", "message": "slow down"})


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-not-a-key")
    monkeypatch.setenv("OPN_DRAFTER_TOKEN", TOKEN)


def wire(
    monkeypatch: pytest.MonkeyPatch, model: ScriptedModel, service: FakeService
) -> list[tuple[str, str]]:
    """Replace the two seams; answers the (url, token) the poster was built with."""
    built: list[tuple[str, str]] = []

    def poster(url: str, token: str) -> FakeService:
        built.append((url, token))
        return service

    monkeypatch.setattr(draft_run, "make_model", lambda _settings: model)
    monkeypatch.setattr(draft_run, "make_poster", poster)
    return built


def draft(
    root: Path, report: Path, capsys: pytest.CaptureFixture[str], *extra: str
) -> tuple[int, dict[str, Any]]:
    argv = ["gloss", "draft", "--graph", str(root), "--report", str(report), *extra]
    code = cli.main(argv)
    out = capsys.readouterr()
    assert TOKEN not in out.out and TOKEN not in out.err
    on_disk = report.read_text(encoding="utf-8") if report.is_file() else ""
    assert TOKEN not in on_disk
    return code, json.loads(out.out) if out.out.strip() else {}


def keys_of(entries: list[dict[str, Any]]) -> list[str]:
    return [e["key"] for e in entries]


#: The fixture's gloss subjects in coverage order, the root's statement among them.
GLOSS_KEYS = [
    key("and-reassoc", "Statement.lean"),
    key("and-reassoc", "Witness.lean"),
    key(ROOT, "Statement.lean"),
    key(ROOT, "Witness.lean"),
    key("tutorial-and-swap", "Statement.lean"),
    key("tutorial-and-swap", "Witness.lean"),
]


# --- a live run ---------------------------------------------------------------------------------


def test_drafts_land_with_the_drafter_and_no_author(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """Every drafted subject is posted once, as the drafter: the words, the subject with the hash
    of the text drafted, and the drafter block (model, version, the graph commit) — never an
    author, which the service supplies from the token. The root's statement is skipped by rule
    and two proofs without an outline are reported, not drafted from their source."""
    root, commit = graph
    model = ScriptedModel([GLOSS, GLOSS, EXPLAINER, GLOSS, GLOSS, GLOSS])
    report = tmp_path / "report.json"
    service = FakeService(report_path=report)
    built = wire(monkeypatch, model, service)

    code, out = draft(root, report, capsys, "--submit-url", SERVICE)

    assert code == 0, out
    assert built == [(SERVICE, TOKEN)]
    assert len(service.bodies) == 6 and len(model.prompts) == 6
    for body in service.bodies:
        assert "author" not in body and body["supersedes"] is None
        assert body["drafter"] == {
            "model": "fake-model",
            "model_version": "fake-model-2026-10-04",
            "input_commit": commit,
        }
        assert body["licence"] == "CC-BY-4.0"
    gloss_bodies = [b for b in service.bodies if b["subject"]["kind"] != "proof"]
    first = gloss_bodies[0]
    assert first["subject"] == {
        "kind": "statement",
        "target_id": TARGET,
        "node_id": "and-reassoc",
        "lean_hash": schemas.content_hash(
            (nodes(root) / "and-reassoc" / "Statement.lean").read_bytes()
        ),
    }
    assert first["text"] == GLOSS
    [explainer] = [b for b in service.bodies if b["subject"]["kind"] == "proof"]
    assert explainer["subject"]["node_id"] == OUTLINED
    assert explainer["subject"]["proof"] == schemas.content_hash(
        (nodes(root) / OUTLINED / "Proof.lean").read_bytes()
    )

    assert out == json.loads(report.read_text(encoding="utf-8"))
    assert out["mode"] == "live" and out["graph_commit"] == commit and out["finished"]
    assert out["cut_short"] is None and out["post_failed"] == []
    assert len(out["posted"]) == 6
    drafting = out["drafting"]
    assert keys_of(drafting["skipped"]) == [f"gloss {TARGET}/{ROOT} statement"]
    assert sorted(keys_of(out["no_outline"])) == [
        key(ROOT, "Proof.lean"),
        key("tutorial-and-swap", "Proof.lean"),
    ]
    assert out["passed_over"] == []  # mode new: a Context with a chain-less dep is not "new"
    # Written as it goes: when the second draft was posted, the report on disk already named the
    # first as posted, and the run as not finished.
    second = service.seen_on_disk[1]
    assert keys_of(second["posted"]) == [key("and-reassoc", "Statement.lean")]
    assert second["finished"] is False


def test_every_draft_carries_a_drafter_block_and_no_author(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """The record each check saw is a draft: ``author: null`` and the drafter named."""
    root, commit = graph
    seen: list[dict[str, Any]] = []
    real = draft_run.scratch_check

    def spying(graph_root: Path, *, service_login: str) -> Any:
        with real(graph_root, service_login=service_login) as check:

            def wrapped(d: drafter.Draft) -> Any:
                seen.append(d.front_matter)
                return check(d)

            yield wrapped

    monkeypatch.setattr(draft_run, "scratch_check", contextlib.contextmanager(spying))
    wire(monkeypatch, ScriptedModel([GLOSS] * 2), FakeService())
    monkeypatch.setenv("OPN_DRAFTER_MAX_SUBJECTS", "2")
    code, out = draft(root, tmp_path / "r.json", capsys, "--submit-url", SERVICE)
    assert code == 0, out
    assert len(seen) == 2
    for front in seen:
        assert front["author"] is None
        assert front["drafter"]["name"] == "opn-drafter"
        assert front["drafter"]["input_commit"] == commit
    assert out["drafting"]["stop_kind"] == "cap"  # a capped run is a batch, not a failure


def test_a_draft_failing_its_checks_twice_is_not_posted(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """R16: a gloss naming a constant its file does not use is regenerated once; failing again
    it is recorded as not drafted, with the reason, and nothing is posted for it."""
    root, _ = graph
    model = ScriptedModel([INVENTED, INVENTED, GLOSS])
    service = FakeService()
    wire(monkeypatch, model, service)
    monkeypatch.setenv("OPN_DRAFTER_MAX_SUBJECTS", "2")
    code, out = draft(root, tmp_path / "r.json", capsys, "--submit-url", SERVICE)
    assert code == 0, out
    [failed] = out["drafting"]["not_drafted"]
    assert failed["key"] == f"gloss {TARGET}/and-reassoc statement"
    assert "Nat.Coprime.symm" in failed["reason"]
    assert len(service.bodies) == 1
    assert service.bodies[0]["subject"]["kind"] == "witness"


def test_the_check_is_the_gates_own(graph: tuple[Path, str]) -> None:
    """The check run on each draft is the gate's pre-flight over a copy of the checkout: a draft
    of text that is not the file as it stands is refused ``gloss-subject-mismatch`` there, and
    the copy is left as it was (the draft is removed after each check)."""
    root, commit = graph
    subject = drafter.gloss_subject(
        root, TARGET, "witness", input_commit=commit, node="and-reassoc", root=ROOT
    )
    stale = drafter.GlossSubject(
        target=TARGET,
        kind="witness",
        lean_text=subject.lean_text + "\n-- since changed\n",
        input_commit=commit,
        node="and-reassoc",
    )
    good = drafter.render(subject, GLOSS, model="m", model_version="1", date="2026-10-05")
    bad = drafter.render(stale, GLOSS, model="m", model_version="1", date="2026-10-05")
    with draft_run.scratch_check(root, service_login="open-proof-network[bot]") as check:
        assert [d.code for d in check(good)] == []  # type: ignore[attr-defined]
        assert [d.code for d in check(bad)] == ["gloss-subject-mismatch"]  # type: ignore[attr-defined]
        assert [d.code for d in check(good)] == []  # type: ignore[attr-defined]
    assert not (nodes(root) / "and-reassoc" / glosses.GLOSS_DIR).exists()


# --- a run cut short ----------------------------------------------------------------------------


def test_a_provider_429_mid_run_leaves_a_report_and_exits_non_zero(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """AC14 through the command: the provider answers 429 on the second subject. The first is
    drafted and posted; the second is left with the provider's reason; everything after is left
    as not attempted; the report on disk says so, and the run exits 1. When the provider failed,
    the report on disk already named the first draft as posted: a run killed there keeps it."""
    root, _ = graph
    report = tmp_path / "report.json"
    on_disk_at_failure: list[dict[str, Any]] = []

    class Failing(ScriptedModel):
        def complete(self, *, system: str, prompt: str, max_tokens: int = 16000) -> Any:
            if len(self.prompts) == 1:
                on_disk_at_failure.append(json.loads(report.read_text(encoding="utf-8")))
            return super().complete(system=system, prompt=prompt, max_tokens=max_tokens)

    model = Failing([GLOSS, 429])
    service = FakeService(report_path=report)
    wire(monkeypatch, model, service)

    code, _ = draft(root, report, capsys, "--submit-url", SERVICE)

    assert code == 1
    on_disk = json.loads(report.read_text(encoding="utf-8"))
    assert on_disk["finished"] and on_disk["cut_short"] == "provider"
    drafting = on_disk["drafting"]
    assert drafting["stop_kind"] == "provider" and "429" in drafting["stopped"]
    assert [d["key"] for d in drafting["drafted"]] == [f"gloss {TARGET}/and-reassoc statement"]
    assert keys_of(on_disk["posted"]) == [key("and-reassoc", "Statement.lean")]
    left = drafting["left"]
    assert left[0]["key"] == f"gloss {TARGET}/and-reassoc witness"
    assert "429" in left[0]["reason"]
    assert all("not attempted" in e["reason"] for e in left[1:])
    assert len(left) == 5  # the witness, the explainer, the root's witness, the tutorial's two
    assert keys_of(drafting["skipped"]) == [f"gloss {TARGET}/{ROOT} statement"]
    [before] = on_disk_at_failure
    assert keys_of(before["posted"]) == [key("and-reassoc", "Statement.lean")]
    assert before["finished"] is False


def test_a_service_that_refuses_stops_the_run(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """A 429 from the service (the drafter's write or pull-request limit) stops the run before
    another model call is spent on a draft nothing will take; the run exits 1."""
    root, _ = graph
    model = ScriptedModel([GLOSS])
    service = FakeService(answers={0: 429})
    wire(monkeypatch, model, service)
    code, out = draft(root, tmp_path / "r.json", capsys, "--submit-url", SERVICE)
    assert code == 1
    assert out["cut_short"] == "service" and len(model.prompts) == 1
    [failed] = out["post_failed"]
    assert failed["status"] == 429 and failed["key"] == key("and-reassoc", "Statement.lean")
    assert out["drafting"]["stop_kind"] == "caller"
    assert all("the service stopped the run" in e["reason"] for e in out["drafting"]["left"])


def test_an_unreachable_service_stops_the_run(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    root, _ = graph
    service = FakeService(answers={0: draft_run.PostError("the service could not be reached")})
    wire(monkeypatch, ScriptedModel([GLOSS]), service)
    code, out = draft(root, tmp_path / "r.json", capsys, "--submit-url", SERVICE)
    assert code == 1 and out["cut_short"] == "service"


# --- a dry run ----------------------------------------------------------------------------------


def test_a_dry_run_calls_no_model_and_posts_nothing(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--dry-run`` needs no credential (it is what the workflow runs without them), builds no
    model and no poster, and lists what would be drafted and why: every gloss subject with its
    coverage reason, the outlined proof, the two without an outline, and the Context passed over.
    """
    root, commit = graph

    def forbidden(*_args: Any) -> Any:
        pytest.fail("a dry run built a model or a poster")

    monkeypatch.setattr(draft_run, "make_model", forbidden)
    monkeypatch.setattr(draft_run, "make_poster", forbidden)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPN_DRAFTER_TOKEN", raising=False)
    report = tmp_path / "dry.json"
    code, out = draft(root, report, capsys, "--dry-run")
    assert code == 0, out
    assert out["mode"] == "dry-run" and out["model"] is None and out["graph_commit"] == commit
    planned = {p["key"]: p["reason"] for p in out["planned"]}
    assert list(planned) == [
        *GLOSS_KEYS[:2],
        key(OUTLINED, "Proof.lean"),
        *GLOSS_KEYS[2:],
    ]
    assert planned[key(ROOT, "Statement.lean")] == glosses.ROOT_WITHOUT_INFORMAL
    assert planned[key(OUTLINED, "Proof.lean")] == glosses.NO_EXPLAINER
    assert len(out["no_outline"]) == 2
    assert out["drafting"] is None and out["posted"] == [] and out["post_failed"] == []
    assert out == json.loads(report.read_text(encoding="utf-8"))


def test_new_offers_what_has_no_chain_and_uncovered_offers_more(
    graph: tuple[Path, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gloss of text that has since changed leaves its file uncovered (R20) but the file has a
    chain: ``new`` (what a merge just created, R17) passes it by, ``uncovered`` (the backfill,
    R21) offers it."""
    root, _ = graph
    witness = nodes(root) / "and-reassoc" / "Witness.lean"
    doc = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {
            "kind": "witness",
            "node": "and-reassoc",
            "module": None,
            "lean_hash": schemas.content_hash(b"an earlier text\n"),
        },
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    text = "---\n" + json.dumps(doc) + "\n---\nWhat the witness said.\n"
    directory = witness.parent / glosses.GLOSS_DIR
    directory.mkdir()
    (directory / f"{schemas.content_hash(text.encode())}.md").write_text(text, encoding="utf-8")

    _, new = draft(root, tmp_path / "new.json", capsys, "--dry-run")
    _, uncovered = draft(
        root, tmp_path / "all.json", capsys, "--dry-run", "--subjects", "uncovered"
    )
    witness_key = key("and-reassoc", "Witness.lean")
    assert witness_key not in [p["key"] for p in new["planned"]]
    [row] = [p for p in uncovered["planned"] if p["key"] == witness_key]
    assert row["reason"] == glosses.EARLIER_TEXT
    # A Context.lean is never drafted: it is covered by the statements it restates (R20).
    [context] = uncovered["passed_over"]
    assert context["key"] == key(ROOT, "Context.lean") and "restates" in context["reason"]


def test_a_named_list_drafts_those_and_says_why_any_is_passed_over(
    graph: tuple[Path, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = graph
    names = tmp_path / "keys.txt"
    names.write_text(
        "# the run by hand on a named list (R17)\n"
        f"{key('tutorial-and-swap', 'Witness.lean')}\n"
        f"{key(ROOT, 'Statement.lean')}\n"
        "targets/propositional/nodes/no-such-node/Statement.lean\n",
        encoding="utf-8",
    )
    _, out = draft(root, tmp_path / "r.json", capsys, "--dry-run", "--subjects", str(names))
    assert out["subjects"] == "list"
    assert [p["key"] for p in out["planned"]] == [
        key("tutorial-and-swap", "Witness.lean"),
        key(ROOT, "Statement.lean"),
    ]
    [passed] = out["passed_over"]
    assert passed["key"].endswith("no-such-node/Statement.lean")


def test_a_root_statement_is_never_sent_to_the_model(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """F20-Q11: named alone, the root's statement is skipped by rule; no model call, no post."""
    root, _ = graph
    names = tmp_path / "keys.txt"
    names.write_text(key(ROOT, "Statement.lean") + "\n", encoding="utf-8")
    model = ScriptedModel([])
    service = FakeService()
    wire(monkeypatch, model, service)
    code, out = draft(
        root, tmp_path / "r.json", capsys, "--subjects", str(names), "--submit-url", SERVICE
    )
    assert code == 0, out
    assert model.prompts == [] and service.bodies == []
    assert keys_of(out["drafting"]["skipped"]) == [f"gloss {TARGET}/{ROOT} statement"]


# --- refusals -----------------------------------------------------------------------------------


def test_a_live_run_without_credentials_refuses_by_name(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = graph
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPN_DRAFTER_TOKEN", raising=False)
    code = cli.main(["gloss", "draft", "--graph", str(root), "--report", str(tmp_path / "r.json")])
    err = capsys.readouterr().err
    assert code == 2
    assert "OPENROUTER_API_KEY" in err and "OPN_DRAFTER_TOKEN" in err and "--submit-url" in err
    assert not (tmp_path / "r.json").exists()


def test_the_token_is_a_secret_of_the_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from opn_gate import config  # noqa: PLC0415

    settings = config.load({"OPN_DRAFTER_TOKEN": TOKEN})
    assert settings.drafter_token == TOKEN
    assert "drafter_token" in config.SECRET_NAMES
    assert TOKEN not in repr(settings)


def test_a_spent_token_budget_ends_a_batch_without_failing_it(
    graph: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    live: None,
) -> None:
    """The budget (C6, §6) is a cap like the subject cap: the run stops, names what it left, and
    exits 0; the next batch picks the rest up. Only the provider or the service fail a run."""
    root, _ = graph
    monkeypatch.setenv("OPN_DRAFTER_TOKEN_BUDGET", "100")  # one call reports 150 tokens
    model = ScriptedModel([GLOSS])
    wire(monkeypatch, model, FakeService())
    code, out = draft(root, tmp_path / "r.json", capsys, "--submit-url", SERVICE)
    assert code == 0, out
    assert out["drafting"]["stop_kind"] == "budget" and out["cut_short"] is None
    assert len(out["posted"]) == 1 and len(model.prompts) == 1


def test_the_real_poster_sends_the_token_in_one_header_and_names_no_secret() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"path": "p", "hash": "h", "pr_url": "u"})

    poster = draft_run.HttpPoster(SERVICE + "/", TOKEN, transport=httpx.MockTransport(handler))
    answer = poster.post({"text": "x"})
    assert answer == draft_run.Answer(201, {"path": "p", "hash": "h", "pr_url": "u"})
    [request] = seen
    assert str(request.url) == SERVICE + "/glosses"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(request.content) == {"text": "x"}

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(draft_run.PostError) as caught:
        draft_run.HttpPoster(SERVICE, TOKEN, transport=httpx.MockTransport(down)).post({})
    assert TOKEN not in str(caught.value) and "ConnectError" in str(caught.value)
