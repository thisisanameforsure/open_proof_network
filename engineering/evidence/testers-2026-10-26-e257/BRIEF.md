# Brief: three agents on erdos-257 for three hours (2026-10-26)

You are one of three contributors to the Open Proof Network working on **Erdős problem 257** for three
hours. The network is a crowdsourced Lean 4 proof network; contributions land as pull requests on the
graph repository through the network's service, are checked by a gate, and merge automatically when green.

Two jobs, equal weight:
1. **Mathematics.** Move erdos-257 forward on the record: proofs, partials (a proof with named holes),
   witnesses, related variants, literature records, approach records, postmortems, glosses/explainers.
2. **Bugs and feature requests.** Everything that slows you down, confuses you, or is wrong is a finding.
   Write each one down the moment you hit it, with evidence (see "Findings" below). The lead will verify
   every one, so a finding without a reproduction is worth little.

## Where things are

- Site: https://openproofnetwork.org (problem page: https://openproofnetwork.org/problems/erdos-257/ ;
  follow links from the home page if that path is wrong — and if it is, that is a finding).
- MCP endpoint: `https://api.openproofnetwork.org/mcp` (HTTP JSON-RPC). The service's HTTP routes are
  under `https://api.openproofnetwork.org/`.
- The contributor guide: `AGENTS.md` in a fresh clone of the graph:
  `git clone https://github.com/thisisanameforsure/open_proof_network_graph.git <your dir>/graph`
  Read it first. It tells you how to get a token, claim a node, check Lean fast, precheck, and submit.
- **Black box.** Do not read the network's source code (the `open_proof_network` repository or anything
  under `/Users/mikehiggins/Desktop/repos/open_proof_network*`, and nothing under `/Users/mikehiggins/Desktop/repos/opn-*`
  other than your own evidence folder). Do not read `.env` files anywhere. You are testing what a real
  outside contributor gets. The graph clone is yours to read in full.
- There is no hosted prover (Aristotle) available in this run. Lean is written by you and checked through
  the network's fast check.

## Your files

- Evidence folder: `/Users/mikehiggins/Desktop/repos/opn-testers-1026/engineering/evidence/testers-2026-10-26-e257/`
- Your log: `<ID>.md` there (e.g. `A.md`). **Append as you go, timestamped (`date -u +%H:%MZ`)**: every claim,
  precheck id, PR number, refusal, idea abandoned and why. If you are killed mid-run (the laptop may lose
  power), this file is all that survives, and the lead finishes your work from it. Write the Lean you are
  about to submit into `<ID>/` *before* submitting it, with a note in the log of what it is for.
- Your working files (Lean, scripts, receipts): `<ID>/` there.
- **Secrets never go in the evidence folder.** Keep your token only in your private scratch dir (given in
  your prompt). Never write a token, or a whole token response, to the evidence folder or a log. Refer to it
  as "my token".
- The board: `COORDINATION.md` there. Append-only, one line per note: `HH:MMZ <ID>: <note>`. **Claim a
  node on the board before working on it**, read the board before choosing, post when you submit,
  stop, or find something another agent should know (a lemma you need, a lemma you proved).

## Rules

- **Run window: 20:20Z until 23:20Z.** Stop starting new submissions at 23:05Z; write your final report by
  23:20Z. Work continuously until then: when one line of attack dies, record why and take the next.
  Do not stop early because the problem is hard — that is expected; the record of what was tried, and
  smaller true statements proved, are the deliverable.
- **Tokens:** token minting is capped at about 10 starts per day for this whole machine. Mint ONE token
  and reuse it for the whole run. If you are refused (429), post it on the board and say so in your log;
  the lead can submit for you.
- Contribute only through the service/MCP. Never push to the graph repository, never merge, never close
  or comment on other people's pull requests. Do not open pull requests on the network repo.
- Re-read the node's current state (frontier / node) right before every write: others are working too.
- Never manufacture content to make a check pass. A trivial variant, a restated hypothesis, or a
  "statement" chosen because it is easy is not mathematics. If you add a node, it must be something a
  mathematician would agree is a meaningful, true step towards the problem. The record already holds
  fifteen proved special cases; another easy special case is worth little unless it is a step on a route.
- Before you stop, file a **postmortem** (through the network) on the node(s) you worked on: what you
  tried and why it did not close. Then write your final report.
- Network from this laptop sometimes drops connections (lost SYNs, 20–75 s stalls). Retry. Before calling
  a route "slow", measure it: `curl -s -o /dev/null -w '%{time_connect} %{time_total}\n' <url>`; a long
  `time_connect` is the laptop's path, not the service.

## The problem and what the record already holds

Erdős 257: for infinite A ⊆ ℕ, is Σ_{n∈A} 1/(2^n − 1) irrational? The graph's root states the
affirmative. Read the record (problem page, `graph.json`, the nodes' files, literature, annexes,
approach records, postmortems) before choosing. Summary as of 20:15Z today (graph `ee817d04`):

- **Proved:** the gap lemma `spec-ddd99827`; uniqueness of representation `spec-5e2e0890`;
  `erdos-257--h1` (a representation of a rational is the greedy one); the bookkeeping holes
  `spec-a70fcca4--h1..--h3`; fifteen special-case variants (A = ℕ, every AP, eventually periodic,
  pairwise coprime with Σ1/a < ∞, squarefree, k-th powers, sums of two squares, lacunary/ratio-two,
  long gaps, Liouville criterion, powers of two and three, unions of chains and of two bases, and two
  structural facts: the subset sums have Lebesgue measure 1 and form a Cantor set; only countably many
  sets have a rational sum).
- **Open (where the problem actually is):**
  - `erdos-257` (root) is a case-split partial: its fifteen special cases are lemmas pointing at the
    variants, and what is left is `erdos-257--h18`, "every other infinite set".
  - `erdos-257--h2` "no rational is an infinite greedy sum" (the open core), resting on
    `erdos-257--h2--h1` "a rational's greedy set is finite or co-finite". Kovač expects the root to be
    **false**.
  - `spec-a70fcca4-v2`, a **refutes** variant: "1/2 is the sum of an infinite set". Its open hole
    `spec-a70fcca4--h4` (the greedy walk for 1/2 never stalls) rests on `--h4--h1` (a skipped step
    leaves at most 2^-m + 4^-m/3), which rests on two alternative holes `--h4--h1--h1` (after a skipped
    m ≥ 2, another skip within (m, 2m]) and `--h4--h1--h2` (after a skipped m ≥ 1, another skip within
    (m, 3m+2]). Computation to depth 20000 confirms both; no mechanism is known.
  - `variant-6b364d2b` (A = primes, Tao–Teräväinen arXiv:2512.01739 Thm 1.3) is a partial whose remaining
    hole `--h1--h1` is TT §§5.6–5.14 (κ₂–κ₅ for each Lemma 5.2 cube): a known result, not yet in Lean.
  - `variant-5274cf38--h1`: purely periodic sets (Luca–Tachiya 2014 Thm 1.1 for 0/1 sequences) — a
    known result whose Lean proof is missing. Erdős's 1948 CRT argument with f_B(m) = #{d | m : d ∈ B}
    in place of d(m) is the route; the A = ℕ proof on `variant-2f5236aa` is the template.
- **Literature caveats (checked on 2026-10-22):** Tao–Teräväinen prove only A = primes; prime powers and
  other bases are a remark. Kovač–Tao Rem. 4.1 proves uniqueness and the Cantor set, not measure; measure 1
  is Nitecki arXiv:1106.3779 Thm 4(1) / Hornich 1941. Kovač (forum, 25 Aug 2025): for base t ≥ 3 the
  subsum set is null; base 2 is the only fat case.
- **Numerics (lead, 2026-10-20/22):** the greedy walk for 1/2 runs to depth 20000 without stalling; the
  chosen set looks like fair coin flips; over all rationals p/q with q ≤ 250, stalls occur only at
  steps ≤ 12 and halve per step, and every denominator q ≥ 4 has rationals whose walk is alive, so no
  denominator class of `--h2` is provable by itself. A stall at m forces every later element to be
  chosen, which is why `--h2--h1` reads "finite or co-finite".

Realistic expectations: proving or refuting the root would solve an open Erdős problem. Valuable
outcomes in three hours are true intermediate statements proved in Lean on the open nodes, honest
decompositions whose holes are genuinely smaller, known results formalised where the record has a hole
for them, literature records with precise citations, and words that make the page readable — plus
well-evidenced findings.

## Findings (bugs and feature requests)

In your log, a `## Findings` section, one entry per finding:

- **Kind:** bug / feature request / docs.
- **What happened**, exactly: the tool or route, the arguments (no token), the response (trimmed), the
  time (UTC) and any ids (claim, precheck, job, PR).
- **What you expected**, and why (quote the guide where it says so).
- **Cost to you** (minutes lost, work abandoned).
- **How to reproduce** in one or two steps.

Do not guess at the network's internals; describe what you observed.

## Final report (last section of your log, and your final message to the lead)

1. What you landed (PR numbers, kind, node, merged or not).
2. Unfinished business the lead should finish: exact files, what each needs, what it waits on.
3. Findings, most important first (pointer to the log entries).
4. One paragraph: what would have made you twice as productive.
