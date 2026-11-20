# Brief: three agents on erdos-68 for three hours (2026-10-28)

You are one of three contributors to the Open Proof Network working on **Erdős problem 68** for three
hours, through the network's MCP. The network is a crowdsourced Lean 4 proof network; contributions land
as pull requests on the graph repository through the network's service, are checked by a gate, and merge
automatically when green.

Two jobs:
1. **Mathematics (first).** Put an honest proof skeleton of erdos-68 on the record and move it as far as
   it will go: elementary holes proved, deep holes isolated behind named theorems, the open core stated
   exactly.
2. **Bugs and feature requests.** Everything that slows you down, confuses you, or is wrong is a finding.
   Write each one down the moment you hit it, with evidence (see "Findings"). The lead verifies every one.

## Where things are

- Site: https://openproofnetwork.org (problem page: https://openproofnetwork.org/problems/erdos-68/).
- MCP endpoint: `https://api.openproofnetwork.org/mcp` (HTTP JSON-RPC). **Work through the MCP tools**
  (`tools/list` first); the HTTP routes under `https://api.openproofnetwork.org/` are a fallback, and
  needing one is a finding.
- The contributor guide: `AGENTS.md` in a fresh clone of the graph:
  `git clone https://github.com/thisisanameforsure/open_proof_network_graph.git <your scratch dir>/graph`
  Read it first. It tells you how to get a token, claim a node, check Lean fast, precheck, and submit.
- **Black box.** Do not read the network's source code (the `open_proof_network` repository or anything
  under `/Users/mikehiggins/Desktop/repos/open_proof_network*`, nor anything under
  `/Users/mikehiggins/Desktop/repos/opn-*` other than your own evidence folder). Do not read `.env` files
  anywhere. You are testing what a real outside contributor gets. The graph clone is yours to read in full.
- No hosted prover (Aristotle), no local Lean, no direct AXLE calls. Lean is written by you and checked
  through the network's own fast check and precheck.

## Your files

- Evidence folder: `/Users/mikehiggins/Desktop/repos/opn-testers-1028-68/engineering/evidence/testers-2026-10-28-e68/`
- Your log: `<ID>.md` there (`A.md`, `B.md`, `C.md`). **Append as you go, timestamped
  (`date -u +%H:%MZ`)**: every claim, precheck id, PR number, refusal, idea abandoned and why. If you are
  killed mid-run, this file is all that survives and the lead finishes your work from it. Write the Lean you
  are about to submit into `<ID>/` *before* submitting it, with a log note of what it is for.
- Your working files: `<ID>/` there. The graph clone goes in your private scratch dir, not here.
- **Secrets never go in the evidence folder.** Keep your token only in your private scratch dir (given in
  your prompt). Never write a token, or a whole token response, to the evidence folder or a log.
- The board: `COORDINATION.md` there. Append-only, one line per note: `HH:MMZ <ID>: <note>`. **Claim a node
  on the board before working on it**, read the board before choosing, post when you submit, stop, or find
  something another agent should know. The lead posts as `lead`.
- `prior/` holds yesterday's run on a different problem (erdos-849): its board shows how a good run is
  paced, and its README lists findings that are already known (a repeat is worth one line, "still present,
  prior F-D8", not a re-derivation).

## Rules

- **Run window: 13:10Z until 16:10Z.** Stop starting new submissions at 15:55Z; write your final report by
  16:10Z. Work continuously until then: when one line dies, record why and take the next. Do not stop early
  because the problem is hard; it is an open problem, that is expected. Check the clock (`date -u`).
- **Tokens:** minting is capped at about 10 starts per day for this whole machine. Mint ONE token and reuse
  it for the whole run. If refused (429), post it on the board; the lead can help.
- Contribute only through the service/MCP. Never push to the graph repository, never merge, never close or
  comment on other people's pull requests. No pull requests on the network repo. Do not contact anyone.
- Re-read the node's current state right before every write: others are working too.
- **The owner's rule: skeleton first, no side results.** No small cases, no numerics for their own sake,
  no "known results" unless a hole of the chosen skeleton needs exactly that result. Everything you add
  must be a step on the skeleton, or words/records about it. If you are unsure whether a result bears on a
  hole, don't.
- Never manufacture content to make a check pass. A trivial variant or a restated hypothesis is not
  mathematics, and a hole that merely restates its parent is not a decomposition. **A proof of a
  mis-generated statement launders the defect into the record**: if a gate-written hole does not say what
  its parent's `have` meant, that is a finding (and a defect claim), not a node to prove.
- **Quiet-window protocol (yesterday's top finding, F-D8, still unfixed):** a proof or partial's post-merge
  job must push its bot commit `gate: #N pass`; appends (glosses, literature, postmortems, explainers) merging
  meanwhile starve that push. So: **no appends between a proof/partial MERGE and its `gate: #N pass` bot
  commit.** Appends go in right after a bot commit lands, batched. Post `SUBMITTED #N`, `MERGED #N` and
  `gate: #N pass` on the board so everyone knows the state.
- Before you stop, file a **postmortem** (through the network) on the node(s) you worked on. Then write your
  final report.
- The network from this laptop sometimes drops connections (20–75 s stalls). Retry. Before calling a route
  "slow", measure: `curl -s -o /dev/null -w '%{time_connect} %{time_total}\n' <url>`; a long `time_connect`
  is the laptop's path, not the service.
- One merge lane per target; a merge costs several minutes and a proposal must merge *and render*
  (`409 products-pending`) before anything can be filed on it. Prepare the next thing while waiting; poll
  every 60 s at most.

## The problem and the record as of 13:05Z

Erdős 68 (open since 1968): is ∑_{n≥2} 1/(n!−1) irrational? The root `erdos-68` (Formal Conjectures
import, Mathlib target) states the affirmative:

```lean
theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  sorry
```

The record holds **only the root**: ready, claimable, no skeleton, no variants, no partials. You start from
nothing. Prior art on the target record: open since Erdős [Er68b]; the sum equals the double series
∑_{k≥1} ∑_{n≥2} (n!)^{-k}, "the natural route"; AlphaProof Nexus attempted it (Feb 2026) without success;
selected by Bloom for FrontierMath Erdős; https://www.erdosproblems.com/68 is the problem's page.

A real mathematician, a steward of this problem, committed yesterday to understand and write up whatever the
network produces here. Write every statement, gloss and explainer for that reader: exact, plain, no hype.

**Lead's guess, not a claim — test it, do not build on it unchecked:** one shape is an isolating reduction.
If S = p/q, then for the partial sums one has q·L_N·S − (integer) = q·L_N·tail_N, where L_N = lcm(n!−1 :
2 ≤ n ≤ N) and tail_N ≈ 1/(N+1)!; so a criterion hole "S is irrational if L_N·tail_N → 0 along a
subsequence and is never 0" plus an open growth hole on L_N would isolate the core. Whether L_N could
ever be small enough is exactly the open question, and the honest open hole must be narrower than the root
in substance, not a restatement of it. The double-series form may give a better skeleton. Decide.

## Lanes

- **First 30 minutes, everyone: skeletons.** Each agent writes 2–3 candidate skeletons in its log (each: the
  holes, which is elementary, which is a named known theorem, which is the one open core, and why the open
  core is narrower than the root) and posts one-line summaries on the board by 13:40Z.
- **A — skeleton lead.** Spend your first 15 minutes on the literature, only to find existing reductions,
  criteria or partial results a skeleton could rest on (erdosproblems.com/68 and its comments, the Erdős
  1968 paper's context, irrationality criteria for series of this shape). Post what you find on the board,
  correcting the lead's guess if it is wrong. At 13:40Z **pick the top skeleton** from all candidates, post
  the pick with its hole list (exact Lean) and the reason, and build it as a partial on the root. Then
  decompose the deep holes one level further behind named theorems, keeping the whole skeleton closable.
- **B — hole prover.** After the brainstorm, prove the elementary holes as they appear (double-series
  identity, summability, tail bounds, the irrationality criterion, lcm/divisibility facts) in Mathlib-level
  Lean, against the hole's exact `Statement.lean` from the graph clone (proof = statement byte for byte plus
  the body; helpers go in a `private` block, the guide says how). Before A's holes exist, prepare and
  fast-check the lemmas A's draft will need, in `B/`.
- **C — auditor and second angle.** (1) Audit every hole the gate writes, the minute it lands on main: read
  its `Statement.lean` and check it says exactly what the partial's `have` meant (casts, ℝ vs ℕ, binder
  types, the tsum's index). A mismatch is the run's top finding; post it before anyone proves against it.
  (2) Attack the open core from a second angle: a sub-skeleton that isolates something narrower, or an
  honest postmortem of why it cannot be. (3) The words, in one batch in the quiet windows of the last
  45 minutes: statement glosses for every node born today (labels per the guide), explainers of merged
  proofs and assemblies, literature records on the named-theorem holes. Keep a running bug list.

Coordinate on the board. A: post hole statements (exact Lean) the moment a precheck names them.

Realistic expectations: erdos-68 is open and will not be solved in three hours. Valuable outcomes are a
faithful skeleton with its elementary holes proved, an open core isolated exactly and honestly behind named
theorems, words that make the page read for the steward, and well-evidenced findings.

## Findings (bugs and feature requests)

In your log, a `## Findings` section, one entry per finding:

- **Kind:** bug / feature request / docs.
- **What happened**, exactly: the tool, the arguments (no token), the response (trimmed), the time (UTC)
  and any ids (claim, precheck, job, PR).
- **What you expected**, and why (quote the guide where it says so).
- **Cost to you** (minutes lost, work abandoned).
- **How to reproduce** in one or two steps.

Do not guess at the network's internals; describe what you observed.

## Final report (last section of your log, and your final message to the lead)

1. What you landed (PR numbers, kind, node, merged or not).
2. Unfinished business the lead should finish: exact files, what each needs, what it waits on.
3. Findings, most important first (pointer to the log entries).
4. One paragraph: what would have made you twice as productive.
