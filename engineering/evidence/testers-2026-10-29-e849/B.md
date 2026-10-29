# B — the nine (k,l) pairs (t1029e-b), 2026-10-29

## Log

- 13:09Z started. Read BRIEF, prior README + board, guide sections (tutorial, check, skeleton, carried witnesses, MCP appendix). Graph cloned to my scratch. MCP helper in scratch. Tutorial precheck 01M63WDF4R3MM78X05ES4DHTKC running (anonymous, for the token).
- 13:09Z read the nine pair holes --h2--h1--h1--h1..--h9 on main (statements as on prior board 12:48Z). No local pari/sage; curve identification will go through LMFDB pages.
- 13:15Z token minted (pseudonym t1029e-b). Claims: --h1 01M63WSPR051Z997Z7RCDW493E, --h6 01M63WSRPG8S3J903HFS1PVQQG (ttl 4h).
- 13:15Z LMFDB checked: 37.a1 integral points (10) and 1611.a1 (jump [0,0,-9,-9,0] → 1611.a1, 22 points). Both partials fast-checked (result.okay true, only sorry warning): B/partial-h6-pair34-37a1.lean, B/partial-h1-pair23-1611a1.lean. Plan posted on board.
- 13:17Z prechecks: (3,4) on --h6 job 01M63WWX98VDYWWN7KS0HNJ596 (witness carried, B/partial-h6.1.witness); (2,3) on --h1 job below (B/partial-h1.1.witness).
- 13:17Z (2,3) precheck job 01M63WX908TTV22C57KER4N6VD.
- 13:22Z SUBMITTED #1168 (submission 01M63X71G8AJDA8QEMPE7BB4R4), partial (2,3) on --h1, hole h_1611a1 → expected --h2--h1--h1--h1--h1. Also: (4,6) and (2,6) models computed — (4,6): X=30w,Y=900U on [0,300,0,21600,810000] reduces (u=2) to [0,75,1,1350,12656] ≅ LMFDB 232425.a1 [0,0,1,-525,10156] (rank 3, 42 pts); x_red = 15w/2+25, y_red = (225U−1)/2, w=m(m−5), U=n²−3n+1. (2,6): [0,900,0,194400,65610000] → u=6 → LMFDB 14475.a1 [0,1,1,-58,1294] (rank 2, 24 pts); x_red = 5w/2+8, y_red = 75n−38; (78,14) ↦ (323,5812) ✓. LMFDB point lists verified by python (each satisfies the equation; brute search |x| ≤ 3e6 finds no other).
- 14:40Z SUBMITTED #1171 (submission 01M641NYR07TNVCT5NQEE7P5GW), (3,4) on --h6. Next: (2,6) on --h4 fast-checking (B/partial-h4-pair26-14475a1.lean when it compiles).
- 14:45Z #1168 merged 13:43:59Z (attestation 001168, gate run 40883958701). #1171 merged 14:44:44Z, attestation-pending.
- 14:45Z Session suspended ~13:23Z → 14:40Z (wall clock jumped 78 min while a background check_lean on p26 hung; nothing returned). Lost ~75 min. Environment, not the service (laptop sleep per prior lessons).
- 14:45Z (2,6) on --h4: fast check timed out (504, 20 s) until I cleared the nonlinear hypotheses before 48-way rcases; then compiles (result.okay true). Precheck 01M641WXD021D17A0M7J9CFPHZ. Claims --h4 01M641YAAG6V3HJ12TBNKJCBMY, --h8 01M641YC90A8X9QV26BVMTEE3P.
- 14:49Z SUBMITTED #1175 (2,6) on --h4, hole → --h2--h1--h1--h4--h1. Lean B/partial-h4-pair26-14475a1.lean.
- 14:53Z (4,6) on --h8: V,W substitution (n(n-3)=2V, m(m-5)=2W via Nat.even_mul_succ_self) avoids parity case splits; algebra in private helper e849b_pair46. Whole file times out the 20 s fast check (504); helper alone and main alone (helper sorried) both compile. Precheck refused 409 products-pending (graph 187981e1 changed nodes after 4f771bb8) — retrying. Lean B/partial-h8-pair46-232425a1.lean.
- 15:01Z FINDING candidate: #1171 merged 14:44:43Z, no bot commit/attestation/hole node at 15:00Z while later #1172 got 'gate: #1172 pass' 15:00:27Z. get_submission 1171: waiting_on products, attestation-pending. (4,6) precheck refused 409 products-pending repeatedly 14:53–15:00Z (retry loop). Drafts ready: literature x4 (B/literature-drafts/), postmortems x4 (B/postmortem-drafts/), explainer for #1168 (dry-run ok, hash 0e0877d3…).
- 15:01Z (4,6) precheck accepted: job 01M642WP080KM50VHXGMGBAWNX.

## Findings

- **F-B1 [bug, corroborated by C] A partial's post-merge job died on one GitHub 503 and nothing retried.** #1171 (partial, --h2--h1--h1--h6) merged 14:44:43Z; C read its post-merge run 40894548804: step "Fetch the merged pull request's body…" got `gh: HTTP 503` and exited 1 after 42 s. At 15:01Z: no `attestations/001171.json`, no node `--h2--h1--h1--h6--h1` on main, `get_submission 1171` = `waiting_on: products`, `attestation_note: attestation-pending`; the later #1172 got `gate: #1172 pass` at 15:00:27Z and did not catch #1171 up. Expected: a transient API error retried, or the next post-merge job replaying the unattested merge (prior finding #1's "its merges are replayed"). Cost: the hole cannot be glossed, audited or given a literature record; my appends for it wait. Repro: read run 40894548804's log.
- **F-B7 [bug, still present, prior #1] A partial's attestation push is still starved by appends merging in the same lane.** #1179 merged 15:30:39Z; its post-merge run 40902300897 reached "Commit the attestation and the products" at 15:39:02Z and was refused `! [rejected] HEAD -> main (fetch first)` six times at ~77 s intervals (15:39:04Z, 15:40:21Z, 15:41:38Z, 15:42:55Z, 15:44:12Z, 15:45:29Z) while appends (#1211, #1212, #1213 …) merged; conclusion failure, replay dispatched as run 40904999533 at 15:46:47Z. #1175 (merged 15:20:17Z) took 15 min for the same reason (seven appends merged behind it). Filing appends in a "quiet window" does not help: the actor merges them minutes later, possibly under the next partial (C's F-C6). Cost: every hole of mine waited 15–30 min before it could get words; my final batch of words is squeezed against 16:00Z.
- **F-B2 [feature/docs] The 20 s fast check cannot check a partial whose assembly has a long case split, so the first whole-file check is a precheck.** (2,6) on --h4 and (4,6) on --h8: `check_lean` mode check answered `504 check-timeout` (14:42Z, 14:52Z; log ids in B/*.res.json); the helper alone and the main theorem alone (helper `sorry`ed) each compile in time. The guide says to use helpers to stay under the heartbeat cap, but the 20 s wall budget is per check, not per declaration. Asking: a longer budget for authenticated checks, or a mode that checks declarations one at a time. Cost ~15 min of rewriting to make (2,6) fit (clearing the nonlinear hypotheses before a 48-way `rcases` brought it under 20 s).
- **F-B3 [bug, still present, prior #2] `409 products-pending` held the (4,6) precheck 8 minutes** (14:53Z–15:01:46Z, retry loop every ~60 s; message names graph 187981e1 "changed erdos-849's nodes after 4f771bb8"), while other agents' merges kept arriving.
- **F-B4 [docs, still present, prior C F-C2]** `le_or_lt` is an unknown identifier at the pinned Mathlib (use `le_or_gt`); found by fast check 14:50Z.
- **F-B6 [bug] A replayed post-merge job writes no outline, so the merged partial can never get a step-anchored explainer.** #1171's replay ('gate: #1171 pass (replayed)', 15:12:06Z) wrote the attestation and the hole, but no `targets/erdos-849/outlines/5e41d7ba….json` (sha256 of the partial file); at 15:21Z `list_words_needed` still lists that path as the row's `outline`, and `submit_gloss` (kind proof, dry_run) answers `400 explainer-step-unknown … has no outline to name steps of (F20-R4)`. Expected: the replay renders the outline like a first-time job, or the list does not name a file that does not exist. Workaround: an explainer whose sections name no steps. Repro: `submit_gloss` dry run on node variant-3969f1f7--h2--h1--h1--h6 with proof 5e41d7ba… and any `{steps: …}` heading.
- **F-B5 [environment, not the service]** My session was suspended ~13:23Z–14:40Z (wall clock jumped 78 min during one background `check_lean`; A and C report the same window as a laptop network outage). Lost ~75 min.
- 15:06Z SUBMITTED #1179 (4,6) on --h8, hole → --h2--h1--h1--h8--h1.
- 15:12Z 'gate: #1171 pass (replayed)' 15:12:06Z (27 min after merge; F-B1 resolved by replay).
- 15:18Z appends: literature #1186 (1611.a1 hole), #1188 (37.a1 hole), explainer #1193 (#1168), postmortems #1195 (--h1), #1197 (--h6). #1171 outline 5e41d7ba… not on main at 15:17Z though gate: #1171 pass landed 15:12Z.
- 15:20Z #1175 merged 15:20:17Z; appends #1194/#1196/#1201 merged right after it in the same batch (merge actor). Watching whether its bot commit is delayed.
- 15:21Z #1171 explainer dry-run refused 400 explainer-step-unknown: "attempts/20261029T131800Z-t1029e-b-partial.lean … has no outline to name steps of (F20-R4)". The replayed post-merge job (gate: #1171 pass (replayed), 15:12:06Z) wrote no outline; list_words_needed still names outlines/5e41d7ba….json as the outline, which is not on main.
- 15:28Z #1175 post-merge run 40900531703 in_progress 9 min; 7+ appends merged under it (#1194,#1196,#1201-#1206,#1208).
- 15:32Z #1179 merged 15:30:39Z.
- 15:35Z gate: #1175 pass 15:35:09Z.
- 15:57Z STOPPED submissions. #1179's replay (run 40904999533) still in progress, #1180 (A) merged 15:47Z without bot commit: not quiet, so the last seven appends were not filed; they are in B/final-batch/ for the lead. Claims released (4).

## Final report

### 1. Landed

| PR | kind | node | state |
|---|---|---|---|
| #1168 | partial (2,3): hole `h_1611a1` = integral points of LMFDB 1611.a1 → `--h2--h1--h1--h1--h1` | `variant-3969f1f7--h2--h1--h1--h1` | merged 13:43Z, attested 13:52Z, hole audited clean (C) |
| #1171 | partial (3,4): hole `h_37a1` = integral points of LMFDB 37.a1 → `--h2--h1--h1--h6--h1` | `--h2--h1--h1--h6` | merged 14:44Z, attested by replay 15:12Z, audited clean (C) |
| #1175 | partial (2,6): hole `h_14475a1` = integral points of LMFDB 14475.a1 → `--h2--h1--h1--h4--h1` | `--h2--h1--h1--h4` | merged 15:20Z, attested 15:35Z, audited clean (C) |
| #1179 | partial (4,6): hole `h_232425a1` = integral points of LMFDB 232425.a1 → `--h2--h1--h1--h8--h1` | `--h2--h1--h1--h8` | merged 15:30Z; post-merge push refused 6×, replay run 40904999533 in progress at 15:57Z |
| #1186, #1188 | literature (known) | `--h1--h1` (1611.a1), `--h6--h1` (37.a1) | merged (gate 15:48Z) |
| #1193 | explainer of #1168's assembly | `--h2--h1--h1--h1` | merged |
| #1195, #1197 | postmortems | `--h2--h1--h1--h1`, `--h2--h1--h1--h6` | merged |

Net effect: four of the nine solved pairs ((2,3), (3,4), (2,6), (4,6)) are now proved in Lean *modulo one statement each*: the list of integral points of one named minimal Weierstrass model (LMFDB label, Cremona label), which Sage/Magma `integral_points()` recomputes in seconds. The binomial algebra (falling factorials, the change of variables, the case analysis on the listed points) is kernel-checked. Each point list was checked in Python (every point on the curve; no other point with |x| ≤ 3·10⁶) and independently by C.

### 2. Unfinished business for the lead

All files are MCP argument JSON in `B/final-batch/`, each dry-run clean where a dry run exists:
- `propose_literature` `14475.a1.json` (node `--h2--h1--h1--h4--h1`, on main now) and `232425.a1.json` (node `--h2--h1--h1--h8--h1`, after #1179's replay writes it).
- `submit_postmortem` `14475.a1.req.json` (node `--h2--h1--h1--h4`) and `232425.a1.req.json` (node `--h2--h1--h1--h8`).
- `submit_gloss` `ex1175r.json` (explainer of #1175, step-anchored to outline f0b21037…), `ex1171r.json` (explainer of #1171, sections unanchored because its replay wrote no outline, F-B6), `ex1179r.json` (explainer of #1179, unanchored; re-anchor to steps if `outlines/fcb0b80f….json` appears after the replay).
- Waits on: `gate: #1179 pass (replayed)` and `gate: #1180 pass`, then a quiet window.
- Not done, and why: pairs (2,4), (2,8), (4,8) are quartic (genus-1, not Weierstrass) models; Stroeker–de Weger, Math. Comp. 68 (1999) Table 1 gives the transformations, and neither ams.org nor matwbn would serve a PDF here, so no exactly sourced curve statement could be written. (2,5) and (3,6) were taken by A.

### 3. Findings (most important first; details in ## Findings above)

1. F-B7 (prior #1, still present): partial attestation pushes starved by append merges — #1179 refused 6× and replayed; #1175 delayed 15 min; "quiet-window" filing does not make the merge quiet.
2. F-B1 (with C): #1171's post-merge job died on one GitHub 503 with no retry; attested only by replay 27 min later.
3. F-B6: a replayed post-merge job writes no outline, so the merged partial can never get a step-anchored explainer, while `list_words_needed` names the missing outline file.
4. F-B2: the 20 s fast-check budget cannot check a whole partial with a long case split, though each declaration fits; first whole-file check is a precheck.
5. F-B3 (prior #2): `409 products-pending` held a precheck 8 min.
6. F-B4 (prior): `le_or_lt` renamed to `le_or_gt` at the pin, undocumented.
7. F-B5 (environment): session suspended 13:23–14:40Z.

### 4. What would have made me twice as productive

Half of my working time after the outage was waiting on the merge lane rather than on mathematics: every partial waited 15–30 minutes for its bot commit, and the words for each hole could only be filed after that, then waited again behind other appends. A post-merge push that rebases until it lands (or a lane that holds appends while a partial's job runs) would have given me every hole on main within minutes of its merge and let me finish the words inside the window. Second, a fast check with a per-declaration or longer budget would have saved two rewrites of the (2,6)/(4,6) assemblies. Third, access to Stroeker–de Weger's Math. Comp. paper (its Table 1) would have let me do the three quartic pairs the same way.
