"""The Lambda entrypoint (F05-R1): ``opn_api.lambda_handler.handler``.

Builds the application once per execution environment from the function's environment plus
the SecureString parameters under ``OPN_API_PARAMETER_PREFIX`` (C8 item 3), and hands events
to it through Mangum (the API Gateway HTTP API payload, no server process). A direct invocation
that names a scheduled task runs it instead (``TASKS``; F26-Q17).
"""

from __future__ import annotations

import logging
from typing import Any

from mangum import Mangum

from opn_api import app as appmod
from opn_api import config

log = logging.getLogger("opn_api")


def build() -> Any:
    prefix = config.load().parameter_prefix
    try:
        environ = config.environment_with_parameters(prefix)
    except Exception as exc:
        log.error("parameter store unreadable under %s: %s", prefix, type(exc).__name__)
        environ = None
    settings = config.load(environ)
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    return appmod.create_app(settings)


APP = build()
_HTTP = Mangum(APP, lifespan="off")
#: F26-Q17 (ruled 2026-10-12): the scheduled tasks a direct invocation may run. A direct
#: invocation reaches the function only through IAM (``lambda:InvokeFunction``, which the nightly
#: workflow's role holds and nothing else does); an API Gateway event is always served as HTTP.
TASKS: tuple[str, ...] = ("review-notice",)


def _is_http(event: Any) -> bool:
    return isinstance(event, dict) and "requestContext" in event


def handler(event: Any, context: Any) -> Any:
    """An API Gateway event to the app through Mangum; a direct invocation naming one of
    ``TASKS`` (``{"opn_task": "review-notice", "targets": [...]?}``) runs that task on the app's own
    context and answers its outcomes. Anything else is refused by name, never guessed at."""
    if _is_http(event) or not isinstance(event, dict) or "opn_task" not in event:
        return _HTTP(event, context)
    task = str(event["opn_task"])
    if task not in TASKS:
        log.warning("refused a direct invocation naming task %r", task)
        return {"task": task, "error": "unknown-task"}
    from opn_api import review_notice  # noqa: PLC0415 — only the scheduled task needs it

    targets = event.get("targets")
    target_ids = [str(t) for t in targets] if isinstance(targets, list) else None
    outcomes = review_notice.run(APP.state.context, target_ids)
    log.info("review notice: %d targets read", len(outcomes))
    return {"task": task, "outcomes": outcomes}
