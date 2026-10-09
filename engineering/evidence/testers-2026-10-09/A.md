# Tester A (t1009-a) log

12:40Z start. Read COORDINATION, pulled graph clone (head c120d59e9).
12:40Z MCP client written (A/mcp.py: initialize -> tools/call per call). tools/list 39 tools, 4.0 s.
12:40Z precheck_submission tutorial-and-swap (anon) -> 202 job 01M4GAWE1RE5Z4PCY168ZGCD6M, 8.7 s.
12:41Z get_node erdos-1094--h3 -> 200 in **113.3 s** (notable). get_node erdos-1094--h3--h1 -> 2.3 s.
12:42Z Read both nodes. Observation: both Witness.lean files still carry the `-- hole: h_small_n` / `-- hole: h_sieve` line, although the guide says the node is "born with the file less its `-- hole:` line" (AGENTS.md ~l.1275, 1313). Both slots are `theorem witness : True := trivial`, which is the right type here (statements start with ∃, no top-level hypotheses).
12:44Z get_precheck tutorial -> done/pass (poll call took 69.9 s).
12:44Z get_token (MCP) -> 201, pseudonym t1009-a, identity 01M4GB3SD04QW150Y9Y8XA616X, 1.0 s. Token kept in session scratchpad (0600), not in evidence.
12:46Z claim_node erdos-1094--h3--h1 ttl 2 -> 201 claim 01M4GB76S0XM1C4VWJMH27NEVT, 2.5 s.
12:46Z Numerics (A/numerics1.py, numerics2.py): primes in (k/2,k] alone fail sporadically over the whole n range for k≤150 (no elementary n-range). Parity split: for k≤500, 0 failures with k odd & n even (p=2), even-k last failure (1579,58), odd/odd last (1469,39).
12:47Z check_lean (mode check, node erdos-1094--h3--h1) on 2-hole skeleton (A/skeleton.lean): 1.6 s, result.okay true, only sorry; okay=false with lint sorry-present as documented.
12:48Z submit_informal_annex with steps h_keven,h_odd -> 201, PR #462, hash 094494042f14…, **40.4 s**.
12:48Z precheck_submission (partial + 2 carried witnesses, citing annex 094494…) -> 409 products-pending, retry_after 240, **36.5 s** for a refusal. PR #462 merged 12:48:58Z (under a minute after opening).
12:49Z check_lean witness mode with a not-yet-node statement (hole_keven) and `True` witness -> okay true, expected True, given True, matches, 2.7 s.
12:52Z precheck_submission retried -> 202 job 01M4GBH730HT9SCN1Y5EQG5GBC (graph_commit da1f411e), 23.9 s.
12:53Z submit_postmortem on erdos-1094--h3--h1 (route: range split via Bertrand, blocked/missing-library) -> 201 PR #466, 42.7 s.
12:54Z Latency probe: curl /health x3: connect 0.15 s, 0.15 s, **35.2 s**. The 20-110 s call times are this laptop's TCP connect (lost SYN/retransmit), environment, not the service. get_precheck poll took 68.3 s for the same reason.
12:56Z get_precheck -> done, verdict pass (steps 1,2,4-8 pass). holes: h_keven, h_odd, expected_witness True, both carried witnesses checked:true, proved_binders [].
12:56Z submit_proof (artifact_type partial, precheck_job_id, tooling) -> 201 PR #468, submission 01M4GBRR9RXKGT8FYDN797VK5Q, 4.5 s.
12:57Z propose_literature on erdos-1094--h3: status known (Konyagin 1999 via erdosproblems.com/1095; inference g(k)>k² eventually is mine, flagged) -> 201 PR #469, 4.7 s.
12:57Z get_submission 468 -> state open, waiting_on gate, queue: {"position": null, "of": 1, "ahead": []} -- position null while "of" is 1 (watch).
13:00Z PR #469 (literature) merged 13:00:01Z. #468 re-gated after B's #467 merged on the same target (queue showed position 2 of 3 -> merge 1 of 2 -> gate 1 of 1).
13:11Z PR #468 (skeleton) MERGED 13:11Z (opened 12:56Z; ~15 min incl. one re-gate). get_submission -> merged, waiting_on products, attestation_note attestation-pending.
13:17Z get_node erdos-1094--h3--h1--h1 / --h2: exist, ready, origin skeleton-hole, carried witnesses written as Witness.lean WITHOUT the `-- hole:` line (as the guide says). Node appeared ~6 min after merge (13:11 -> 13:17); get_node answered node-unknown with a clear "post-merge job" message meanwhile.
13:18Z submit_gloss on --h3--h1--h1 -> PR #475; on --h3--h1--h2 -> PR #476 (5-6 s each). Both merged 13:18:40Z/13:18:44Z.
13:19Z list_frontier: both new holes ready/needs proof/claimable; --h3 shows literature_proposed. get_submission 468: merged, attestations/000468.json. list_my_claims (68 s, env) shows my claim; release_claim -> 200 released 13:19:26Z.
13:19Z Site https://openproofnetwork.org/problems/erdos-1094/ (200) lists both new hole ids.

## Handoff

Landed (all through the MCP, pseudonym t1009-a):
- PR #462 annex on erdos-1094--h3--h1 (annex/v2, steps h_keven, h_odd; hash 094494042f14ef24ecf8b5aa0d9b122ec0e066058d1cc7b4cef3be7b5e912a3c): parity split + why no range-of-n split falls out of Bertrand. Merged 12:48:58Z.
- PR #466 postmortem on erdos-1094--h3--h1: range split via primes in (k/2,k] + Bertrand, outcome blocked / missing-library (needs primes in short intervals). Merged 12:53:52Z.
- PR #468 partial (skeleton) on erdos-1094--h3--h1, citing the annex, two carried `True` witnesses. Proved assembly: K = max K₁ (max K₂ 1); p = 2 settles k odd & n even. Holes -> new nodes, both `ready`:
  - erdos-1094--h3--h1--h1 (h_keven): k even. Numerically K₁ = 58 (last failure (1579,58), k ≤ 500).
  - erdos-1094--h3--h1--h2 (h_odd): k odd, n odd. Numerically K₂ = 39 (last failure (1469,39), k ≤ 500).
  Neither hole alone implies the parent (each leaves the other parity class); both are implied by the parent. Merged 13:11Z, attestation 000468.
- PR #469 literature proposal on erdos-1094--h3: `known` (Konyagin 1999, g(k) ≫ exp(c log² k) ⇒ g(k) > k² eventually; inference flagged as mine, papers not read; explicitly NOT covering --h3--h1). Awaiting steward/curator confirmation. Merged 13:00:01Z.
- PR #475, #476 statement glosses on the two new holes. Merged 13:18Z.
- Claim on erdos-1094--h3--h1 taken 12:46Z, released 13:19Z.

Ready but unsent: nothing. Open PRs of mine: none.
Honest assessment: the progress is small. The p = 2 class is the only elementary piece I found; the two holes are still the analytic core (equidistribution of n/p mod 1). The annex and postmortem record why a range split is blocked on short-interval primes.

## BUGS

Network bugs:

A1 (MINOR, reproduced once, not re-probed) — `get_submission` queue block for a just-opened PR says `position: null` beside `of: 1`, `ahead: []` and `stale: false`.
  Repro: submit_proof (partial) on erdos-1094--h3--h1 at 12:56Z (PR #468), then get_submission {"submission_id":"468"} at 12:57:07Z.
  Expected: a position (PR #468 was open, waiting_on gate), or `stale: true` / a note saying the listing predates the PR.
  Actual: `"queue": {"position": null, "of": 1, "ahead": [], "read_at": "2026-10-09T12:56:08Z", "stale": false}`, `pull_request.read_at` 12:57:07Z, waiting_on `gate`. The queue listing was read at 12:56:08Z, before the PR existed, but is marked not stale. A minute later (12:57:42Z) it read position 2 of 3. Evidence: A/s468-1257.json.

A2 (MINOR, observed on two older nodes; new nodes correct) — Witness.lean of the 2026-10-08 holes keeps the `-- hole:` line.
  Repro: get_node erdos-1094--h3 and erdos-1094--h3--h1 (12:41Z). `files["Witness.lean"]` begins `-- hole: h_small_n` / `-- hole: h_sieve`, then `theorem witness : True := trivial`.
  Expected (guide ~l.1275 and l.1313): the hole's node is born with the carried file "less its `-- hole:` line".
  Actual: the line is still there on those two nodes. My own holes created today (--h3--h1--h1/--h2) do not have it, so this looks like a legacy of an older writer (or a carried-witness path that has since been fixed). Harmless to step 7 (witness passes) but the file is not what the guide says. Evidence: A/node-erdos-1094--h3.json, A/node-erdos-1094--h3--h1.json.

Environment problems (not the network):

A3 (env) — Intermittent 20-110 s call latency from this laptop: get_node 113.3 s (12:41Z), submit_informal_annex 40.4 s, precheck refusal 36.5 s, submit_postmortem 42.7 s, get_precheck 68.3 s, list_my_claims 68.2 s. `curl -w` on /health x3 at 12:54Z: connect 0.149 s, 0.150 s, **35.17 s**; time is spent in TCP connect, i.e. the laptop's path (known lost-SYN pattern), not the service.
A4 (env) — `timeout` and `sympy` not installed on the laptop; wrote a plain sieve instead. No impact.

Doc mismatches in the guide: none blocking. Every documented step I used (tutorial precheck -> get_token, claim, check_lean check/witness, annex with steps, products-pending retry, partial with carried witnesses, submit_proof, get_submission waiting_on/attestation, release_claim) behaved as written. Note A2 above is the one place the record and the guide disagree.

## FEATURES

F1 — No way to wait for "products rendered for node X" except polling get_node until node-unknown stops (took ~6 min after merge; ~3.5 min for the annex). A `get_submission` field such as `products_rendered_at` / the commit that carries the new nodes, or the new hole ids on a merged partial's record, would let an agent go straight to the children.
F2 — The precheck `products-pending` refusal gives retry_after 240 for an annex that merged within a minute of opening; it was accurate (retry at +3.5 min worked), but a refusal costs a full round trip each time. A precheck that queues until the products are rendered (opt-in) would save the loop.
F3 — A partial's receipt does not say which node ids its holes will become; I inferred `--h1`/`--h2` from the guide. The precheck `holes` list has `name` but no future `node_id`.
F4 — MCP tool output is the full document; `get_node` with all prose is large (31 kB for --h3). `include: []` helps; documenting it near get_node's first mention (not only in the appendix) would save tokens for a first-time agent.
F5 — No elementary content is offered by the target for the residue core; a `missing_lemmas` signal (short-interval primes) from my postmortem is recorded but nothing aggregates such requests across nodes.
13:20Z Token and tutorial nonce file deleted from scratchpad.
