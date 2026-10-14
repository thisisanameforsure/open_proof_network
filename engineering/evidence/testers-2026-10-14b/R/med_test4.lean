import Mathlib

/-
In this Lean file, produced by Aristotle from Harmonic
(aristotle-harmonic@harmonic.fun), we give a proof of the best known lower bound
for Erdős Problem 451 (https://www.erdosproblems.com/451). More precisely, we
show the following result (titled `main_theorem` all the way at the
bottom of the file):

For all sufficiently large integers `k` and all integers `n` with

`2k < n ≤ exp(log²k / (20 log log k))`,

the product `(n-k)(n-k+1)⋯(n-1)` is, with `θ = 21/40`, divisible by some prime
`p ∈ (k, k + 3k^θ)`.

The proof relies on a well-known result by Baker, Harman and Pintz on primes in
short intervals, which is stated as `axiom bhp` down below. Apart from this
single axiom, the formalization is completely self-contained.

In particular, as the proof uses a result by Konyagin on function values close
to rationals, this result is also proved along the way as `konyagin_thm`.

ChatGPT came up with the proof of `main_theorem`, and for more
information one can check out the short paper that Quanyu Tang and I wrote.

W. van Doorn and Q. Tang, Consecutive integers free of certain prime factors. 
arXiv:2606.19863 (2026).

Lean version: leanprover/lean4:v4.28.0
-/

noncomputable section

open scoped BigOperators
open Finset Filter
open scoped BigOperators Nat

/-- The product `(n-k)(n-k+1)⋯(n-1) = ∏_{i=1}^{k} (n - i)`. -/
def Pprod (k : ℕ) (n : ℤ) : ℤ := ∏ i ∈ Finset.Icc 1 k, (n - (i : ℤ))

/-- The exponent `θ = 21/40`. -/
def theta : ℝ := 21 / 40

/-- The number of primes `p` (as positive integers) with `a < p < b`. -/
def primeCard (a b : ℝ) : ℕ :=
  ((Finset.Ioo ⌊a⌋ ⌈b⌉).filter
    (fun p : ℤ => 0 < p ∧ (p.natAbs).Prime ∧ a < (p : ℝ) ∧ (p : ℝ) < b)).card
lemma theta_pos : (0 : ℝ) < theta := by unfold theta; norm_num
lemma theta_lt_one : theta < 1 := by unfold theta; norm_num

/-- If a prime `p` divides one of the factors `n - i` with `1 ≤ i ≤ k`, then it
divides `P`. -/
lemma dvd_Pprod_of_factor (k : ℕ) (n : ℤ) (p : ℤ) (i : ℕ)
    (hi : i ∈ Finset.Icc 1 k) (hp : p ∣ (n - (i : ℤ))) : p ∣ Pprod k n := by
  unfold Pprod
  exact hp.trans (Finset.dvd_prod_of_mem (fun i : ℕ => (n - (i : ℤ))) hi)

/-
If `p ∣ t` for some integer `t` strictly between `n - k` and `n`, then `p`
divides `P` (as `t` equals one of the factors `n - i`).
-/
lemma dvd_Pprod_of_mem (k : ℕ) (n : ℤ) (p : ℤ) (t : ℤ)
    (h1 : n - (k : ℤ) < t) (h2 : t < n) (hpt : p ∣ t) : p ∣ Pprod k n := by
  convert dvd_Pprod_of_factor k n p ( Int.toNat ( n - t ) ) ?_ ?_ using 1 <;> norm_num [ Int.toNat_of_nonneg ( sub_nonneg.mpr h2.le ) ];
  · omega;
  · assumption

/-
If a prime `p ∈ (k, k + k^θ)` is such that `n/p` is far from any integer
(distance `≥ 1/k^{1-θ}`), then `p` divides `P`.
-/
lemma dvd_from_far (k : ℕ) (n : ℤ) (p : ℕ) (hk1 : 1 ≤ k) (hp0 : 0 < p)
    (hkp : (k : ℝ) < p) (hpk : (p : ℝ) < (k : ℝ) + (k : ℝ) ^ theta)
    (hfar : 1 / (k : ℝ) ^ (1 - theta) ≤ |(n : ℝ) / (p : ℝ) - round ((n : ℝ) / (p : ℝ))|) :
    (p : ℤ) ∣ Pprod k n := by
  -- Set `i := n % (p : ℤ)` and `j := i.toNat`.
  set i := n % (p : ℤ)
  set j := i.toNat
  have hj : (j : ℤ) = i := by
    exact Int.toNat_of_nonneg <| Int.emod_nonneg _ <| by positivity;
  -- From `hfar`, we have `(p:ℝ)/(k:ℝ)^(1-theta) ≤ (min i (p-i) : ℝ)`.
  have h_frac : (p : ℝ) / (k : ℝ) ^ (1 - theta) ≤ min (i : ℝ) ((p : ℝ) - i) := by
    have h_frac : |(n : ℝ) / p - round ((n : ℝ) / p)| = min ((i : ℝ) / p) (1 - (i : ℝ) / p) := by
      have h_frac : Int.fract ((n : ℝ) / p) = (i : ℝ) / p := by
        rw [ Int.fract_eq_iff ];
        field_simp;
        norm_cast;
        exact ⟨ by norm_num; exact Int.emod_nonneg _ ( by positivity ), Int.emod_lt_of_pos _ ( by positivity ), n / p, by linarith [ Int.emod_add_mul_ediv n p ] ⟩;
      rw [ ← h_frac, abs_sub_round_eq_min ];
    have hp' : (0:ℝ) < p := by exact_mod_cast hp0
    have h1 := mul_le_mul_of_nonneg_left hfar hp'.le
    rw [h_frac, mul_min_of_nonneg _ _ hp'.le] at h1
    have e1 : (p:ℝ) * ((i:ℝ)/p) = i := by field_simp
    have e2 : (p:ℝ) * (1 - (i:ℝ)/p) = p - i := by field_simp
    rw [e1, e2] at h1
    calc (p:ℝ) / (k:ℝ)^(1-theta) = p * (1 / (k:ℝ)^(1-theta)) := by ring
      _ ≤ _ := h1
  -- So `1 ≤ i ≤ k`.
  have h_i_bounds : 1 ≤ i ∧ i ≤ k := by
    have h_i_bounds : (p : ℝ) / (k : ℝ) ^ (1 - theta) > (k : ℝ) ^ theta := by
      rw [ gt_iff_lt, lt_div_iff₀ ] <;> norm_num at *;
      · rw [ ← Real.rpow_add ] <;> norm_num ; linarith [ ( by norm_cast : ( k : ℝ ) + 1 ≤ p ) ];
        grind +extAll;
      · positivity;
    constructor <;> norm_num at *;
    · exact Int.le_of_lt_add_one ( by rw [ ← @Int.cast_lt ℝ ] ; push_cast; linarith [ show ( k : ℝ ) ^ theta ≥ 1 by exact Real.one_le_rpow ( mod_cast hk1 ) ( by exact div_nonneg ( by norm_num ) ( by norm_num ) ) ] );
    · exact Int.le_of_lt_add_one ( by rw [ ← @Int.cast_lt ℝ ] ; push_cast; linarith );
  convert dvd_Pprod_of_factor k n ( p : ℤ ) j _ _ using 1;
  · grind;
  · exact ⟨ n / p, by linarith [ Int.emod_add_mul_ediv n p ] ⟩

/-- The set of integers `m ∈ (k, k + k^θ)` such that `n/m` is within `1/k^{1-θ}`
of an integer. Its cardinality is exactly the quantity `K` bounded by
`konyagin_application`. -/
def badSet (k : ℕ) (n : ℤ) : Finset ℤ :=
  (Finset.Ioo (k : ℤ) ((k : ℤ) + ⌊(k : ℝ) ^ theta⌋ + 2)).filter
    (fun m : ℤ => (m : ℝ) < (k : ℝ) + (k : ℝ) ^ theta ∧
      |(n : ℝ) / (m : ℝ) - round ((n : ℝ) / (m : ℝ))| < 1 / (k : ℝ) ^ (1 - theta))
lemma exists_far_prime (k : ℕ) (n : ℤ) (hk1 : 1 ≤ k)
    (hcount : ((badSet k n).card : ℝ) < (primeCard (k : ℝ) ((k : ℝ) + (k : ℝ) ^ theta) : ℝ)) :
    ∃ p : ℕ, p.Prime ∧ (k : ℝ) < p ∧ (p : ℝ) < (k : ℝ) + (k : ℝ) ^ theta ∧
      (p : ℤ) ∣ Pprod k n := by
  norm_cast at *;
  contrapose! hcount;
  refine' le_trans ( Finset.card_le_card _ ) _;
  exact Finset.image ( fun m : ℤ => m ) ( Finset.filter ( fun m : ℤ => ( m : ℝ ) < ( k : ℝ ) + ( k : ℝ ) ^ theta ∧ |( n : ℝ ) / m - round ( ( n : ℝ ) / m )| < 1 / ( k : ℝ ) ^ ( 1 - theta ) ) ( Finset.Ioo ( k : ℤ ) ( ( k : ℤ ) + ⌊ ( k : ℝ ) ^ theta⌋ + 2 ) ) );
  · intro p hp; simp_all +decide ;
    refine' ⟨ _, _ ⟩;
    · linarith [ show ⌈ ( k : ℝ ) ^ theta⌉ ≤ ⌊ ( k : ℝ ) ^ theta⌋ + 1 by exact Int.ceil_le_floor_add_one _ ];
    · exact Classical.not_not.1 fun h => hcount ( Int.natAbs p ) hp.2.2.1 ( by linarith [ abs_of_pos hp.2.1 ] ) ( by simpa [ abs_of_pos hp.2.1 ] using hp.2.2.2.2 ) ( by simpa [ abs_of_pos hp.2.1 ] using dvd_from_far k n ( Int.natAbs p ) hk1 ( by linarith [ abs_of_pos hp.2.1 ] ) ( by simpa [ abs_of_pos hp.2.1 ] using hp.2.2.2.1 ) ( by simpa [ abs_of_pos hp.2.1 ] using hp.2.2.2.2 ) ( by simpa [ abs_of_pos hp.2.1 ] using h ) );
  · unfold badSet; aesop;

/-
Core asymptotic fact: `(log x)^b · x^{-c} → 0` for `c > 0`.
-/
lemma tendsto_log_rpow_mul_rpow_neg (b c : ℝ) (hc : 0 < c) :
    Filter.Tendsto (fun x : ℝ => (Real.log x) ^ b * x ^ (-c)) Filter.atTop (nhds 0) := by
  -- Use the fact that `Real.log x ^ b` is little-o of `x ^ c` as `x` tends to infinity.
  have h_log : (fun x : ℝ => Real.log x ^ b) =o[Filter.atTop] (fun x : ℝ => x ^ c) :=
    isLittleO_log_rpow_rpow_atTop b hc
  convert h_log.tendsto_div_nhds_zero.congr' _ using 1;
  filter_upwards [ Filter.eventually_gt_atTop 0 ] with x hx using by rw [ div_eq_mul_inv, Real.rpow_neg hx.le ] ;

/-
A sub-`tt` power times any log-power is eventually dominated by
`C · k^tt / log k`, for `C > 0` and `α < tt`.
-/
lemma poly_log_lt (A α β tt : ℝ) (hα : α < tt) (C : ℝ) (hC : 0 < C) :
    ∀ᶠ k : ℕ in Filter.atTop,
      A * (k : ℝ) ^ α * (Real.log k) ^ β ≤ C * (k : ℝ) ^ tt / Real.log k := by
  -- Let's choose any $C > 0$ and derive a contradiction.
  have h_lim : Filter.Tendsto (fun k : ℕ => (A * (k : ℝ) ^ α * (Real.log k) ^ β) / ((k : ℝ) ^ tt / (Real.log k))) Filter.atTop (nhds 0) := by
    -- Simplify the expression inside the limit.
    suffices h_simp : Filter.Tendsto (fun k : ℕ => A * (Real.log k) ^ (β + 1) * (k : ℝ) ^ (α - tt)) Filter.atTop (nhds 0) by
      refine h_simp.congr' ?_;
      filter_upwards [ Filter.eventually_gt_atTop 1 ] with k hk ; rw [ Real.rpow_sub ( by positivity ) ] ; ring_nf;
      rw [ Real.rpow_add ( Real.log_pos ( Nat.one_lt_cast.mpr hk ) ), Real.rpow_one ] ; norm_num ; ring;
    have := @tendsto_log_rpow_mul_rpow_neg ( β + 1 ) ( tt - α ) ?_;
    · convert this.const_mul A |> Filter.Tendsto.comp <| tendsto_natCast_atTop_atTop using 2 <;> norm_num ; ring;
    · linarith;
  filter_upwards [ h_lim.eventually ( gt_mem_nhds hC ), Filter.eventually_gt_atTop 1 ] with k hk₁ hk₂;
  rw [ div_lt_iff₀ ( div_pos ( Real.rpow_pos_of_pos ( Nat.cast_pos.mpr hk₂.le ) _ ) ( Real.log_pos ( Nat.one_lt_cast.mpr hk₂ ) ) ) ] at hk₁ ; ring_nf at hk₁ ⊢ ; linarith

/-
The `θ`-power times `(log k)^{-2}` is eventually dominated by `C · k^tt / log k`.
-/
lemma poly_log_lt_eq (A tt : ℝ) (C : ℝ) (hC : 0 < C) :
    ∀ᶠ k : ℕ in Filter.atTop,
      A * (k : ℝ) ^ tt * (Real.log k) ^ (-(2 : ℝ)) ≤ C * (k : ℝ) ^ tt / Real.log k := by
  -- We'll use that $A \leq C \cdot \log k$ for sufficiently large $k$.
  have h_log_bound : ∀ᶠ k : ℕ in Filter.atTop, A ≤ C * Real.log k := by
    exact Filter.eventually_atTop.mpr ⟨ ⌈Real.exp ( A / C ) ⌉₊ + 1, fun k hk => by nlinarith [ Nat.le_ceil ( Real.exp ( A / C ) ), Real.log_exp ( A / C ), Real.log_le_log ( by positivity ) ( show ( k :ℝ ) ≥ Real.exp ( A / C ) by exact le_of_lt ( Nat.lt_of_ceil_lt hk ) ), mul_div_cancel₀ A hC.ne' ] ⟩;
  filter_upwards [ h_log_bound, Filter.eventually_gt_atTop 1 ] with k hk₁ hk₂;
  have hl : 0 < Real.log k := Real.log_pos (by exact_mod_cast hk₂)
  have hp : 0 ≤ (k:ℝ)^tt := Real.rpow_nonneg (Nat.cast_nonneg _) _
  rw [Real.rpow_neg hl.le, Real.rpow_two]
  have e : A * (k:ℝ)^tt * (Real.log k ^ 2)⁻¹ = A * (k:ℝ)^tt / Real.log k / Real.log k := by
    field_simp
  rw [e, div_le_div_iff_of_pos_right hl, div_le_iff₀ hl]
  nlinarith [mul_le_mul_of_nonneg_right hk₁ hp]

/-
The `tt`-power times `(log k)^β` with `β < -1` is eventually dominated by
`C · k^tt / log k`.
-/
lemma poly_log_lt_logpow (A tt β : ℝ) (hβ : β < -1) (C : ℝ) (hC : 0 < C) :
    ∀ᶠ k : ℕ in Filter.atTop,
      A * (k : ℝ) ^ tt * (Real.log k) ^ β ≤ C * (k : ℝ) ^ tt / Real.log k := by
  have h_log_pow : Filter.Tendsto (fun k : ℕ => A * (Real.log k) ^ (β + 1)) Filter.atTop (nhds 0) := by
    simpa using tendsto_const_nhds.mul ( tendsto_rpow_neg_atTop ( by linarith : 0 < - ( β + 1 ) ) |> Filter.Tendsto.comp <| Real.tendsto_log_atTop.comp tendsto_natCast_atTop_atTop );
  filter_upwards [ h_log_pow.eventually ( gt_mem_nhds hC ), Filter.eventually_gt_atTop 1 ] with k hk₁ hk₂ ; rw [ le_div_iff₀ ( Real.log_pos <| Nat.one_lt_cast.mpr hk₂ ) ] ; ring_nf at *;
  convert mul_le_mul_of_nonneg_left hk₁.le ( Real.rpow_nonneg ( Nat.cast_nonneg k ) tt ) using 1 ; rw [ show ( 1 + β ) = β + 1 by ring, Real.rpow_add ( Real.log_pos <| Nat.one_lt_cast.mpr hk₂ ), Real.rpow_one ] ; ring

/-
If the count of primes in `(a, b)` is positive, there is a prime in `(a, b)`.
-/
lemma konyagin_finish (k : ℕ) (n : ℤ) (hk1 : 1 ≤ k) (C : ℝ)
    (hbhp : C * (k : ℝ) ^ theta / Real.log k ≤
      (primeCard (k : ℝ) ((k : ℝ) + (k : ℝ) ^ theta) : ℝ))
    (hcard : ((badSet k n).card : ℝ) < C * (k : ℝ) ^ theta / Real.log k) :
    ∃ p : ℕ, p.Prime ∧ (k : ℝ) < p ∧ (p : ℝ) < (k : ℝ) + 3 * (k : ℝ) ^ theta ∧
      (p : ℤ) ∣ Pprod k n := by
  obtain ⟨p, hp, hpk, hpb, hdvd⟩ := exists_far_prime k n hk1 (lt_of_lt_of_le hcard hbhp)
  refine ⟨p, hp, hpk, ?_, hdvd⟩
  have : (0 : ℝ) ≤ (k : ℝ) ^ theta := Real.rpow_nonneg (by positivity) _
  linarith

lemma eventually_le_rpow (p A : ℝ) (hp : 0 < p) :
    ∀ᶠ k : ℕ in Filter.atTop, A ≤ (k : ℝ) ^ p := by
  exact Filter.Tendsto.eventually_ge_atTop ( tendsto_rpow_atTop hp |> Filter.Tendsto.comp <| tendsto_natCast_atTop_atTop ) A

/-
`(log k)^2 < k` for all sufficiently large `k`.
-/
def medWindow (k : ℕ) : Finset ℤ :=
  (Finset.Ioo (k : ℤ) ((k : ℤ) + ⌊(k : ℝ) ^ theta⌋ + 2)).filter
    (fun m : ℤ => (m : ℝ) < (k : ℝ) + (k : ℝ) ^ theta)

/-- The `h`-fiber: window integers `m` with `n/m` within `1/k^{1-θ}` of `h`. -/
def medFiber (k : ℕ) (n : ℤ) (h : ℤ) : Finset ℤ :=
  (medWindow k).filter (fun m : ℤ => |(n : ℝ) / (m : ℝ) - (h : ℝ)| < 1 / (k : ℝ) ^ (1 - theta))

/-- The set of integers `h` between `⌊n/(k+k^θ)⌋` and `⌈n/k⌉`. -/
def medJ (k : ℕ) (n : ℤ) : Finset ℤ :=
  Finset.Icc ⌊(n : ℝ) / ((k : ℝ) + (k : ℝ) ^ theta)⌋ ⌈(n : ℝ) / (k : ℝ)⌉

/-
At most `2L+1` integers `m` (within any finset) satisfy `|m - x| < L`.
-/
lemma card_int_abs_sub_lt_le (x L : ℝ) (hL : 0 ≤ L) (S : Finset ℤ) :
    ((S.filter (fun m : ℤ => |(m : ℝ) - x| < L)).card : ℝ) ≤ 2 * L + 1 := by
  -- Every integer `m` with `|(m:ℝ) - x| < L` satisfies `x - L < m < x + L`.
  have h_filter_subset : S.filter (fun m : ℤ => |(m : ℝ) - x| < L) ⊆ Finset.Ioo (⌊x - L⌋) (⌈x + L⌉) := by
    intro m hm; simp_all +decide [ abs_lt ] ;
    exact ⟨ Int.floor_lt.2 ( by linarith ), Int.lt_ceil.2 ( by linarith ) ⟩;
  refine' le_trans _ ( show 2 * L + 1 ≥ ↑ ( Int.toNat ( ⌈x + L⌉ - ⌊x - L⌋ - 1 ) ) from _ );
  · refine' mod_cast le_trans ( Finset.card_le_card h_filter_subset ) _ ; simp +decide [ Int.card_Ioo ];
  · rcases n : ⌈x + L⌉ - ⌊x - L⌋ - 1 with ( _ | _ | n ) <;> simp_all +decide [ Int.toNat ];
    · rw [ ← @Int.cast_inj ℝ ] at * ; norm_num at * ; linarith [ Int.floor_le ( x - L ), Int.lt_floor_add_one ( x - L ), Int.le_ceil ( x + L ), Int.ceil_lt_add_one ( x + L ) ];
    · linarith;
    · linarith

/-
Every bad integer lies in some fiber indexed by `h ∈ medJ`.
-/
lemma badSet_subset_biUnion (k : ℕ) (n : ℤ) (hk1 : 1 ≤ k) (hn : 0 < n) :
    badSet k n ⊆ (medJ k n).biUnion (medFiber k n) := by
  intro m hm; simp_all +decide ;
  refine' ⟨ round ( ( n : ℝ ) / m ), _, _ ⟩ <;> simp_all +decide [ medJ, medFiber ];
  · -- From `hmW` (unfold `medWindow`, `Finset.mem_filter`, `Finset.mem_Ioo`): `(k:ℤ) < m` and `(m:ℝ) < (k:ℝ)+(k:ℝ)^theta`. So `(k:ℝ) < (m:ℝ)` and `(m:ℝ) > 0`.
    have hm_bounds : (k : ℝ) < m ∧ m < (k : ℝ) + (k : ℝ) ^ theta := by
      exact ⟨ mod_cast Finset.mem_Ioo.mp ( Finset.mem_filter.mp hm |>.1 ) |>.1, Finset.mem_filter.mp hm |>.2.1 ⟩;
    constructor <;> rw [ round_eq ] <;> norm_num [ Int.floor_le, Int.le_ceil ] at *;
    · exact Int.floor_mono <| le_add_of_le_of_nonneg ( div_le_div_of_nonneg_left ( by positivity ) ( by linarith [ show ( k : ℝ ) ≥ 1 by norm_cast ] ) <| by linarith ) <| by positivity;
    · refine' Int.le_of_lt_add_one ( Int.floor_lt.mpr _ );
      norm_num +zetaDelta at *;
      linarith [ show ( n : ℝ ) / m < ( n : ℝ ) / k by gcongr ; linarith, Int.le_ceil ( ( n : ℝ ) / k ) ];
  · unfold badSet at hm; unfold medWindow at *; aesop;

/-
`|medJ| ≤ 3 + n / k^{2-θ}`.
-/
lemma medJ_card_le (k : ℕ) (n : ℤ) (hk1 : 1 ≤ k) (hn : 0 < n) :
    ((medJ k n).card : ℝ) ≤ 3 + (n : ℝ) / (k : ℝ) ^ (2 - theta) := by
  -- By definition of медJ, we have
  have cei : (medJ k n).card ≤ (⌈(n : ℝ) / k⌉ - ⌊(n : ℝ) / (k + (k : ℝ) ^ theta)⌋ + 1) := by
    simp +decide [ medJ ];
    constructor <;> linarith [ show ⌊ ( n : ℝ ) / ( k + k ^ theta ) ⌋ ≤ ⌈ ( n : ℝ ) / k ⌉ from Int.floor_le_ceil _ |> le_trans <| Int.ceil_mono <| by gcongr ; linarith [ Real.rpow_nonneg ( Nat.cast_nonneg k ) theta ] ];
  -- By definition of ceiling and floor functions, we have:
  have h_ceil_floor : (⌈(n : ℝ) / k⌉ : ℝ) < (n : ℝ) / k + 1 ∧ (⌊(n : ℝ) / (k + (k : ℝ) ^ theta)⌋ : ℝ) > (n : ℝ) / (k + (k : ℝ) ^ theta) - 1 := by
    exact ⟨ Int.ceil_lt_add_one _, Int.sub_one_lt_floor _ ⟩;
  -- Now bound the difference:
  have h_diff : (n : ℝ) / k - (n : ℝ) / (k + (k : ℝ) ^ theta) ≤ (n : ℝ) / (k : ℝ) ^ (2 - theta) := by
    rw [ Real.rpow_sub ] <;> norm_num;
    · field_simp;
      nlinarith only [ show ( k : ℝ ) ≥ 1 by norm_cast, show ( k : ℝ ) ^ theta ≥ 0 by positivity ];
    · linarith;
  push_cast [ ← @Int.cast_le ℝ ] at * ; linarith

/-
Each fiber has at most `1 + 8 k^{1+θ}/n` elements.
-/
lemma medFiber_card_le : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → ∀ n : ℤ,
    (1 / 2) * (k : ℝ) ^ (2 - theta) < (n : ℝ) → ∀ h : ℤ,
    ((medFiber k n h).card : ℝ) ≤ 1 + 8 * (k : ℝ) ^ (1 + theta) / (n : ℝ) := by
  obtain ⟨k₀, hk₀⟩ : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → 8 ≤ (k : ℝ) ^ (1 - theta) := by
    convert Filter.eventually_atTop.mp ( eventually_le_rpow ( 1 - theta ) 8 ( by linarith [ theta_lt_one ] ) ) using 1;
  refine' ⟨ k₀ + 2, fun k hk n hn h => _ ⟩ ; norm_num at *;
  by_cases h_empty : medFiber k n h = ∅;
  · norm_num [ h_empty ];
    exact add_nonneg zero_le_one ( div_nonneg ( by positivity ) ( by exact_mod_cast ( by linarith [ show ( 0 :ℝ ) ≤ k ^ ( 2 - theta ) by positivity ] : ( 0 :ℝ ) ≤ n ) ) );
  · -- Since `medFiber k n h` is nonempty, we can pick any `m₀ ∈ medFiber k n h`.
    obtain ⟨m₀, hm₀⟩ : ∃ m₀ ∈ medFiber k n h, (k : ℝ) < m₀ ∧ (m₀ : ℝ) < (k : ℝ) + (k : ℝ) ^ theta ∧ |(n : ℝ) / m₀ - (h : ℝ)| < 1 / (k : ℝ) ^ (1 - theta) := by
      obtain ⟨ m₀, hm₀ ⟩ := Finset.nonempty_of_ne_empty h_empty; use m₀; simp_all +decide [ medFiber, medWindow ] ;
      exact_mod_cast hm₀.1.1.1;
    -- We'll use that $h \geq \frac{n}{2k}$ to bound $m/h$.
    have h_h_ge : (h : ℝ) ≥ (n : ℝ) / (2 * (k : ℝ)) := by
      have h_h_ge : (h : ℝ) > (n : ℝ) / ((k : ℝ) + (k : ℝ) ^ theta) - 1 := by
        have h_h_ge : (n : ℝ) / m₀ > (n : ℝ) / ((k : ℝ) + (k : ℝ) ^ theta) := by
          gcongr <;> norm_cast at *;
          · exact_mod_cast hn.trans_le' ( mul_nonneg ( by norm_num ) ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) );
          · linarith;
          · exact_mod_cast hm₀.2.2.1;
        linarith [ abs_lt.mp hm₀.2.2.2, show ( 1 : ℝ ) / k ^ ( 1 - theta ) ≤ 1 by exact div_le_self zero_le_one <| Real.one_le_rpow ( by norm_cast; linarith ) <| by linarith [ show theta < 1 by exact theta_lt_one ] ];
      have h_h_ge : (n : ℝ) / ((k : ℝ) + (k : ℝ) ^ theta) - (n : ℝ) / (2 * (k : ℝ)) ≥ 1 := by
        rw [ div_sub_div, ge_iff_le, le_div_iff₀ ];
        · have h_h_ge : (k : ℝ) ^ (2 - theta) ≥ 8 * (k : ℝ) := by
            have := hk₀ k ( by linarith );
            exact le_trans ( mul_le_mul_of_nonneg_right this ( Nat.cast_nonneg _ ) ) ( by rw [ ← Real.rpow_add_one ( by norm_cast; linarith ) ] ; ring_nf; norm_num );
          rw [ Real.rpow_sub ] at * <;> norm_num at *;
          · nlinarith [ show ( k : ℝ ) ^ theta > 0 by exact Real.rpow_pos_of_pos ( Nat.cast_pos.mpr ( by linarith ) ) _, show ( k : ℝ ) ^ theta ≤ k by exact le_trans ( Real.rpow_le_rpow_of_exponent_le ( by norm_cast; linarith ) ( show theta ≤ 1 by exact le_of_lt ( by norm_num [ theta ] ) ) ) ( by norm_num ), mul_div_cancel₀ ( ( k : ℝ ) ^ 2 ) ( show ( k : ℝ ) ^ theta ≠ 0 by exact ne_of_gt ( Real.rpow_pos_of_pos ( Nat.cast_pos.mpr ( by linarith ) ) _ ) ) ];
          · linarith;
          · lia;
          · linarith;
        · exact mul_pos ( add_pos_of_pos_of_nonneg ( Nat.cast_pos.mpr ( by linarith ) ) ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) ) ( mul_pos zero_lt_two ( Nat.cast_pos.mpr ( by linarith ) ) );
        · exact ne_of_gt ( add_pos_of_pos_of_nonneg ( Nat.cast_pos.mpr ( by linarith ) ) ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) );
        · norm_cast ; linarith;
      linarith;
    -- Using the bound on $m/h$, we can show that $|m - n/h| < 4k^{1+\theta}/n$.
    have h_abs_lt : ∀ m ∈ medFiber k n h, |(m : ℝ) - (n : ℝ) / (h : ℝ)| < 4 * (k : ℝ) ^ (1 + theta) / (n : ℝ) := by
      intro m hm
      have h_abs_lt_step : |(m : ℝ) - (n : ℝ) / (h : ℝ)| ≤ (m : ℝ) / (h : ℝ) * |(n : ℝ) / (m : ℝ) - (h : ℝ)| := by
        by_cases hm_pos : 0 < m <;> by_cases hh_pos : 0 < h <;> simp_all +decide [div_mul_eq_mul_div];
        · field_simp;
          rw [ abs_div, abs_div, abs_of_pos ( by positivity : 0 < ( h : ℝ ) ), abs_of_pos ( by positivity : 0 < ( m : ℝ ) ) ];
          rw [ mul_div_cancel₀ _ ( by positivity ), mul_div_cancel₀ _ ( by positivity ), abs_sub_comm ];
        · contrapose! h_h_ge;
          exact lt_of_le_of_lt ( Int.cast_nonpos.mpr hh_pos ) ( div_pos ( by exact lt_of_le_of_lt ( by positivity ) hn ) ( by norm_cast; linarith ) );
        · grind +locals;
        · contrapose! hn;
          exact le_trans ( show ( n : ℝ ) ≤ 0 by exact_mod_cast le_of_not_gt fun hn => by { exact absurd h_h_ge ( by { exact not_le_of_gt <| lt_of_le_of_lt ( by norm_cast ) <| div_pos ( by positivity ) <| by norm_cast; linarith } ) } ) <| by positivity;
      -- Using the bound on $m/h$, we can show that $m/h \leq 4k^2/n$.
      have h_m_div_h_le : (m : ℝ) / (h : ℝ) ≤ 4 * (k : ℝ) ^ 2 / (n : ℝ) := by
        have h_m_div_h_le : (m : ℝ) ≤ 2 * (k : ℝ) := by
          have h_m_le : (m : ℝ) < (k : ℝ) + (k : ℝ) ^ theta := by
            exact Finset.mem_filter.mp ( Finset.mem_filter.mp hm |>.1 ) |>.2;
          exact_mod_cast Int.le_of_lt_add_one ( by rw [ ← @Int.cast_lt ℝ ] ; push_cast; linarith [ show ( k : ℝ ) ^ theta ≤ k by exact le_trans ( Real.rpow_le_rpow_of_exponent_le ( by norm_cast; linarith ) ( show theta ≤ 1 by exact le_of_lt theta_lt_one ) ) ( by norm_num ) ] );
        rw [ div_le_div_iff₀ ] <;> norm_num at *;
        · rw [ div_le_iff₀ ] at h_h_ge <;> nlinarith [ show ( k : ℝ ) ≥ 2 by norm_cast; linarith, show ( n : ℝ ) > 0 by exact lt_of_le_of_lt ( by positivity ) hn ];
        · exact_mod_cast h_h_ge.trans_lt' ( div_pos ( show ( 0 : ℝ ) < n by exact lt_of_le_of_lt ( by positivity ) hn ) ( by norm_cast; linarith ) );
        · exact_mod_cast hn.trans_le' ( mul_nonneg ( by norm_num ) ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) );
      -- Using the bound on $|n/m - h|$, we can show that $|n/m - h| < 1/k^{1-\theta}$.
      have h_abs_lt_step2 : |(n : ℝ) / (m : ℝ) - (h : ℝ)| < 1 / (k : ℝ) ^ (1 - theta) := by
        exact Finset.mem_filter.mp hm |>.2;
      refine lt_of_le_of_lt h_abs_lt_step <| lt_of_le_of_lt ( mul_le_mul_of_nonneg_right h_m_div_h_le <| abs_nonneg _ ) ?_;
      convert mul_lt_mul_of_pos_left h_abs_lt_step2 ( show ( 0 : ℝ ) < 4 * k ^ 2 / n by exact div_pos ( by norm_cast; nlinarith ) ( by exact_mod_cast ( by linarith [ show ( 0 :ℝ ) < n by exact lt_of_le_of_lt ( by positivity ) hn ] : ( 0 :ℝ ) < n ) ) ) using 1 ; ring_nf;
      rw [ show ( 1 + theta : ℝ ) = 2 - ( 1 - theta ) by ring, Real.rpow_sub ] <;> norm_num ; ring ; linarith;
    have h_card_le : ((medFiber k n h).card : ℝ) ≤ 2 * (4 * (k : ℝ) ^ (1 + theta) / (n : ℝ)) + 1 := by
      have := card_int_abs_sub_lt_le ( ( n : ℝ ) / h ) ( 4 * ( k : ℝ ) ^ ( 1 + theta ) / n ) ?_ ( medFiber k n h );
      · convert this using 2 ; rw [ Finset.filter_true_of_mem h_abs_lt ];
      · exact div_nonneg ( mul_nonneg zero_le_four ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) ) ( by linarith [ show ( 0 : ℝ ) ≤ n by exact_mod_cast Int.le_of_lt_add_one ( by { rw [ ← @Int.cast_lt ℝ ] ; push_cast; linarith [ show ( 0 : ℝ ) ≤ k ^ ( 2 - theta ) by positivity ] } ) ] );
    exact h_card_le.trans_eq ( by ring )

/-- The `n`-free upper bound for the bad count on the medium range. -/
def g_med (k : ℕ) : ℝ :=
  3 + 56 * (k : ℝ) ^ (2 * theta - 1) + (k : ℝ) ^ theta * (Real.log k) ^ (-(2 : ℝ))

/-
The elementary counting bound for the bad count on the medium range.
-/
lemma med_card_bound : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → ∀ n : ℤ,
    (1 / 2) * (k : ℝ) ^ (2 - theta) < (n : ℝ) →
    (n : ℝ) ≤ (k : ℝ) ^ 2 / (Real.log k) ^ 2 →
    ((badSet k n).card : ℝ) < g_med k := by
  -- By definition of $g_{\text{med}}$, we know that for sufficiently large $k$, $g_{\text{med}}(k)$ is greater than the bound given by the lemma.
  have h_bound : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → ∀ n : ℤ,
    (1 / 2) * (k : ℝ) ^ (2 - theta) < (n : ℝ) →
    (n : ℝ) ≤ (k : ℝ) ^ 2 / (Real.log k) ^ 2 →
    ((badSet k n).card : ℝ) ≤ (3 + (n : ℝ) / (k : ℝ) ^ (2 - theta)) * (1 + 8 * (k : ℝ) ^ (1 + theta) / (n : ℝ)) := by
      have := @medFiber_card_le;
      obtain ⟨k₀, hk₀⟩ := this
      use max k₀ 2
      intro k hk n hn hhigh
      have hk0 : k₀ ≤ k := by
        exact le_trans ( le_max_left _ _ ) hk
      have hk1 : 1 ≤ k := by
        linarith [ le_max_right k₀ 2 ]
      have hn0 : 0 < n := by
        exact_mod_cast hn.trans_le' ( mul_nonneg ( by norm_num ) ( Real.rpow_nonneg ( Nat.cast_nonneg _ ) _ ) )
      have h_card : ((badSet k n).card : ℝ) ≤ ∑ h ∈ medJ k n, ((medFiber k n h).card : ℝ) := by
        exact_mod_cast Finset.card_le_card ( badSet_subset_biUnion k n hk1 hn0 ) |> le_trans <| Finset.card_biUnion_le;
      refine le_trans h_card <| le_trans ( Finset.sum_le_sum fun x hx => hk₀ k hk0 n hn x ) ?_;
      have := medJ_card_le k n hk1 hn0; norm_num at *; nlinarith [ show ( 0 :ℝ ) ≤ 8 * k ^ ( 1 + theta ) / n by positivity ] ;
  obtain ⟨ k₀, hk₀ ⟩ := h_bound; use Max.max k₀ 2; intros k hk n hn hn'; refine lt_of_le_of_lt ( hk₀ k ( le_trans ( le_max_left _ _ ) hk ) n hn hn' ) ?_ ; unfold g_med; ring_nf; norm_num;
  -- Simplify the expression by cancelling out common terms.
  have h_simp : (n : ℝ) * (k : ℝ) ^ (1 + theta) / (k : ℝ) ^ (2 - theta) = (n : ℝ) * (k : ℝ) ^ (2 * theta - 1) ∧ (k : ℝ) ^ (1 + theta) / (n : ℝ) < 2 * (k : ℝ) ^ (2 * theta - 1) ∧ (n : ℝ) / (k : ℝ) ^ (2 - theta) ≤ (k : ℝ) ^ theta * (Real.log k) ^ (-2 : ℝ) := by
    refine' ⟨ _, _, _ ⟩;
    · rw [ mul_div_assoc, ← Real.rpow_sub ( by norm_cast; linarith [ le_max_right k₀ 2 ] ) ] ; ring_nf;
    · rw [ div_lt_iff₀ ];
      · refine' lt_of_le_of_lt _ ( mul_lt_mul_of_pos_left hn ( by exact mul_pos zero_lt_two ( Real.rpow_pos_of_pos ( Nat.cast_pos.mpr ( by linarith [ le_max_right k₀ 2 ] ) ) _ ) ) ) ; ring_nf ; norm_num [ theta ];
        rw [ ← Real.rpow_add' ] <;> norm_num;
      · exact lt_of_le_of_lt ( by positivity ) hn;
    · convert div_le_div_of_nonneg_right hn' ( Real.rpow_nonneg ( Nat.cast_nonneg k ) _ ) using 1 ; norm_cast ; norm_num ; ring_nf;
      rw [ show ( k : ℝ ) ^ theta = ( k : ℝ ) ^ ( 2 - ( 2 - theta ) ) by ring_nf, Real.rpow_sub ] <;> norm_num ; ring ; linarith [ le_max_right k₀ 2 ];
  ring_nf at *;
  by_cases hn : n = 0 <;> simp_all +decide [ mul_assoc, mul_comm, mul_left_comm ];
  · exact absurd ‹_› ( not_lt_of_ge ( by positivity ) );
  · linarith

/-
The medium bound `g_med` is eventually dominated by `C · k^θ / log k`.
-/
lemma med_rhs_le (C : ℝ) (hC : 0 < C) :
    ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → g_med k ≤ C * (k : ℝ) ^ theta / Real.log k := by
  -- Apply `poly_log_lt` three times to get each term's bound, then combine them.
  have h1 : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → 3 ≤ (C / 3) * (k : ℝ) ^ theta / Real.log k := by
    have := poly_log_lt 3 0 0 theta theta_pos ( C / 3 ) ( by linarith ) ; aesop;
  have h2 : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → 56 * (k : ℝ) ^ (2 * theta - 1) ≤ (C / 3) * (k : ℝ) ^ theta / Real.log k := by
    convert poly_log_lt 56 ( 2 * theta - 1 ) 0 theta ( by linarith [ theta_pos, theta_lt_one ] ) ( C / 3 ) ( by linarith ) using 1;
    norm_num [ Filter.eventually_atTop ]
  have h3 : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → (k : ℝ) ^ theta * (Real.log k) ^ (-(2 : ℝ)) ≤ (C / 3) * (k : ℝ) ^ theta / Real.log k := by
    convert poly_log_lt_eq 1 theta ( C / 3 ) ( by linarith ) using 1;
    norm_num [ Filter.eventually_atTop ];
  obtain ⟨a1, h1'⟩ := h1
  obtain ⟨a2, h2'⟩ := h2
  obtain ⟨a3, h3'⟩ := h3
  refine ⟨max a1 (max a2 a3), fun k hk => ?_⟩
  have x1 := h1' k (le_trans (le_max_left _ _) hk)
  have x2 := h2' k (le_trans (le_trans (le_max_left _ _) (le_max_right _ _)) hk)
  have x3 := h3' k (le_trans (le_trans (le_max_right _ _) (le_max_right _ _)) hk)
  simp only [g_med]
  have e : C * (k:ℝ) ^ theta / Real.log k = 3 * (C / 3 * (k:ℝ) ^ theta / Real.log k) := by ring
  linarith


def BHP : Prop := ∃ C : ℝ, 0 < C ∧ ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k →
    C * (k : ℝ) ^ theta / Real.log k ≤ (primeCard (k : ℝ) ((k : ℝ) + (k : ℝ) ^ theta) : ℝ)

lemma case_medium (hB : BHP) : ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k → ∀ n : ℤ,
    (1 / 2) * (k : ℝ) ^ (2 - theta) < (n : ℝ) →
    (n : ℝ) ≤ (k : ℝ) ^ 2 / (Real.log k) ^ 2 →
    ∃ p : ℕ, p.Prime ∧ (k : ℝ) < p ∧ (p : ℝ) < (k : ℝ) + 3 * (k : ℝ) ^ theta ∧
      (p : ℤ) ∣ Pprod k n := by
  obtain ⟨C, hC, kb, hb⟩ := hB
  obtain ⟨k1, hk1card⟩ := med_card_bound
  obtain ⟨k2, hk2rhs⟩ := med_rhs_le C hC
  refine ⟨max (max kb k1) (max k2 2), ?_⟩
  intro k hk n hlow hhigh
  have hkb : kb ≤ k := le_trans (le_trans (le_max_left _ _) (le_max_left _ _)) hk
  have hki1 : k1 ≤ k := le_trans (le_trans (le_max_right _ _) (le_max_left _ _)) hk
  have hki2 : k2 ≤ k := le_trans (le_trans (le_max_left _ _) (le_max_right _ _)) hk
  have hk2le : 2 ≤ k := le_trans (le_trans (le_max_right _ _) (le_max_right _ _)) hk
  have hk1 : 1 ≤ k := by omega
  have hbhp : C * (k : ℝ) ^ theta / Real.log k ≤
      (primeCard (k : ℝ) ((k : ℝ) + (k : ℝ) ^ theta) : ℝ) := by
    exact hb k hkb
  have hcard : ((badSet k n).card : ℝ) < C * (k : ℝ) ^ theta / Real.log k :=
    lt_of_lt_of_le (hk1card k hki1 n hlow hhigh) (hk2rhs k hki2)
  exact konyagin_finish k n hk1 C hbhp hcard

/-! ### Large case machinery (Konyagin with variable `r`) -/


end