# C (t1018-c) log — Aristotle-first

- 19:20Z cloned graph to C/graph; MCP client C/mcp.py (token in C/token.txt, chmod 600 — do not commit).
- 19:23Z tutorial precheck 01M587B1RGXB1J2B7DEPWKTGQ1 pass; token minted (201) as t1018-c.
- 19:25Z claimed erdos-1094--h3--h2--h1 (claim 01M587K8ERBECHQZBATKPRTNSB, ttl 2h).
- 19:25Z opn-prove run --preset aristotle on it: REFUSED project-limit (exit 0 from CLI; opn-prove exit 1) while only ONE project (D's abd1d0b0) was RUNNING on the account. Receipt C/r/ar-refused-1925.json, list C/r/ar-list-1926.txt.
- 19:27Z retry refused again; aristotle list --status shows only abd1d0b0 RUNNING (r/ar-list-1927.txt). Limit is effectively 1. Posted to board. Working EES by hand meanwhile.
- 19:28Z partial p1/partial.lean (c:=min c 1/2; n≥k² case proved; hole h_lt = same with n<k*k). fast check: no errors, only sorry lint (r/check-p1-b.json). precheck job 01M587SASGRSD401AFN4N44VTZ.
- 19:38Z precheck 01M587SASGRSD401AFN4N44VTZ PASS (all steps; hole h_lt expected node erdos-1094--h3--h2--h1--h1, expected_witness True). One SSL handshake timeout on get_precheck polling (laptop path).
- 19:38Z submit_proof called; MCP call still not answered after >2 min (urllib timeout 300s).
- 19:40Z Aristotle project 9e8d9ab2-ad63-44b6-80bc-5cdcfa923fcb on h_lt (custom Problem.lean in hlt/proj via --project).
- 19:44Z first submit_proof died on client-side SSL handshake timeout (nothing reached service: get_my_submissions empty). Retry 19:45Z: 201, submission 01M588QBQG0N4P22NMRMKZ2RM5, PR #762 (partial, hole h_lt -> erdos-1094--h3--h2--h1--h1). Receipt r/sub-p1.json.
- 19:58Z PR #762 gate passed, waiting_on=merge. Aristotle 9e8d9ab2 still running (18 min; trying Chebyshev/Selberg sieve in Mathlib, compiling locally on v4.28.0).
- 20:05Z Aristotle 9e8d9ab2 COMPLETE_WITH_ERRORS after 24 min. Its ARISTOTLE_SUMMARY.md says Problem.lean holds a full proof of h_lt modulo one `have hoheisel` (primes in (x, x+x^θ], θ<1), with Lucas-based divisibility and window j=⌊2n/k⌋-1. BUT the downloaded archive's Problem.lean is byte-identical to what was sent (22 lines, original sorry) — both via opn-prove's download and a fresh `aristotle download`. opn-prove correctly reports answered:false. The proof text is lost. Receipts r/aristotle-9e8d9ab2-summary.md, r/aristotle-9e8d9ab2-run.json, hlt/dl2/.
- 20:07–20:17Z PR #762 never merged: waiting_on alternated merge / branch-update every 1–2 min (r/pr762-watch.txt), gate green since ~19:58Z.

## FINAL REPORT (C, t1018-c)

**1. Outcome**
- PR #762 — partial on `erdos-1094--h3--h2--h1` (h_ees). Assembly proves the n ≥ k² range outright (c' = min c ½, k^{3/2} < k² ≤ n); one hole `h_lt` = the same statement with `n < k*k` (planned node `--h3--h2--h1--h1`, witness `True`). Precheck 01M587SASGRSD401AFN4N44VTZ PASS, gate green; **still OPEN at 20:17Z** (merge queue).
- PR #769 — postmortem on `--h3--h2--h1` (reduction-to-known / exhausted / missing-library), recording Aristotle's reduction of h_lt to Hoheisel's theorem.
- Aristotle project 9e8d9ab2 on h_lt: COMPLETE_WITH_ERRORS. The summary describes a full proof modulo Hoheisel, but the file it returned was not changed.

**2. Bugs**
- B1 (Aristotle, opn-prove preset): the result archive does not contain the work the summary describes. Steps: `opn_prove.py run --preset aristotle --project hlt/proj ...`. In `ARISTOTLE_SUMMARY.md` Aristotle says "Problem.lean now contains a complete proof of h_lt except for one sorry … committed and pushed", but the archive's `Problem.lean` is byte-identical to the input (22 lines, bare `sorry`). A fresh `aristotle download 9e8d9ab2-…` gives the same file (`cmp` SAME; hlt/out vs hlt/dl2). opn-prove correctly records `answered: false`. Expected: the filled file, or no claim that one exists. Actual: 24 minutes of output lost. Receipts: r/aristotle-9e8d9ab2-summary.md, r/aristotle-9e8d9ab2-run.json, hlt/dl2/. (Possibly Aristotle-side; worth reporting to Harmonic. opn-prove could say so: "summary claims edits but file unchanged".)
- B2 (Aristotle concurrency): the brief said about 4 slots. The account refused `too many projects in progress` while `aristotle list --status RUNNING` showed exactly one project (D's abd1d0b0). This happened twice, at 19:25Z and 19:25:47Z (r/ar-refused-1925.json, r/ar-list-1927.txt). The effective limit is 1. The CLI exits 0 (documented); opn-prove maps it to `refused: project-limit` (good).
- B3 (merge queue, network): PR #762's gate was green by about 19:58Z, yet at 20:17Z it was still open. `get_submission` `pull_request.waiting_on` flipped between `merge` and `branch-update` about every 1–2 minutes for 20+ minutes (r/pr762-watch.txt). The hole node, and so any follow-up on it inside the hour, was never available. Expected: merged within a few rounds. Likely cause: other agents' merges keep making it BEHIND. Not verified as a defect; it may be queue throughput.
- B4 (environment, minor): two MCP calls (get_precheck poll, then submit_proof) died on a client-side TLS handshake timeout (`_ssl.c:1063`) while a curl straight after showed connect 0.16 s and tls 0.33 s. The submit had not reached the service (get_my_submissions was empty), and the retry gave 201. This is the known laptop path, not the service.

**3. Feature requests**
- F1: a partial on a hole that does not exist yet (or a "stacked" partial bound to a pending PR's planned `expected_node_id`). Aristotle's reduction arrived 20 minutes after my partial was submitted. Because #762 had not merged, I could not file the next step on h_lt within the hour.
- F2: opn-prove should detect "summary says edited, file unchanged" and keep the summary prominently in the run record (it does keep it). It could also try `aristotle download` again automatically.
- F3: the board brief, or `get_hosted_checkers`, should publish the real Aristotle concurrency limit.

**4. Biggest time costs**
- Waiting on Aristotle: one 24-minute run with nothing usable, and about 15 minutes blocked on the slot before that.
- Waiting on the merge queue: #762 green but open for over 20 minutes.
