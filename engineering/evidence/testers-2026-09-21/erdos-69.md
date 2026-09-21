# Tester log: erdos-69 (outside-contributor run, 2026-09-21)

Start 06:23 UTC. Entry point: https://openproofnetwork.org/problems/erdos-69/ . Token never written here.

- 06:23 GET /problems/erdos-69/ 200. Page links "How to contribute" -> /docs/#agents. Guide (AGENTS.md rendered) read in full (~55k chars of text).
- Note (guide contradiction, to verify): "After the skeleton merges" says the parent "stays open: a direct proof of it ... is accepted at any time, holes proved or not", and a few paragraphs later "Until then any proof of the parent, even one that uses no hole, fails step 4 with dep-unproved."
- 06:24 POST /precheck tutorial (anonymous) -> 202 job 01M31A5XMR0BF0EQM37NZZ605W. I then LOST the nonce: my scratch file was overwritten by a parallel tester sharing the same scratchpad dir (tester-harness problem, not the network's). Consequence that IS about the network: the nonce is shown once and there is no way to recover it; a lost nonce costs a whole new precheck. Re-ran 06:27 -> job 01M31AAYS0QC4Y52E6HAR2KHZK.
- Finding: the HTTP path has no route to read a node's files (Statement.lean, Context.lean, attempts, annex). GET / lists none; the guide assumes a clone ($GRAPH) or MCP get_node. I read them from raw.githubusercontent.com at the frontier's rendered_from sha.
- Read deep hole erdos-69--h2-v2--h1-v2: prior postmortem + annex (agent-e69w-9550) show it is equivalent to the root (N=0 circular; integrality propagates upward in N). Plan: skeleton (partial) reducing it to a T-free arithmetic crux + three routine analytic lemmas.
- 06:27:30 POST /check {target_id erdos-69, node_id erdos-69--h2-v2--h1-v2, mode check} -> 200 after **75.07 s** (guide: "about a second"). Next two calls 3.4 s and 1.9 s, so first call is a cold start. Not flagged in the answer.
- 06:29 tutorial precheck done/pass (~2.5 min). POST /tokens -> 201, pseudonym agent-e69x-d614. POST /claims deep hole ttl 2 -> 201 claim 01M31AFM68ZKE5A0N0G3F77G6T.
- 06:30 My own maths slip: first crux hole was FALSE (missing 2^k factors); fast check said okay:true since a false `sorry` have still elaborates. Caught only while writing the annex prose. Wish: a cheap plausibility probe for holes. Corrected; check okay:true, lint [sorry-present].
- 06:31 POST /annexes (deep hole) -> see below.
- 06:31:08 POST /annexes -> 201, PR #133, hash a120bc75…; gate success, waiting_on "merge" at 06:31:37, merged by ~06:32:10 (fast, no human).
- 06:31:22 POST /precheck partial (artifact_type partial, citing a120bc75…) while #133 still open -> 202 job 01M31AK1J8K8ZM1C17KJ46S2E4, graph_commit 040f0558. Result ~2 min later: verdict fail, step 2 `annex-uncited` "not on this node; submit the annex first". The service knew at POST time that the annex was its own open PR #133; it could have answered 409 (like node-pending) instead of spending a 2-minute run. Guide says "Submit the informal argument first" but not "wait for it to MERGE before prechecking".
- 06:32-06:34 fast-checked full proofs of Lemmas 1,2 (hsplit,hpos) standalone: okay:true first try (2.5 s each).
- 06:34 re-POST /precheck same bundle after #133 merged.
- 06:34:51 POST /precheck (2nd) -> 202 job 01M31ASAQRPHK9BMM1YM76RH21 but `graph_commit` STILL 040f0558 although #133 merged at 06:32:12 (main e44149859b). /frontier.json rendered_from was still 040f0558 until ~06:35:30 (then bfe4c734). So for ~3.5 min after my annex merged, a precheck citing it is pinned to a commit without it. Expect a second `annex-uncited`. Nothing in the 202 warns. (Other testers were merging at the same time: #132, #135.)
- 06:36:58 POST /precheck (3rd) -> 202 job 01M31AX6RGHA9Z1GZX70DA6FQT, graph_commit bfe4c734 (has the annex).
- 06:35-06:37 fast-checked full proofs of all three routine lemmas (split, positivity, log tail bound) and a single-declaration witness for the 4th hole (Lambert ∧ split ∧ pos ∧ bound) with everything inlined as `have`s: okay:true.
- 06:39 precheck #2 (01M31ASAQ…RH21) done: fail step 2 annex-uncited, as predicted (stale graph_commit). ~4 min wasted.
- 06:40 precheck #3 (01M31AX6…6FQT) done: steps 1,2 pass; FAIL step 4 `hole-not-roundtrip` on hcrux. The printed closed type says `∃ N k m,` with NO binder types, so `m : ℤ` is lost (only occurrence is `(↑m : ℝ)`), and re-elaboration cannot recover it. The gate's printer sets pp.coercions.types/pp.numericTypes but evidently not binder types on ∃. The diagnostic is 4 kB of Lean repeated three times and never says WHICH part failed to round-trip or what to change. Fast check had said okay:true. Workaround: restate the crux over ℕ with `%`.
- 06:41:12 POST /precheck (4th; crux restated over ℕ with %) -> job 01M31B4YT0E6SJBTZH8XSFGPWN; done PASS at ~06:44:20 (steps 1,2,4,5,6,7,8 pass; step 6 code `hazards-derived-statement`).
- 06:44:40 POST /submissions artifact_type partial -> see next line.
- 06:44:34 POST /submissions -> 201 submission 01M31BB42GQM5QS38RTJY6KT74, PR #139 (partial on erdos-69--h2-v2--h1-v2; holes hsplit, hpos, hbound, hcrux).
- 06:46:40 probe: POST /proposals/witness node_id erdos-69--h2-v2--h1-v2--h1 (the hole #139 will create) -> 404 node-unknown (message does mention the post-merge lag). Guide promises 409 node-pending only for proposals; a pending partial's holes get the typo answer.
- 06:47:16 one GET /submissions/<id> took ~60 s (others <1 s).
- gate on #139 still in_progress at 06:49 (guide: "about three minutes on a Mathlib target").
- 06:50:30 gate on #139 green (~6 min, guide says ~3). waiting_on=merge at 06:50:40. At 06:50:58 the merge actor merged main INTO my branch (2nd time; first 06:47:37 mid-run) because other testers' PRs merged meanwhile; head moved to b46403db, gate restarted, waiting_on back to "gate" at 06:51:18. Each update costs another ~6 min Mathlib gate, during which main can move again: starvation risk under concurrent contributors. No field in GET /submissions says "gate restarted because branch was updated (n times)".
- GET /submissions.json: every entry's waiting_on is null/absent (only the per-id route computes it).
- 06:54:13 third 'Merge branch main into' on #139, again while its gate run was still in progress (the run it interrupted is wasted). Starvation observed: submitted 06:44:34, still not merged at 06:57.

## Appendix: fast-checked (AXLE okay:true, non-authoritative) proofs of the three routine holes of #139, for whoever proves them

```lean
import Mathlib

open scoped ArithmeticFunction.omega

theorem omega_series_summable : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
  have hbound : ∀ n : ℕ,
      (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
    intro n
    have h1 : ω n ≤ n + 1 := by
      rw [ArithmeticFunction.cardDistinctFactors_apply]
      calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
        _ ≤ (Finset.range (n + 1)).card :=
            Finset.card_le_card (fun p hp =>
              Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
        _ = n + 1 := Finset.card_range _
    have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
    have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
    rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
    nlinarith [mul_le_mul_of_nonneg_right h2 h4]
  refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
  exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
    (summable_geometric_of_lt_one (by norm_num) (by norm_num))

theorem tail_summable (N : ℕ) : Summable (fun j : ℕ => (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)) := by
  have hshift : Summable (fun j : ℕ => (ω (j + (N + 1)) : ℝ) / 2 ^ (j + (N + 1))) :=
    (summable_nat_add_iff (f := fun n : ℕ => (ω n : ℝ) / 2 ^ n) (N + 1)).2 omega_series_summable
  refine (hshift.mul_left ((2 : ℝ) ^ N)).congr (fun j => ?_)
  rw [show j + (N + 1) = N + 1 + j by omega]
  rw [show (2 : ℝ) ^ (N + 1 + j) = 2 ^ N * 2 ^ (j + 1) by rw [← pow_add]; congr 1; omega]
  field_simp

theorem hpos : ∀ M : ℕ, 0 < ∑' j : ℕ, (ω (M + 1 + j) : ℝ) / 2 ^ (j + 1) := by
  intro M
  refine (tail_summable M).tsum_pos (fun j => by positivity) 1 ?_
  have h1 : 0 < ω (M + 1 + 1) := by
    rw [ArithmeticFunction.cardDistinctFactors_apply]
    have : (M + 1 + 1).primeFactors.Nonempty := Nat.nonempty_primeFactors.2 (by omega)
    exact Finset.card_pos.2 this
  have : (0 : ℝ) < (ω (M + 1 + 1) : ℝ) := by exact_mod_cast h1
  positivity

theorem tail_step (N : ℕ) :
    ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
      = (ω (N + 1) : ℝ) / 2 + (∑' j : ℕ, (ω (N + 1 + 1 + j) : ℝ) / 2 ^ (j + 1)) / 2 := by
  rw [(tail_summable N).tsum_eq_zero_add, ← tsum_div_const]
  congr 1
  · simp
  · refine tsum_congr (fun j => ?_)
    rw [show N + 1 + (j + 1) = N + 1 + 1 + j by omega, pow_succ (2 : ℝ) (j + 1)]
    field_simp

theorem hsplit : ∀ N k : ℕ,
    ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
      = ∑ j ∈ Finset.range k, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
        + (∑' j : ℕ, (ω (N + k + 1 + j) : ℝ) / 2 ^ (j + 1)) / 2 ^ k := by
  intro N k
  induction k with
  | zero => simp
  | succ k ih =>
    rw [ih, tail_step (N + k), Finset.sum_range_succ]
    rw [show N + (k + 1) = N + k + 1 by omega, show N + 1 + k = N + k + 1 by omega, pow_succ]
    field_simp
    ring

theorem omega_le_logb (n : ℕ) (hn : 1 ≤ n) : (ω n : ℝ) ≤ Real.logb 2 n := by
  have h1 : 2 ^ ω n ≤ n := by
    rw [ArithmeticFunction.cardDistinctFactors_apply]
    calc 2 ^ n.primeFactorsList.dedup.length = 2 ^ n.primeFactors.card := rfl
      _ ≤ ∏ p ∈ n.primeFactors, p :=
          Finset.pow_card_le_prod _ _ _ (fun p hp => (Nat.prime_of_mem_primeFactors hp).two_le)
      _ ≤ n := Nat.le_of_dvd (by omega) (Nat.prod_primeFactors_dvd n)
  have h2 : ((2 : ℝ) ^ ω n) ≤ (n : ℝ) := by exact_mod_cast h1
  have hn0 : (0 : ℝ) < n := by exact_mod_cast hn
  rw [Real.le_logb_iff_rpow_le (by norm_num) hn0, Real.rpow_natCast]
  exact h2

theorem geo1 : HasSum (fun j : ℕ => (1 : ℝ) / 2 ^ (j + 1)) 1 := by
  have h' := (hasSum_geometric_two).mul_left (1 / 2 : ℝ)
  have hf : (fun j : ℕ => (1 : ℝ) / 2 ^ (j + 1)) = fun i : ℕ => 1 / 2 * (1 / 2 : ℝ) ^ i := by
    funext j
    rw [pow_succ, one_div_pow]
    field_simp
  have hv : (1 / 2 * 2 : ℝ) = 1 := by norm_num
  rw [hv] at h'
  rw [hf]
  exact h'

theorem geo2 : HasSum (fun j : ℕ => (j : ℝ) / 2 ^ (j + 1)) 1 := by
  have h' := (hasSum_coe_mul_geometric_of_norm_lt_one (r := (1 / 2 : ℝ))
    (by norm_num [Real.norm_eq_abs])).mul_left (1 / 2 : ℝ)
  have hf : (fun j : ℕ => (j : ℝ) / 2 ^ (j + 1)) = fun i : ℕ => 1 / 2 * ((i : ℝ) * (1 / 2 : ℝ) ^ i) := by
    funext j
    rw [pow_succ, one_div_pow]
    field_simp
  have hv : (1 / 2 * (1 / 2 / (1 - 1 / 2) ^ 2) : ℝ) = 1 := by norm_num
  rw [hv] at h'
  rw [hf]
  exact h'

theorem hbound : ∀ M : ℕ,
    ∑' j : ℕ, (ω (M + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ Real.logb 2 ((M : ℝ) + 1) + 1 := by
  intro M
  have hL : 0 ≤ Real.logb 2 ((M : ℝ) + 1) := Real.logb_nonneg (by norm_num) (by linarith [Nat.cast_nonneg (α := ℝ) M])
  have hterm : ∀ j : ℕ, (ω (M + 1 + j) : ℝ) / 2 ^ (j + 1)
      ≤ Real.logb 2 ((M : ℝ) + 1) * (1 / 2 ^ (j + 1)) + (j : ℝ) / 2 ^ (j + 1) := by
    intro j
    have h1 := omega_le_logb (M + 1 + j) (by omega)
    have hM : (0 : ℝ) < (M : ℝ) + 1 := by positivity
    have hj : (0 : ℝ) < (j : ℝ) + 1 := by positivity
    have h2 : Real.logb 2 ((M + 1 + j : ℕ) : ℝ) ≤ Real.logb 2 (((M : ℝ) + 1) * ((j : ℝ) + 1)) := by
      apply Real.logb_le_logb_of_le (by norm_num) (by positivity)
      push_cast
      nlinarith [Nat.cast_nonneg (α := ℝ) M, Nat.cast_nonneg (α := ℝ) j]
    rw [Real.logb_mul hM.ne' hj.ne'] at h2
    have h3 : Real.logb 2 ((j : ℝ) + 1) ≤ (j : ℝ) := by
      rw [Real.logb_le_iff_le_rpow (by norm_num) hj, Real.rpow_natCast]
      have : j + 1 ≤ 2 ^ j := Nat.lt_two_pow_self
      exact_mod_cast this
    have hp : (0 : ℝ) < 2 ^ (j + 1) := by positivity
    rw [mul_one_div, ← add_div]
    exact div_le_div_of_nonneg_right (by linarith) hp.le
  have hs : HasSum (fun j : ℕ => Real.logb 2 ((M : ℝ) + 1) * (1 / 2 ^ (j + 1)) + (j : ℝ) / 2 ^ (j + 1))
      (Real.logb 2 ((M : ℝ) + 1) * 1 + 1) := (geo1.mul_left _).add geo2
  calc ∑' j : ℕ, (ω (M + 1 + j) : ℝ) / 2 ^ (j + 1)
      ≤ ∑' j : ℕ, (Real.logb 2 ((M : ℝ) + 1) * (1 / 2 ^ (j + 1)) + (j : ℝ) / 2 ^ (j + 1)) :=
        (tail_summable M).tsum_le_tsum hterm hs.summable
    _ = Real.logb 2 ((M : ℝ) + 1) + 1 := by rw [hs.tsum_eq, mul_one]
```

Witness for the 4th hole (hcrux) = one declaration `witness : ID ∧ SPLIT ∧ POS ∧ BND` built from the Lambert proof in the node's existing Witness.lean plus the theorems above inlined as `have`s (fast-checked okay:true at 06:37).

- 06:57:36 fourth update of #139. Correlation (from graph commit log): updates at 06:47:37, 06:50:58, 06:54:13, 06:57:36 follow main moving at 06:46:56 (bot "gate: #138 pass"), 06:49:52 (merge #134), 06:53:01 (bot "gate: #134 pass"), 06:57:27 (merge #136). So ONE foreign merge restarts my 6-minute gate TWICE (its merge commit, then its bot commit ~3 min later), and the actor updates even while my run is mid-flight. The guide itself advises humans: "Merge one hole's pull request, wait for that commit, then update the next branch; a branch updated in between is behind again" — the merge actor does not do that.
- 07:04 #139 MERGED (submitted 06:44:34; 20 min, 5 gate runs of which 4 were thrown away by branch updates). GET /submissions/<id> now waiting_on null, attestation_path null.
- 07:08:00 bot commit "gate: #139 pass"; 07:08:52 frontier shows the four holes erdos-69--h2-v2--h1-v2--h1..h4 (origin skeleton-hole, ready_since null, claimable true). ~4.5 min after merge.
- Observed in generated files: (a) hole Witness.lean slot has NO import/open header and reads `theorem witness : ∃ N k, <identity> := by sorry` — the guide says the slot "says theorem witness : True := by sorry whatever the statement is" (outdated), and the printed `∃ N k,` has untyped binders that cannot elaborate on their own; (b) new holes' META.yaml is `schema: meta/v3` while older nodes are meta/v4 (observation only).
- 07:10 POST /check mode check with node_id on each witness file -> okay:true but lint `helper-declarations` (false alarm: a witness file by definition declares `witness`, not the statement's theorem).
- 07:10 POST /proposals/witness x4 -> 201 each: PRs #141 (h1), #142 (h2), #143 (h3), #144 (h4).
- 07:11:41 fast check (mode verify, node_id) of full Proof.lean for holes h1,h2,h3: okay:true each, lint `context-restated` although the proofs use nothing from Context (lint seems to fire whenever a Context is inlined).
- 07:11:51 POST /precheck Proof.lean for ...--h1 -> 409 node-blocked cause witness-missing (as documented). Cannot pipeline the proof's precheck behind the witness PR.
- 07:15:42 GET /submissions/141 timed out after 20 s (second slow read of this route).
- 07:19:51 witness PRs #141-#144 all still gate in_progress ~9 min after opening (branches being re-updated). Step-7 verdict on my witness types NOT observed. Stopped here (timebox exceeded). Claim released.
- Unsubmitted but ready: proof_h1/h2/h3 (Lean in the appendix above, wrapped as intro + haves + exact).
