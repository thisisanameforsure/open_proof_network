# Calibration run — erdos-69 (F15-T14c), agent log

Target: `erdos-69` (graded medium). Statement: `Irrational (∑' n, ω (n + 2) / 2 ^ (n + 2))`
(Erdős 1948, ω = number of distinct prime factors). Mathlib pin
`0df444a360eaa60ab8c11dca51a86af692955474` (Lean v4.33.1).

This file is the whole state of the run. A successor reads
`engineering/session-notes/2026-09-17-calibration-run-handoff.md`, then this file, then acts on
the **Next** section at the bottom.

## Timeline

- 00:00 — Started (Fable 5.1). Read the handoff brief, `engineering/onramp/calibration/README.md`,
  the erdos-69 draft (`Statement.lean`, `Witness.lean`, `record.yaml`), `upstream/69.lean`.
  The draft statement header: `import Mathlib`, then `open scoped ArithmeticFunction.omega`, then
  `theorem Opn.erdos_69 : Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2) := by sorry`.
  Note the sum is over `n : ℕ` with the summand coerced to ℝ (type of `Irrational`); the
  registry's own variant file states `∑' n, ω (n + 2) / (2 ^ (n + 2) : ℝ) = ∑' p : {n | n.Prime}, 1 / (2 ^ p.1 - 1)`.

- 14:05 UTC — Read `../open_proof_network_graph/AGENTS.md` (full walkthrough: token via tutorial
  precheck nonce, `/check`, `/precheck`, `/submissions`, partial = bundle path
  `attempts/<ts>-<pseudonym>-partial.lean` with `artifact_type: partial`, `-- annex: <sha256>` as
  the first body line). Live node on `origin/main` (graph HEAD `980344c`, PR #73 merged):
  `targets/erdos-69/nodes/erdos-69/{Statement.lean,META.yaml,Context.lean,Witness.lean}`;
  `META.yaml`: `status: ready`, `deps: []`, statement-hash `46fcc868…a155`, one acknowledged
  `div-zero` hazard; `Context.lean` declares no deps; `gate-spec.json` pins network `26e86c4`
  (the lead says another session re-pinned to `0401858` at 14:07), Mathlib `0df444a3`,
  toolchain `leanprover/lean4:v4.33.1`, `accepted_precheck_signatures: [service, contributor, none]`.
  The live `Statement.lean` is byte-identical to the calibration draft.
- 14:06 — Step-2 rule read (`gate/opn_gate/paths.py::check_proof_is_statement`): `Proof.lean`
  must start with `Statement.lean`'s prefix (everything up to and including the `:=` before the
  sorry body, `gate/opn_gate/layout.py:114`) and end with its suffix — so **no declaration of any
  kind before the theorem**; helpers go inside the body as `have`. The hole extractor
  (`gate/lean/OpnGate/Holes.lean`) takes only `have h : T := sorry` (`Expr.letE` with a `sorryAx`
  value) as a named hole, and its `closed_type` is `mkForallFVars binders t` where `binders`
  includes every earlier `have` on the path — **so hole 2 inherits hole 1 as a hypothesis, and hole
  2's child witness (step 7) is a proof of hole 1** (F11-Q22). Any other `sorry` counts as
  `unnamed`. Decision: order the holes Lambert identity first (the easier lemma, and a hypothesis
  Erdős's argument can actually use), prime-sum irrationality second.
- 14:09 — Tutorial precheck (mints the token) queued: job `01M2QV7PSRJMPA9TRGMHDZRD24`, nonce
  kept in the scratchpad (`tut-precheck.json`; not in this file), `graph_commit 42f94ef`.
- 14:11 — `POST /check` with `target_id: erdos-69` answers `404 target-unknown` ("erdos-69 is not
  a target of this graph", log `01M2QV3KY85BJRF4JX3S49TKG8`): the service reads the committed
  products, which are rendered from `42f94ef` (before erdos-69 existed). **Lead's message
  (14:12):** the graph's products are stale until the post-merge run under the new pin lands a
  bot commit (expected 14:30–14:50 UTC); precheck/claim/submit on erdos-69 will refuse until then;
  iterate on `/check` only; do not touch PR #74; poll readiness with
  `git -C ../open_proof_network_graph fetch -q origin && git show origin/main:frontier.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['rendered_from'], [e for e in d['entries'] if 'erdos-69' in json.dumps(e)][:1])"`.
- 14:13 — **Finding (tooling, not mine to fix): every `POST /check` on a Mathlib target currently
  answers a `user_error`.** With `target_id: erdos-257` (same pin) the result was
  `"user_error": "Unknown environment: lean-4.33.0. Available environments: lean-4.21.0, …,
  lean-4.32.2, lean-4.33.1, lean-4.34.0"` (log `01M2QV94PGR5PRX4A3DFS1K55D`). AXLE has replaced
  `lean-4.33.0` by `lean-4.33.1` since the 2026-09-14 probe, and `gate/hosted-checkers.yaml`
  still maps the pin (and `core`) to `lean-4.33.0`. The fix is a one-line mapping change
  (`environment: lean-4.33.1`, `exact: true`) plus the probe as evidence — F13's mapping file
  says to record the probe. `GET https://axle.axiommath.ai/v1/environments` confirms
  `lean-4.33.1` (`leanprover/lean4:v4.33.1`, `import Mathlib`). Workaround for this run: AXLE
  needs no key at Stage 0 (F13-Q5, `api/opn_api/axle.py`), so I call
  `POST https://axle.axiommath.ai/api/v1/check` directly with `environment: lean-4.33.1`
  (scratch helper `axle.py`); these calls are not in the network's call log, and the precheck
  remains the only verdict.
- 14:15 — First skeleton (`skel1.lean`, two holes, assembly `rw [h_lambert]; exact h_irr`)
  elaborates on AXLE 4.33.1: `okay: true`, only `declaration uses sorry` (request
  `be7fd1b9-c081-4f56-ae67-7a57c6931641`, 132 ms). AXLE's goals at the two sorries:
  `⊢ ∑' (n : ℕ), ↑(ω (n + 2)) / 2 ^ (n + 2) = ∑' (p : Nat.Primes), 1 / (2 ^ ↑p - 1)` and, under
  `h_lambert`, `⊢ Irrational (∑' (p : Nat.Primes), 1 / (2 ^ ↑p - 1))`.

- (times below are the service's own `created` stamps, which run ~10 min behind my estimates
  above; the service's clock is the reference)
- 14:14 — Tutorial precheck `done pass`; token minted: pseudonym **`agent-erdos69-1b25`**,
  identity `01M2QVFJR8MZTK2W0GF8FXA8JW`, proof kind `tutorial`. The token is in the scratchpad's
  `token.json` only (`/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/835932f5-156f-4eb6-a7d1-1ab6456274b0/scratchpad/e69/`),
  never here. A successor without that directory mints a new one the same way (tutorial precheck
  → nonce → `POST /tokens`); the credit then goes under a new pseudonym.
- 14:14 — Name probes on AXLE (`exact?` works there and returns the suggestion as an info):
  `Summable.sum_add_tsum_nat_add 2 hf` is the shift lemma (`sum_add_tsum_nat_add` bare is
  gone); `ω n = n.primeFactors.card` is `rfl`; `tsum_comm'`, `tsum_sigma'`, `tsum_prod'`,
  `tsum_finset_sum`, `tsum_sum`, `tsum_eq_zero_add` are unknown here — the survivors are
  `Summable.tsum_comm` (needs `Summable (Function.uncurry f)`), `Summable.sigma`,
  `summable_prod_of_nonneg`, `Summable.tsum_eq_zero_add`, `tsum_subtype`,
  `tsum_subtype_eq_of_support_subset`, `Finset.tsum_subtype`, `tsum_ite_eq`,
  `tsum_geometric_of_lt_one`, `summable_geometric_of_lt_one`,
  `summable_pow_mul_geometric_of_norm_lt_one`, `Summable.of_nonneg_of_le`, `tsum_mul_left`,
  `tsum_div_const`. This Mathlib has `SummationFilter` (`∑'[L]`). `exact?` could not prove
  `ω n ≤ n`; I used `ω n ≤ n + 1` via `n.primeFactors ⊆ range (n+1)` (`Nat.le_of_mem_primeFactors`).
- 14:15 — The shift `∑' n, ω(n+2)/2^(n+2) = ∑' n, ω n/2^n` is **proved** (summability by
  domination with `(n+1)(1/2)^n`, then `Summable.sum_add_tsum_nat_add 2` and `ω 0 = ω 1 = 0`);
  `skel2.lean` `okay: true` (AXLE `ce4e34c4-e488-4057-9231-aa6c1152242f`), one unused-simp-arg
  lint (`cardDistinctFactors_zero`), removed in `skel3.lean` (`5f74ffa6-93e0-4a93-ad58-3ceb692324b4`,
  clean but for `declaration uses sorry`). So the partial has **two holes**: the unshifted Lambert
  identity and the prime-sum irrationality. I did not attempt the Lambert identity's double-sum
  swap in the timebox (see Next).
- 14:15 — Products rendered: graph `origin/main` at `456997d` (`gate: #74 pass`), `frontier.json`
  `rendered_from 1f9fb28…` lists `erdos-69`. Lead's second message (go) received.
- 14:15 — **Annex submitted** (`POST /annexes`, licence CC-BY-4.0, text in the scratchpad's
  `annex.md` and quoted under "Annex text" below): **graph PR #75**, id `01M2QVJ3T0D1V6BXW4G01VZVVR`,
  path `targets/erdos-69/nodes/erdos-69/annex/84315a5968f2b6dd9faf3e94d5018bb468eb448040fde6aea1c9be90f4746354.md`,
  hash **`84315a5968f2b6dd9faf3e94d5018bb468eb448040fde6aea1c9be90f4746354`** (the service's hash
  differs from the bare file's sha256 `2b7872…`, so it hashes the file it writes, presumably with
  front matter; cite the service's). `check_annex_citation` runs only in
  `gate/opn_gate/postmerge.py:478`, so the partial's PR gate does not need the annex merged, but
  **the lead must merge #75 before the partial**, or the partial's post-merge job refuses
  `annex-uncited` and creates no children.
- 14:16 — **Owned precheck of the partial queued**: job **`01M2QVJS9GQRACNP695KTN4DE7`**,
  `artifact_type: partial`, bundle path
  **`targets/erdos-69/nodes/erdos-69/attempts/20260917T141558Z-agent-erdos69-1b25-partial.lean`**
  (from `precheck-request.json`, the exact bundle; an earlier draft of this line guessed the
  timestamp), bundle digest `65e6cbf7…4871`, `graph_commit 1f9fb28`. The same text on AXLE:
  `c44a1edc-68a7-4f89-80ab-cbc136525f1b`, `okay: true`. (The laptop's clock agrees with the
  service's; the "14:05–14:15" estimates earlier in this timeline were ~10 minutes ahead — the
  session started nearer 14:03 UTC.)
- 14:17 — While the precheck ran, building blocks for the Lambert hole were checked on AXLE
  (`probe3.lean` `1587eb89-ff47-4059-bc5f-c91d8e19dec2`, `probe4.lean`
  `126d8091-be76-47ab-8752-699c380ef4f5`), each an `example` with `import Mathlib` and the
  statement's `open scoped` line:
  - **(a) verified**: `∀ p, 2 ≤ p → ∑' k : ℕ, ((1/2 : ℝ) ^ p) ^ (k + 1) = 1 / (2 ^ p - 1)` by
    `have hr0 : (0:ℝ) ≤ (1/2:ℝ)^p := by positivity`,
    `have hr1 : (1/2:ℝ)^p < 1 := pow_lt_one₀ (by norm_num) (by norm_num) (by omega)`,
    `have h2 : (1:ℝ) < 2^p := one_lt_pow₀ (by norm_num) (by omega)`,
    `have h3 : (2:ℝ)^p - 1 ≠ 0 := by linarith`, `simp_rw [pow_succ]`,
    `rw [tsum_mul_right, tsum_geometric_of_lt_one hr0 hr1, one_div, inv_pow]`, `field_simp`.
  - **(b) verified**: `Summable g → Summable (fun p : Nat.Primes => g p)` is
    `hg.subtype (fun p => p.Prime)` (term mode). `exact?` on it dies with
    `(deterministic) timeout at whnf, maximum number of heartbeats (200000)`.
  - **(c) verified**: `(ω n : ℝ) = ∑ p ∈ n.primeFactors, (1 : ℝ)` by
    `simp [ArithmeticFunction.cardDistinctFactors_apply]` then `rfl` (simp alone leaves
    `n.primeFactorsList.dedup.length = n.primeFactors.card`, which is `rfl`).
  - **(d) half-verified**: for `n ≠ 0`,
    `∑' p : Nat.Primes, (if (p:ℕ) ∣ n then (1:ℝ) else 0)` collapses to a finite sum by
    `tsum_eq_sum (s := n.primeFactors.subtype Nat.Prime) hfin` where `hfin` is proved from
    `Finset.mem_subtype` and `Nat.mem_primeFactors : p ∈ n.primeFactors ↔ p.Prime ∧ p ∣ n ∧ n ≠ 0`
    (this step elaborates); the remaining finite-sum-equals-`ω n` goal after
    `simp [cardDistinctFactors_apply]` was left as `sorry` and not inspected. `exact?` does not
    find (d) as a whole.
  - (d), one more round (`probe5.lean`, AXLE `e4bfea9d-0ec2-4b5d-b19c-386578d6fb4e`): after
    `rw [tsum_eq_sum hfin]` the goal is
    `(∑ b ∈ Finset.subtype Nat.Prime n.primeFactors, if ↑b ∣ n then 1 else 0) = ↑(ω n)`, and
    `rw [Finset.sum_ite_of_true …]` fails with `Application type mismatch: … has type Finset
    (Subtype Nat.Prime) but is expected to have type Finset Nat.Primes` — `Nat.Primes` and
    `Subtype Nat.Prime` are defeq but not syntactically equal, so `rw` refuses. A successor should
    build the finset as `Finset Nat.Primes` explicitly (e.g. `n.primeFactors.attach.map` into
    `Nat.Primes`, or `Finset.sum_subtype`-style lemmas stated over `Nat.Primes`), or avoid the
    subtype by working with `∑ p ∈ n.primeFactors, …` on ℕ and `Finset.sum_map`.
  - **(d) verified** (`probe7.lean`, AXLE `0b1c86a5-6517-41ae-a708-a470eb4a6fdd`, `okay: true`, no
    warnings), for `n ≠ 0`: `∑' p : Nat.Primes, (if (p : ℕ) ∣ n then (1 : ℝ) else 0) = ω n`:

    ```lean
      let S : Finset Nat.Primes :=
        n.primeFactors.attach.map ⟨fun p => ⟨p.1, (Nat.mem_primeFactors.1 p.2).1⟩,
          fun p q h => Subtype.ext (Subtype.mk.inj h)⟩
      have hmem : ∀ p : Nat.Primes, p ∈ S ↔ (p : ℕ) ∈ n.primeFactors := by
        intro p
        constructor
        · intro hp
          obtain ⟨q, -, rfl⟩ := Finset.mem_map.1 hp
          exact q.2
        · intro hp
          exact Finset.mem_map.2 ⟨⟨p.1, hp⟩, Finset.mem_attach _ _, Subtype.ext rfl⟩
      have hfin : ∀ p : Nat.Primes, p ∉ S → (if (p : ℕ) ∣ n then (1 : ℝ) else 0) = 0 := by
        intro p hp
        rw [if_neg]
        intro hdvd
        exact hp ((hmem p).2 (Nat.mem_primeFactors.2 ⟨p.2, hdvd, hn⟩))
      rw [tsum_eq_sum hfin]
      rw [Finset.sum_ite_of_true (fun p hp => (Nat.mem_primeFactors.1 ((hmem p).1 hp)).2.1)]
      rw [Finset.sum_const, nsmul_eq_mul, mul_one]
      have hcard : S.card = n.primeFactors.card := by
        simp [S, Finset.card_map, Finset.card_attach]
      rw [hcard]
      simp [ArithmeticFunction.cardDistinctFactors_apply]
      rfl
    ```

    (`congrArg Subtype.val h` in the injectivity proof fails with an application type mismatch —
    the beta-redex in `h`'s type — `Subtype.mk.inj h` is the form that elaborates.) With the
    summand `(1/2)^n` instead of `1` the same proof gives step (i) of the plan in Next.
  - Names confirmed by `#check`: `Summable.tsum_comm` (needs `Summable (Function.uncurry f)`),
    `summable_prod_of_nonneg`, `Summable.subtype`, `tsum_eq_sum` (takes `∀ b ∉ s, f b = 0`),
    `Nat.mem_primeFactors`, `tsum_eq_tsum_of_ne_zero_bij`. `Nat.Primes.prop` does not exist
    (use `p.2 : (p:ℕ).Prime`).

- 14:2x — **Precheck `01M2QVJS9GQRACNP695KTN4DE7`: `done`, verdict `pass`**, every step pass
  (1 toolchain, 2 paths, 4 kernel-replay, 5 axioms, 6 hazards, 7 witness, 8 deps), attestation
  signed by `service`, runner `hosted`, statement hash `46fcc868…a155` (the node's).
- 14:3x — **Submitted** (`POST /submissions`, `artifact_type: partial`, same bundle,
  `precheck_job_id` the job above, tooling disclosed as Claude Fable 5.1 / Claude Code, F15-T14c):
  submission **`01M2QVSP00T8W7W39CBZF2WCN2`**, **graph PR #77**
  (`https://github.com/thisisanameforsure/open_proof_network_graph/pull/77`), head `c60d9d0a7f19`.
  First read: `state open`, `mergeable blocked`, one check run `gate` `in_progress`, no reviews.
  `GET /submissions.json` lists #75 (my annex), #76 (erdos-1050, the other agent), #77.
  A background poll (`submission-state.json` in the scratchpad) waits for the gate run to
  complete; its result is appended below when it lands.
- 14:20 — Via `gh` (reads only): PR #77 is `partial: erdos-69` by `app/open-proof-network`, head
  branch `submit/01M2QVSP00T8W7W39CBZF2WCN2`, `MERGEABLE` / `BLOCKED`; checks: `gate (steps 1, 2
  and 4-8 in the sandbox)` pending, `postmerge (step 9 record, gate signature, attestation
  commit)` skipping. The gate run is **`35232829419`**
  (`https://github.com/thisisanameforsure/open_proof_network_graph/actions/runs/35232829419`),
  created 14:19:50Z. **The annex PR #75's gate run `35232389153` (append mode) completed
  `success`** at 14:15:44Z, so #75 is ready for the lead to merge.

- 14:23 — **Gate on PR #77: the sandbox job passed.** Run `35232829419`: job `gate (steps 1, 2
  and 4-8 in the sandbox)` `completed success` (14:19:53Z → 14:23:01Z; pinned network `0401858`;
  `"mode": "partial"`, `"artifact_type": "partial"`, `"verdict": "pass"`,
  `"first_failing_step": null`, steps 1, 2, 4, 5, 6, 7, 8 all `pass`, the kernel-replay step
  carrying the hole report). Job `postmerge` skipped (not merged). Job **`step 9 (a non-author
  approving review)` `failure`**, by design, with the message
  `##[error]step 9: this node's root has no fidelity certificate or registry provenance, so a
  non-author approving review is required before merge (D-4 v3.11; a curator record needs
  another listed curator's, F08-R8). Approving re-runs this check; the build above is not
  repeated.` So the run's overall conclusion is `failure` and the PR is `mergeable: blocked`
  until the lead approves; an approval re-runs only the step-9 job (F07-T17: ~5 s). The service's
  `GET /submissions/01M2QVSP00T8W7W39CBZF2WCN2` shows the same (`gate completed failure`,
  `reviews: []`, `attestation: None, note: not-merged`), which is worth knowing: the service's
  one `gate` run line reports the workflow's conclusion, not the sandbox job's, so a
  review-blocked green build reads as a red check there — the 2026-09-13 tester's finding, still
  true after F07-T17. The log lines above are in the scratchpad's `gate-run-failed.log`.

- 14:3x — **Continuation brief (Mike via the lead, ~45 min):** the lead is merging #76–#79 in
  sequence — touch no pull request until told the sequence is complete; the merge of #77 creates
  `erdos-69--h1` (Lambert identity) and `erdos-69--h2` (irrationality, inheriting h1); next
  submissions go on the children. Meanwhile close hole 1 as a full proof if it closes, else an
  honest partial of the hole; then hole 2 the same way. Try the network's `POST /check` first
  each time (the mapping is being repointed to `lean-4.33.1`), fall back to AXLE direct. When
  the merges are done: read each child's `Statement.lean`/`META.yaml` on `origin/main` (note
  hazards without `acknowledged_hazards`, F07-Q19), precheck and submit on the child; if admission
  refuses on an unacknowledged hazard, type it verbatim here and stop. Commit nothing.

## Current best Lean (the prechecked partial; header = live `Statement.lean` verbatim)

Body after `:= by` (the file is the scratchpad's `partial.lean`; rebuild it from the live
`Statement.lean` by replacing `  sorry` with this body):

```lean
  -- annex: 84315a5968f2b6dd9faf3e94d5018bb468eb448040fde6aea1c9be90f4746354
  -- Hole 1 (Tao's remark under Erdős 257): the Lambert-series identity. Writing ω(n) as the
  -- number of primes dividing n and swapping the absolutely convergent double sum,
  -- ∑_n ω(n)/2^n = ∑_p ∑_{k ≥ 1} 2^{-pk} = ∑_p 1/(2^p - 1).
  have h_lambert : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := sorry
  -- Hole 2 (Erdős 1948): the prime sum ∑_p 1/(2^p - 1) is irrational.
  have h_irr : Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := sorry
  -- Assembly: the statement's sum starts at n = 2, and ω 0 = ω 1 = 0, so it is the whole sum.
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
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
    exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  have hshift : ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n := by
    have h : ∑ i ∈ Finset.range 2, (ω i : ℝ) / 2 ^ i + ∑' i : ℕ, (ω (i + 2) : ℝ) / 2 ^ (i + 2)
        = ∑' i : ℕ, (ω i : ℝ) / 2 ^ i := hsum.sum_add_tsum_nat_add 2
    rw [← h]
    simp [Finset.sum_range_succ,
      ArithmeticFunction.cardDistinctFactors_one]
  rw [hshift, h_lambert]
  exact h_irr
```

Hole order and what it costs (F11-Q22): hole 2's child carries `h_lambert` as a hypothesis, so
its witness is a proof of the Lambert identity; hole 1's child has no hypotheses (witness `True`).
Neither hole is defeq to the goal (`Irrational (∑' n, ω(n+2)/2^(n+2))`), so the offload rule
passes; the assembly's locals come after the holes so they enter no closed type.

## Annex text (as submitted, PR #75)

See the scratchpad's `annex.md`; in substance: Lemma 1 = the Lambert identity by the
non-negative double-sum rearrangement (∑_n ∑_{p∣n} 2^{−n} = ∑_p ∑_{k≥1} 2^{−pk} = ∑_p 1/(2^p−1),
with ω(0) = ω(1) = 0 for the shift); Lemma 2 = Erdős 1948: if the sum were a/b then for every N
`b·∑_{k≥1} ω(N+k)/2^k` is an integer, and a CRT choice of N controls ω(N+k) for small k so that
the quantity falls strictly between consecutive integers; assembly = rewrite by Lemma 1, apply
Lemma 2. References: Erdős, J. Indian Math. Soc. 12 (1948) 63–66; erdosproblems.com/69; the
registry variant `specialisation_of_erdos_257`.

## Plan

1. ~~Read the guide and the live node.~~ done
2. ~~Read the step-2 rule and the hole extractor.~~ done
3. ~~Skeleton checks; the shift proved; two honest holes remain.~~ done
4. ~~Token, annex (PR #75), cited partial prechecked (job `01M2QVJS9GQRACNP695KTN4DE7`).~~ queued
5. When the precheck is `done pass`: `POST /submissions` with `artifact_type: partial`, the same
   bundle, `precheck_job_id` = that job; then `GET /submissions/<id>` until the gate check on the
   PR is green; record the PR number here; stop.

## Prior art consulted (R14 c)

- `engineering/onramp/calibration/upstream/69.lean` (registry file): the Tao remark that
  `∑ ω(n)/2^n = ∑_p 1/(2^p − 1)` (special case of Erdős 257).
- (to be filled as consulted)

## Lean sources tried

(each attempt: what, `/check` id, verdict, exact errors)

## Check / precheck / PR ids

(none yet)

## Check / precheck / PR ids (summary)

| What | Id |
|---|---|
| Tutorial precheck (token) | `01M2QV7PSRJMPA9TRGMHDZRD24`, pass |
| Identity | pseudonym `agent-erdos69-1b25`, id `01M2QVFJR8MZTK2W0GF8FXA8JW` |
| `/check` on erdos-69 (refused, products stale) | log `01M2QV3KY85BJRF4JX3S49TKG8` |
| `/check` on erdos-257 (user_error, environment retired) | log `01M2QV94PGR5PRX4A3DFS1K55D` |
| AXLE direct, lean-4.33.1: skel1 / skel2 / skel3 / partial | `be7fd1b9-…6641` / `ce4e34c4-…242f` / `5f74ffa6-…24b4` / `c44a1edc-…525f1b`, all `okay: true` |
| AXLE probes | `361f2d6c-…90d9`, `b8fc16cb-…b22d`, `1587eb89-…dec2`, `126d8091-…f4f5` |
| Annex | id `01M2QVJ3T0D1V6BXW4G01VZVVR`, **PR #75**, hash `84315a5968f2b6dd9faf3e94d5018bb468eb448040fde6aea1c9be90f4746354` |
| Owned precheck of the partial | **`01M2QVJS9GQRACNP695KTN4DE7`**, pass, signed `service` |
| Submission | **`01M2QVSP00T8W7W39CBZF2WCN2`**, **PR #77**, `artifact_type: partial` |

## State

**Partial PR open, gate green (#77)**: the sandbox gate job passed (verdict `pass`, mode
`partial`); the pull request is `blocked` only on step 9, the non-author approving review, which
is the lead's act and re-runs in seconds. The annex PR #75 is also open and green. Nothing on the
graph was pushed, merged or closed by me; the graph's main working tree was not touched (reads
via `git show origin/main:…` only). Deliverable (2) of the brief is met; deliverable (1), a full
proof, was not attempted beyond the shift lemma in the timebox (~25 minutes of wall clock used
from the service's 14:03 to 14:27; the rest of the budget went to the tooling findings).

## Next (for the lead / a successor)

1. **Approve step 9 on PR #77** (a non-author approving review; `gh pr review 77 --approve` by
   the owner, or the dismiss-and-approve sequence F07-T17's check uses), which re-runs only the
   `step 9` job; then the run is green end to end. Nothing else is needed from the prover side.
2. **Merge order: #75 (annex) before #77 (partial).** `check_annex_citation` runs in the
   post-merge job (`gate/opn_gate/postmerge.py:478`), not in the PR gate, so #77 can be green with
   #75 unmerged, but merging #77 first makes its post-merge job refuse `annex-uncited` and create
   no children. Sequence: merge #75 → wait for its bot commit → update #77's branch if BEHIND →
   merge #77 → wait for its bot commit.
3. **What the merge produces**: two child nodes, `erdos-69--h1` (the Lambert identity,
   `∑' n, ω n / 2^n = ∑' p : Nat.Primes, 1 / (2^p − 1)`, no hypotheses, origin `skeleton-hole`)
   and `erdos-69--h2` (`Irrational (∑' p : Nat.Primes, 1/(2^p − 1))` **with `h_lambert` as a
   hypothesis**, F11-Q22), both `blocked: witness-missing` until witnessed via
   `POST /proposals/witness`. h1's witness is `True`; **h2's witness is a proof of h1** (the
   inherited hypothesis is a closed proposition, so step 7 asks for a proof of it). Watch for
   F07-Q19 on h2: its statement carries an unused hypothesis binder, and if `unused-binder` (or any
   checker) flags it, the job writes no `acknowledged_hazards`, and admission would refuse every
   submission against h2 — check h2's `META.yaml` after the bot commit, and read the post-merge
   run's log rather than its conclusion.
4. **If the gate on #77 is red**: read the run log (`gh run view --repo thisisanameforsure/open_proof_network_graph --log`)
   and compare with the precheck, which passed the same bundle at graph commit `1f9fb28` — a
   difference is the workflow's, not the Lean's (e.g. a BEHIND base, the pin at `0401858` vs the
   precheck's checkout). Do not resubmit before reading it.
5. **Closing the Lambert hole (h1) later**, with the blocks verified above ((a)–(d) at 14:17): let
   `f : Nat.Primes → ℕ → ℝ`, `f p n = if (p:ℕ) ∣ n + 1 then (1/2)^(n+1) else 0` (index shifted so
   `n + 1 ≥ 1`; with `n` itself every prime divides 0 and the column is not summable). Then
   (i) `∑' p, f p n = ω (n+1) / 2^(n+1)` by (d) then (c); (ii) `∑' n, f p n = ∑' k, ((1/2)^p)^(k+1)`
   by `tsum_eq_tsum_of_ne_zero_bij` with `k ↦ p*(k+1) − 1`, then (a); (iii) summability of
   `Function.uncurry f` on `Nat.Primes × ℕ` from `summable_prod_of_nonneg` (rows dominated by
   `(1/2)^(n+1)`, column sums `≤ 2·(1/2)^p`, summable over the primes by (b)); (iv)
   `Summable.tsum_comm` swaps; (v) the proved `hshift`/`hsum` in the partial finish. Budget an
   hour of AXLE rounds; `exact?` times out on subtype-summability goals, so give it the term.
6. **Closing the irrationality hole (h2)** is the research-grade part (Erdős 1948); no attempt was
   made in the timebox. The literature route is in the annex text and the prior-art list.
7. **Tooling finding for the network (not the graph)**: `gate/hosted-checkers.yaml` maps the pin
   to AXLE `lean-4.33.0`, which AXLE has retired for `lean-4.33.1`; until it is changed every
   `POST /check` on a Mathlib target answers a `user_error` and `check_lean` on the MCP is dead
   for agents. One-line fix plus the environment probe as evidence (see 14:13).

## Continuation (Mike's "keep working", ~45 min from 14:3x)

- **Hole 1, the Lambert identity, is FULLY PROVED** (`h1-full.lean`; AXLE
  `eb8e1cb2-1af6-4431-9a20-5cd6a326dc52`, `okay: true`, no warnings, 967 ms; axioms exactly
  `[propext, Classical.choice, Quot.sound]`, `606c83fd-87d8-46b8-a03b-fbeacfea1eaa`). Route:
  `f p n = if p ∣ n+1 then (1/2)^(n+1) else 0` over `Nat.Primes × ℕ`; rows summable by
  domination; columns `∑' n, f p n = ∑' k, ((1/2)^p)^(k+1)` by `tsum_eq_tsum_of_ne_zero_bij`
  with `k ↦ p*k + (p−1)` (injective by `Nat.eq_of_mul_eq_mul_left`; onto the support since
  `p ∣ n+1` gives `n+1 = p*(k+1)`), then `= 1/(2^p − 1)`; `Summable (Function.uncurry f)` from
  `summable_prod_of_nonneg` with the column bound `1/(2^p−1) ≤ 2·(1/2)^p` and `Summable.subtype`;
  `Summable.tsum_comm` swaps; per-n collapse `∑' p, f p n = ω(n+1)/2^(n+1)` over an explicit
  `Finset Nat.Primes`; the shift by one via `Summable.tsum_eq_zero_add` and `ω 0 = 0`. Six pieces
  first checked as separate examples in one round (`h1-pieces.lean`,
  `99c827ab-4bc9-4226-bdaf-df6cda55ee19`, all clean), then assembled — the assembly passed first
  time. The whole text is in "Hole proofs, verbatim" below.
- **Hole 2: the integrality step is proved and the partial elaborates** with one hole
  (`h2-partial.lean`; AXLE `b379a848-096f-4dfa-89f0-d7feb52fd63c`, only `declaration uses
  sorry`). Shape: with `E N := ∑' j, ω(N+1+j)/2^(j+1)` (the tail after N, rescaled by `2^N`):
  hole B `∀ b, 0 < b → ∃ N, ∀ z : ℤ, b * E N ≠ z` (Erdős's CRT choice of N — the research part,
  not attempted); proved A `∀ q : ℚ, (q:ℝ) = ∑' n, ω n/2^n → ∀ N, ∃ z : ℤ, q.den * E N = z` with
  `z = 2^N·q.num − ∑_{n≤N} q.den·ω(n)·2^(N−n)` (`Summable.sum_add_tsum_nat_add (N+1)`,
  `tsum_div_const`, `eq_sub_of_add_eq'`, `Rat.mul_den_eq_num` cast, `pow_sub₀`, and the final
  identity by `linear_combination (2:ℝ)^N * hS + hA`); assembly `rintro ⟨q, hq⟩`, B at `q.den`, A
  at `hq.trans h_lambert.symm`. Two attempts before it closed, both recorded: a `rw` chain died
  on `mul_sub`'s distribution (`4fa86344-…74ca`: "Did not find an occurrence of the pattern
  ?a * (?b * ?c)"), then a redundant `ring` after `field_simp` ("No goals to be solved",
  `63d59a5c-…30d9`). Hole B is placed *first* so that no proved `have` precedes it; its closed
  type will still carry the child's own `h_lambert` binder (the extractor closes over the
  theorem's binders).
- Graph state at 14:5x: #75 (annex) and #76 merged with bot commits; **#77 merged** (`93784e8`)
  but its `gate: #77 pass` bot commit had not landed, so `erdos-69--h1`/`--h2` did not exist yet;
  #78, #79 still open (the lead's sequence). A read-only watcher (background, fetch every 20 s)
  reports when `targets/erdos-69/nodes/erdos-69--h1/Statement.lean` appears on `origin/main`.
  No pull request was touched, per the brief. The network's `POST /check` still mapped to
  `lean-4.33.0` at 14:3x (log `01M2QWTAXG0VPYZ57YA3301YN5`, answered with lint only), so AXLE
  direct remained the checker.

### Next, continued (supersedes item 5 above)

1. When the lead says the sequence is complete and the children exist: read
   `targets/erdos-69/nodes/erdos-69--h1/{Statement.lean,META.yaml}` and `…--h2/…` on
   `origin/main`; note any `hazards` without `acknowledged_hazards` (F07-Q19; the `unused-binder`
   checker may flag h2's `h_lambert`). If h1's `META.yaml` says `blocked: witness-missing`, the
   hole must first be witnessed via `POST /proposals/witness` (h1 has no hypotheses: witness
   `True`) and that PR merged (lead) before a proof can be admitted — check the guide's "After the
   skeleton merges" section: witness → ready → proof.
2. Hole 1: `Proof.lean` = the child's `Statement.lean` with the body replaced by the verbatim
   block below; `POST /check` in `verify` mode if the mapping is fixed, else AXLE direct;
   `POST /precheck` (token in the scratchpad, `artifact_type: proof`, bundle path
   `targets/erdos-69/nodes/erdos-69--h1/Proof.lean`); `POST /submissions` as `proof`; gate green;
   stop. If admission/precheck refuses on an unacknowledged hazard, type it verbatim here and stop.
3. Hole 2: the partial below as `attempts/<ts>-agent-erdos69-1b25-partial.lean` on `erdos-69--h2`,
   `artifact_type: partial`; its witness first if `witness-missing` (h2's witness is a proof of
   h1 — the block below is that proof, wrapped as `⟨proof, trivial⟩`-style per the witness type
   `gate/lean/OpnGate/WitnessType.lean` computes; read that file before writing it).
4. Hole B (the mathematics that remains): see the annex; a Lean route would fix `b`, take
   `K` large, `N ≡ 0 (mod ∏_{p ≤ K} p)` by CRT so `ω(N+k) = ω_{≤K}(k) + ω_{>K}(N+k)`, and bound
   `b·E N` between consecutive integers; nobody has written this in Lean.

## Prior art consulted (R14 c) — final

- `engineering/onramp/calibration/upstream/69.lean` (the registry file, c7f31d5f): the statement
  and Tao's remark, as `erdos_69.variants.specialisation_of_erdos_257`, that
  `∑ ω(n)/2^n = ∑_p 1/(2^p − 1)`.
- `engineering/onramp/calibration/README.md` and `erdos-69/record.yaml`: the grade and the two-lemma
  route (Lambert identity; Erdős 1948, J. Indian Math. Soc. 12, 63–66).
- The prompt's hint that some routes go through `∑_p ∑_k 2^{−pk}` and count integers of the form
  pk in a residue window. No web page, paper or public formalization was fetched during the run
  (timebox); the Lean is my own, with names confirmed on AXLE. Erdős's argument is recalled, not
  re-read: the annex says so by calling Lemma 2 a sketch.

## Lean sources tried (all in the scratchpad; header = live `Statement.lean` verbatim)

| File | What | Verdict (AXLE lean-4.33.1) |
|---|---|---|
| `skel1.lean` | two holes, assembly `rw [h_lambert]; exact h_irr` (shifted identity as hole 1) | okay, `declaration uses sorry` only |
| `probe1.lean`–`probe4.lean` | `#check`/`exact?` name probes and the building blocks (a)–(d) | see 14:14 and 14:17; every error quoted there |
| `skel2.lean` | shift proved (hbound/hsum/hshift), holes = unshifted identity + irrationality | okay, plus one unused simp-arg lint |
| `skel3.lean` | lint removed | okay, `declaration uses sorry` only |
| `partial.lean` | skel3 with `-- annex: 84315a59…` | okay; precheck pass; submitted as PR #77 |


## Hole proofs, verbatim (continuation; both checked on AXLE lean-4.33.1 with `import Mathlib` and the statement's `open scoped ArithmeticFunction.omega`)

### Hole 1 — the Lambert identity, FULL PROOF (`h1-full.lean`, AXLE `eb8e1cb2-1af6-4431-9a20-5cd6a326dc52`, `okay: true`, no warnings; axioms `[propext, Classical.choice, Quot.sound]`, AXLE `606c83fd-87d8-46b8-a03b-fbeacfea1eaa`)

To submit on `erdos-69--h1`: take the child's `Statement.lean` byte for byte, replace its `sorry`
body with the tactic block below (everything after `:= by`), and precheck as `proof`.

```lean
example : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := by
  -- (a) the per-prime geometric series
  have hgeom : ∀ p : ℕ, 2 ≤ p →
      ∑' k : ℕ, ((1 / 2 : ℝ) ^ p) ^ (k + 1) = 1 / (2 ^ p - 1) := by
    intro p hp
    have hr0 : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ p := by positivity
    have hr1 : (1 / 2 : ℝ) ^ p < 1 := pow_lt_one₀ (by norm_num) (by norm_num) (by omega)
    have h2 : (1 : ℝ) < 2 ^ p := one_lt_pow₀ (by norm_num) (by omega)
    have h3 : (2 : ℝ) ^ p - 1 ≠ 0 := by linarith
    simp_rw [pow_succ]
    rw [tsum_mul_right, tsum_geometric_of_lt_one hr0 hr1, one_div, inv_pow]
    field_simp
  -- (D) the multiples of a prime p, reindexed
  have hD : ∀ p : ℕ, p.Prime →
      ∑' n : ℕ, (if p ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)
        = ∑' k : ℕ, ((1 / 2 : ℝ) ^ p) ^ (k + 1) := by
    intro p hp
    have hp1 : 1 ≤ p := hp.one_lt.le
    have hk : ∀ k : ℕ, p * k + (p - 1) + 1 = p * (k + 1) := by
      intro k
      rw [Nat.mul_succ, Nat.add_assoc, Nat.sub_add_cancel hp1]
    have hg : ∀ k : ℕ, ((1 / 2 : ℝ) ^ p) ^ (k + 1) ≠ 0 := fun k => by positivity
    refine tsum_eq_tsum_of_ne_zero_bij (fun k => p * k.1 + (p - 1)) ?_ ?_ ?_
    · intro k k' h
      have h' : p * k.1 + (p - 1) = p * k'.1 + (p - 1) := h
      exact Subtype.ext (Nat.eq_of_mul_eq_mul_left hp.pos (Nat.add_right_cancel h'))
    · intro n hn
      have hn' := Function.mem_support.1 hn
      have hdvd : p ∣ n + 1 := by
        by_contra hnot
        exact hn' (if_neg hnot)
      obtain ⟨m, hm⟩ := hdvd
      rcases m with _ | k
      · omega
      · refine ⟨⟨k, hg k⟩, ?_⟩
        show p * k + (p - 1) = n
        rw [← hk k] at hm
        exact (Nat.add_right_cancel hm).symm
    · rintro ⟨k, -⟩
      show (if p ∣ p * k + (p - 1) + 1 then (1 / 2 : ℝ) ^ (p * k + (p - 1) + 1) else 0)
        = ((1 / 2 : ℝ) ^ p) ^ (k + 1)
      rw [hk k, if_pos (dvd_mul_right p (k + 1)), pow_mul]
  -- the column sums
  have hcol : ∀ p : Nat.Primes,
      ∑' n : ℕ, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)
        = 1 / (2 ^ (p : ℕ) - 1) := by
    intro p
    rw [hD p p.2, hgeom p p.2.two_le]
  -- (R) each row is summable
  have hR : ∀ p : ℕ, Summable (fun n : ℕ => if p ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0) := by
    intro p
    refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_)
      (summable_geometric_of_lt_one (by norm_num) (by norm_num) : Summable fun n : ℕ => (1 / 2 : ℝ) ^ n)
    · split_ifs <;> positivity
    · split_ifs
      · exact pow_le_pow_of_le_one (by norm_num) (by norm_num) (Nat.le_succ n)
      · positivity
  -- (Cb), (Sc): the column sums are summable over the primes
  have hb : ∀ p : ℕ, p.Prime → (1 : ℝ) / (2 ^ p - 1) ≤ 2 * (1 / 2 : ℝ) ^ p := by
    intro p hp
    have h2p : (2 : ℝ) ≤ 2 ^ p := by
      calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
        _ ≤ 2 ^ p := pow_le_pow_right₀ (by norm_num) hp.one_lt.le
    have hpos : (0 : ℝ) < 2 ^ p / 2 := by positivity
    calc (1 : ℝ) / (2 ^ p - 1) ≤ 1 / (2 ^ p / 2) := one_div_le_one_div_of_le hpos (by linarith)
      _ = 2 * (1 / 2 : ℝ) ^ p := by rw [one_div_div, one_div_pow, mul_one_div]
  have hSc : Summable (fun p : Nat.Primes => (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := by
    have hg : Summable (fun n : ℕ => 2 * (1 / 2 : ℝ) ^ n) :=
      (summable_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left 2
    refine Summable.of_nonneg_of_le (fun p => ?_) (fun p => ?_) (hg.subtype (fun n => n.Prime))
    · have : (1 : ℝ) < 2 ^ (p : ℕ) := one_lt_pow₀ (by norm_num) p.2.ne_zero
      exact div_nonneg zero_le_one (by linarith)
    · exact hb p p.2
  -- (C) the double family is summable
  have hC : Summable (Function.uncurry
      (fun (p : Nat.Primes) (n : ℕ) => if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)) := by
    have hnn : (0 : Nat.Primes × ℕ → ℝ) ≤ Function.uncurry
        (fun (p : Nat.Primes) (n : ℕ) => if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0) := by
      rintro ⟨p, n⟩
      show (0 : ℝ) ≤ (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)
      split_ifs <;> positivity
    refine (summable_prod_of_nonneg hnn).2 ⟨fun p => hR p, ?_⟩
    exact hSc.congr (fun p => (hcol p).symm)
  -- the swap
  have hswap : ∑' n : ℕ, ∑' p : Nat.Primes, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)
      = ∑' p : Nat.Primes, ∑' n : ℕ, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0) :=
    hC.tsum_comm
  -- (B) the per-n collapse
  have hBgen : ∀ m : ℕ, m ≠ 0 → ∀ c : ℝ,
      ∑' p : Nat.Primes, (if (p : ℕ) ∣ m then c else 0) = (ω m : ℝ) * c := by
    intro m hm c
    let S : Finset Nat.Primes :=
      m.primeFactors.attach.map ⟨fun p => ⟨p.1, (Nat.mem_primeFactors.1 p.2).1⟩,
        fun p q h => Subtype.ext (Subtype.mk.inj h)⟩
    have hmem : ∀ p : Nat.Primes, p ∈ S ↔ (p : ℕ) ∈ m.primeFactors := by
      intro p
      constructor
      · intro hp
        obtain ⟨q, -, rfl⟩ := Finset.mem_map.1 hp
        exact q.2
      · intro hp
        exact Finset.mem_map.2 ⟨⟨p.1, hp⟩, Finset.mem_attach _ _, Subtype.ext rfl⟩
    have hfin : ∀ p : Nat.Primes, p ∉ S → (if (p : ℕ) ∣ m then c else 0) = 0 := by
      intro p hp
      rw [if_neg]
      intro hdvd
      exact hp ((hmem p).2 (Nat.mem_primeFactors.2 ⟨p.2, hdvd, hm⟩))
    rw [tsum_eq_sum hfin]
    rw [Finset.sum_ite_of_true (fun p hp => (Nat.mem_primeFactors.1 ((hmem p).1 hp)).2.1)]
    rw [Finset.sum_const, nsmul_eq_mul]
    have hcard : S.card = m.primeFactors.card := by
      simp [S, Finset.card_map, Finset.card_attach]
    have hω : (m.primeFactors.card : ℝ) = ω m := by
      simp [ArithmeticFunction.cardDistinctFactors_apply]
      rfl
    rw [hcard, hω]
  have hB : ∀ n : ℕ,
      ∑' p : Nat.Primes, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0)
        = (ω (n + 1) : ℝ) / 2 ^ (n + 1) := by
    intro n
    rw [hBgen (n + 1) n.succ_ne_zero, one_div_pow, mul_one_div]
  -- the original series is summable (as in the partial)
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
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
    exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  -- assembly
  calc ∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' n : ℕ, (ω (n + 1) : ℝ) / 2 ^ (n + 1) := by
        rw [hsum.tsum_eq_zero_add]
        simp
    _ = ∑' n : ℕ, ∑' p : Nat.Primes, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0) :=
        tsum_congr (fun n => (hB n).symm)
    _ = ∑' p : Nat.Primes, ∑' n : ℕ, (if (p : ℕ) ∣ n + 1 then (1 / 2 : ℝ) ^ (n + 1) else 0) := hswap
    _ = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := tsum_congr hcol
```

### Hole 2 — a PARTIAL: hole B (Erdős's choice of N) is the only hole; the integrality step A is proved (`h2-partial.lean`, AXLE `b379a848-096f-4dfa-89f0-d7feb52fd63c`, `okay: true`, only `declaration uses sorry`)

To submit on `erdos-69--h2`: the child's statement carries `h_lambert` as a hypothesis (F11-Q22);
take its `Statement.lean` byte for byte and replace the `sorry` body with the block below, adapting
the hypothesis name to the child's binder name if the post-merge job renamed it. Precheck and
submit as `partial` at `attempts/<ts>-<pseudonym>-partial.lean`.

```lean
example (h_lambert : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) :
    Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := by
  -- Hole B (Erdős 1948): for every b ≥ 1 there is an N whose rescaled tail
  -- ∑_j ω(N+1+j)/2^(j+1) = 2^N · ∑_{n > N} ω(n)/2^n, times b, is not an integer — the choice
  -- of N by the Chinese remainder theorem that controls ω(N+1), ω(N+2), … .
  have hB : ∀ b : ℕ, 0 < b → ∃ N : ℕ, ∀ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) ≠ z := sorry
  -- Integrality (proved): if the series is the rational q, every rescaled tail times q.den is an
  -- integer, namely 2^N · q.num − ∑_{n ≤ N} q.den · ω(n) · 2^(N−n).
  have hA : ∀ q : ℚ, (q : ℝ) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n → ∀ N : ℕ,
      ∃ z : ℤ, (q.den : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
    intro q hq N
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
    have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
      refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
      exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
        (summable_geometric_of_lt_one (by norm_num) (by norm_num))
    have h2N : (2 : ℝ) ^ N ≠ 0 := by positivity
    -- the tail as 2^N times (the sum minus its first N+1 terms)
    have htail : ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
        = 2 ^ N * (∑' n : ℕ, (ω n : ℝ) / 2 ^ n - ∑ n ∈ Finset.range (N + 1), (ω n : ℝ) / 2 ^ n) := by
      have h := hsum.sum_add_tsum_nat_add (N + 1)
      have h2 : ∑' i : ℕ, (ω (i + (N + 1)) : ℝ) / 2 ^ (i + (N + 1))
          = (∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)) / 2 ^ N := by
        rw [← tsum_div_const]
        refine tsum_congr (fun j => ?_)
        rw [add_comm j (N + 1), show N + 1 + j = j + 1 + N by ring, pow_add, div_div]
      rw [h2] at h
      have h3 := eq_sub_of_add_eq' h
      rw [← h3]
      field_simp
    -- the integer
    have hnum : (q.den : ℝ) * (q : ℝ) = q.num := by
      have := congrArg (Rat.cast : ℚ → ℝ) (Rat.mul_den_eq_num q)
      push_cast at this
      linarith
    have hS : (q.den : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = q.num := by rw [← hq]; exact hnum
    have hA : ∑ n ∈ Finset.range (N + 1), (q.den : ℝ) * (ω n : ℝ) * 2 ^ (N - n)
        = 2 ^ N * ((q.den : ℝ) * ∑ n ∈ Finset.range (N + 1), (ω n : ℝ) / 2 ^ n) := by
      rw [Finset.mul_sum, Finset.mul_sum]
      refine Finset.sum_congr rfl (fun n hn => ?_)
      have hn' : n ≤ N := Nat.lt_succ_iff.1 (Finset.mem_range.1 hn)
      rw [pow_sub₀ (2 : ℝ) two_ne_zero hn']
      field_simp
    refine ⟨2 ^ N * q.num - ∑ n ∈ Finset.range (N + 1), (q.den : ℤ) * ω n * 2 ^ (N - n), ?_⟩
    push_cast
    rw [htail]
    linear_combination (2 : ℝ) ^ N * hS + hA
  -- Assembly
  rintro ⟨q, hq⟩
  obtain ⟨N, hN⟩ := hB q.den q.den_pos
  obtain ⟨z, hz⟩ := hA q (hq.trans h_lambert.symm) N
  exact hN z hz
```
