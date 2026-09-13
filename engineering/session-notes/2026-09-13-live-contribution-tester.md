# 2026-09-13 — a fresh agent makes a live contribution through the MCP

The second agent-perspective test, and the first on the live network (the 2026-09-12 test ran on
a staged bench, `2026-09-12-erdos-376-tester.md`). A subagent was handed exactly two strings — the
website and the MCP endpoint — and told to make one deliberate contribution, ideally a skeleton
with a couple of `sorry` holes, and to report every bug from a contributor's seat. Everything it
did was real: real precheck runs on the scratch repository, real pull requests on the graph, and
the orchestrating session then approved, merged and checked what the record and the site did with
them. Raw material is in `2026-09-13-live-contribution-tester/`:

| File | What |
|---|---|
| `TESTER-BRIEF.md` | the instruction the tester got |
| `tester-report.md` | the tester's own report: journey, 14 bugs, features wanted, its writes log, its Lean |
| `writes.log` | one line per write, in order |
| `tester-files/` | its MCP client (`mcp.py.txt`), every request body and response, PR #33's check output; the token file is not included |

## What happened, in order

| When (UTC) | Who | What |
|---|---|---|
| 15:53–15:58 | tester | Read the site and the docs page (which carries the whole guide). MCP `initialize` / `tools/list` unauthenticated. `precheck_submission` on the tutorial node through the MCP: **401**. Same bundle over HTTP `POST /precheck`: passed in 2 min. `POST /tokens` → pseudonym `agent-4b1f4d`. |
| 15:58 | tester | `claim_node` on `variant-93e79cb5` (the only claimable node), `submit_informal_annex` → graph **PR #32**; one refusal probe (`claim_node` on a euclid hole, 409, correct). |
| 15:58–16:06 | tester | Three skeleton prechecks: guide's shape failed step 2 (`proof-not-statement`, citation in the header); citation moved into the body at `Proof.lean` failed step 5 (`sorryAx`); the same file at `attempts/<ts>-<pseudonym>-partial.lean` **passed** as `artifact-partial` with holes `h₁`, `h₂`. A fourth run with `artifact_type: partial` on `POST /precheck` was accepted and ignored. |
| 16:08 | tester | `submit_proof(artifact_type=partial)` → graph **PR #33**. Its gate check went **red in 8 s**: the workflow evaluates step 9 (non-author review) *before* the sandbox, the tutorial root has no certificate, and the App is the author. Sandbox steps skipped. |
| 16:09 | session | Merged #32 (append mode, green). Post-merge bot commit `dfd772a`; site deployed by dispatch within a minute; node page shows the annex; live frontier `annex_present: true`. |
| 16:11 | session | `update-branch` on #33 (strict up-to-date), approved it as `thisisanameforsure` (non-author; the App is the author). Two gate runs, both green (steps 1–8 in the sandbox this time); `mergeable_state: clean`. |
| 16:13 | session | Merged #33. Post-merge: `--apply-partial` created `variant-93e79cb5--h1` and `--h2` (origin `skeleton-hole`, status `blocked`, cause `witness-missing`), attestation `000033.json` (`review: pr-approval by thisisanameforsure`, steps 1–8 pass, `trust_base: kernel`), products regenerated, bot commit `6486959`, site dispatched. **No duplicate `attempts/` file** — the F11-Q28 fix held on its first live use. |
| 16:16 | session | Site at `6486959`: target page lists the two holes, the variant is "blocked on a dependency" with deps h1, h2; frontier page updated; both hole pages render. Both generated `Statement.lean` and `Witness.lean` files elaborate under the pinned toolchain (`sorry` warning only). The api's `/frontier.json` lagged by its cache window, then caught up. MCP `get_node` on a new hole answers from the file. |
| 16:10 | tester | `release_claim` → frontier shows no active claim. Total footprint: 5 prechecks, 1 token, 2 claims (1 refused), 1 annex, 1 submission, 1 release. No `gh`, no `git push`, no local repository read. |

The contribution landed: an annex and a two-hole skeleton on the tutorial variant, merged, attested,
rendered. The sequence a human had to supply was exactly the one the protocol names — a non-author
approving review (D-4 step 9) and the merge (F07-Q16) — plus the branch update the strict ruleset
demands after every bot commit.

## Findings verified by the session

Numbers are the tester's. "Verified how" is what this session checked, not what the tester said.

| # | Finding | Verified how | Severity |
|---|---|---|---|
| 1 | **The MCP path cannot bootstrap an identity.** Every write tool, `precheck_submission` included, refuses without a bearer; the HTTP route lets the tutorial node be anonymous (R2) and there is no token tool. | `mcp/writes.py:42` — `forward()` raises `unauthorized()` before any call; `routes.py:65` exempts `/precheck` from the bearer. | **blocks the MCP path** — an MCP-only client is read-only forever |
| 3 | The guide's skeleton example places `-- annex:` between the imports and the theorem; step 2 refuses (`proof-not-statement`, F00-R19 compares the header). | `AGENTS.md:611`; precheck job `01M2DQW9KR9PNRW008DQT1ARY5`. | blocks a contributor following the guide literally |
| 4 | Nothing says a partial is prechecked and submitted at `attempts/<ts>-<pseudonym>-partial.lean`; the guide's permitted-paths table says that path is written "by the gate". | `AGENTS.md:301`; `postmerge.py:230` (`PARTIAL_SUFFIX`); F11 made the submission *be* the attempts file and the guide was not updated. | blocks (cost two prechecks) |
| 7 | **A correct submission shows as a failed check.** The workflow runs step 9 before the sandbox; without a non-author approval the job exits 1 with an annotation only an admin can read easily; the build never runs. | run `34767678011`: step "Step 9 — a non-author approving review" failure, steps 8–11 skipped; job log 403 to the tester. | wrong signal to every non-certified submission |
| 2 | `get_schema` reads `schemas/<name>.json` from the graph, which holds 4 of the 27 families `info.json` lists. | `mcp/reads.py:393`; `ls graph/schemas`. Same as 2026-09-12 finding 5. | confusing |
| 8 | Guide says `attestations/<pull request number>.json`; files are zero-padded (`000033.json`). | `AGENTS.md:453`; `ls attestations`. Same as 2026-09-12 finding 13. | confusing |
| 5 | `POST /precheck` accepts and ignores unknown fields. | job `01M2DR4M70JSXZT8FJTAEA4HRH`: same digest, same verdict. | confusing (a wasted 2.5-min run) |
| 6 | The annex hash covers the front matter the service writes, not the text sent; the guide reads as "hash your text". | `appends.py:173-213`; sha256 of the text ≠ file name. By design (R11), undocumented. | confusing; fatal for a pre-computed citation |
| 11 | Committed products carry `claims.history_count: 0` while the live frontier says 6. | `frontier.json` at `6486959`; **`OPN_API_CLAIMS_URL` is not set on the graph repo** (`gh variable list`), so F05-R10's overlay has never run and CONTEXT.json / the site's claims column are always zero. | wrong record (products), one repo variable |
| 10 | Unauthenticated MCP writes answer the SDK's OAuth body (`invalid_token`), the HTTP route a sentence with the fix. | `mcp/auth.py:28`. | confusing |
| 14 | The docs page says no licence and no DCO text are committed to the graph; the api serves a DCO and issues tokens against it. | graph root has no `LICENSE`; `identity.py:50` holds `DCO_TEXT` as a constant; the site renders the absence. | protocol gap (D-23) |

Not re-verified here: 9 (site vs service stamps), 12 (argument-name drift `ttl`/`ttl_hours`,
`attestation`/`precheck_job_id`, `stmt`/`statement` — the adapter renames on purpose, `writes.py:50`),
13 (precheck job carries no `started` or run link).

## What the session saw that the tester could not

- **A skeleton's first hole was the tutorial's own proved theorem.** `variant-93e79cb5--h1` is
  `∀ p q, p ∧ q → q ∧ p` — byte-for-byte the statement of `tutorial-and-swap`, proved since day one
  in the same target. The post-merge job created a blocked node for it. D-12's offload rule only
  compares a hole with the node's own goal; F08's consolidation only runs on proposals. A hole whose
  closed type equals an existing node's statement should become a dependency edge, not a new node.
- **A merged skeleton makes its parent worse off on the frontier.** The variant went from `ready`
  (claimable, `ready_since 2026-09-11`) to `blocked` (still claimable because R5 keeps every open
  variant, `ready_since: null`), and its two holes are `blocked / witness-missing`, so they are not
  on the frontier and nobody can claim them. The one node a newcomer could work on became a node
  the site calls "blocked on a dependency", and the work it spawned is invisible until a curator
  writes two witnesses by hand — exactly what the euclid on-ramp needed on 2026-09-12. The
  tester, following the guide, had no idea witnesses were its next move: the guide mentions
  `/proposals/witness` once (`AGENTS.md:712`) and **the MCP has no witness tool at all**
  (`routes.py:116` has the route; `mcp/writes.py` does not). Also D-33's dormancy clock restarts
  from nothing for the parent.
- **Hole provenance loses the declared tooling.** The submission's `submission-meta` block named
  the model; both holes' `META.yaml` say `provenance.model: null`.
- **The graph's post-merge products reach the site in about two minutes** (F04-T8's dispatch):
  `dfd772a` and `6486959` were both live before the session finished reading the bot commit.
- **The api's `/frontier.json` is behind the graph for up to its cache window** after a bot
  commit; the tester's bug 9 is this, seen from the other side.

## What a contributor wanted and did not find

In the tester's order: a way to earn a token over the MCP; `artifact_type` on the precheck (or the
partial path stated in the skeleton section); where the citation line may go; what the annex hash
covers; a view of its own pending submissions, claims and prechecks; the step-9 verdict as a
neutral or pending check with a comment, not a red X; an answer to "can I submit to a
non-claimable node?" (it did not spend a Mathlib run to find out); `get_schema` serving every name
`info.json` lists; `started` and a run link on a precheck job. From this side, add: a witness tool
on the MCP and a sentence in the skeleton section saying the holes are yours to witness next.

## Lessons

- Two strings are enough. A fresh agent given only the site and the MCP endpoint found the guide,
  learned the JSON-RPC shape, earned a token and landed a valid partial in 20 minutes with twelve
  writes and no junk — the bench's 23-PR footprint was a property of the bench's zero-cost
  prechecks, not of agents.
- Every red check on a valid submission is a bug report waiting to happen. Step 9 runs first for a
  good reason (no sandbox for a PR nobody will approve), but the workflow should say so where the
  submitter can read it.
- The MCP's write gate is right for D-28 and wrong for R2: the one anonymous write the protocol
  allows is the one that mints every identity.
- Test the state a mode leaves behind (2026-09-12's lesson) and then test *who can act on it*: the
  skeleton merged perfectly and left two nodes no one but a curator can touch.
