"""The Lambda entrypoint (F05-R1): ``opn_api.lambda_handler.handler``.

Builds the application once per execution environment from the function's environment plus
the SecureString parameters under ``OPN_API_PARAMETER_PREFIX`` (C8 item 3), and hands events
to it through Mangum (the API Gateway HTTP API payload, no server process).
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


handler = Mangum(build(), lifespan="off")
