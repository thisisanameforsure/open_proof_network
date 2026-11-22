"""F14-T20: every draft is admitted by the gate before any pull request opens.

The hosted fast check samples a port in 20 s and reads no committed ``defs/`` (T19, Q17); the
gate's own admission in the sandbox image is the verdict. ``gate/tools/wave_admit.py`` takes a
drafts directory the wave driver wrote, imports each draft (one shard of them) into a scratch copy
of a graph with ``intake import-fc --sandbox --image <the pinned image>`` and records what the
gate said, so that the import of the bulk load runs only over what the gate has already admitted.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph
from test_wave import PIN, run_wave

TOOL = Path(__file__).resolve().parents[1] / "tools" / "wave_admit.py"
IMAGE = "ghcr.io/example/opn-gate@sha256:" + "a" * 64


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("wave_admit", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def drafts(tmp_path: Path) -> tuple[Path, Path, Path]:
    """The fixture registry drafted, a scratch graph, and a live-shaped gate-spec to inherit."""
    out, _result, _doc = run_wave(tmp_path)
    graph = copy_graph(tmp_path / "graph-parent", publish=True)
    spec = graph / "targets" / TARGET / "gate-spec.json"
    return out, graph, spec


def test_shards_partition_the_drafts_in_id_order() -> None:
    tool = load_tool()
    ids = [f"t{i}" for i in range(10)]
    shards = [tool.shard_of(ids, k, 4) for k in range(4)]
    assert shards == [["t0", "t4", "t8"], ["t1", "t5", "t9"], ["t2", "t6"], ["t3", "t7"]]
    assert tool.shard_of(ids, 0, 1) == ids
    with pytest.raises(ValueError, match="shard 4 of 4"):
        tool.shard_of(ids, 4, 4)


def test_the_import_command_is_the_scripts_with_the_sandbox_and_the_image(
    drafts: tuple[Path, Path, Path],
) -> None:
    """One source for a draft's inputs: its manifest. The argv is import.sh's line for the target
    with --sandbox, the pinned image and the spec to inherit; a draft with ports passes --defs, a
    draft with acknowledgements --hazards, and the mode `no-toolchain` is the dry run."""
    out, graph, spec = drafts
    tool = load_tool()
    manifest = json.loads((out / "erdos-7003" / "draft.json").read_text(encoding="utf-8"))
    argv = tool.import_argv(
        out / "erdos-7003",
        manifest,
        graph=graph,
        spec=spec,
        image=IMAGE,
        mode="sandbox",
        pin=PIN,
        network="1" * 40,
        catalog=Path("docs/lean_conjecture_catalog.json"),
        author="curator",
    )
    assert argv[:3] == ["intake", "import-fc", str(out / "upstream" / manifest["file"])]
    joined = " ".join(argv)
    assert f"--at {PIN}" in joined and f"--graph {graph}" in joined
    assert "--target erdos-7003" in joined and f"--spec {spec}" in joined
    assert f"--defs {out / 'erdos-7003' / 'defs'}" in joined and "--hazards" not in joined
    assert (
        "--key erdos:7003" in joined
        and "--evidence-from docs/lean_conjecture_catalog.json" in joined
    )
    assert argv[-3:] == ["--sandbox", "--image", IMAGE]
    plain = json.loads((out / "erdos-7001" / "draft.json").read_text(encoding="utf-8"))
    dry = tool.import_argv(
        out / "erdos-7001",
        plain,
        graph=graph,
        spec=spec,
        image=None,
        mode="no-toolchain",
        pin=PIN,
        network="1" * 40,
        catalog=Path("c.json"),
        author="curator",
    )
    assert "--defs" not in dry and dry[-1] == "--no-toolchain" and "--image" not in dry


def fake_gate(refuse: dict[str, str]) -> Callable[[list[str], Path], tuple[int, str]]:
    """A stand-in for the CLI: admits every target but those in ``refuse``, naming the check."""

    def command(argv: list[str], _cwd: Path) -> tuple[int, str]:
        target = argv[argv.index("--target") + 1]
        if target in refuse:
            return 1, json.dumps(
                {"ok": False, "refused": {"check": refuse[target], "message": "witness-sorry"}}
            )
        return 0, "INFO something on stderr went to stdout first\n" + json.dumps(
            {"ok": True, "target": target, "checks": [{"check": "statement", "ok": True}]}
        )

    return command


def test_a_shard_run_records_each_verdict_and_lists_the_admitted(
    drafts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    out, graph, spec = drafts
    tool = load_tool()
    seen: list[str] = []
    gate = fake_gate({"erdos-7003": "witness"})

    def command(argv: list[str], cwd: Path) -> tuple[int, str]:
        seen.append(argv[argv.index("--target") + 1])
        return gate(argv, cwd)

    report_dir = tmp_path / "admit-0"
    summary = tool.run(
        out,
        graph,
        spec,
        report_dir,
        image=IMAGE,
        shard=0,
        shards=2,
        mode="sandbox",
        command=command,
        pin=PIN,
        network="1" * 40,
        catalog=Path("c.json"),
        author="curator",
    )
    ids = sorted(p.name for p in out.iterdir() if (p / "draft.json").is_file())
    assert seen == tool.shard_of(ids, 0, 2)
    assert "erdos-7003" in seen  # the fixture's ids put it in shard 0
    assert summary["shard"] == [0, 2] and summary["image"] == IMAGE
    assert summary["admitted"] == [t for t in seen if t != "erdos-7003"]
    assert summary["refused"] == [
        {"target": "erdos-7003", "exit": 1, "check": "witness", "message": "witness-sorry"}
    ]
    # Each verdict is kept whole, the admitted ones too.
    saved = json.loads((report_dir / "erdos-7003.json").read_text(encoding="utf-8"))
    assert saved["ok"] is False and saved["verdict"]["refused"]["check"] == "witness"
    first = json.loads((report_dir / f"{summary['admitted'][0]}.json").read_text(encoding="utf-8"))
    assert first["ok"] is True and first["verdict"]["checks"][0]["check"] == "statement"
    assert json.loads((report_dir / "summary.json").read_text(encoding="utf-8")) == summary


def test_the_merged_report_filters_the_import_script_to_the_admitted(
    drafts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """The shards' summaries merge into one report, and the import script the curator runs is
    import.sh with only the admitted targets' lines (the header kept)."""
    out, graph, spec = drafts
    tool = load_tool()
    gate = fake_gate({"erdos-7003": "witness", "erdos-7001": "statement"})
    shards = [
        tool.run(
            out,
            graph,
            spec,
            tmp_path / f"admit-{k}",
            image=IMAGE,
            shard=k,
            shards=3,
            mode="sandbox",
            command=gate,
            pin=PIN,
            network="1" * 40,
            catalog=Path("c.json"),
            author="curator",
        )
        for k in range(3)
    ]
    merged = tool.merge([tmp_path / f"admit-{k}" for k in range(3)], out, tmp_path / "merged")
    ids = sorted(p.name for p in out.iterdir() if (p / "draft.json").is_file())
    assert merged["admitted"] == [t for t in ids if t not in ("erdos-7001", "erdos-7003")]
    assert [r["target"] for r in merged["refused"]] == ["erdos-7001", "erdos-7003"]
    assert merged["shards"] == 3 and sum(len(s["admitted"]) for s in shards) == len(
        merged["admitted"]
    )
    script = (tmp_path / "merged" / "import-admitted.sh").read_text(encoding="utf-8")
    original = (out / "import.sh").read_text(encoding="utf-8")
    assert script.startswith(original.split("uv run", 1)[0])  # the header, verbatim
    assert "--target erdos-7003 " not in script and "--target erdos-7001 " not in script
    assert all(f"--target {t} " in script for t in merged["admitted"])
    assert script.count("uv run") == len(merged["admitted"])
    report = (tmp_path / "merged" / "REPORT.md").read_text(encoding="utf-8")
    assert f"Admitted {len(merged['admitted'])}, refused 2" in report
    assert "`erdos-7003`: witness — witness-sorry" in report


def test_the_dry_run_imports_through_the_real_command(
    drafts: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """Mode `no-toolchain` drives the real CLI: the targets land in the scratch graph with their
    ports, and the verdict is the import's own JSON."""
    out, graph, spec = drafts
    tool = load_tool()
    summary = tool.run(
        out,
        graph,
        spec,
        tmp_path / "dry",
        image=None,
        shard=0,
        shards=1,
        mode="no-toolchain",
        command=None,
        pin=PIN,
        network="1" * 40,
        catalog=out.parent / "catalog.json",
        author="curator",
        only=["erdos-7003", "erdos-7001"],
    )
    assert summary["admitted"] == ["erdos-7001", "erdos-7003"], summary
    assert (graph / "targets" / "erdos-7003" / "defs" / "Local.lean").is_file()
    doc = yaml.safe_load(
        (graph / "targets" / "erdos-7003" / "target.yaml").read_text(encoding="utf-8")
    )
    assert doc["id"] == "erdos-7003"
    saved = json.loads((tmp_path / "dry" / "erdos-7003.json").read_text(encoding="utf-8"))
    assert saved["verdict"]["ok"] is True


def test_the_verdict_is_read_through_the_log_lines_around_it() -> None:
    """The CLI prints its JSON indented, and when it refuses, the sandbox's log lines follow it
    on stderr (seen on the first live run: every refusal read as `error` with the log's tail as
    its message). The last JSON object is read as a prefix, whatever follows it."""
    tool = load_tool()
    text = (
        "INFO opn_gate.admit: admission check hazards failed: hazard-unacknowledged\n"
        '{\n  "ok": false,\n  "refused": {\n    "check": "hazards",\n'
        '    "message": "hazard-unacknowledged: off-by-one-range at 2 < n"\n  }\n}\n'
        "opn-gate: refused: admission refused 'erdos-1002': root: hazards: Diagnostic(...)\n"
    )
    verdict = tool.last_json(text)
    assert verdict is not None and verdict["refused"]["check"] == "hazards"
    check, message = tool.refusal_of(verdict, text)
    assert check == "hazards" and message.startswith("hazard-unacknowledged: off-by-one-range")
