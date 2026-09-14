# 2026-09-13 — a fresh agent finishes a proof of Euclid's theorem from the website alone

The third agent-perspective test, the second on the live network. A subagent was handed one string,
`https://openproofnetwork.org/`, and told: finalize a proof of `infinitude-of-primes` that passes the
gate, then prove it another way, and report every issue with the stack, the documentation and the
MCP along the way. The orchestrating session reviewed and merged what landed (it is the non-author
reviewer D-4 step 9 needs, since the App authors every service-opened pull request), and checked the
record, the service and the site after each merge. The session was stopped by the owner after the
fourth merge, because another agent had begun changing how a theorem keeps several proofs (D-25
v3.13); the tester never submitted a root proof. Raw material is in `2026-09-13-euclid-tester/`:

| File | What |
|---|---|
| `TESTER-BRIEF.md` | the instruction the tester got |
| `issues-notes.md` | the tester's 40 running notes (it was stopped before writing its report) |
| `writes.log` | one line per write, in order, with its own polling notes |
| `orchestrator-log.md` | this session's timeline, the record checks and the code reading behind each finding |
| `root-A-assembly-Proof.lean`, `root-B-direct-Proof.lean` | the two root proofs the tester wrote and prechecked but never submitted |

## What happened, in order

| When (UTC) | Who | What |
|---|---|---|
| 19:11–19:21 | tester | Read the site, the docs page, `info.json`, the MCP `tools/list`. Earned a token (pseudonym `euclid-tester-7c2`). Claim on the blocked root: 404 `node-not-in-frontier`; claim on a hole: 409 `node-not-claimable` with no reason (the target is `listed`). Prechecked all four holes and both root proofs through the MCP; the holes passed, both root proofs failed step 4 `dep-unproved`. |
| 19:30–19:33 | tester | `submit_proof` on h1–h4 → graph PRs #34–#37. Every gate check red within ~13 s: step 9 evaluated before the sandbox. |
| 19:31 | session | Approved #34; the review-triggered run built and passed steps 1, 2, 4–8. `mergeable_state` stayed `blocked`: the failed `pull_request` run was still in the rollup. Re-ran it by hand; `clean`. |
| 19:53 → 20:02 | session | Merged #34; bot commit `f345529`. h1 `proved`, attestation `000034.json`. Site at `f345529` within 2.5 min; api frontier 4.5 min later. |
| 20:02 → 20:57 | session | #35, #36, #37 each: `update-branch`, approve within seconds (so the synchronize run passes step 9 too), both runs green, merge, wait for the bot commit. Bot commits `ef04537`, `b3779de`; the site within about a minute each time, the api within 72 s. |
| 20:23–20:35 | tester | GitHub's anonymous API budget exhausted while watching its own PRs; blind for 12 minutes. |
| ~21:00 | owner | Stopped the run. #37's post-merge job still running; no PR open. |
| next morning | record | #37's bot commit `0801922` landed; all four holes `proved`, the root `ready` (not claimable: the target is listed). No root proof submitted. |

## Findings verified by the session

| Finding | Verified how | Severity |
|---|---|---|
| **Every merged attestation drops what the submitter declared.** `000034`–`000036` say `submitter: null`, `model_and_tooling: undeclared`, `tooling` nulls, `precheck_attestation` nulls, beside PR bodies carrying `euclid-tester-7c2`, `claude-opus-5` and a service-signed precheck. | `cli.run_gate` reads `--pr-body-file` only for the bounce rule and builds with no `submission=`; `cli.run_postmerge` runs the pipeline with no policy and builds with no `submission=`; gate.yml fetches the body only in partial mode. | wrong record |
| **No merge has ever credited anyone.** No `ledger/` on the graph; the Contributors page says "the first merged proof … will start the ledger". | `ledger.proof_entry` and `postmortem_entry` have no production caller; `run_ledger` and its workflow step run only for proposals. | wrong record |
| **A valid PR is red, and approval alone does not unblock it.** | run `34777912609` failed at the step-9 step, build skipped; after approval the rollup held FAILURE and SUCCESS under one required name, `mergeable_state: blocked` until the failed run was re-run. | blocks every non-certified submission |
| **A pending submission is invisible through the network.** | `get_submission` reads merged attestations only (zero-padded); no `GET /submissions/<id>`; the store records nothing at submit time; the host seam cannot read a PR's state. | blocks a contributor (visibility) |
| **Open work is invisible to the next contributor.** | with four PRs open, `/frontier.json`, `list_frontier` and `get_node` showed four untouched holes. | wasted work |
| **A blocked node's refusal says "not in the frontier"; a listed target's says "not claimable" with no reason.** | `claims.find_entry` reads only the frontier; `targets/index.json` carries `not_claimable` reasons the route never reads. | confusing |
| **Precheck spends a hosted run on a node that cannot pass.** | `post_precheck` checks existence only; the blocked root ran to step 4 twice. | friction |
| **`/frontier.json` lagged `/info.json` and `get_node` by up to 4.5 minutes.** | one cache entry per path, one context per Lambda instance, no cross-path invalidation. | confusing |
| **The site says "blocked on a dependency" for a witness-missing hole with no dependencies**, and the DAG labels all four holes `infinitude-of-primes-…`. | `STATUS_WORDS` ignores `cause`; `dag.py` head-truncates at 21 characters. | confusing / cosmetic |
| **The docs page renders the guide's `output` fences as bare fragments and its tables as run-on text.** | AGENTS.md goes through `prose.render`, not `render_document`. | confusing |
| **The guide never says a skeleton's holes must all merge before the parent can be finalized, that attestation ids are zero-padded, or how to watch a submission.** | read. | blocks (cost two prechecks) |
| **The graph README cites decisions v3.10.** | `git show origin/main:README.md`. | cosmetic |
| **`OPN_API_CLAIMS_URL` is still unset**, so committed products say zero claims. | `gh variable list`. | wrong record (re-found) |

Re-found from earlier passes: the MCP cannot mint a token; MCP argument names differ from the routes'
(`ttl`, `stmt`, `attestation`); `get_schema` serves 4 of the families `info.json` lists; step 9 runs
before the build.

## For the agent changing how a theorem keeps several proofs

- A merged skeleton locks its parent against **every** proof until all holes merge: the tester's
  direct proof (root B, which uses no hole) failed step 4 `dep-unproved` exactly as the assembly did
  (`steps/stage.py`). Both files are in the directory beside this note.
- The **pinned** gate (network `0e3bab6`) lets a pull request modify a merged `Proof.lean` (paths
  rule `A` or `M`) and classifies any `.lean` under `attempts/` as a partial, so a second proof merged
  before the re-pin would overwrite the first.
- The tester read the tutorial variant as claimable while `blocked` on its holes as a contradiction
  (`products.in_frontier`'s variant branch); the owner wants that registered, not changed.

## Timing, for the next plan

A hole cost about 20 minutes of machine time (a 10-minute review-triggered build, an 8–11 minute
post-merge job) plus a human approval, a merge and a branch update; under the strict up-to-date rule
four holes were four sequential rounds, about 65 minutes from the first merge to the last.
