"""The one config module for the gate (conventions §1; constitution C6, C8; F00-R17).

Every environment variable and secret the gate reads is read here and nowhere else. Each
non-secret value has a documented default; secrets default to ``None`` and are never logged.

Variables (prefix ``OPN_``):

``OPN_RUNNER``
    Runner class recorded in attestations (D-34): ``local`` or ``hosted``. Default ``local``.
``OPN_LOG_LEVEL``
    Python logging level name for the gate's own logs, checked against the names ``logging``
    knows at load. Default ``INFO``.
``OPN_ELAN_HOME``
    Where elan keeps toolchains; used only to locate the pinned toolchain when it is not already
    on ``PATH``. Default ``~/.elan``.
``OPN_DIAGNOSTIC_MAX_BYTES``
    Diagnostics longer than this are truncated with an explicit marker (F00 §6). Default ``8192``.
``OPN_LEAN_PKG_BIN``
    Directory holding the gate's Lean metaprograms (``opn-witness-type``, ``opn-used-constants``,
    ``opn-hazards``; F01-R1, F02-R1). Default: ``gate/lean/.lake/build/bin`` in this repo; the
    step-3 image sets its own.
``OPN_MATHLIB_HOME``
    Where Mathlib checkouts live, one per pinned commit: ``<home>/<sha>`` holds the checkout
    ``gate/scripts/install-mathlib.sh`` made, with its built oleans (F11-R6; D-7). Consulted only
    when a graph's ``gate-spec.json`` pins ``mathlib_sha``. Default ``~/.opn/mathlib``; the
    step-3 image sets its own.
``OPN_PR_AUTHOR``
    The login that opened the pull request under check, as the host reports it
    (``github.event.pull_request.user.login``). Consulted by ``classify`` for the curator mode
    alone (F08-R8), where the author must be a listed identity; ``--author`` overrides it. It is
    an environment variable rather than only a flag so the graph's workflow can set it before its
    pinned gate understands the flag (F08-Q8). Default ``None``: no author is known, and a
    curator-shaped pull request is refused.
``OPN_LISTED_TARGETS_MAX``
    How many open-track targets may be listed at once (F11-R9; Stages: Stage 0 lists a handful so
    the mission is visible, and none of them is claimable). Default ``5``.
``OPN_QA_ATTEMPT_BUDGET_S``
    The tactic budget of one soundness-screen attempt, in wall-clock seconds inside the sandbox
    (F12-R3, §6). Default ``60``; provisional until the on-ramp graph measures it (F12-Q4).
``OPN_QA_SUBJECT_BUDGET_S``
    The budget of one ``qa screen`` run over one subject, in seconds; attempts that would start
    past it are recorded ``inconclusive`` rather than skipped (F12-R3, §6). Default ``300``.
``OPN_MODEL``
    The model the QA brief and back-translation ask (F12-R6, R7, Q5): a Messages API model id
    whose leading letters name its family for R7's independence rule. Default ``claude-opus-5``.
``OPN_MODEL_API_KEY``
    **Secret.** The model provider's API key (F12 §7; C8: the curator's ``.env``, never in
    the graph, a log or a record). Default ``None`` — meaning "no model: the brief and
    back-translation refuse before they start".
``OPN_GATE_SIGNING_KEY``
    **Secret.** The gate's ed25519 private key (C8 item 1), present only in the post-merge job's
    environment. Default ``None`` — meaning "no key: emit an unsigned attestation".
``OPN_PRECHECK_SIGNING_KEY``
    **Secret.** The precheck service's ed25519 private key (C8 item 2). Default ``None``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Runner = Literal["local", "hosted"]

DEFAULT_RUNNER: Runner = "local"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ELAN_HOME = Path.home() / ".elan"
DEFAULT_DIAGNOSTIC_MAX_BYTES = 8192
DEFAULT_LISTED_TARGETS_MAX = 5  # F11-R9 §6: the Stage 0 count, config rather than a constant
DEFAULT_LEAN_PKG_BIN = Path(__file__).resolve().parents[1] / "lean" / ".lake" / "build" / "bin"
DEFAULT_MATHLIB_HOME = Path.home() / ".opn" / "mathlib"  # F11-R6: one checkout per pinned sha
DEFAULT_QA_ATTEMPT_BUDGET_S = 60.0  # F12 §6: per screen attempt, provisional (F12-Q4)
DEFAULT_QA_SUBJECT_BUDGET_S = 300.0  # F12 §6: per subject per run
DEFAULT_MODEL = "claude-opus-5"  # F12-Q5: recorded on every brief row, swapped by config

SECRET_NAMES: tuple[str, ...] = ("gate_signing_key", "precheck_signing_key", "model_api_key")


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
    mathlib_home: Path = DEFAULT_MATHLIB_HOME
    listed_targets_max: int = DEFAULT_LISTED_TARGETS_MAX
    qa_attempt_budget_s: float = DEFAULT_QA_ATTEMPT_BUDGET_S
    qa_subject_budget_s: float = DEFAULT_QA_SUBJECT_BUDGET_S
    model: str = DEFAULT_MODEL
    pr_author: str | None = None
    model_api_key: str | None = field(default=None, repr=False)
    gate_signing_key: str | None = field(default=None, repr=False)
    precheck_signing_key: str | None = field(default=None, repr=False)

    def __repr__(self) -> str:  # secrets never appear in a repr or a log (C8)
        return (
            f"Settings(runner={self.runner!r}, log_level={self.log_level!r}, "
            f"elan_home={str(self.elan_home)!r}, "
            f"diagnostic_max_bytes={self.diagnostic_max_bytes}, "
            f"listed_targets_max={self.listed_targets_max}, "
            f"qa_attempt_budget_s={self.qa_attempt_budget_s}, "
            f"qa_subject_budget_s={self.qa_subject_budget_s}, model={self.model!r}, "
            f"model_api_key={'<set>' if self.model_api_key else None}, "
            f"lean_pkg_bin={str(self.lean_pkg_bin)!r}, "
            f"mathlib_home={str(self.mathlib_home)!r}, pr_author={self.pr_author!r}, "
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

    raw_listed = env.get("OPN_LISTED_TARGETS_MAX", str(DEFAULT_LISTED_TARGETS_MAX))
    try:
        listed_targets_max = int(raw_listed)
    except ValueError as exc:
        msg = f"OPN_LISTED_TARGETS_MAX must be an integer, got {raw_listed!r}"
        raise ConfigError(msg) from exc
    if listed_targets_max < 0:
        msg = f"OPN_LISTED_TARGETS_MAX must not be negative, got {listed_targets_max}"
        raise ConfigError(msg)

    budgets: dict[str, float] = {}
    for name, default in (
        ("OPN_QA_ATTEMPT_BUDGET_S", DEFAULT_QA_ATTEMPT_BUDGET_S),
        ("OPN_QA_SUBJECT_BUDGET_S", DEFAULT_QA_SUBJECT_BUDGET_S),
    ):
        raw_budget = env.get(name, str(default))
        try:
            budgets[name] = float(raw_budget)
        except ValueError as exc:
            msg = f"{name} must be a number of seconds, got {raw_budget!r}"
            raise ConfigError(msg) from exc
        if not budgets[name] > 0 or budgets[name] == float("inf"):
            msg = f"{name} must be a positive number of seconds, got {raw_budget!r}"
            raise ConfigError(msg)

    raw_level = env.get("OPN_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    log_level = raw_level.upper()
    if log_level not in logging.getLevelNamesMapping():
        names = ", ".join(sorted(logging.getLevelNamesMapping()))
        msg = f"OPN_LOG_LEVEL must be a logging level name ({names}), got {raw_level!r}"
        raise ConfigError(msg)

    return Settings(
        runner=runner,
        log_level=log_level,
        elan_home=Path(env.get("OPN_ELAN_HOME", str(DEFAULT_ELAN_HOME))).expanduser(),
        diagnostic_max_bytes=diagnostic_max_bytes,
        listed_targets_max=listed_targets_max,
        qa_attempt_budget_s=budgets["OPN_QA_ATTEMPT_BUDGET_S"],
        qa_subject_budget_s=budgets["OPN_QA_SUBJECT_BUDGET_S"],
        model=env.get("OPN_MODEL") or DEFAULT_MODEL,
        model_api_key=env.get("OPN_MODEL_API_KEY") or None,
        lean_pkg_bin=Path(env.get("OPN_LEAN_PKG_BIN", str(DEFAULT_LEAN_PKG_BIN))).expanduser(),
        mathlib_home=Path(env.get("OPN_MATHLIB_HOME", str(DEFAULT_MATHLIB_HOME))).expanduser(),
        pr_author=env.get("OPN_PR_AUTHOR") or None,
        gate_signing_key=env.get("OPN_GATE_SIGNING_KEY") or None,
        precheck_signing_key=env.get("OPN_PRECHECK_SIGNING_KEY") or None,
    )


#: What git exports to a hook, and what a linked worktree's hook therefore hands every child:
#: with these set, ``git -C <graph>`` acts on the *calling* repository, not on the graph checkout.
#: The gate's git calls drop them (F08-Q18).
GIT_REPO_VARIABLES: tuple[str, ...] = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_PREFIX")


def child_environment(
    extra: dict[str, str] | None = None, *, drop: tuple[str, ...] = ()
) -> dict[str, str]:
    """A copy of the process environment for a child process, plus ``extra``, minus ``drop``.

    The toolchain seam passes this to ``subprocess`` so elan finds its home, and the gate's git
    calls pass ``drop=GIT_REPO_VARIABLES``; the gate never reads a value from it here. This is the
    second and last place the module touches ``os.environ``.
    """
    merged = {k: v for k, v in os.environ.items() if k not in drop}
    if extra:
        merged.update(extra)
    return merged
