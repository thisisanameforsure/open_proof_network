# B (t1018-b) log
- 19:20Z cloned graph into B/graph, read guide sections, built B/bin/mcp.py (JSON-RPC client)
- 19:22Z tutorial precheck job 01M587DDY0NM5CB4SHKQWA61Q9 (anonymous) for token
- 19:25Z token earned for t1018-b (stored B/.token, mode 600)
- 19:26Z claimed erdos-1094--h2--h1--h4--h1--h2 (claim 01M587MBKRFPJDC200KY8MXY8Z)
- 19:28Z partial (gcd=k closed, hole h_proper: gcd<k) check_lean verify ok bar sorry (log 01M587NBV0DG1RH0Y76R68BWDJ); first precheck refused 400 partial-unlabelled (claim line had text after $…$); precheck job 01M587REF8YSQSEW84TQMP4DJB
- 19:31Z precheck 01M587REF8YSQSEW84TQMP4DJB PASS (hole h_proper -> expected erdos-1094--h2--h1--h4--h1--h2--h1, expected_witness True); 19:32Z re-precheck with carried witness: job 01M587ZQW05G4QZT6R3HKDJNVV
- 19:36Z precheck 01M587ZQW05G4QZT6R3HKDJNVV PASS with carried witness checked; 19:37Z submitted partial: submission 01M5887WKR5GQ4C9DKPWQKRM1Q, graph PR #757 (receipt B/submit1.json). Search (B/search.py): up to k=400 the only (n,k) meeting all of the hole's hypotheses is (62,6); k≤1500 running
- 19:38Z postmortem submitted on erdos-1094--h2--h1--h4--h1--h2: id 01M588ADNGFKBEEKVD18TPTJ5T, PR #758 (B/pm1.yaml, B/pm1-receipt.json). Stats B/stats300.txt
- 19:39Z search k<=1500: only (62,6) meets all hole hypotheses (B/search1500.txt)
- 19:41Z PR #757 MERGED by merge actor (gate success), waiting_on products
- 19:46Z postmortem PR #758 merged
- 19:49Z hole node erdos-1094--h2--h1--h4--h1--h2--h1 on the frontier (ready), `became` filled 8 min after merge; claim released 19:49Z

## FINAL REPORT (t1018-b)

### 1. Outcome
- Node `erdos-1094--h2--h1--h4--h1--h2` (case n/gcd(n,k) prime, gcd ≥ 2): **partial merged**, graph PR #757
  (submission 01M5887WKR5GQ4C9DKPWQKRM1Q, precheck 01M587ZQW05G4QZT6R3HKDJNVV with carried witness `True`), merged by
  the actor ~19:41Z, no human. The case gcd(n,k)=k is proved in the assembly (it forces k | n, n/k = k prime, so
  k² | k!, i.e. k | (k-1)!, impossible). New hole node `erdos-1094--h2--h1--h4--h1--h2--h1` (adds gcd(n,k) < k), ready.
- Postmortem on the same node, PR #758, merged (id 01M588ADNGFKBEEKVD18TPTJ5T): the proper-gcd case carries the whole
  Kummer/ELS difficulty. Exact search (B/search.py, B/stats.py): for k ≤ 1500 the only (n,k) meeting every hypothesis
  of the hole is (62,6); for k ≤ 300, of 148814 structural candidates only 8 have no carry for all p ≤ k.
- No full proof of any node.

### 2. Bugs
None that I can evidence as a network defect. Observations checked and *not* bugs:
- One `get_submission` call took 68 s (two neighbours 1.0 s); `curl -w %{time_connect}` to /health right after was
  0.16 s. Matches the known laptop SYN-retransmission path (log 2026-09-21), not the service.
- `check_lean` lint `header-diverges` at line 3 on my first draft was correct (I had dropped the blank line after the
  imports when copying the header by hand).
- Parent stays `ready`/claimable after the partial merged; I believe this is by design (a merged partial is not a proof),
  but a reader might expect it to show "decomposed, waiting on hole".

### 3. Feature requests
- `partial-unlabelled` / `claim-form`: my claim line was `-- claim: $\gcd(n,k) < k$ added to …` and the refusal said only
  that the line "is not `$…$` with something inside". Saying "trailing text after the closing `$`; move it to a prose
  comment line" would have saved one round trip (receipt: B/precheck1.json was overwritten; the 400 body is quoted in B.md 19:28Z).
- A precheck that only re-checks carried witness files (or a check_lean witness mode against an *unborn* hole by
  partial + hole name) would remove the second ~4 min full precheck needed just to attach `True` as a witness.
- Products lag: hole node appeared 8 min after merge (`waiting_on: products`); a `get_submission` field with the
  queue position of the render would help planning a follow-up partial inside a one-hour window.

### 4. What cost the most time
Mathematics, not tooling: looking for an elementary contradiction in the proper-gcd case (none; the computation shows
the difficulty is the no-carry condition for p ≤ k). Tooling: two full prechecks (~4 min each) and the 8-minute products
wait after the merge.
