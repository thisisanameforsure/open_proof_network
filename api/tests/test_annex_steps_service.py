"""F18-T5 (R6; D-31 v3.26): the service takes a stepped annex, and refuses a skeleton that
does not follow one before any pull request opens.

* ``POST /annexes`` takes ``steps`` (``[{id, summary}]``) and writes ``annex/v2``; without them
  the file is ``annex/v1`` byte for byte as before. Steps are held to ``annex/v2`` and to unique
  ids, and are taken only for a target whose pinned gate reads ``annex/v2``
  (``OPN_API_ANNEX_STEPS_FROM``, compared as ``OPN_API_USES_FROM`` is): an older gate refuses
  such an append, so the route says so instead of opening a pull request that goes red.
* ``POST /submissions`` of a partial citing a stepped annex is refused ``annex-step-missing``
  when a hole its precheck named is no step. The hole names are the extractor's — the precheck's
  result carries them (``holes[].name``) — so nothing is guessed from the text, and a result
  that names no holes refuses nothing (the gate decides).
"""

from __future__ import annotations

from typing import Any

import pytest
import samples
import yaml
from api_fakes import Harness, PrecheckKey, make_harness, make_precheck_key, result_zip
from mcp_client import NODE, NODE_DIR, TARGET, seed_node

from opn_api import config
from opn_gate import annex, modes, paths, schemas
from opn_gate.paths import Change

STEPS_FROM = "5e9" + "0" * 37
PIN = samples.SHA1  # what samples.gate_spec pins
ENV = {"OPN_API_ANNEX_STEPS_FROM": STEPS_FROM}
STEPS = [
    {"id": "right", "summary": "r follows from the hypothesis"},
    {"id": "left", "summary": "q and p, swapped"},
]


def world(h: Harness, *, understands: bool | None = True) -> None:
    seed_node(h)
    h.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(network_commit=PIN)
    )
    if understands is not None:
        h.githost.ancestry[(STEPS_FROM, PIN)] = understands
    h.context.files.clear()


def post_annex(h: Harness, token: str, **extra: Any) -> Any:
    body = {"node_id": NODE, "text": "Swap, then reassociate.\n", "licence": "CC-BY-4.0", **extra}
    return h.client.post("/annexes", json=body, headers=h.auth(token))


def only_file(h: Harness) -> tuple[str, str]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    return next(iter(push.files.items()))


# --- POST /annexes ------------------------------------------------------------------------------


def test_an_annex_with_steps_is_written_as_v2_and_the_gate_takes_it() -> None:
    h = make_harness(ENV)
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = post_annex(h, token, steps=STEPS)
        assert r.status_code == 201, r.text
        path, content = only_file(h)
        assert path == f"{NODE_DIR}annex/{r.json()['hash']}.md"
        front = annex.front_matter(content)
        assert front is not None
        assert front["schema"] == "annex/v2" and front["steps"] == STEPS
        assert schemas.violations(front, "annex/v2") == []
        assert annex.steps_of(content) == tuple(annex.Step(s["id"], s["summary"]) for s in STEPS)
        located = paths.locate(path)
        assert located is not None and located.role == "annex"
        assert paths.check_content_hash_name(located, content.encode()) is None
        assert modes.classify([Change("A", path)]).mode == "append"


def test_an_annex_without_steps_is_v1_as_before() -> None:
    h = make_harness(ENV)
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = post_annex(h, token)
        assert r.status_code == 201, r.text
        _, content = only_file(h)
        front = annex.front_matter(content)
        assert front is not None and front["schema"] == "annex/v1" and "steps" not in front


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [{"id": "1bad", "summary": "s"}],
        [{"id": "h", "summary": ""}],
        [{"id": "h", "summary": "x" * 301}],
        [{"id": "h"}],
        [{"id": "h", "summary": "s", "extra": 1}],
        "right",
        [{"id": "a", "summary": "s"}, {"id": "a", "summary": "t"}],  # ids are unique
    ],
)
def test_malformed_steps_are_refused_before_anything_is_pushed(steps: Any) -> None:
    h = make_harness(ENV)
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = post_annex(h, token, steps=steps)
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "record-invalid", r.text
        assert h.githost.pushes == [] and h.githost.pulls == []


@pytest.mark.parametrize("understands", [False, None], ids=["older-pin", "host-cannot-say"])
def test_steps_on_a_target_whose_gate_predates_v2_are_refused(understands: bool | None) -> None:
    h = make_harness(ENV)
    with h.client:
        world(h, understands=understands)
        token = h.token_for("code_alice", "alice")
        r = post_annex(h, token, steps=STEPS)
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "annex-steps-unsupported", r.text
        assert h.githost.pushes == [] and h.githost.pulls == []
        # The same prose without steps is taken as v1, as before.
        assert post_annex(h, token).status_code == 201


def test_steps_are_refused_when_no_commit_is_configured() -> None:
    h = make_harness()
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        r = post_annex(h, token, steps=STEPS)
        assert r.status_code == 400 and r.json()["error"] == "annex-steps-unsupported", r.text


def test_the_setting_defaults_empty_and_refuses_a_short_id() -> None:
    assert config.load({}).annex_steps_from == ""
    assert config.load({"OPN_API_ANNEX_STEPS_FROM": STEPS_FROM.upper()}).annex_steps_from == (
        STEPS_FROM
    )
    with pytest.raises(config.ConfigError):
        config.load({"OPN_API_ANNEX_STEPS_FROM": "5e9"})


# --- POST /submissions: the pre-flight ----------------------------------------------------------


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


PARTIAL_PATH = NODE_DIR + "attempts/20261003T120000Z-alice-partial.lean"


def annex_on_node(h: Harness, steps: list[dict[str, str]] | None) -> str:
    front = samples.annex_front_matter(node=NODE, schema="annex/v2" if steps else "annex/v1")
    if steps:
        front["steps"] = steps
    content = f"---\n{yaml.safe_dump(front, sort_keys=True)}---\nprose\n".encode()
    digest = schemas.content_hash(content)
    h.githost.files[f"{NODE_DIR}annex/{digest}.md"] = content
    h.context.files.clear()
    return digest


def assembly(digest: str) -> str:
    return (
        "theorem OpnProp.and_reassoc : True := by\n"
        f"  -- annex: {digest}\n"
        "  have right : True := sorry\n"
        "  have left : True := sorry\n"
        "  trivial\n"
    )


def passing_job(
    h: Harness, key: PrecheckKey, token: str, bundle: dict[str, str], holes: list[str] | None
) -> str:
    h.commit_precheck_key(key.public)
    created = h.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle}, headers=h.auth(token)
    )
    assert created.status_code == 202, created.text  # guard: the precheck takes this bundle
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=NODE,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
        holes=None if holes is None else [{"name": n, "closed_type": "True"} for n in holes],
    )
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    return str(doc["id"])


def submit(h: Harness, token: str, bundle: dict[str, str], job: str) -> Any:
    body = {"node_id": NODE, "artifact_type": "partial", "bundle": bundle, "precheck_job_id": job}
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def test_a_partial_whose_hole_is_no_step_is_refused_before_any_pull_request(
    key: PrecheckKey,
) -> None:
    """The precheck ran on a gate that does not check steps (it passed); its result still names
    the holes the extractor found, and ``left`` is no step of the annex."""
    h = make_harness(ENV)
    with h.client:
        world(h)
        digest = annex_on_node(h, STEPS[:1])
        token = h.token_for("code_alice", "alice")
        bundle = {PARTIAL_PATH: assembly(digest)}
        job = passing_job(h, key, token, bundle, ["right", "left"])
        pushed = len(h.githost.pushes)
        r = submit(h, token, bundle, job)
        assert r.status_code == 400, r.text
        body = r.json()
        assert body["error"] == "annex-step-missing", r.text
        assert body["details"] == {"annex": digest, "missing": ["left"], "steps": ["right"]}
        assert h.githost.pulls == [] and len(h.githost.pushes) == pushed


@pytest.mark.parametrize(
    ("steps", "holes"),
    [
        (STEPS, ["right", "left"]),  # every hole is a step
        ([*STEPS, {"id": "combine", "summary": "the assembly"}], ["right", "left"]),
        (None, ["anything"]),  # a v1 annex is unchecked
        (STEPS[:1], None),  # a result that names no holes: the gate decides
    ],
    ids=["matching", "step-without-hole", "v1", "no-holes-named"],
)
def test_a_partial_the_check_allows_opens(
    key: PrecheckKey, steps: list[dict[str, str]] | None, holes: list[str] | None
) -> None:
    h = make_harness(ENV)
    with h.client:
        world(h)
        digest = annex_on_node(h, steps)
        token = h.token_for("code_alice", "alice")
        bundle = {PARTIAL_PATH: assembly(digest)}
        job = passing_job(h, key, token, bundle, holes)
        r = submit(h, token, bundle, job)
        assert r.status_code == 201, r.text
        assert len(h.githost.pulls) == 1


# --- the MCP tool -------------------------------------------------------------------------------


def test_the_mcp_annex_tool_forwards_steps() -> None:
    """The tool declares ``steps`` and forwards it, so an agent writes a stepped annex the way
    the route takes one; without the forward the route would write ``annex/v1``."""
    from mcp_client import McpClient  # noqa: PLC0415

    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    assert "steps" in BY_NAME["submit_informal_annex"].input_schema["properties"]
    h = make_harness(ENV)
    with h.client:
        world(h)
        token = h.token_for("code_alice", "alice")
        opened = McpClient(h).ok(
            "submit_informal_annex",
            {"node_id": NODE, "text": "prose\n", "licence": "CC-BY-4.0", "steps": STEPS},
            token=token,
        )
        assert opened["body"]["pr_number"] == 1, opened
        _, content = only_file(h)
        front = annex.front_matter(content)
        assert front is not None and front["schema"] == "annex/v2" and front["steps"] == STEPS
