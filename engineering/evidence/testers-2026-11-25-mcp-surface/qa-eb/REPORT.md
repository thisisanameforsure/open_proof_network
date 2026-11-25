# REPORT — tester t1125-257, 2026-11-25 11:05–11:20Z

Scope: every write operation, the surface's auth and kind rules, and the legacy surface (`/mcp?surface=v1`).
Detailed calls are in LOG.md. No service crash (`internal`) was seen in about 150 calls.

## Incident caused by the tester (not a service bug)

At 11:16:31Z, while testing refusals for `propose_speculative_node`, I sent
`{target_id: "andrica-conjecture", stmt: "theorem s : (1 : Nat) = true := by\n  sorry\n", witness: "theorem witness : True := trivial"}`
and expected `422 statement-fails`. Under Mathlib the statement does elaborate (check_lean shows the goal `↑1 = true`), so the
service opened PR #2044 (proposal `01M896QJT0M31H6TW2S82MK0TC`, node `spec-30cc2228`), which was correct behaviour.
I withdrew it 11 s later with `withdraw_submission`: 200 `withdrawn: true`, branch deleted. The GitHub API confirms it is
closed and not merged (closed 11:16:41Z). After that I used only refusals that cannot pass: unknown ids and schema failures.

## Operations in scope

| Operation | Tested | Result | Notes |
|---|---|---|---|
| claim_node | yes: 2 correct, 6 bad | ok | Claim then release on andrica-conjecture. Agrees with list_my_claims, the legacy tool and /claims.json. L5 |
| release_claim | yes: 2 correct, 3 bad | ok | Releasing twice returns 200 with the same receipt |
| precheck_submission | yes: 2 jobs, 5 bad | ok | Tutorial job passed. get_precheck agrees with GET /precheck/<id> |
| check_lean | yes: 3 correct, 5 bad | ok, low | Correct and broken proofs behave as documented. L4 |
| get_token | refusals only (6) | ok, low | Not called correctly, so that no stray identity was minted. L8 |
| renew_token | refusal only (1) | ok | Not called correctly: it would rotate the connection's token |
| submit_proof | refusals only (6) | **bug** | B2 |
| submit_postmortem | refusals (4) | ok, low | L3 |
| submit_informal_annex | refusals (3) | ok | |
| submit_gloss | dry runs (20) | **bug** | B1, L10 |
| withdraw_gloss | refusals (4) | ok | Path traversal refused (`record-invalid`) |
| submit_approach_record | refusals (3) | ok | |
| file_defect_claim | refusals (6) | ok, low | L4 |
| file_revision_request | refusals (4) | ok | |
| propose_speculative_node | refusals (4), plus 1 accidental open (see incident) | ok | |
| propose_variant | refusals (3) | low | L6 |
| propose_witness | refusals (3) | ok | |
| withdraw_submission | 1 correct (my own #2044), 5 bad | ok | Merged → 409; another identity's PR → 403 not-holder |
| propose_literature | refusals (3) | ok, low | L3 |
| confirm_literature | refusals (3) | ok, low | L7 |
| set_display_name | refusals (4) | ok | |
| register_target | refusals (2) | ok, low | L7 |
| submit_candidate | refusals (4) | low | L1 |
| *Surface: kind rules* | read(write op), write(read op) | ok | `operation-kind-mismatch`, with a clear message |
| *Surface: unknown op / tool* | 4 calls | ok, low | L9 |
| *Surface: `arguments` missing / not object* | str, array, null, missing, extra keys | ok, low | L3 |
| *Surface: auth* | write and read with no token (raw MCP) | low | L2 |
| *Surface: search* | no args, named ops, query | low | B3, L5, L11 |
| *Legacy surface* | 10 tools compared | ok | Same answers as read/write for claim_node, release_claim, list_my_claims, check_lean, get_precheck, submit_gloss (dry), withdraw_submission, propose_literature, set_display_name, submit_candidate |

## Bugs

### B1 — medium — submit_gloss dry run accepts `drafted_with` values the description says are `tooling-invalid`
- Call: `write submit_gloss {"subject":{"kind":"statement","node_id":"tutorial-and-swap"},"text":"$x$ words","licence":"CC-BY-4.0","drafted_with":"some model","dry_run":true}`.
  It answered `{"status":200,"body":{"ok":true,"dry_run":true,...,"warnings":[]}}`.
- The same happened with `"drafted_with":"   "` (whitespace only), on both the new surface and legacy `submit_gloss`.
- Expected: the description says `drafted_with` must be written `<model name> (<model id>)`, 1–200 characters after
  whitespace is normalised, and "anything else is tooling-invalid". A value of 222 characters is refused `tooling-invalid`,
  so the check exists but enforces only the length.
- Impact: dry runs exist to catch what a real submission would refuse. Either the dry run misses the check, or the
  documented rule is not enforced at all. I could not test the real submission, because it would open a PR.
- Reproduce: the call above.

### B2 — medium — submit_proof's documented error codes `automation-missing` and `automation-invalid` never reach the caller
- Call: `write submit_proof {"artifact_type":"proof","node_id":"tutorial-and-swap"}`.
  It answered `{"error":"arguments-invalid","message":"'automation' is a required property; ...","source":"adapter"}`, with no HTTP status.
- Call: `... "automation":{"method":"robot","models":["m"],"framework":"f"}`.
  It answered `arguments-invalid` "'robot' is not one of [...]".
- Expected: the description, and the schema's own `automation` description, say "missing: 400 automation-missing;
  malformed: 400 automation-invalid". The adapter's schema check runs first, so those codes are never returned.
  precheck_submission's documented `400 automation-invalid` behaves the same way. Legacy v1 answers identically.
- Reproduce: either call above.

### B3 — medium — list_frontier with no arguments is too large to use over MCP
- Call: `read list_frontier {}`. It returned 355,075 characters (602 entries, frontier/v8). The client could not take it
  inline and wrote it to a file.
- Expected: a result an agent can read, or paging/filters that the default call uses. The instructions' first-contribution
  path starts with exactly this call. This is outside my write scope, but it is a surface usability problem.

### Low (polish and documentation)
- **L1** submit_candidate: the description says `read_others` is "required (the blind rule)", but the input schema's `required` is
  `["target_id","lean"]`. The endpoint does refuse it (`400 candidate-not-blind`), so only the schema is wrong.
- **L2** The no-token error envelope differs by tool. On write it is `{"status":401,"body":{"error":"unauthenticated",...}}`;
  on read (list_my_claims) it is `{"error":"unauthenticated",...,"source":"adapter","status":401}`. Reproduced with raw MCP POSTs without a token.
- **L3** Adapter `arguments-invalid` messages leak Python reprs (`"None is not of type 'object'"` for `arguments: null`)
  and report only the first error. For example, `propose_literature` with status "hard", references [] and summary ""
  names only `summary`, and postmortem `{}` names only `route`.
- **L4** Lean diagnostics count lines from the checker's injected `import Mathlib` header. A broken 3-line proof reports `-:5:9`,
  and a 1-line defect-claim exhibit reports `-:3:23` (check_lean, file_defect_claim, file_revision_request).
- **L5** claim_node: the 168 h cap is not in the schema (`ttl` has no `maximum`), and the refusal says `ttl_hours` while the argument is `ttl`.
  In `search` with no arguments, the plain path for set_display_name, register_target and submit_candidate is prose
  ("names and registrations: …", "reviews: submit_candidate, and …"), not a path.
- **L6** propose_variant returns `400 relation-proof-required` (relation resolves, no relation_proof). The description does not name that code; it names only `relation-decl`.
- **L7** register_target and confirm_literature, for a non-GitHub identity, answer `github-login-required` with the message
  "only an identity proved with GitHub can steward a problem or approve words". The message does not fit either act.
  confirm_literature also checks auth before the documented "never both record and disputes" rule.
- **L8** get_token with a missing `job_id` or `nonce` gives the generic `proof-invalid` "unknown, unfinished, used or unusable tutorial proof" instead of naming the missing field.
- **L9** `operation-unknown` gives no suggestion. `get_nodes` gets no "did you mean get_node". The legacy `tool-unknown` message omits the tool list that the new surface gives.
- **L10** A statement gloss whose text has no LaTeX at all passes the dry run with no warning, although the description says a gloss opens with the statement in LaTeX.
- **L11** `search` with query "dry run" ranks list_submissions, precheck_submission, check_lean, propose_speculative_node and propose_variant
  after submit_gloss, and none of them takes `dry_run`. Only submit_gloss has `dry_run` among the writes.
- **L12** The check_lean lint code `header-diverges` is not in /errors.json. Every other code I saw (about 50) is listed.
- **L13** Several bearer HTTP routes have no MCP operation: /stewards, /approvals, /motions, /votes, /writeups, /shelvings,
  /dco/accept, /reviews, /reviews/{id}/answers and /reviews/{id}/signatures. Still, `review-unknown` tells an MCP caller
  "one opens with POST /reviews", and every write is refused `dco-reaccept-required` after a DCO change, with no MCP way to re-accept.

## Unconfirmed / not tested
- Whether a real (non-dry) submit_gloss refuses `drafted_with: "some model"`. Not tested, because it would open a PR.
- Correct calls of get_token and renew_token. Not made, because they would mint an identity or rotate the session token.
- Refusals that need another identity's open PR or gloss (`not-holder` on an open PR, `withdrawal-unauthorized`).
  There were no open PRs, and I did not try anything that could alter others' work.
