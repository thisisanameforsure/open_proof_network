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
    #: F23-R3: the route also accepts a web session from the site (the cookie, the site's exact
    #: Origin and ``X-OPN-Web: 1``) and answers the site's credentialed CORS. Every other route
    #: ignores the cookie.
    web: bool = False

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
# F07's rows. D-35 gives ``submit_proof`` the endpoint by name; the three append tools share one
# row, whose plain path is the pull request itself — the endpoint only opens it.
D35_POST_SUBMISSIONS = "POST /submissions"
D35_APPEND_PR = "a PR appending the schema-checked file under the node or target"
# F07-T43 (ruling D5, 2026-09-24): the holder withdraws a pull request the service opened.
D35_DELETE_SUBMISSION = "DELETE /submissions/<id>"
D35_OWNED_BY_F07: frozenset[str] = frozenset(
    {D35_POST_SUBMISSIONS, D35_APPEND_PR, D35_DELETE_SUBMISSION}
)
# F08's row: the two proposal tools share one, whose plain path is the pull request that creates
# the node directory; witness completion is the same row, on a directory that already exists
# (F08-R5). Revision requests and defect claims share the other (T4).
D35_PROPOSAL_PR = "a PR creating the node directory with origin set"
D35_CLAIM_PR = "a PR appending the schema-checked record to the target"
D35_OWNED_BY_F08: frozenset[str] = frozenset({D35_PROPOSAL_PR, D35_CLAIM_PR})
# F13's row (D-35 v3.14): the fast check answers in the same response, so there is no polling read.
D35_POST_CHECK = "POST /check"
D35_OWNED_BY_F13: frozenset[str] = frozenset({D35_POST_CHECK})
# F20's row (D-35 v3.30): submit_gloss and withdraw_gloss, each by the endpoint D-35 names.
D35_POST_GLOSSES = "POST /glosses"
D35_POST_GLOSS_WITHDRAWALS = "POST /glosses/withdrawals"
D35_OWNED_BY_F20: frozenset[str] = frozenset({D35_POST_GLOSSES, D35_POST_GLOSS_WITHDRAWALS})

ROUTES: tuple[RouteSpec, ...] = (
    # F05-T13, Q13: the index of this table, served at the root. Open, no D-35 row.
    RouteSpec("GET", "/", "index:get_index", None),
    RouteSpec("GET", "/health", "app:health", None),
    RouteSpec("GET", "/info.json", "info:get_info", None),
    RouteSpec("GET", "/dco.json", "identity:get_dco", None),
    RouteSpec("GET", "/frontier.json", "frontier:get_frontier", None),
    RouteSpec("GET", "/claims.json", "frontier:get_claims", None),
    RouteSpec("GET", "/auth/github/start", "identity:github_start", D35_POST_TOKENS),
    RouteSpec("GET", "/auth/github/callback", "identity:github_callback", D35_POST_TOKENS),
    RouteSpec("POST", "/tokens", "identity:post_tokens", D35_POST_TOKENS),
    # F23-R2 (D-35 v3.33): a first web sign-in's DCO tick. Sign-in under the D-19 identity rules,
    # so D-35's token row, as the two auth routes above are; it makes the identity and a web
    # session, never a token.
    RouteSpec(
        "POST", "/auth/web/accept", "identity:post_web_accept", D35_POST_TOKENS, feature="F23"
    ),
    # F05-T27, T29 (D-19 v3.29): optional rotation of a live token. Token issuance under the D-19
    # identity rules, so D-35's token row (Q27, Q29).
    RouteSpec("POST", "/tokens/renew", "identity:post_renew", D35_POST_TOKENS, authenticated=True),
    RouteSpec("POST", "/claims", "claims:post_claims", D35_POST_CLAIMS, authenticated=True),
    RouteSpec(
        "DELETE", "/claims/{claim_id}", "claims:delete_claim", D35_DELETE_CLAIM, authenticated=True
    ),
    # F05-T14 (ruling D3(b), 2026-09-24): a caller's own claims with their ids, which the public
    # registry does not publish. A read with no D-35 row, like /checks/{check_id}; the bearer is
    # required because the list is the identity's own.
    RouteSpec("GET", "/claims/mine", "claims:get_my_claims", None, authenticated=True),
    # R2: the bearer is not required by the route table, because the tutorial node is open to an
    # unauthenticated caller (Q2); the handler authenticates for every other node.
    RouteSpec("POST", "/precheck", "precheck:post_precheck", D35_POST_PRECHECK, feature="F06"),
    RouteSpec(
        "GET", "/precheck/{job_id}", "precheck:get_precheck", D35_GET_PRECHECK, feature="F06"
    ),
    RouteSpec(
        "POST",
        "/submissions",
        "submissions:post_submissions",
        D35_POST_SUBMISSIONS,
        authenticated=True,
        feature="F07",
    ),
    # F07-T16: reads, like /frontier.json — what the service opened and how it is doing. The plain
    # path is the pull request on the host and, once merged, attestations/<n>.json.
    RouteSpec("GET", "/submissions.json", "pending:get_submissions", None, feature="F07"),
    # F07-T70 (the owner, 2026-10-04): the caller's own submissions, open and recently finished,
    # as /claims/mine is for claims. A read with no D-35 row; matched before the route below,
    # which would refuse "mine" as an id.
    RouteSpec(
        "GET",
        "/submissions/mine",
        "pending:get_my_submissions",
        None,
        authenticated=True,
        feature="F07",
    ),
    RouteSpec("GET", "/submissions/{submission_id}", "pending:get_submission", None, feature="F07"),
    # F07-T43 (ruling D5): the identity that opened a pull request closes it, unmerged.
    RouteSpec(
        "DELETE",
        "/submissions/{submission_id}",
        "withdraw:delete_submission",
        D35_DELETE_SUBMISSION,
        authenticated=True,
        feature="F07",
    ),
    RouteSpec(
        "POST",
        "/postmortems",
        "appends:post_postmortems",
        D35_APPEND_PR,
        authenticated=True,
        feature="F07",
    ),
    RouteSpec(
        "POST", "/annexes", "appends:post_annexes", D35_APPEND_PR, authenticated=True, feature="F07"
    ),
    RouteSpec(
        "POST",
        "/approach-records",
        "appends:post_approach_records",
        D35_APPEND_PR,
        authenticated=True,
        feature="F07",
    ),
    RouteSpec(
        "POST",
        "/proposals/speculative",
        "proposals:post_speculative",
        D35_PROPOSAL_PR,
        authenticated=True,
        feature="F08",
    ),
    RouteSpec(
        "POST",
        "/proposals/variant",
        "proposals:post_variant",
        D35_PROPOSAL_PR,
        authenticated=True,
        feature="F08",
    ),
    RouteSpec(
        "POST",
        "/proposals/witness",
        "proposals:post_witness",
        D35_PROPOSAL_PR,
        authenticated=True,
        feature="F08",
    ),
    RouteSpec(
        "POST",
        "/revision-requests",
        "requests:post_revision_requests",
        D35_CLAIM_PR,
        authenticated=True,
        feature="F08",
    ),
    RouteSpec(
        "POST",
        "/defect-claims",
        "requests:post_defect_claims",
        D35_CLAIM_PR,
        authenticated=True,
        feature="F08",
    ),
    # F20-R10 (D-35 v3.30): a gloss or explainer, and a withdrawal of one version, each refused
    # by the gate's own checks before any pull request opens.
    RouteSpec(
        "POST",
        "/glosses",
        "glosses:post_glosses",
        D35_POST_GLOSSES,
        authenticated=True,
        feature="F20",
        web=True,  # F23-R3
    ),
    RouteSpec(
        "POST",
        "/glosses/withdrawals",
        "glosses:post_withdrawals",
        D35_POST_GLOSS_WITHDRAWALS,
        authenticated=True,
        feature="F20",
        web=True,  # F23-R3
    ),
    # F13-R8, Q2: open like the tutorial precheck; a presented token is authenticated and charged
    # per identity, and an anonymous caller is charged per address, by the handler.
    RouteSpec("POST", "/check", "checks:post_check", D35_POST_CHECK, feature="F13"),
    # F13-R10: a caller's own call record. A read with no D-35 row, like /submissions/{id}; the
    # bearer is required because a record is readable by its identity alone.
    RouteSpec(
        "GET", "/checks/{check_id}", "checks:get_check", None, authenticated=True, feature="F13"
    ),
    # F13-R11, Q12: which hosted environment serves each pin and each target. Network
    # configuration, open like /dco.json; info.json stays the graph's product (info/v1, info/v2).
    RouteSpec("GET", "/hosted-checkers.json", "checks:get_hosted_checkers", None, feature="F13"),
    # --- F05-T23, F05-T24 (audit 2026-10-04, owner-approved): documentation an agent reads ---
    # Open reads with no D-35 row, like /hosted-checkers.json: the error-code catalog (F13-T29),
    # and the two plain-text files an agent or a crawler asks a host for first.
    RouteSpec("GET", "/errors.json", "errorcodes:get_errors", None),
    RouteSpec("GET", "/llms.txt", "wayfinding:get_llms_txt", None),
    RouteSpec("GET", "/robots.txt", "wayfinding:get_robots_txt", None),
)

#: F05-T13 (Q13): one sentence per route, keyed by its label and served by ``GET /``. A test
#: holds this to ``ROUTES`` in both directions, so a route cannot ship without saying what it
#: is for. The guide is where each is documented; these are for finding the way there.
PURPOSES: dict[str, str] = {
    "GET /": "This index: every route, whether it needs a bearer, and what it is for.",
    "GET /health": "Whether the service is configured and which store it runs on.",
    "GET /info.json": "The graph's info.json with the rate limits in force filled in.",
    "GET /dco.json": "The sign-off text a token is issued against, and its version.",
    "GET /frontier.json": "The open statements, with the live claim counts laid over them.",
    "GET /claims.json": "The live claims registry alone, as the post-merge job commits it.",
    "GET /auth/github/start": "Begin the GitHub proof of identity for a token (browser).",
    "GET /auth/github/callback": "Finish the GitHub proof of identity and issue the token.",
    "POST /tokens": "Issue a token: from a passing tutorial precheck (no account) or GitHub.",
    "POST /auth/web/accept": "Finish a first sign-in on the site: accept the DCO, then return "
    "to the page with a web session (browser).",
    "POST /tokens/renew": (
        "Rotate a token (optional; one in use never lapses): a new token, the old one retired."
    ),
    "POST /claims": "Claim an open statement for a time, so others can see it is being worked.",
    "DELETE /claims/{claim_id}": "Release a claim you hold.",
    "GET /claims/mine": "Your own active claims with their ids, and who else holds each node.",
    "POST /precheck": "Run the gate on a bundle in the hosted sandbox before submitting it.",
    "GET /precheck/{job_id}": "A precheck job's state, and its signed attestation when done.",
    "POST /submissions": "Open the pull request for a prechecked proof or partial proof.",
    "GET /submissions.json": "Every pull request the service opened that is still open, in "
    "merge-queue order, each with its position.",
    "GET /submissions/mine": "Your own submissions: the open ones with their place in the "
    "queue, and the most recently merged or closed.",
    "GET /submissions/{submission_id}": "One submission: its pull request, where it stands, "
    "and its place in the merge queue with what is ahead.",
    "DELETE /submissions/{submission_id}": "Withdraw a pull request you opened, closed unmerged.",
    "POST /postmortems": "Record a failed attempt on a statement, by pull request.",
    "POST /annexes": "Attach informal mathematics to a statement, by pull request.",
    "POST /approach-records": "Record an approach to a whole problem, by pull request.",
    "POST /proposals/speculative": "Propose a new statement under a problem, by pull request.",
    "POST /proposals/variant": "Propose a variant of a problem's statement, by pull request.",
    "POST /proposals/witness": "Supply the witness a statement is waiting for, by pull request.",
    "POST /revision-requests": "Ask a curator to revise a statement, with the reason.",
    "POST /defect-claims": "Claim a statement is defective, with a Lean exhibit the gate checks.",
    "POST /glosses": "Say in words what a Lean file or a merged proof says, or revise those "
    "words, by pull request; refused first by the gate's own checks.",
    "POST /glosses/withdrawals": "Withdraw one version of a gloss or explainer, by pull "
    "request; the file stays and is read as absent.",
    "POST /check": "Check Lean text within 20 s on a hosted checker, or preview a witness's "
    "expected type for a node or a statement's text (mode witness); never authoritative.",
    "GET /checks/{check_id}": "The record of one of your own fast-check calls.",
    "GET /hosted-checkers.json": "Which hosted checker environment serves each pin and target.",
    # --- F05-T23, F05-T24 ---
    "GET /errors.json": "Every error code the gate and the service emit, what it means and what "
    "to do about it; ?prefix= narrows it.",
    "GET /llms.txt": "Where an agent starts, as full URLs: the guide, this index, info.json, the "
    "error codes and the MCP endpoint.",
    "GET /robots.txt": "Crawlers are welcome everywhere; it names no path.",
}
