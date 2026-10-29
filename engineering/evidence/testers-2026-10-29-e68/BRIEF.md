# Brief: four agents on erdos-68 for 90 minutes (2026-10-29)

You are one of four contributors to the Open Proof Network working on **Erdős problem 68** for 90 minutes,
through the network's MCP. The network is a crowdsourced Lean 4 proof network; contributions land as pull
requests on the graph repository through the network's service, are checked by a gate, and merge
automatically when green.

Two jobs:
1. **Mathematics (first).** Move the open core of erdos-68 forward: a sub-skeleton under it whose open hole
   is honestly narrower, its elementary holes proved, deep holes behind named theorems.
2. **Bugs and feature requests.** Everything that slows you down, confuses you, or is wrong is a finding.
   Write each one down the moment you hit it, with evidence (see "Findings"). The lead verifies every one.

## Where things are

- Site: https://openproofnetwork.org (problem page: https://openproofnetwork.org/problems/erdos-68/).
- MCP endpoint: `https://api.openproofnetwork.org/mcp` (HTTP JSON-RPC). **Work through the MCP tools**
  (`tools/list` first); the HTTP routes under `https://api.openproofnetwork.org/` are a fallback, and
  needing one is a finding.
- The contributor guide: `AGENTS.md` in a fresh clone of the graph:
  `git clone https://github.com/thisisanameforsure/open_proof_network_graph.git <your scratch dir>/graph`
  Read the parts you need (token, claim, fast check, precheck, partials, submit, words). `git pull` it
  before reading any node's `Statement.lean`.
- **Black box.** Do not read the network's source code (the `open_proof_network` repository or anything
  under `/Users/mikehiggins/Desktop/repos/open_proof_network*`, nor anything under
  `/Users/mikehiggins/Desktop/repos/opn-*` other than your own evidence folder). Do not read `.env` files
  anywhere. You are testing what a real outside contributor gets. The graph clone is yours to read in full.
- No hosted prover (Aristotle), no local Lean, no direct AXLE calls. Lean is written by you and checked
  through the network's own fast check and precheck.

## Your files

- Evidence folder: `/Users/mikehiggins/Desktop/repos/opn-testers-1029-68/engineering/evidence/testers-2026-10-29-e68/`
- Your log: `<ID>.md` there (`A.md` … `D.md`). **Append as you go, timestamped (`date -u +%H:%MZ`)**: every
  claim, precheck id, PR number, refusal, idea abandoned and why. If you are killed mid-run, this file is all
  that survives and the lead finishes your work from it. Write the Lean you are about to submit into `<ID>/`
  *before* submitting it, with a log note of what it is for.
- **Secrets never go in the evidence folder.** Your token is already in a file in your private scratch dir
  (given in your prompt); read it from there into a shell variable for each call. Never print it, never
  write it, or any whole token response, to the evidence folder or a log.
- The board: `COORDINATION.md` there. Append-only, one line per note: `HH:MMZ <ID>: <note>`. **Claim a node
  on the board before working on it**, read the board before choosing, post when you submit, stop, or find
  something another agent should know. The lead posts as `lead`.
- `prior/` holds **yesterday's run on this same problem**: `README.md` (outcome and findings — read it
  first), `BRIEF.md`, `COORDINATION.md`, the logs `A.md`–`C.md` and their Lean in `A/`, `B/`, `C/`. Reuse
  that Lean. Already-known findings are worth one line ("still present, prior #N"), not a re-derivation.

## Rules

- **Run window: 14:45Z until 16:15Z.** Stop starting new submissions at 16:00Z; write your final report by
  16:15Z. Work continuously until then: when one line dies, record why and take the next. Do not stop early
  because the problem is hard; it is open, that is expected. Check the clock (`date -u`).
- **Tokens:** use the token you were given; do not mint (minting is capped at ~10 starts a day for this
  machine and another run is using the machine). If it is refused (`401`, `403 dco-reaccept-required`),
  follow the guide for that exact response (DCO re-acceptance is done with the token itself) and post it on
  the board.
- Contribute only through the service/MCP. Never push to the graph repository, never merge, never close or
  comment on other people's pull requests. No pull requests on the network repo. Do not contact anyone.
- Re-read the node's current state right before every write: others are working too. Another run (four
  agents, erdos-849) is using the network at the same time; its pull requests are not yours.
- **The owner's rule: skeleton first, no side results.** No small cases, no numerics for their own sake,
  no "known results" unless a hole of the chosen skeleton needs exactly that result. Everything you add
  must be a step on the skeleton, or words/records about it. If you are unsure whether a result bears on a
  hole, don't.
- Never manufacture content to make a check pass. A trivial variant or a restated hypothesis is not
  mathematics, and a hole that merely restates its parent is not a decomposition. **An open hole equivalent
  to its parent (or to the root) is not progress** — yesterday's route 2 did exactly that (`--h6` ≡ root);
  for every proposed open hole, say in the log why it is strictly narrower, or why no reverse implication
  is known. **A proof of a mis-generated statement launders the defect into the record**: if a gate-written
  hole does not say what its parent's `have` meant, that is a finding (and a defect claim), not a node to
  prove.
- **Quiet-window protocol (prior finding, still unfixed):** a proof or partial's post-merge job must push its
  bot commit `gate: #N pass`; appends (glosses, literature, postmortems, explainers) merging meanwhile can
  starve that push. So: **no appends between a proof/partial MERGE and its `gate: #N pass` bot commit.**
  Appends go in right after a bot commit lands, batched. Post `SUBMITTED #N`, `MERGED #N` and
  `gate: #N pass` on the board so everyone knows the state.
- A partial still cannot carry proofs of its own holes (prior finding #5): prove the holes against their
  exact printed types while the partial merges, then submit each proof once its hole node exists.
- Before you stop, file a **postmortem** (through the network) on the node(s) you worked on. Then write your
  final report.
- The network from this laptop sometimes drops connections (20–75 s stalls). Retry. Before calling a route
  "slow", measure: `curl -s -o /dev/null -w '%{time_connect} %{time_total}\n' <url>`; a long `time_connect`
  is the laptop's path, not the service.
- One merge lane per target; a merge costs several minutes and a proposal must merge *and render*
  (`409 products-pending`) before anything can be filed on it. Prepare the next thing while waiting; poll
  every 60 s at most.

## The problem and the record as of 14:40Z

Erdős 68: is S = ∑_{n≥2} 1/(n!−1) irrational? The root `erdos-68` states the affirmative:

```lean
theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  sorry
```

Yesterday's three agents left (graph main, see `prior/README.md` for detail and PR numbers):

| Node | Status | What it is |
|---|---|---|
| `erdos-68` | ready | the root, two decompositions |
| `erdos-68--h1` | proved | if N!·x ∉ ℤ for arbitrarily large N, then x is irrational |
| `erdos-68--h2` | proved | N!·S = F_N + c with 0 < c ≤ 2/N, F_N = Σ_{n=2}^N N!/(n!−1) |
| `erdos-68--h3` | ready, **open core of route 1** | ∀M ∃N≥M, fract(F_N) < 1 − 2/N. Implies the root; no reverse implication known |
| `erdos-68--h5` | proved | sharp tail: 1/(N+1) < c < 1/N for N ≥ 4 |
| `erdos-68--h6` | ready | route 2's core, **equivalent to the root** — attacking it is attacking the root |

Ready for the day `--h3` is proved: `prior/B/proof-erdos-68-closing.lean`, the root's closing proof through
route 1, which passed the fast check. Refuted yesterday: the lcm-growth route (gcd(N!−1,(N−1)!−1) | N−1
makes L_N·tail_N → ∞; approach #1137). A real steward (Jiwon Kang) is committed to this problem: write every
statement, gloss and explainer for her — exact, plain, no hype.

So the target today is **`erdos-68--h3`**: fract(F_N) where F_N = Σ_{n=2}^N N!/(n!−1). Each summand
N!/(n!−1) = (N!/n!)·n!/(n!−1) = (N!/n!)·(1 + 1/(n!−1)), so fract(F_N) = fract(Σ_n (N!/n!)/(n!−1)), a sum
controlled by the residues of N!/n! modulo n!−1. Whether that gives a narrower handle is for you to decide.

## Lanes

- **First 20 minutes (until 15:05Z), A and B: skeletons.** Each writes 2–3 candidate sub-skeletons of
  `--h3` in its log (each: the holes, which is elementary, which is a named known theorem, which is the one
  open core, and why that core is strictly narrower than `--h3`, not equivalent to it or to the root) and
  posts one-line summaries on the board by 15:05Z.
- **A — skeleton lead.** At 15:05Z **pick the top sub-skeleton** from all candidates (A's and B's), post the
  pick with its hole list (exact Lean) and the reason, claim `--h3`, and build it as a partial on `--h3`.
  Then decompose its deep hole one level further if honest, keeping the whole thing closable.
- **B — second angle, then structure.** After the brainstorm: if the second-best candidate attacks a
  different node honestly (a new route on the root whose open core is narrower than the root and is neither
  `--h3` nor `--h6`), build it; otherwise take the top pick's deepest hole and decompose it one level, or
  write the honest postmortem of why the candidates collapse back to `--h3`.
- **C — hole prover.** From the start: read `prior/` Lean (B's lemmas, `fract_reduce.lean`, `tail.lean`) and
  prepare, in `C/`, fast-checked Mathlib lemmas a sub-skeleton of `--h3` will need (fract of F_N rewritten
  through N!/n! mod n!−1, bounds on the n near N terms). From 15:05Z, prove the elementary holes of A's (and
  B's) skeleton against the exact printed types, then against each hole's `Statement.lean` once it exists
  (proof = statement byte for byte plus the body; helpers in a `private` block, the guide says how).
- **D — auditor and words.** (1) Audit every hole the gate writes, the minute it lands on main: read its
  `Statement.lean` and check it says exactly what the partial's `have` meant (casts, ℝ vs ℕ, binder types,
  ranges, the fract). A mismatch is the run's top finding; post it before anyone proves against it. Audit
  the precheck's printed holes too, before the partial is submitted. (2) Check every claimed "strictly
  narrower" on the board: try to prove the reverse implication; post the verdict. (3) The words, in quiet
  windows from 15:30Z: statement glosses for every node born today (labels per the guide), explainers of
  merged proofs and assemblies, literature records on named-theorem holes. Keep a running bug list.

Coordinate on the board. A: post hole statements (exact Lean) the moment a precheck names them.

Realistic expectations: `--h3` is as hard as anything nobody has done; it will not be solved in 90 minutes.
Valuable outcomes are a faithful sub-skeleton with its elementary holes proved, an open core isolated
exactly and honestly, words that make the page read for the steward, and well-evidenced findings.

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
