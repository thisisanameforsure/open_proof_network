"""Shared fixtures for the gate tests. The `lean` tier needs the real toolchain (conventions §2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import config, toolchain
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

ROOT = Path(__file__).resolve().parents[2]
PINNED_TOOLCHAIN = (ROOT / "lean-toolchain").read_text().strip()


@pytest.fixture(scope="session")
def real_toolchain() -> LocalToolchain:
    """The real seam, or a failure naming the install script (R16)."""
    settings = config.load()
    elan = toolchain.find_elan(path_env=None, elan_home=settings.elan_home)
    return LocalToolchain(elan)


@pytest.fixture(scope="session")
def pinned(real_toolchain: LocalToolchain) -> ResolvedToolchain:
    return real_toolchain.resolve(PINNED_TOOLCHAIN, install=False)


@pytest.fixture(scope="session")
def sandbox_image() -> str:
    """The step-3 image for the repo's pinned toolchain, built once per session (docker tier)."""
    from opn_gate import sandbox  # noqa: PLC0415 — docker-tier only

    return sandbox.build_image(ROOT / "gate", PINNED_TOOLCHAIN)


@pytest.fixture(scope="session")
def fixture_graph_repo(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """The propositional fixture as a git repo: a base commit without the tutorial proof, then
    a commit adding Proof.lean — the shape of a merged submission."""
    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    root = tmp_path_factory.mktemp("graph-repo") / "graph"
    shutil.copytree(ROOT / "gate" / "tests" / "fixtures" / "graphs" / "propositional", root)
    proof = root / "targets/propositional/nodes/tutorial-and-swap/Proof.lean"
    proof_text = proof.read_text()
    proof.unlink()
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(root.parent),
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    proof.write_text(proof_text)
    git("add", "-A")
    git("commit", "-q", "-m", "prove tutorial-and-swap")
    return root, git("rev-parse", "HEAD")


LEAN_PKG_DIR = ROOT / "gate" / "lean"


@pytest.fixture(scope="session")
def lean_pkg(real_toolchain: LocalToolchain, pinned: ResolvedToolchain) -> Path:
    """The Lake package's built executables directory (lean tier); builds on first use."""
    import subprocess  # noqa: PLC0415

    bin_dir = LEAN_PKG_DIR / ".lake" / "build" / "bin"
    proc = subprocess.run(
        [str(real_toolchain.elan), "run", pinned.name, "lake", "build"],
        cwd=LEAN_PKG_DIR,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert (bin_dir / "opn-witness-type").is_file()
    assert (bin_dir / "opn-used-constants").is_file()
    return bin_dir
