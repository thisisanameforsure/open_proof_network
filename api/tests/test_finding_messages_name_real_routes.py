"""F22-T25 (R6): every route a service message names exists.

Tester finding 2026-10-06: two answers (``github-login-taken`` and ``token-expired``) sent a
person to ``POST /tokens/recover {pseudonym, recovery_code}``, a route the service does not
have, because the recovery code D-19 v3.29 promises (F05-T30) was never built. A message is an
instruction an agent follows literally; one that names a missing route costs a 404 and a guess.
The guard reads every ``METHOD /path`` written in the service's source and holds it to
``routes.ROUTES``."""

from __future__ import annotations

import re
from pathlib import Path

from opn_api import routes

SOURCE = Path(__file__).resolve().parents[1] / "opn_api"
NAMED = re.compile(r"\b(GET|POST|DELETE|PUT|PATCH) (/[A-Za-z0-9_./{}<>-]*)")
#: The modules that speak to other hosts (GitHub, AXLE) name those hosts' routes, not ours.
OTHER_HOSTS = {"githost.py", "axle.py"}


def known(method: str, path: str) -> bool:
    path = path.rstrip(".,;:)")
    for spec in routes.ROUTES:
        pattern = re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(spec.path))
        concrete = re.sub(r"<[^>]+>", "x", path)
        if spec.method == method and (spec.path == path or re.fullmatch(pattern, concrete)):
            return True
    return False


def test_every_route_a_message_names_exists() -> None:
    missing = sorted(
        {
            f"{file.relative_to(SOURCE)}: {method} {path}"
            for file in SOURCE.rglob("*.py")
            if file.name not in OTHER_HOSTS
            for method, path in NAMED.findall(file.read_text(encoding="utf-8"))
            if not known(method, path)
        }
    )
    assert missing == [], missing
