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
