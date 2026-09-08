"""The one config module for the gate (conventions §1; constitution C6, C8; F00-R17).

Every environment variable and secret the gate reads is read here and nowhere else. Each
non-secret value has a documented default; secrets default to ``None`` and are never logged.

Variables (prefix ``OPN_``):

``OPN_RUNNER``
    Runner class recorded in attestations (D-34): ``local`` or ``hosted``. Default ``local``.
``OPN_LOG_LEVEL``
    Python logging level name for the gate's own logs. Default ``INFO``.
``OPN_ELAN_HOME``
    Where elan keeps toolchains; used only to locate the pinned toolchain when it is not already
    on ``PATH``. Default ``~/.elan``.
``OPN_DIAGNOSTIC_MAX_BYTES``
    Diagnostics longer than this are truncated with an explicit marker (F00 §6). Default ``8192``.
``OPN_LEAN_PKG_BIN``
    Directory holding the gate's Lean metaprograms (``opn-witness-type``, ``opn-used-constants``,
    ``opn-hazards``; F01-R1, F02-R1). Default: ``gate/lean/.lake/build/bin`` in this repo; the
    step-3 image sets its own.
``OPN_GATE_SIGNING_KEY``
    **Secret.** The gate's ed25519 private key (C8 item 1), present only in the post-merge job's
    environment. Default ``None`` — meaning "no key: emit an unsigned attestation".
``OPN_PRECHECK_SIGNING_KEY``
    **Secret.** The precheck service's ed25519 private key (C8 item 2). Default ``None``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Runner = Literal["local", "hosted"]

DEFAULT_RUNNER: Runner = "local"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ELAN_HOME = Path.home() / ".elan"
DEFAULT_DIAGNOSTIC_MAX_BYTES = 8192
DEFAULT_LEAN_PKG_BIN = Path(__file__).resolve().parents[1] / "lean" / ".lake" / "build" / "bin"

SECRET_NAMES: tuple[str, ...] = ("gate_signing_key", "precheck_signing_key")


class ConfigError(ValueError):
    """A configured value is not acceptable. Raised at load time, never later (C7)."""


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the gate's configuration."""

    runner: Runner = DEFAULT_RUNNER
    log_level: str = DEFAULT_LOG_LEVEL
    elan_home: Path = DEFAULT_ELAN_HOME
    diagnostic_max_bytes: int = DEFAULT_DIAGNOSTIC_MAX_BYTES
    lean_pkg_bin: Path = DEFAULT_LEAN_PKG_BIN
    gate_signing_key: str | None = field(default=None, repr=False)
    precheck_signing_key: str | None = field(default=None, repr=False)

    def __repr__(self) -> str:  # secrets never appear in a repr or a log (C8)
        return (
            f"Settings(runner={self.runner!r}, log_level={self.log_level!r}, "
            f"elan_home={str(self.elan_home)!r}, "
            f"diagnostic_max_bytes={self.diagnostic_max_bytes}, "
            f"lean_pkg_bin={str(self.lean_pkg_bin)!r}, "
            f"gate_signing_key={'<set>' if self.gate_signing_key else None}, "
            f"precheck_signing_key={'<set>' if self.precheck_signing_key else None})"
        )


def load(environ: dict[str, str] | None = None) -> Settings:
    """Build ``Settings`` from ``environ`` (default: the real process environment).

    Tests pass an explicit mapping; production code calls ``load()`` with no argument. This is the
    only function in the gate that touches ``os.environ``.
    """
    env = os.environ if environ is None else environ

    raw_runner = env.get("OPN_RUNNER", DEFAULT_RUNNER)
    runner: Runner
    if raw_runner == "local":
        runner = "local"
    elif raw_runner == "hosted":
        runner = "hosted"
    else:
        msg = f"OPN_RUNNER must be 'local' or 'hosted', got {raw_runner!r}"
        raise ConfigError(msg)

    raw_max = env.get("OPN_DIAGNOSTIC_MAX_BYTES", str(DEFAULT_DIAGNOSTIC_MAX_BYTES))
    try:
        diagnostic_max_bytes = int(raw_max)
    except ValueError as exc:
        msg = f"OPN_DIAGNOSTIC_MAX_BYTES must be an integer, got {raw_max!r}"
        raise ConfigError(msg) from exc
    if diagnostic_max_bytes <= 0:
        msg = f"OPN_DIAGNOSTIC_MAX_BYTES must be positive, got {diagnostic_max_bytes}"
        raise ConfigError(msg)

    return Settings(
        runner=runner,
        log_level=env.get("OPN_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        elan_home=Path(env.get("OPN_ELAN_HOME", str(DEFAULT_ELAN_HOME))).expanduser(),
        diagnostic_max_bytes=diagnostic_max_bytes,
        lean_pkg_bin=Path(env.get("OPN_LEAN_PKG_BIN", str(DEFAULT_LEAN_PKG_BIN))).expanduser(),
        gate_signing_key=env.get("OPN_GATE_SIGNING_KEY") or None,
        precheck_signing_key=env.get("OPN_PRECHECK_SIGNING_KEY") or None,
    )


def child_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """A copy of the process environment for a child process, plus ``extra``.

    The toolchain seam passes this to ``subprocess`` so elan finds its home; the gate never reads
    a value from it here. This is the second and last place the module touches ``os.environ``.
    """
    merged = dict(os.environ)
    if extra:
        merged.update(extra)
    return merged
