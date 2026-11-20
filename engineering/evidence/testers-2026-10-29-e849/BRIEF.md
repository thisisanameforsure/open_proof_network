# Brief: three agents on erdos-849 for three hours (2026-10-29)

You are one of three contributors to the Open Proof Network working on **Erdős problem 849** for three
hours, through the network's MCP. The network is a crowdsourced Lean 4 proof network; contributions land
as pull requests on the graph repository through the network's service, are checked by a gate, and merge
automatically when green.

Two jobs:
1. **Mathematics (first).** Move the chosen skeleton (below) as far as it will go: cited holes reduced to
   narrower, exactly named statements; elementary pieces proved; the open core stated exactly.
2. **Bugs and feature requests.** Everything that slows you down, confuses you, or is wrong is a finding.
   Write each one down the moment you hit it, with evidence (see "Findings"). The lead verifies every one.

## Where things are

- Site: https://openproofnetwork.org (problem page: https://openproofnetwork.org/problems/erdos-849/).
- MCP endpoint: `https://api.openproofnetwork.org/mcp` (HTTP JSON-RPC). **Work through the MCP tools**
  (`tools/list` first); the HTTP routes under `https://api.openproofnetwork.org/` are a fallback, and
  needing one is a finding.
- The contributor guide: `AGENTS.md` in a fresh clone of the graph:
  `git clone https://github.com/thisisanameforsure/open_proof_network_graph.git <your scratch dir>/graph`
  Read it first. It tells you how to get a token, claim a node, check Lean fast, precheck, and submit.
  `git pull` your clone before reading any node's files: others are merging.
- **Black box.** Do not read the network's source code (the `open_proof_network` repository or anything
  under `/Users/mikehiggins/Desktop/repos/open_proof_network*`, nor anything under
  `/Users/mikehiggins/Desktop/repos/opn-*` other than your own evidence folder). Do not read `.env` files
  anywhere. You are testing what a real outside contributor gets. The graph clone is yours to read in full.
- No hosted prover (Aristotle), no local Lean, no direct AXLE calls. Lean is written by you and checked
  through the network's own fast check and precheck.

## Your files

- Evidence folder: `/Users/mikehiggins/Desktop/repos/opn-testers-1029-849/engineering/evidence/testers-2026-10-29-e849/`
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
- `prior/` holds the 2026-10-27 run on this same problem: its README is the state you inherit and the
  findings already known (a repeat is worth one line, "still present, prior #1", not a re-derivation).
  Its board shows how a good run is paced.

## Rules

- **Run window: 13:15Z until 16:15Z.** Stop starting new submissions at 16:00Z; write your final report by
  16:15Z. Work continuously until then: when one line dies, record why and take the next. Do not stop early
  because the problem is hard; it is an open problem, that is expected. Check the clock (`date -u`).
- **Tokens:** minting is capped at about 10 starts per day for this whole machine. Mint ONE token and reuse
  it for the whole run. If refused (429), post it on the board; the lead can help.
- Contribute only through the service/MCP. Never push to the graph repository, never merge, never close or
  comment on other people's pull requests. No pull requests on the network repo. Do not contact anyone.
- Re-read the node's current state right before every write: others are working too.
- **The owner's rule: skeleton first, no side results.** No small cases, no numerics for their own sake,
  no "known results" unless a hole of the skeleton needs exactly that result. Do not work on the root's
  other variants (`variant-3e42e1ad`, `variant-72919549`, `variant-a30f5217`): they are side results.
  Everything you add must be a step on the skeleton, or words/records about it. If unsure, don't.
- Never manufacture content to make a check pass. A trivial variant or a restated hypothesis is not
  mathematics, and a hole that merely restates its parent is not a decomposition. A decomposition of a cited
  hole is worth doing only if each new hole is *narrower and exactly sourced* (a named equation, a named
  theorem with its paper and number) or elementary. **A proof of a mis-generated statement launders the
  defect into the record**: if a gate-written hole does not say what its parent's `have` meant, that is a
  finding (and a defect claim), not a node to prove.
- **Quiet-window protocol (prior finding #1, still unfixed):** a proof or partial's post-merge job must push
  its bot commit `gate: #N pass`; appends (glosses, literature, postmortems, explainers) merging meanwhile
  starve that push. So: **no appends between a proof/partial MERGE and its `gate: #N pass` bot commit.**
  Appends go in right after a bot commit lands, batched. Post `SUBMITTED #N`, `MERGED #N` and
  `gate: #N pass` on the board so everyone knows the state.
- Before you stop, file a **postmortem** (through the network) on the node(s) you worked on. Then write your
  final report.
- The network from this laptop sometimes drops connections (20–75 s stalls). Retry. Before calling a route
  "slow", measure: `curl -s -o /dev/null -w '%{time_connect} %{time_total}\n' <url>`; a long `time_connect`
  is the laptop's path, not the service.
- One merge lane per target; a merge costs several minutes and a partial must merge *and render*
  (`409 products-pending`) before anything can be filed on its holes. Prepare the next thing while waiting;
  poll every 60 s at most.

## The problem and the record as of 13:10Z

Erdős 849: for every t ≥ 1, is there an a appearing as C(n,k), 1 ≤ k ≤ n/2, in exactly t rows n? The root
`erdos-849` states the affirmative. Singmaster's conjecture (bounded multiplicity) would refute it, and that
is the skeleton chosen on 2026-10-26 and built out on 2026-10-27:

`variant-3969f1f7` — Singmaster bounded in row form (proved, it refutes the root). Its holes:

- `--h1` proved.
- `--h3` (MRSTT 2022 Thm 1.3, the large-k regime k ≥ exp(log^{5/6} n)) — decomposed along the paper; open
  are exactly `--h3--h1--h1` (Prop 1.9) and `--h3--h2` (Prop 1.10), each with a postmortem saying why it was
  not split further. Read those postmortems before deciding to touch them.
- `--h2` (small k, k < exp(log^{5/6} n)) — reduced to de Weger's conjecture `--h2--h1` (BBdW 2017 Conj 2.1:
  every C(n,k) = C(m,l), 2 ≤ k < l, k ≤ n/2, l ≤ m/2, is one of the listed sporadic solutions) and then
  split along BBdW Thm 2.2. Open holes on this side:
  - **the nine solved (k,l) pairs**, `--h2--h1--h1--h1` … `--h9`: each says C(n,k) = C(m,l) for one fixed
    pair has only the listed solutions (e.g. `--h1`: C(n,2) = C(m,3) ⇒ (16,10), (56,22), (120,36);
    `--h2`: C(n,2) = C(m,4) ⇒ (21,10)). Cited (Avanesov 1966, Pintér 1995, de Weger 1996, Stroeker–de Weger
    1999, …), none formalised.
  - **two near-diagonal shapes**, `--h2--h1--h4--h2--h1` (C(n,k) ≠ C(n−1,k+2)) and `--h2--h1--h4--h2--h2`
    (C(n,k) ≠ C(n−2,k+1)), cited, not formalised. (The adjacent shape C(n,k) = C(n−1,k+1), Tovey/Lind, was
    proved in Lean by an agent on 10-27: `--h2--h1--h2`, read its proof.)
  - **two computational holes**, `--h2--h1--h3` (n ≤ 10⁶) and `--h2--h1--h4--h1` (value ≤ 10⁶⁰): searches,
    not provable inside the gate's caps as stated. Leave them unless you find an honest reduction.
  - **the open core** `--h2--h1--h4--h2--h3`: de Weger's conjecture with every case of BBdW Thm 2.2
    removed. Genuinely open.

Every node has a statement gloss, literature records and explainers from the earlier runs (read them with
`get_node`). A real steward may read this target; write every statement, gloss and explainer for a
mathematician reader: exact, plain, no hype.

## Lanes

- **First 20 minutes, everyone:** read the record for your lane (statements, postmortems, literature records,
  the Tovey/Lind proof) and post on the board a plan: which holes you take, the sub-skeleton you will build
  for each (new holes, which are elementary and which are named theorems, and why each is narrower than the
  hole), by 13:35Z. Claim the holes on the board.
- **A — the near-diagonal shapes and the open core.** (1) The two shapes `--h2--h1--h4--h2--h1` and
  `--h2--h1--h4--h2--h2`: find exactly what the literature proved and how (the Tovey/Lind proof went through a
  Pell equation; these may reduce to a specific elliptic curve or a Thue/Pell family). Build the reduction as
  a partial whose remaining hole is an exactly named Diophantine statement, and prove the reduction; if a
  shape is elementary, prove it outright. (2) Then the open core from a second angle: a sub-skeleton that
  isolates something strictly narrower (a further family of shapes, or a bound on l in terms of k), or an
  honest postmortem of why not.
- **B — the nine (k,l) pairs.** For each pair hole, the classical proof reduces C(n,k) = C(m,l) by
  completing squares/cubes to integral points on one explicit curve (an elliptic curve with a known Cremona/
  LMFDB label, a quartic, or a Thue equation). Build partials whose new hole is that exact integral-points
  statement (named, sourced), and prove the elementary algebra that reduces the pair to it. Start with the
  pairs whose curve is simplest (say which in your plan). An integral-points statement with a short known
  elementary proof (descent, a Pell argument) is worth proving outright; one that needs Baker's method or a
  Mordell–Weil computation stays a cited hole with its source.
- **C — auditor, Lean on call, words.** (1) Audit every hole the gate writes, the minute it lands on main:
  read its `Statement.lean` and check it says exactly what the partial's `have` meant (casts, binder types,
  the bounds, the ordering hypotheses). A mismatch is the run's top finding; post it before anyone proves
  against it. (2) Prove elementary holes A and B create, as they appear (proof = statement byte for byte plus
  the body; helpers in a `private` block, the guide says how), and help with Lean that fails the fast check.
  (3) Before 14:30Z, read the two MRSTT postmortems and say on the board whether either proposition has an
  honest further split along the paper; if it does, build it. (4) The words, in one batch in the quiet
  windows of the last 45 minutes: statement glosses for every node born today (labels per the guide),
  explainers of merged proofs and assemblies, literature records on the new named-theorem holes. Keep a
  running bug list.

Coordinate on the board. Post hole statements (exact Lean) the moment a precheck names them.

Realistic expectations: the open core will not be solved in three hours. Valuable outcomes are cited holes
replaced by exactly named narrower statements with the elementary reductions proved, any shape or pair that
yields to an elementary argument proved outright, words that make the page read for a mathematician, and
well-evidenced findings.

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
