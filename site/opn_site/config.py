"""The site generator's configuration (C6). Read here and nowhere else.

``OPN_SITE_GRAPH_REPO_URL``
    The graph repository every page links files into at the rendered commit (F04-R2).
    Default: the Stage 0 graph under the founder's account (D-35, conventions §1).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_GRAPH_REPO_URL = "https://github.com/thisisanameforsure/open_proof_network_graph"


@dataclass(frozen=True)
class Settings:
    graph_repo_url: str = DEFAULT_GRAPH_REPO_URL


def load(environ: dict[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    return Settings(graph_repo_url=env.get("OPN_SITE_GRAPH_REPO_URL", DEFAULT_GRAPH_REPO_URL))
