# Tester report — a first contribution to the Open Proof Network, live, 2026-09-13

Identity earned: pseudonym `agent-4b1f4d` (identity id `01M2DQV7E0FKSQ8SCYYY5WFEB8`, proof kind `tutorial`).
Working files: `scratchpad/tester/` (every request body, every response, `writes.log`).

## 1. Journey

1. **Website** (`https://openproofnetwork.org/`). Home, Targets, Frontier, Contributors, Docs. The Docs page carries the
   whole of the graph's `AGENTS.md` plus the architecture decisions. That guide was enough to learn the shape of a
   contribution, the three paths (git / HTTP / MCP), how a token is earned, the artifact types and the skeleton rules.
   The frontier page listed 10 nodes; only one, `variant-93e79cb5` on target `tutorial`, was claimable. The targets
   page said *why* each of the other six targets is not claimable (status `listed`, grade below
   `screened-and-signed`, no D-10 posting) — clear.
2. **MCP** (`https://api.openproofnetwork.org/mcp`). `initialize` and `tools/list` work with no token and no session
   header; 21 tools, every one mapping to a plain path. Read tools (`list_targets`, `get_target`, `list_frontier`
   with filters, `get_node`, `get_defs`, `get_gate_spec`, `get_precheck`) all worked first time and unauthenticated.
   `get_schema` was broken for every protocol schema (bug 2). There is no token tool.
3. **Choosing a node.** The protocol (D-6, D-25, D-33) makes claims advisory and says `listed` blocks *claims*, not
   submissions, so a submission to a non-claimable Erdős root or a `euclid-primes` hole might have been accepted. I did
   not try one: the brief asks for the node the network says is open to me, a Mathlib precheck there costs minutes
   each, and there was exactly one claimable node. I probed non-claimability once with a claim on
   `infinitude-of-primes--h1` (refused cleanly: `409 node-not-claimable`). Whether the precheck or submission on such a
   node is refused stays unknown (see Features wanted).
   **Chosen node: `variant-93e79cb5` (target `tutorial`), `∀ p q : Prop, p ∧ q → p`**, because it is the only node
   the frontier marks claimable. The mathematics is trivial; the contribution is a well-formed two-hole skeleton
   (D-31 / D-12 #5), which is the artifact type the brief asked for and the network calls the entry task.
4. **Earning a token.** `precheck_submission` on the tutorial node through the MCP, no token: **401** (bug 1). The same
   bundle through `POST /precheck` over plain HTTP: 202, job `01M2DQPD4G354SM2AZVFX2RXZ5`, passed in 2 min 4 s,
   nonce → `POST /tokens` → 201, token.
5. **Claim + annex.** `claim_node` (MCP, bearer) → 201, claim `01M2DQVN3GHC8KAF5GDJFCW4TX`. `submit_informal_annex`
   (MCP, bearer) → 201, graph PR #32, hash `c761b2b1…`. The hash is not the sha256 of the text I sent (bug 6).
6. **Skeleton precheck, three attempts.**
   - Guide's shape (citation comment in the header, path `Proof.lean`): **fail step 2** `proof-not-statement` (bug 3).
   - Citation moved inside the proof body, path `Proof.lean`: passes step 2 and 4, **fail step 5**
     `axiom-not-allowed: sorryAx` — the precheck treated the skeleton as a full proof; no argument tells it otherwise
     (bug 4). Sending `artifact_type: "partial"` on `POST /precheck` was silently accepted and ignored (bug 5).
   - Same file at `attempts/20260913T160600Z-agent-4b1f4d-partial.lean`: **pass**, step 2 says `partial-submission`,
     step 4 says `artifact-partial`, holes `h₁`, `h₂`. Nothing in the guide says a partial goes under this path; the
     permitted-paths table says that file is written *by the gate* (bug 3/4).
7. **Submission.** `submit_proof` (MCP, bearer, `artifact_type: partial`, the passing job document as `attestation`)
   → 201, submission `01M2DRDN90JWNYA2N6GMQZYEPZ`, **graph PR #33**. The commit is authored and signed off by
   `agent-4b1f4d`, committed by `open-proof-network[bot]`; the body carries the attestation block and a
   `submission-meta/v1` block with the tooling I declared.
8. **What the network did with it.** PR #33's `gate` check completed **failure** 8 s after opening: workflow step
   "Step 9 — a non-author approving review, unless the statement is certified" failed and every sandbox step was
   skipped. So the gate's own build (steps 1–8) never ran on the pull request; the network's mechanical answer is
   "needs a human". The only place the reason is visible is a check-run annotation on GitHub (bug 7). PR #32 (annex)
   went green in append mode and was merged by a human at 16:09:50Z while I was still working; the post-merge job
   re-rendered products (`rendered_from 776ff82…`), the site rebuilt (`dfd772ad`), and both now show the annex.
   PR #33 remains open, red, awaiting review; `mergeable_state` was `unstable` then `unknown` after `main` moved.
9. **Cleanup.** `release_claim` (MCP, bearer) → 200, released 16:10:13Z; the live frontier shows no active claim.

What a contributor can see about a pending contribution: the `pr_url`, the pull request page, and (via GitHub's
public API) the check-run status and annotations. What they cannot: the precheck's whereabouts while `running`
(no `started`, no run link — the job is not among the graph repository's Actions runs, which is where I looked; it
runs elsewhere), the gate job's log (`403 Must have admin rights` on the logs endpoint; the raw-log URL 404s), any
comment on the PR, any service endpoint for a submission (`get_submission` reads only merged attestations), and any
list of their own prechecks or claims.

## 2. Bugs

1. **MCP path cannot bootstrap an identity.** `precheck_submission` on the tutorial node with no bearer →
   `{"status":401,"body":{"error":"invalid_token","error_description":"Authentication required"}}`. The guide says
   "The tutorial node needs no token; every other node does", the server's own `instructions` say writes need a token
   from `POST /tokens`, and there is no MCP tool for `POST /tokens`. A client that only speaks MCP (`claude mcp add`)
   can never earn a token. Expected: the tool to pass the anonymous tutorial precheck through, or a `get_token` tool.
   **Severity: blocks a contributor (MCP path). Where: MCP adapter (auth applied to a tool the guide exempts) and
   guide (the appendix says "there is no MCP-only capability" but the reverse gap is unmentioned).**
2. **`get_schema` finds no protocol schema.** `get_schema("postmortem/v1")` — the exact call the guide names — returns
   `{"error":"not-found","message":"the graph has no schemas/postmortem/v1.json at main","source":"graph"}`. Same for
   `frontier/v2`, `meta/v4`, `attestation/v4`, `graph/v3`, `annex/v1`, `submission-meta/v1`. `info.json` advertises 26
   schema names with versions; the graph's `schemas/` holds only `attestation/{v1,v2}`, `gate-spec/v1`, `meta/v1`.
   The tool reads the wrong place (the graph) for schemas that live with the network. The `mcp/<tool>/v1` result
   schemas do resolve. **Severity: confusing / blocks a contributor who wants to validate a postmortem before
   sending. Where: MCP adapter (or the graph is missing the files the index promises).**
3. **The guide's skeleton shape is refused by the gate.** The guide's example puts `-- annex: <sha256>` between the
   imports and the theorem. Precheck job `01M2DQW9KR9PNRW008DQT1ARY5`: step 2 `proof-not-statement`,
   `"Proof.lean diverges from Statement.lean at line 2 (header or signature)"`, `got: "-- annex: c761…"`. The
   diagnostic itself is excellent (line, expected, got). Placing the comment inside the body after `by` passes.
   **Severity: blocks a contributor following the guide literally. Where: guide.**
4. **A skeleton cannot pass the precheck at the path the guide implies.** With the citation in the body and the file
   at `Proof.lean` (job `01M2DQZ6CGM671DVYZX0HA2ES8`): step 5 `axiom-not-allowed`, `axioms: ["sorryAx"]`. The precheck
   has no `artifact_type`, so it judges every `Proof.lean` as a full proof, and `submit_proof` requires a *passing*
   attestation, so a partial is impossible unless you guess the path. The path that works,
   `attempts/<timestamp>-<pseudonym>-partial.lean`, appears in the guide's permitted-paths table as written by "the
   gate", and the skeleton section says only "it merges into `attempts/`". The successful precheck's own step-2
   diagnostic (`partial-submission`) proves the gate knows the convention; the guide does not state it.
   **Severity: blocks a contributor (cost me two extra prechecks). Where: guide, and a service gap (precheck has no
   artifact_type).**
5. **`POST /precheck` silently accepts unknown fields.** Sending `artifact_type: "partial"` (job
   `01M2DR4M70JSXZT8FJTAEA4HRH`) returned 202 with the same `bundle_digest` and the same step-5 failure. A refused
   unknown field would have saved a 2.5-minute run and told me the field does not exist. **Severity: confusing.
   Where: service.**
6. **Annex hash is not the hash of the text.** I sent 616 bytes of text; sha256 of it is `4af22f5d…`; the service
   returned `c761b2b1…` and named the file after that. The merged file carries YAML front matter (contributor, date,
   licence, model_and_tooling, node, schema) — the hash is of the file the service wrote. The guide says "content-hashed
   into `annex/<sha256>.md`" and "the hash a skeleton must cite", which a contributor will read as "hash your text".
   Nothing tells you the hash covers front matter you did not write. **Severity: confusing (harmless once you use
   the returned `hash`; fatal for anyone who pre-computes and cites it). Where: guide / service contract.**
7. **A submission awaiting review reports as a failed check with no explanation a contributor can reach.** PR #33's
   `gate` check is `completed / failure` eight seconds after opening; workflow step "Step 9 — a non-author approving
   review…" fails and steps 1–8 are skipped. The reason ("step 9: this node's root has no fidelity certificate or
   registry provenance, so a non-author approving review is required before merge … Re-runs when a review is
   submitted.") exists only as a check-run annotation; no PR comment, nothing in the service, the job log is
   `403 Must have admin rights`, and nothing the site shows. A red X on a correct submission is what a newcomer sees.
   Also the order: step 9 is evaluated *before* the sandbox build, so a reviewer is asked to approve a partial the
   authoritative gate has not yet built. **Severity: confusing / wrong signal. Where: gate workflow (record repo),
   protocol gap (D-4 step 9 vs a red check).**
8. **`get_submission` id shape differs from the guide.** The guide: "the signed attestation is
   `attestations/<pull request number>.json`". The files are `000002.json`, `000019.json`; `get_submission("2")` is
   not-found, `get_submission("000002")` works. The tool's `submission_id` also invites the `submission_id` that
   `submit_proof` returned (`01M2DRDN…`), which is not-found either. **Severity: confusing. Where: guide + adapter.**
9. **The site does not say it is behind the service.** Home/frontier pages said "rendered from 14d87ac", the service's
   products said `rendered_from 0a8580f`; both were right (products render at the merge commit, the site's stamp is the
   later push it was built from), but the two numbers disagree with no explanation, and the site's Claims column is
   static ("0 active" while my claim was live on the service). Cosmetic, but the frontier page says "This is exactly
   what an agent sees through list_frontier", which is untrue for claims. **Severity: cosmetic. Where: site.**
10. **Unauthenticated-write refusal differs by path.** HTTP: `401 {"error":"unauthenticated","message":"this route
    needs \`Authorization: Bearer <token>\`"}` — clear. MCP: `401 {"error":"invalid_token","error_description":
    "Authentication required"}` — an OAuth-flavoured body from a different layer, and it does not say how to get a
    token. **Severity: confusing. Where: MCP adapter.**
11. **`get_node` disagrees with itself on claim history.** `context.claims.history_count` was 0 while the live
    `claims.history_count` was 5 (then 6) on the same node. One is the file, one is the service; nothing labels which.
    **Severity: cosmetic. Where: adapter / context bundle.**
12. **Argument-name drift between paths.** MCP `claim_node.ttl` vs HTTP `ttl_hours`; MCP `submit_proof.attestation`
    (an object) vs HTTP `precheck_job_id` (a string); the guide's HTTP proposal uses `statement` while the MCP tool
    uses `stmt`. Each works, but a contributor moving between the guide's curl blocks and the tools has to notice.
    **Severity: confusing. Where: adapter / guide.**
13. **Precheck job carries no progress or provenance.** `state: running` with `started: null`, `finished: null`, no
    runner or run URL, for ~2–2.5 minutes even on a Mathlib-free target. Nothing to tell a stuck job from a slow one.
    **Severity: confusing. Where: service.**
14. **Docs page: licence and DCO sections say nothing is committed.** "No license text is committed to the graph yet;
    D-23 settles it before the first external contributor" — yet the service issues tokens and the annex tool demands
    a licence enum. As the first external contributor, I signed a DCO (version `f7ac75b4…`, served by `/dco.json`) for
    a repository whose licence the site says is unsettled. **Severity: confusing / protocol gap. Where: site + D-23.**

## 3. Features wanted

- A token tool on the MCP (or an unauthenticated tutorial precheck through `precheck_submission`) — without one the
  MCP path is read-only for a stranger.
- `precheck_submission` / `POST /precheck` to take `artifact_type` (or the guide to state the `attempts/…-partial.lean`
  convention in the skeleton section, next to the example).
- A one-line statement of where the `-- annex:` line may go (inside the body) — or step 2 to allow it in the header.
- The annex tool's response to say what was hashed (or the guide to say the hash covers the front matter).
- A service view of my own pending things: `GET /submissions/<id>` (state, PR, gate verdict, what it is waiting on),
  `GET /claims` (mine), `GET /precheck?mine` — today the token buys writes and no reads of their consequences.
- The gate to comment on the PR (or the service to expose) the step-9 verdict, so "awaiting a non-author review" does
  not look like a failed build; ideally a *neutral/pending* check rather than `failure`.
- A documented answer to "can I submit to a non-claimable node?" — the protocol blocks claims only; the service's
  behaviour for a precheck or submission on a `listed` target is unstated, and I did not spend a Mathlib run to learn it.
- `get_schema` to serve every name `info.json` lists.
- The precheck job to carry `started`, an elapsed time, and the runner class.

## 4. Writes log

| # | When (UTC) | Endpoint / tool | Node / target | Sent | Returned | Last state observed |
|---|---|---|---|---|---|---|
| W1 | 15:53 | MCP `precheck_submission`, no bearer | `tutorial-and-swap` | `targets/tutorial/nodes/tutorial-and-swap/Proof.lean` (guide's proof) | 401 `invalid_token` | refused, no job |
| W2 | 15:55:38 | HTTP `POST /precheck`, no bearer | `tutorial-and-swap` | same file | 202, job `01M2DQPD4G354SM2AZVFX2RXZ5`, nonce | done, **pass**, service-signed, 15:57:42 |
| W3 | 15:58:16 | HTTP `POST /tokens` | — | `{proof:{kind:tutorial, job_id, nonce}, pseudonym: agent-4b1f4d, dco:{version f7ac75b443f4ca16, accepted:true}}` | 201, identity `01M2DQV7E0FKSQ8SCYYY5WFEB8` | token held locally, not in report |
| W4 | 15:58:30 | MCP `claim_node`, bearer | `variant-93e79cb5` | `ttl: 2` | 201, claim `01M2DQVN3GHC8KAF5GDJFCW4TX`, expires 17:58:30Z | released (W12) |
| W5 | 15:58:31 | MCP `submit_informal_annex`, bearer | `variant-93e79cb5` | `annex.md` text, licence CC-BY-4.0, model_and_tooling | 201, id `01M2DQVP2RM6TK6XYDF86FTPCA`, hash `c761b2b136f154b6b82cbcb375549ec4f9d30d5772bcbcc20df6d092026eb65a`, `pr_url` https://github.com/thisisanameforsure/open_proof_network_graph/pull/32 | gate green (append), **merged 16:09:50Z** by a human; live on the service (`get_node.annexes`, frontier `annex_present: true`) and on the site (commit `dfd772ad`) |
| W6 | 15:58:32 | MCP `claim_node`, bearer (refusal probe) | `infinitude-of-primes--h1` | `ttl: 1` | 409 `node-not-claimable` | refused, nothing landed |
| W7 | 15:58:51 | MCP `precheck_submission`, bearer | `variant-93e79cb5` | `nodes/variant-93e79cb5/Proof.lean` = skeleton, citation in header | 202, job `01M2DQW9KR9PNRW008DQT1ARY5` | done, **fail step 2** `proof-not-statement` |
| W8 | 16:00:26 | MCP `precheck_submission`, bearer | `variant-93e79cb5` | `Proof.lean` = skeleton, citation in body | 202, job `01M2DQZ6CGM671DVYZX0HA2ES8` | done, **fail step 5** `axiom-not-allowed: sorryAx` |
| W9 | 16:03:24 | HTTP `POST /precheck`, bearer | `variant-93e79cb5` | W8 body + `artifact_type: "partial"` | 202, job `01M2DR4M70JSXZT8FJTAEA4HRH` | done, **fail step 5** (field ignored) |
| W10 | 16:05:59 | MCP `precheck_submission`, bearer | `variant-93e79cb5` | `nodes/variant-93e79cb5/attempts/20260913T160600Z-agent-4b1f4d-partial.lean` = same skeleton | 202, job `01M2DR9BJR7PV0KMKBW4EGSTR9` | done, **pass**, `artifact-partial`, holes `h₁`, `h₂`, service-signed |
| W11 | 16:08:20 | MCP `submit_proof`, bearer | `variant-93e79cb5` | `artifact_type: partial`, W10 bundle, `attestation` = W10 job document, tooling {model, version, harness} | 201, submission `01M2DRDN90JWNYA2N6GMQZYEPZ`, `pr_url` https://github.com/thisisanameforsure/open_proof_network_graph/pull/33, PR #33 | **open**; `gate` check `failure` at "Step 9 — non-author approving review" (sandbox steps skipped, build never ran); annotation says it re-runs when a review is submitted; `mergeable_state` unstable → unknown after main moved |
| W12 | 16:10:13 | MCP `release_claim`, bearer | claim `01M2DQVN3GHC8KAF5GDJFCW4TX` | — | 200, `released: 2026-09-13T16:10:13Z` | frontier shows 0 active claims, history 6 |

Totals: 5 prechecks (1 anonymous, 4 owned), 1 token, 2 claims (1 refused), 1 annex, 1 submission, 1 release. Two
pull requests on the record: #32 (merged), #33 (open). No `gh`, no `git push`, no local repository read.

## 5. Unverified Lean

All three Lean artifacts are for target `tutorial` (Lean core only, no Mathlib), so every one was compiled by the
service's precheck and I have its verdict rather than an estimate.

**A. Tutorial proof (W2)** — `Proof.lean`, statement header byte-identical, body:
```
  intro p q hpq
  exact ⟨hpq.right, hpq.left⟩
```
Estimate: elaborates (the guide's own body). Precheck: **pass**, steps 1, 2, 4–8 all pass.

**B. Skeleton, header-placed citation (W7)** — `Proof.lean`:
```
/-! A related variant of the tutorial node (D-30), proposed by the F08 smoke. -/
-- annex: c761b2b136f154b6b82cbcb375549ec4f9d30d5772bcbcc20df6d092026eb65a

theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by
  intro p q hpq
  have h₁ : q ∧ p := sorry        -- lemma 1 of the annex: a conjunction commutes
  have h₂ : q ∧ p → p := sorry    -- lemma 2 of the annex: the right projection
  exact h₂ h₁                     -- the assembly: proved, not sorry
```
Estimate: elaborates (the assembly `h₂ h₁ : p` is well-typed; the holes are `sorry`). Precheck: **fail at step 2**
before any elaboration — `proof-not-statement`, line 2 — so never compiled.

**C. Skeleton, body-placed citation (W8, W9 at `Proof.lean`; W10 and the submitted W11 at
`attempts/20260913T160600Z-agent-4b1f4d-partial.lean`)** — identical text except the citation line moved to the
first line of the body:
```
/-! A related variant of the tutorial node (D-30), proposed by the F08 smoke. -/

theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by
  -- annex: c761b2b136f154b6b82cbcb375549ec4f9d30d5772bcbcc20df6d092026eb65a
  intro p q hpq
  have h₁ : q ∧ p := sorry        -- lemma 1 of the annex: a conjunction commutes
  have h₂ : q ∧ p → p := sorry    -- lemma 2 of the annex: the right projection
  exact h₂ h₁                     -- the assembly: proved, not sorry
```
Estimate: elaborates modulo two `sorry`s; not a trivial skeleton (neither hole is definitionally the goal `p`).
Precheck as `Proof.lean` (W8, W9): step 4 kernel-replay **pass**, step 5 **fail** `sorryAx` (judged as a full proof).
Precheck at the partial path (W10): **pass** — step 2 `partial-submission`, step 4
`partial: OpnProp.and_left_of_and_swap declares ∀ (p q : Prop), p ∧ q → p; 2 hole(s)` (`h₁`, `h₂`), steps 5–8 pass,
attestation `trust_base: kernel`, signed by the service at job `01M2DR9BJR7PV0KMKBW4EGSTR9`. This is the file on
PR #33. The authoritative gate has not compiled it: the workflow stopped at step 9 (review) before the sandbox.
The annex it cites is now merged on the node (PR #32), so the citation check should pass when the gate runs.
