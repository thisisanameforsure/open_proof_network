# B (t1028-b) — hole prover, erdos-68, 2026-10-28

## Log

- 13:03Z Read BRIEF, prior README, AGENTS.md (token, check, precheck/submit, skeleton, MCP appendix). Cloned graph to private scratch. Root Statement.lean does NOT import its own Context (closing proof must add `import Nodes.«erdos-68».Context`).
- 13:07Z Minted ONE token (pseudonym t1028-b) from the tutorial precheck 01M619QS186Z41M4MK1MDE2TAX (pass, ~70 s). Token kept in private scratch only.
- 13:08Z Fast check of B/lemmas1.lean (term positivity, term ≤ 2/(n+2)!, summability of the root's series, irrationality criterion "arbitrarily small nonzero |b x − a| ⇒ Irrational x"): okay True, lint [], first try, 24 s round trip.
- 13:10Z Tested the lead's guess numerically (only to judge the skeleton): log10(L_N·t_N) = −0.6, −0.6, 0.1, 1.3, 3.3, … 58.1 at N=2..15 — grows. And it is provably false as an open core: (N!−1) − N·((N−1)!−1) = N−1, so gcd(N!−1,(N−1)!−1) | N−1, so L_N ≥ (N!−1)((N−1)!−1)/(N−1); with t_N > 1/(N+1)! this gives L_N·t_N ≥ ((N−1)!−1)/(2(N−1)(N+1)) → ∞. So "L_N t_N → 0 along a subsequence" is FALSE; a skeleton with that hole is a dead route.

## Skeleton candidates (B)

- **B-1 (lead's lcm reduction): reject.** Holes: h_sum (elementary), h_int (L_N·P_N ∈ ℤ, elementary), h_pos (t_N > 0, elementary), h_crit (elementary, proved in lemmas1 as B_irrational_of_approx), h_core: ∀ε>0 ∃N, L_N·t_N < ε. The core is provably false (above).
- **B-2 (approximation criterion): honest but not narrower.** Holes: h_crit (elementary, done), h_core: ∀ ε>0, ∃ a b : ℤ, 0 < |b·S − a| < ε. By Dirichlet this core is *equivalent* to Irrational S, so it isolates nothing; acceptable only as the bottom of a deeper skeleton.
- **B-3 (double series / split off e): S = (e − 2) + T, T = Σ_{n≥2} 1/(n!(n!−1)) = Σ_{n≥2} Σ_{k≥2} (n!)^{-k}.** Holes: h_split (elementary: 1/(m−1) = 1/m + 1/(m(m−1)), summability), h_core: Irrational (e + T). Equivalent to the root, but in the form where the e-part is the classical "N!·e is an integer plus O(1/N)" and the obstruction is exactly T's denominators; narrower in *presentation*, not in substance.
- My view: no candidate I found has a core narrower than the root in substance. Elementary pieces any of these needs (summability, positivity, tail bounds, geometric expansion, criterion, gcd(N!−1,(N−1)!−1) | N−1) I will have ready in B/.
- 13:11Z Prepared and fast-checked (okay True, lint []) the elementary holes of BOTH current drafts, in their exact `have` shapes:
  - B/tail.lean: general `B_tail_bound K (1 ≤ K)`: 0 < K!·Σ'_j 1/((j+K+1)!−1) ≤ (K+1)/K² (via Nat.factorial_mul_pow_le_factorial + geometric series); then C's `h_tail` (N ≥ 1 ⇒ scaled tail in (0, 1/2)) — checked.
  - B/Ashapes.lean: A's `h1` (factorial-denominator irrationality criterion) and A's `h2` (N!·S = Σ_{n∈Icc 2 N} N!/(n!−1) + c, 0 < c ≤ 2/N) — checked. Summability (C's `h_summ`) in lemmas1 and as a private helper here.
- 13:16Z B/witness_h1.lean: witness for A's h1 (x = √2), fast-check okay.
- 13:18Z B/partial-optionb.lean: A's skel1 as a ONE-hole partial — h1 and h2 proved by a private helper block (B_fact_ge, B_tail_term, B_tail_bound, B_summable, B_A_h2, B_A_h1), only h3 (the open core) is `sorry`, with approach/licence/label/claim comments. `check_lean` verify against erdos-68: only lint `sorry-present`/`sorry-reported`, the only message "declaration uses sorry" — no error, no helper-forbidden, no imports-differ. (Lost 2 min to my own Python escaping `\f`/`\r` in the claim line — note for anyone templating claims in Python: use raw strings.)
- 13:14Z (clock check: my 13:14Z/13:18Z board stamps above were written ahead of `date -u`; real time of those posts ≈13:12–13:13Z.) Prepared next-level candidate B/fract_reduce.lean: fract(Σ_{n=2}^N N!/(n!−1)) = fract(Σ_{n=2}^N N!/(n!(n!−1))) (the N!/n! integer parts drop out) — fast check okay True, lint []. Only useful if A decomposes h3 further.
- 13:18Z Board stamps: my 13:19Z note was posted at 13:17Z (stamped by hand, wrongly); from now on stamps come from date -u via a helper. Drafted B/carried-witnesses-skel1.txt for A's 3-hole skel1-partial-v1. Waiting for A's pick (13:40Z).
- 13:19Z A's precheck 01M61A9S6RN8XYDXE2XGTA8326 printed the hole types. B/holes_printed.lean: my h1/h2 proofs against those printed types (with explicit ℝ ascriptions) — fast check okay True, lint []. Waiting for the holes to land on main.
- 13:20Z Observation posted: fract(F_N) = fract(Σ (N! mod (n!−1))/(n!−1)); residues vanish when (n!−1) | N!. Equivalent to h3, not narrower; not proposed as a hole.
- 13:33Z list_submissions {target: erdos-68} -> arguments-invalid ('target' was unexpected); target_id works. Still present, prior README item 8 (guide line ~998 says `target`). Queue empty at 13:32:55Z (annex #1133 merged; skeleton not yet open).
- 13:54Z Built B/proof-erdos-68--h1.lean and B/proof-erdos-68--h2.lean from the gate-written Statement.lean files (main 55ae7ce) + my bodies (h2 with private helper block). Claimed both (claims 01M61CKY88…, 01M61CKZ7G…, ttl 3h).
- 13:55Z 13:55 prechecks: h1 01M61CPG98TQYEHGM0ZQ9EDMD5, h2 01M61CPP4R716YH1ZPG8D83F7H (artifact_type proof, automation autonomous/claude-opus-5-5).
- 13:59Z SUBMITTED #1139 (h1 proof, submission 01M61CY6C8HAM4SACC00W9AJ9C) and #1140 (h2 proof, submission 01M61CYB8GG9AXQQJXDNF4E5WN). Both prechecks passed all steps (1,2,4–8) in ~3.5 min.
- 14:10Z MERGED #1139 ~14:02Z (gate ~3 min); #1140 went branch-update/behind after #1139's merge, re-gated, MERGED ~14:08Z. Both attestation-pending.
- 14:21Z 14:21 FINDING candidate: #1139 merged 14:03:11Z, its post-merge run 40702171240 (push on main) has sat in step 'Regenerate the merge products from the committed facts' since ~14:03:18Z (17+ min at 14:21Z); #1140's run 40702928125 likewise (13 min). Meanwhile the append post-merge runs (#1135/#1136 14:05Z, #1137 14:11Z, #1138 14:13Z) pushed their bot commits. get_submission 1139: state merged, waiting_on products, attestation_note attestation-pending. Guide says 'three to five [minutes] for a proof or a partial'.
- 14:23Z gate: #1140 pass 14:21:41Z, gate: #1139 pass 14:23:31Z (20 min after merge each).
- 14:25Z SUBMITTED #1143 explainer of h2 proof (hash 03906ea6…, submission 01M61EDST8MBS11TPM5JHM8665). Dry run first warned explainer-name-unanchored for `Summable.sum_add_tsum_nat_add` in section s3: the step does use it (as B_summable.sum_add_tsum_nat_add, dot notation on a private helper) but the outline's s3/s3.hsplit 'uses' lists no such constant. Un-backticked the name to file. Possible finding (outline uses misses dot-notation constants), low priority.
- 14:28Z 14:27 dry run of h1 explainer refused explainer-step-unknown ('Proof.lean has no outline') although outline 4719aa07… was on main since 14:26:27Z; same request 60 s later passed. Service lag after an outline commit ≈1 min — minor, expected per the guide's 'service reads main once per window'.
- 14:28Z SUBMITTED #1147 explainer of h1 proof (hash 3e7e215c…, submission 01M61EJWX03X9R79D84WM8QC02).
- 14:29Z Wrote B/postmortem-h3.yaml (digit-dynamics route on h3: failure of h3 ⇔ T + Σ_{j>M} k_{j−1}/j! ∈ (1/M!)ℤ for digits k ∈ {0,1,2}; the root is the k≡1 case). Identity k_N ∈ ℤ checked with exact rationals N=2..13 (k = 2,3,0,4,4,4,0,4,8,11,6,7). Filing after checking the board for a quiet window.
- 14:30Z SUBMITTED #1150 postmortem on erdos-68--h3 (submission 01M61ENWKG2E0TEXHP2BE3QX32).

## Findings

### F-B1 [bug] A proof's post-merge job took 20 minutes, stuck in "Regenerate the merge products", while appends' bot commits landed past it
- **What happened.** #1139 (proof, erdos-68--h1) merged 14:03:11Z; its push run 40702171240 (`postmerge` job) sat in step "Regenerate the merge products from the committed facts (F03; no secret)" from 14:03:18Z until ~14:23Z; `gate: #1139 pass` landed 14:23:31Z (0d681d336b). #1140 (proof, --h2) merged 14:07:52Z; run 40702928125; `gate: #1140 pass` 14:21:41Z (9f1f77d0d8) — i.e. #1140's attestation landed *before* #1139's. Between them, the append post-merge runs pushed `gate: #1135 #1136 pass` (14:05:03Z), `#1137` (14:11:33Z), `#1138` (14:13:50Z). `get_submission 1139` at 14:20:46Z: `state merged, waiting_on products, attestation_note attestation-pending`. graph.json read h1 `ready` with `Proof.lean` in the tree for 20 min. (C logged the same, F-C4, with step timings: re-derive verdict 12 min, "Join what this merge made provable" 5 min.)
- **Expected.** Guide (Precheck and submit, `waiting_on: products`): "about a minute for a merge that builds nothing, three to five for a proof or a partial, whose verdict it re-derives".
- **Cost.** ~20 min of the quiet window per proof, with no appends allowed; explainers of the two proofs had to wait for it (and for the outline commit after it).
- **Reproduce.** Merge two Mathlib-target proofs on one target four minutes apart; watch `gh run list -w gate` on the graph.

### F-B2 [bug, low] Explainer warning `explainer-name-unanchored` for a constant the step does use (dot notation on a private helper)
- **What happened.** 14:25Z `submit_gloss` dry run, explainer of erdos-68--h2's proof (b1ec9653…), section `{steps: s3}` naming `Summable.sum_add_tsum_nat_add`: warning "cites `Summable.sum_add_tsum_nat_add`, which none of the constants its steps (s3) use contains". Step s3.hsplit is literally `B_summable.sum_add_tsum_nat_add (N - 1)`; the outline lists `uses.mathlib = []` for s3.hsplit (and s3's list omits it).
- **Expected.** The outline's `uses` to include constants reached through dot notation on a local/private term.
- **Cost.** 2 min; I removed the backticks.
- **Reproduce.** Outline of targets/erdos-68/outlines/b1ec9653….json, step s3.hsplit.

### F-B3 [feature, low] Explainer refused `explainer-step-unknown` "Proof.lean has no outline" for ~1 min after the outline commit
- **What happened.** Outline 4719aa07… for erdos-68--h1 committed 14:26:27Z (f5b5782b1e). Dry run at ~14:27:00Z: `400 explainer-step-unknown … Proof.lean, which has no outline to name steps of`. Same request at 14:28:10Z: ok.
- **Expected/request.** The refusal to say which `main` commit the service read (so a caller knows to retry) rather than asserting the proof has no outline.
- **Cost.** 1 min.

### F-B4 [docs, still present, prior README item 8] `list_submissions` takes `target_id`, the guide says `target`
- 13:32Z `list_submissions {target: "erdos-68"}` → `arguments-invalid ('target' was unexpected)`. Guide line ~998: "`target`, `node` and `kind` narrow it".

### F-B5 [docs, minor; A also logged] `check_lean` answers the `{status, body}` envelope although the guide says only write tools do
- Guide line 26–28: "A write tool answers `{status, body}` … a read tool answers the document itself". `check_lean` (no write) returned `{status: 200, body: {...}}`.

### Not defects (for the lead)
- Fast check: 20–25 s per call, every elementary hole proof passed on the first or second try; precheck of a Mathlib-hole proof: ~3.5 min; PR gate ~3 min; merge actor merged #1139 then updated/re-gated #1140 (~6 min) as designed.
- 14:31Z Findings section written (F-B1..F-B5).
- 14:33Z Prepared B/proof-erdos-68-closing.lean: the root's closing proof through its holes (statement + the one allowed extra import `import Nodes.«erdos-68».Context`, closing.context_import = proof per get_node; body = A's assembly with h1/h2/h3 := erdos_68__h1/__h2/__h3). check_lean mode check, node erdos-68: okay True, lint [], only the inlined Context's 'declaration uses sorry' warnings. NOT submitted: h3 is unproved, so step 4 would fail (unproved hole not staged). Ready the day h3 is proved.

### F-B6 [bug, still present, prior README item 6 (A F6)] Site says "Proved from these holes by …" on the open root
- 14:37Z https://openproofnetwork.org/problems/erdos-68/ root panel: "How it is being proved — Open. A direct proof, or proofs of its holes, close it. Split into — Proved from these holes by 20261028T132200Z-t1028-a-partial.lean (merged in 1936413ac0a1, attestation 001134). h1 → erdos-68--h1 (proved) …" while erdos-68--h3 is open and the root is `ready`. "Proved from" reads as a completed proof to the steward.

## Log (continued)
- 14:35Z Appends #1143, #1147, #1150 all merged, gate_report ok, no warnings (checked 14:35Z). Reviewed A's glosses #1151–#1153: exact.
- 14:46Z 14:46 Site redeployed (site-deploy 14:44Z): h2 node page shows my explainer, sections rendered, attribution 'written by t1028-b, drafted with Claude Opus 5.5'. Ledger ledger/t1028-b.json credits both proofs (h1 merge 2e86f09, h2 merge 17294b3) with the automation block. Attestations 001139/001140 name submitter t1028-b.
- 14:47Z A's route 2 (#1154): h1 restates erdos-68--h1, h2' → erdos-68--h5 (C already proved it on the fast check, C/h2prime-full.lean; C submits), h3' → erdos-68--h6 (open core with window of width 1/(N(N+1))).
- 15:02Z Reviewed C's h5 proof against the gate-written erdos-68--h5 (main 546c4d7): theorem text verbatim; assembled with the real header as B/review-C-proof-erdos-68--h5.lean, verify okay True, lint []. Posted for C.
- 15:03Z 15:05 Found: erdos-68--h6 ⇔ root (argument posted on board). h6 holds exactly for N=4..25.
- 15:05Z SUBMITTED #1158 postmortem on erdos-68--h6 (submission 01M61GNZCGFM6VCJEKKPBV3FVC): h6 ⇔ root.
- 15:03Z Reviewed C's h5 proof against the gate-written statement (verify okay; B/review-C-proof-erdos-68--h5.lean). Found and posted: erdos-68--h6 ⇔ root (k_N forced to 1). A checked and corrected its literature record (#1159).
- 15:05Z SUBMITTED #1158 postmortem on erdos-68--h6 (h6 ⇔ root; refuted-route for "a narrower hole of h6").
- 15:10Z Confirmed A's F-A9 (route 2's restated h1 → node null; route erdos-68@2 live:false resolved:false; sets omit it).

- 15:29Z Reviewed C's explainer #1163: correct.
- 15:36Z B/h6_of_root.lean: Lean certificate of (h5 → Irrational S → h6), check_lean okay True. Backs #1158. Not submitted (not a step of a skeleton).
- 15:46Z Window closing: no further submissions from B. All B PRs merged (#1139 #1140 #1143 #1147 #1150 #1158).

## Final report (B, t1028-b)

### 1. What I landed (all through the MCP; all merged)
| PR | kind | node | state |
|---|---|---|---|
| #1139 | proof | erdos-68--h1 (factorial-multiplier irrationality criterion) | merged 14:03Z, `gate: #1139 pass` 14:23:31Z, status proved |
| #1140 | proof | erdos-68--h2 (N!·S = F_N + c, 0 < c ≤ 2/N; helper: 0 < K!·Σ_{m>K} 1/(m!−1) ≤ (K+1)/K²) | merged 14:07:52Z, `gate: #1140 pass` 14:21:41Z, status proved |
| #1143 | explainer | erdos-68--h2's proof (sections s1, s2, s3 + overview) | merged |
| #1147 | explainer | erdos-68--h1's proof (sections s1, s2, h1, close + overview) | merged |
| #1150 | postmortem | erdos-68--h3: failure of h3 ⇔ T + Σ_{j>M} k_{j−1}/j! ∈ (1/M!)ℤ for digits k ∈ {0,1,2}; the root is k ≡ 1 | merged |
| #1158 | postmortem | erdos-68--h6: h6 ⇔ root (k_N forced to 1), so route 2's core is the problem in finite form | merged |
Also: the carried witness for h1 (x = √2) that A carried in #1134; the review of C's h5 proof against the gate-written statement (verify okay); A's three statement glosses read against the Lean (exact).

### 2. Unfinished business for the lead
- **B/h6_of_root.lean**: fast-checked Lean (okay True) of h5 → Irrational S → h6, i.e. with #1154 and #1162, h6 ⇔ root. Evidence for #1158 only; no place on the record for it as far as I know — the lead's call.
- **B/proof-erdos-68-closing.lean**: the root's closing proof through holes h1/h2/h3 (adds only `import Nodes.«erdos-68».Context`; fast check `check` okay, lint []). Submittable only the day erdos-68--h3 is proved — do not submit before (step 4 refuses an unproved hole).
- Nothing else of mine is open. My two claims (h1, h2) were released at 15:25Z (they stayed active on the proved nodes until released by hand — minor: a claim is not released when its node's proof merges).

### 3. Findings, most important first
1. F-B1 [bug] proof post-merge job 20 min in "Regenerate the merge products" (#1139, #1140), appends' bot commits landing past it; #1140's attestation before #1139's. Same as C's F-C4.
2. Mathematical finding for the steward: route 2's open core erdos-68--h6 is equivalent to the root (#1158; A checked, C checked); route 1's h3 asks more than the root (#1150).
3. Confirmed A's F-A9 (route 2's restated h1 → node null; route erdos-68@2 dead in list_sufficient_sets).
4. F-B6 [bug, prior] site shows "Proved from these holes by …" on the open root.
5. F-B2 [low] outline `uses` misses a Mathlib constant reached by dot notation on a private helper → spurious `explainer-name-unanchored` warning.
6. F-B3 [feature, low] `explainer-step-unknown "no outline"` for ~1 min after the outline commit; say which main commit was read.
7. F-B4 [docs, prior] `list_submissions` `target` vs `target_id`. F-B5 [docs] `check_lean` answers `{status, body}`.

### 4. What would have made me twice as productive
The mathematics of my lane took about 25 minutes (all elementary holes were proved on the fast check before the skeleton was even submitted); the rest was waiting. Two things would have halved it: (a) a proof's post-merge job finishing in the advertised 3–5 minutes instead of 20, since every append and every explainer of my proofs had to wait for both bot commits and then for the outline commit; (b) letting a hole's proof ride with the partial that creates it (or precheck against a hole named by a passing partial precheck) — h1 and h2 were ready at 13:19Z and could not be submitted until 13:55Z. A per-hole "outline ready" signal on `get_submission` would also have saved the polling for the explainers.
