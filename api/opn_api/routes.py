"""The one routes table (F05-R1): every endpoint, with the D-35 row it is the plain path of.

The bijection audit (F09) reads this table: a write route (any method but GET) must name its
D-35 row, and every D-35 row a feature owns must have a route. Read routes may stand alone —
D-28 lists reads as repo-served files the service mirrors.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSpec:
    method: str
    path: str
    handler: str  # ``module:function`` inside opn_api, resolved by app.py
    d35: str | None  # the D-35 plain-path row, verbatim as the document writes it
    authenticated: bool = False  # R5: bearer required
    feature: str = "F05"

    @property
    def write(self) -> bool:
        return self.method != "GET"

    @property
    def label(self) -> str:
        return f"{self.method} {self.path}"


# D-35's plain-path rows F05 owns (the token row and the claim row), verbatim.
D35_POST_TOKENS = "POST /tokens"
D35_POST_PRECHECK = "POST /precheck"
D35_GET_PRECHECK = "GET /precheck/<id>"
D35_POST_CLAIMS = "POST /claims"
D35_DELETE_CLAIM = "DELETE /claims/<id>"
D35_OWNED_BY_F05: frozenset[str] = frozenset({D35_POST_TOKENS, D35_POST_CLAIMS, D35_DELETE_CLAIM})
# F06 owns the precheck pair; GET is a read, so only the POST is a write route (AC13).
D35_OWNED_BY_F06: frozenset[str] = frozenset({D35_POST_PRECHECK, D35_GET_PRECHECK})

ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec("GET", "/health", "app:health", None),
    RouteSpec("GET", "/info.json", "info:get_info", None),
    RouteSpec("GET", "/dco.json", "identity:get_dco", None),
    RouteSpec("GET", "/frontier.json", "frontier:get_frontier", None),
    RouteSpec("GET", "/claims.json", "frontier:get_claims", None),
    RouteSpec("GET", "/auth/github/start", "identity:github_start", D35_POST_TOKENS),
    RouteSpec("GET", "/auth/github/callback", "identity:github_callback", D35_POST_TOKENS),
    RouteSpec("POST", "/tokens", "identity:post_tokens", D35_POST_TOKENS),
    RouteSpec("POST", "/claims", "claims:post_claims", D35_POST_CLAIMS, authenticated=True),
    RouteSpec(
        "DELETE", "/claims/{claim_id}", "claims:delete_claim", D35_DELETE_CLAIM, authenticated=True
    ),
    # R2: the bearer is not required by the route table, because the tutorial node is open to an
    # unauthenticated caller (Q2); the handler authenticates for every other node.
    RouteSpec("POST", "/precheck", "precheck:post_precheck", D35_POST_PRECHECK, feature="F06"),
    RouteSpec(
        "GET", "/precheck/{job_id}", "precheck:get_precheck", D35_GET_PRECHECK, feature="F06"
    ),
)
