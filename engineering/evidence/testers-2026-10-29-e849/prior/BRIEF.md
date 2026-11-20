# Brief: four agents on erdos-849 for three hours (2026-10-27)

You are one of four contributors to the Open Proof Network working on **Erdős problem 849** for three
hours, through the network's MCP. The network is a crowdsourced Lean 4 proof network; contributions land
as pull requests on the graph repository through the network's service, are checked by a gate, and merge
automatically when green.

Two jobs, equal weight:
1. **Mathematics.** Move erdos-849 forward on the record along the proof skeleton already there (below).
2. **Bugs and feature requests.** Everything that slows you down, confuses you, or is wrong is a finding.
   Write each one down the moment you hit it, with evidence (see "Findings"). The lead verifies every one,
   so a finding without a reproduction is worth little.

## Where things are

- Site: https://openproofnetwork.org (problem page: https://openproofnetwork.org/problems/erdos-849/).
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
- No hosted prover (Aristotle) in this run. Lean is written by you and checked through the network's fast check.

## Your files

- Evidence folder: `/Users/mikehiggins/Desktop/repos/opn-testers-1027-849/engineering/evidence/testers-2026-10-27-e849/`
- Your log: `<ID>.md` there (`A.md`, `B.md`, `C.md`, `D.md`). **Append as you go, timestamped
  (`date -u +%H:%MZ`)**: every claim, precheck id, PR number, refusal, idea abandoned and why. If you are
  killed mid-run, this file is all that survives and the lead finishes your work from it. Write the Lean you
  are about to submit into `<ID>/` *before* submitting it, with a log note of what it is for.
- Your working files: `<ID>/` there. The graph clone goes in your private scratch dir, not here.
- **Secrets never go in the evidence folder.** Keep your token only in your private scratch dir (given in
  your prompt). Never write a token, or a whole token response, to the evidence folder or a log.
- The board: `COORDINATION.md` there. Append-only, one line per note: `HH:MMZ <ID>: <note>`. **Claim a node
  on the board before working on it**, read the board before choosing, post when you submit, stop, or find
  something another agent should know. The lead posts as `lead`.
- `prior/` holds yesterday's run on this problem (three agents' logs, board, notes, Lean). Read it before
  you start: it is why the record looks as it does, and its findings are already known (a repeat is still
  worth one line, "still present, prior F-C4", not a re-derivation).

## Rules

- **Run window: 10:55Z until 13:55Z.** Stop starting new submissions at 13:40Z; write your final report by
  13:55Z. Work continuously until then: when one line dies, record why and take the next. Do not stop early
  because the problem is hard; that is expected. Check the clock (`date -u`) regularly.
- **Tokens:** minting is capped at about 10 starts per day for this whole machine. Mint ONE token and reuse
  it for the whole run. If refused (429), post it on the board; the lead can submit for you.
- Contribute only through the service/MCP. Never push to the graph repository, never merge, never close or
  comment on other people's pull requests. No pull requests on the network repo.
- Re-read the node's current state right before every write: others are working too.
- **The owner's rule: no side results.** No small cases, no "known results" unless a hole of the chosen
  skeleton needs exactly that result. Everything you add must be a step on the skeleton, or words/records
  about it. If you are unsure whether a result bears on a hole, don't.
- Never manufacture content to make a check pass. A trivial variant or a restated hypothesis is not
  mathematics. **A proof of a mis-generated statement launders the defect into the record**: if a
  gate-written hole does not say what its parent's `have` meant, that is a finding (and a defect claim),
  not a node to prove.
- Before you stop, file a **postmortem** (through the network) on the node(s) you worked on. Then write your
  final report.
- The network from this laptop sometimes drops connections (20–75 s stalls). Retry. Before calling a route
  "slow", measure: `curl -s -o /dev/null -w '%{time_connect} %{time_total}\n' <url>`; a long `time_connect`
  is the laptop's path, not the service.
- The merge queue is one lane per target and a merge on erdos-849 costs several minutes; a proposal must
  merge *and render* (3–12 min, `409 products-pending`) before anything can be filed on it. Plan around it:
  prepare the next thing while waiting; never idle-poll in a tight loop (poll every 60 s at most).

## The problem and the record as of 10:45Z

Erdős 849: for every t ≥ 1, is there an a with exactly t solutions of C(n, k) = a, 1 ≤ k ≤ n/2? The root
`erdos-849` (Formal Conjectures import) states the affirmative and counts **rows n**, not pairs:

```lean
theorem Opn.erdos_849 : ∀ t ≥ 1, ∃ a : ℕ, {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard = t
```

Yesterday's run put on the record (all merged; read `prior/COORDINATION-2026-10-26.md` for the PR list):
- t = 1..4 as proved variants; `variant-72919549` (infinitely many a with ≥ 3 rows) and `variant-3e42e1ad`
  proposed, proofs withheld by the owner's rule. Cruxes `spec-12191c69` (row count = pair count) and
  `spec-38faff03` (rows ⊆ [2, a]) proved; `variant-a30f5217` (rows(a) ≤ ⌊log₂ a⌋) proposed, proof withheld.
- **The chosen skeleton** (A's top pick of eight): a refutation. `variant-3969f1f7` is Singmaster's
  conjecture in row form, `∃ B, ∀ a, #rows(a) ≤ B`, with relation proof variant → ¬root. Its partial
  (#1029) splits rows(a) by k: `--h1` (2 ≤ k ≤ K: ≤ K rows, **proved**), `--h3` (k ≥ exp((log n)^{5/6}):
  ≤ 2 rows for a ≥ a₀, **MRSTT 2022 Thm 1.3, cited, not formalised**), `--h2` (K < k < exp((log n)^{5/6}):
  the **open core**, bounded only conditionally on de Weger's conjecture, MRSTT Rem 1.5). Literature records
  sit on the root, --h2 and --h3; postmortems on --h2; an approach record on the root lists the discarded
  affirmative routes (all rest on holes believed false).
- Live frontier for the target at 10:45Z: `erdos-849`, `variant-3969f1f7`, `--h2`, `--h3`,
  `variant-3e42e1ad`, `variant-72919549`, `variant-a30f5217`, all ready and claimable. Queue empty.

`prior/mrstt-structure.md` paraphrases the lemma structure of MRSTT Thm 1.3 (maximal-m solution; (1.5)
and (1.7) bound n, m; Prop 1.9 distance estimate via equidistribution Prop 1.12; Prop 1.10 Kane-type
≤ 1 nearby solution ⇒ ≤ 2). `prior/holes-menu.md` lists published results usable as holes, with theorem
numbers. Verify every citation before it goes on the record.

## Lanes

- **A — skeleton lead.** Own the skeleton. First (20 min, in your log): re-brainstorm, briefly — is the
  record's skeleton still the top pick, and what is the single most valuable next decomposition? The
  obvious candidate is a **partial on `--h3`** following MRSTT's own lemma structure, with holes that are
  the paper's named propositions stated faithfully (explicit constants, `∃ C`, the O-inside-the-exponent
  form B warned about) and the elementary steps proved. Yesterday's A judged the assembly's real-analysis
  bookkeeping too costly for the time left; you have three hours and C to prove the elementary holes.
  Post your pick on the board with the hole list; build it; keep the whole skeleton closable (every hole
  statement must be one its parent's assembly can use).
- **B — the open core `--h2`.** The mathematician on the hardest hole. Brainstorm at least five
  sub-skeletons of --h2 (e.g. split K < k ≤ k₀ with the Beukers / de Weger / Blokhuis–Brouwer–de Weger
  finiteness results for C(n,k) = C(m,l) at fixed (k,l), the uniformity in (k,l) being the honest open
  hole; Kane's method; the de Weger-conditional route of MRSTT Rem 1.5 as an explicit hypothesis node).
  Pick one, post it, build a partial on `--h2` whose holes are each a named published theorem or the one
  honest open statement, with the elementary steps proved. Price each hole before you promise it. Words
  for your holes go in the partial's `-- claim:` / `-- label:` lines (read the guide's partial section,
  and yesterday's F1: the label must sit in the comment block directly above the `have`).
- **C — Lean on call.** Prove the elementary holes of A's and B's skeletons as they appear (the hole's
  exact `Statement.lean` from the graph clone, proof must be statement byte for byte plus the body; helpers
  go in a `private` block, the guide says how). Until they exist, prepare and fast-check the lemmas they will
  need in `C/`: 4^m ≤ (2m+1)·C(2m,m) and the (1.5) bound from `prior/`, monotonicity in n and k, the
  maximal-m solution step, the row/pair conversions already merged (`spec-12191c69`, `spec-38faff03`,
  `--h1` — reuse them as deps where the guide allows). Also, first thing: **audit the two live holes**
  `variant-3969f1f7--h2` and `--h3`: read their `Statement.lean` on main and check that each says exactly
  what the partial's `have` meant (casts, the real-valued threshold, binder types). A mismatch is the run's
  top finding; post it before anyone proves against it.
- **D — words, review, reader, tooling.** No new mathematics of your own. (1) Every node born in this run
  gets its words through the route: `label` on glosses, statement glosses, explainers of merged proofs and
  of the skeleton assemblies, each mirroring the Lean exactly. (2) The formalization review on erdos-849:
  re-test the pair route (yesterday's F-C4: `pair-proof` advertised, refused) and record the exact current
  behaviour; attempt whatever answers/records the tools let a non-steward file. (3) Verify, against the
  record and the site, every claim the others post on the board (merged? rendered? page shows it?); report
  disagreements on the board at once. (4) Exercise the whole MCP read surface on erdos-849 once
  (`tools/list`, every read tool) and read the problem page as a mathematician would: anything wrong,
  missing or unreadable is a finding. Keep a running bug list in `D.md` for the lead.

Coordinate on the board. A and B: post hole statements (exact Lean) the moment a precheck names them,
so C and D can start.

Realistic expectations: --h2 is open mathematics and --h3's deep propositions will not be formalised in
three hours. Valuable outcomes are a faithful second-level skeleton of --h3 with its elementary holes
proved, an honest decomposition of --h2 that isolates the open core behind named theorems, words that
make the page read, and well-evidenced findings.

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
