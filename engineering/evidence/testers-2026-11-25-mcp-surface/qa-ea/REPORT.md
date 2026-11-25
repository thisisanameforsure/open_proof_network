# QA report — `search` and every read operation

Tester: t1125-883. Window: 11:05Z–12:00Z, 2026-11-25. Server: https://api.openproofnetwork.org/mcp, three-tool surface.
Targets used: tutorial, erdos-883, erdos-257, erdos-1094, and `abc` (bulk-loaded: 1 ready node, 0 attempts, 0 claims).
No pull request was opened. The only write was one `check_lean` on `tutorial`, which I ran to get a real `log_id` for `get_check`. Full timeline is in LOG.md.

## Coverage

| Operation | Correct call | Bad inputs | Plain path compared | Result |
|---|---|---|---|---|
| search | 26 queries | 8 (limit 0, limit "3", unknown op, extra prop, empty ops, …) | — | **bug** (ranking B2, plain field B1) |
| server_info | ✓ | 1 | GET /info.json, identical | ok |
| list_targets | ✓ | 1 | raw targets/index.json, identical | **bug** (size B3) |
| get_target | ✓ ×5 | 5 | raw graph.json (883, abc), identical | ok |
| list_frontier | ✓ ×4 | 3 | GET /frontier.json, identical | ok (size B3) |
| get_node | ✓ ×3 | 2 | — | ok |
| get_defs | ✓ ×2 | 1 | — | ok |
| get_gate_spec | ✓ | 2 | — | ok |
| get_submission | ✓ (ULID and PR no.) | 3 | GET /submissions/2041 (same keys) | **bug** (plain path B1, codes B5) |
| list_submissions | ✓ | 2 | GET /submissions.json | **bug** (B4) |
| get_schema | ✓ ×2 | 2 | — | ok |
| get_precheck | ✓ | 2 | — | ok |
| get_dco | ✓ | 1 | GET /dco.json, identical | ok |
| list_routes | ✓ | 1 | GET /, identical | ok |
| get_hosted_checkers | ✓ | 1 | GET /hosted-checkers.json, identical | ok |
| list_my_claims | ✓ | 1 | (bearer) | ok |
| get_my_submissions | ✓ | — (no args) | (bearer) | ok |
| get_check | ✓ | 2 | (bearer) | ok |
| list_error_codes | ✓ ×3 | 1 | GET /errors.json, identical | ok |
| list_words_needed | ✓ | 2 | — | ok |
| list_registrations | ✓ ×2 | 1 | — | ok (plain field B1) |
| get_review | ✓ | 3 | GET /reviews/erdos-1094, identical apart from added untrusted_note | ok (plain B1, codes B5) |
| list_review_questions | ✓ ×3 | 1 | GET /reviews/erdos-883/questions, identical | **unconfirmed crash** (U1), plain B1, size B3 |
| list_open_pairs | ✓ ×2 | 2 | cross-checked index open_pairs | ok (plain B1) |
| list_sufficient_sets | ✓ ×3 | 2 | — | **bug** (size B3) |

Kind refusals work: `read claim_node` and `write get_node` both answer `operation-kind-mismatch` with a clear message. An unknown name answers `operation-unknown`.

## Bugs

### B1 — medium — `search`'s `plain` field is prose, or the wrong path, for six operations
- **Call:** `search {}`
- **Answer (excerpts):**
  - `get_review.plain` = "a target's formalization review as the record holds it: the words and cases, …"
  - The same kind of sentence for `list_registrations`, `list_review_questions` and `list_open_pairs`.
  - `set_display_name` and `register_target` = "names and registrations: set_display_name, register_target (v3.37)". `submit_candidate` is similar.
  - `get_submission.plain` = "attestations/<id>.json". The attestation file is actually named by the zero-padded PR number (`attestation_path: "attestations/002041.json"` for ULID 01M87XRTF87CPVAYVRE69KP9ET). The live route `GET /submissions/{id}` is not named.
- **Expected:** a path, per the tool description ("lists every operation with its kind … and plain git/HTTP path"). The full descriptions do carry real paths (`targets/index.json`, `targets/<id>/review/questions/`, `targets/<id>/review/pairs/`). However, `get_review` and `list_review_questions` have live routes that neither the field nor the description names: `GET /reviews/{target_id}` and `GET /reviews/{target_id}/questions`.
- **Repro:** run `search` with no arguments and read the `plain` values.

### B2 — medium — search ranking misses for common requests (5 of 26 realistic queries)
`limit: 5` was used throughout. In order of severity:
| Query | Returned | Right op & rank |
|---|---|---|
| "check the status of my pull request" | get_check, check_lean, file_revision_request, list_submissions, list_words_needed | get_submission / get_my_submissions **absent** |
| "what Lean files need a gloss" | submit_gloss, check_lean, file_defect_claim, file_revision_request, list_words_needed | list_words_needed **#5** |
| "what is the pinned Mathlib version" | check_lean, list_targets, get_gate_spec, … | get_gate_spec #3 |
| "find an open problem to work on" | list_open_pairs, list_frontier, … | list_frontier #2. This is the guide's first step, but the review-only op outranks it |
| "who else is working on this node" | claim_node, get_node, propose_speculative_node, list_frontier, list_my_claims | get_node #2 acceptable; claim_node #1 is a write |

These ranked the right op first: "what does this error code mean", "follow my submission", "read a node's statement", "list the targets", "show my claims", "poll a precheck job", "which Mathlib does the hosted checker support", "shared definitions for a target", "what would settle the root of the graph", "questions waiting on a formalization review", "is this problem registered on Palomar", "get the DCO text", "json schema for a postmortem", "merge queue position", "get node", "frontier".

Pattern: "status"/"check" words pull in `get_check`/`check_lean`. Write ops are often ranked above the read the user needs.

### B3 — medium — some read results are too large to use and cannot be narrowed
| Call | Size |
|---|---|
| `read list_targets {}` | 1,316,781 chars. Takes no arguments: no target filter, no fields, no paging |
| `read list_sufficient_sets {"target_id":"erdos-1094","cut":"any"}` | 1,057,245 chars, `truncated: true`, 569 sets |
| `read list_frontier {}` | 355,075 chars |
| `read list_review_questions {}` | 69,758 chars. Exceeded this client's tool-result limit; the MCP client spilled it to a file |

Expected: a `target_id` filter on list_targets (get_target exists but carries no index fields such as fidelity or node_counts), or paging/limits. The first two are unusable in one agent context.

### B4 — medium — `list_submissions` silently accepts an unknown kind or target
- **Calls:** `read list_submissions {"kind":"nonsense-kind"}` and `{"target_id":"no-such-target"}`
- **Answer:** a normal 200 result (`snapshot_at`, `queue`, …, no error).
- **Expected:** `filter-unknown` (as `list_words_needed {"kind":"nonsense"}` answers) and `not-found` (as list_registrations / list_open_pairs / list_review_questions / list_words_needed answer for an unknown target). A typo in a filter is indistinguishable from "nothing open".
- **Caveat:** 0 submissions were open during the test. So I could not tell whether a valid filter is applied, only that invalid ones are not refused.

### B5 — low — the same input class gets different error codes depending on which layer refuses it
- `get_submission {"submission_id":"not-a-ulid!"}` → `arguments-invalid` (adapter)
- `get_submission {"submission_id":"-5"}` → `submission-id-invalid`, status 400 (service)
- Unknown target: `get_review` → `target-unknown` (service, 404). `get_target`, `get_defs` and `list_sufficient_sets` → `not-found` (graph). `list_*` → `not-found` "no target … in targets/index.json".

Expected: one code per condition, so a client can branch on `error`.

### B6 — low — intermittent long latencies, including on refusals that need no I/O
Measured over MCP-over-HTTP; each call included its own `initialize`. Most calls took 1.1–2 s, but:
- `get_target {}` took 76.2 s, although it is refused by the adapter's schema check.
- `search "frontier"` took 80.1 s.
- `search "get the DCO text"` took 55.6 s.
- Many reads took 36–50 s. For comparison, curl of the plain routes took about 1 s.
- One call hung past 290 s (logged 11:32Z), then took 6.5 s on rerun.

The cause (initialize vs. tools/call) was not isolated, so treat the root cause as unconfirmed. The latencies themselves were reproduced repeatedly across batches (see LOG).

## Unconfirmed

### U1 — (would be high) `list_review_questions {}` answered HTTP 500 with an empty body
- **Call (11:44Z):** MCP `tools/call` `read` `{"operation":"list_review_questions","arguments":{}}` over HTTP. Result: HTTP 500, body length 0, after 30.1 s.
- **Retries:** two over HTTP (11:48Z, 11:49Z) and one over the connection all returned 205 questions normally.
- Not reproduced. Possibly a timeout while the op reads every target's review folder (445 targets).

### U2 — staleness note
`/frontier.json` and every `read_at` say `257feba…`. The raw repo `frontier.json` and `targets/index.json` say `rendered_from a8f1c34…`. GitHub's API rate limit stopped me from checking commit order, so this is probably expected (a file renders from its parent commit). It is not reported as a bug.

## Checked and fine
- Every comparable read equals its plain path exactly: server_info, get_dco, list_routes, get_hosted_checkers, list_error_codes, list_frontier, list_targets, get_target.graph, get_review, list_review_questions. The only extra is an `untrusted_note`.
- Cross-op consistency for erdos-1094: the index has `questions_waiting 8` and `open_pairs 0`. list_review_questions gives 8, list_open_pairs gives 0, and get_review's derived state matches.
- Error messages from schema validation are specific: they name the field, the pattern, the allowed enum values and the valid frontier fields.
