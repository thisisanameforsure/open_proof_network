import Mathlib

/-! Mertens' second theorem, bounded-error form: `∑_{p ≤ x} 1/p = log log x + O(1)`.
The one fact the composite-dilation route to erdos-69 needs that Mathlib at the pin lacks
(annex 9445873d on `erdos-69`).

The first step (`hM`, the estimate with logarithmic weights `∑_{p ≤ n} (log p)/p = log n + O(1)`)
is adapted from `BoundedGaps/Maynard/PrimeMertens.lean` of github.com/frenzymath/FormalPantheon
(commit ffbb65c21afc8a36ace67720f1b0df1c63d26bd1, Apache-2.0): that file's lemmas are inlined as
`have` steps and its four definitions expanded in place. The rest (discrete Abel summation against
`1/log n`, and `log (b/a)` squeezed between `1 - a/b` and `b/a - 1`) is new. -/
theorem Opn.erdos_69_mertens_reciprocal_primes :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C := by
  have hM : ∃ C : ℝ, ∀ n : ℕ,
      |∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) - Real.log n| ≤ C := by
    open Finset Nat Real ArithmeticFunction in
    · classical
      have sum_Ioc_log_eq_log_factorial (n : ℕ) :
          (∑ m ∈ Ioc 0 n, Real.log m) = Real.log n ! := by
        induction n with
        | zero => simp
        | succ n ih =>
            rw [sum_Ioc_succ_top (Nat.zero_le n), ih, Nat.factorial_succ,
              Nat.cast_mul, Real.log_mul]
            · ring
            · exact_mod_cast Nat.succ_ne_zero n
            · exact_mod_cast Nat.factorial_ne_zero n

      have sum_Ioc_log_eq_mangoldt_floor (n : ℕ) :
          (∑ m ∈ Ioc 0 n, Real.log m) =
            ∑ d ∈ Ioc 0 n,
              ArithmeticFunction.vonMangoldt d * (n / d : ℕ) := by
        calc
          (∑ m ∈ Ioc 0 n, Real.log m) =
              ∑ m ∈ Ioc 0 n,
                (ArithmeticFunction.vonMangoldt * ArithmeticFunction.zeta) m := by
            apply sum_congr rfl
            intro m hm
            rw [ArithmeticFunction.vonMangoldt_mul_zeta]
            rfl
          _ = _ := ArithmeticFunction.sum_Ioc_mul_zeta_eq_sum
            ArithmeticFunction.vonMangoldt n

      have floorAverage_le_harmonic {n : ℕ} (hn : 0 < n) :
          ((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d * (n / d : ℕ)) / (n : ℝ)) ≤ (∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) := by
        rw [Finset.sum_div]
        apply Finset.sum_le_sum
        intro d hd
        have hdPos : 0 < d := (Finset.mem_Ioc.mp hd).1
        have hfloor : ((n / d : ℕ) : ℝ) / n ≤ 1 / (d : ℝ) := by
          rw [div_le_div_iff₀ (by exact_mod_cast hn) (by exact_mod_cast hdPos)]
          norm_cast
          simpa only [one_mul] using Nat.div_mul_le_self n d
        calc
          ArithmeticFunction.vonMangoldt d * (n / d : ℕ) / (n : ℝ) =
              ArithmeticFunction.vonMangoldt d * (((n / d : ℕ) : ℝ) / n) := by
            ring
          _ ≤ ArithmeticFunction.vonMangoldt d * (1 / (d : ℝ)) :=
            mul_le_mul_of_nonneg_left hfloor ArithmeticFunction.vonMangoldt_nonneg
          _ = ArithmeticFunction.vonMangoldt d / (d : ℝ) := by ring

      have harmonic_le_floorAverage_add_psi {n : ℕ} (hn : 0 < n) :
          (∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) ≤ ((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d * (n / d : ℕ)) / (n : ℝ)) + Chebyshev.psi n / n := by
        calc
          (∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) ≤
              ∑ d ∈ Ioc 0 n,
                (ArithmeticFunction.vonMangoldt d * (n / d : ℕ) / (n : ℝ) +
                  ArithmeticFunction.vonMangoldt d / (n : ℝ)) := by
            apply Finset.sum_le_sum
            intro d hd
            have hdPos : 0 < d := (Finset.mem_Ioc.mp hd).1
            have hmod := Nat.mod_lt n hdPos
            have hdecomp := Nat.div_add_mod n d
            have hnd : n ≤ (n / d + 1) * d := by
              calc
                n = d * (n / d) + n % d := hdecomp.symm
                _ ≤ d * (n / d) + d := Nat.add_le_add_left hmod.le _
                _ = (n / d + 1) * d := by
                  rw [Nat.add_mul, one_mul, Nat.mul_comm (n / d) d]
            have hfloor : (1 : ℝ) / d ≤
                ((n / d : ℕ) : ℝ) / n + 1 / n := by
              calc
                (1 : ℝ) / d ≤ ((n / d + 1 : ℕ) : ℝ) / n := by
                  rw [div_le_div_iff₀ (by exact_mod_cast hdPos) (by exact_mod_cast hn)]
                  norm_cast
                  simpa only [one_mul] using hnd
                _ = ((n / d : ℕ) : ℝ) / n + 1 / n := by
                  push_cast
                  ring
            calc
              ArithmeticFunction.vonMangoldt d / (d : ℝ) =
                  ArithmeticFunction.vonMangoldt d * (1 / (d : ℝ)) := by ring
              _ ≤ ArithmeticFunction.vonMangoldt d *
                  (((n / d : ℕ) : ℝ) / n + 1 / n) :=
                mul_le_mul_of_nonneg_left hfloor ArithmeticFunction.vonMangoldt_nonneg
              _ = ArithmeticFunction.vonMangoldt d * (n / d : ℕ) / (n : ℝ) +
                  ArithmeticFunction.vonMangoldt d / (n : ℝ) := by ring
          _ = (∑ d ∈ Ioc 0 n,
                ArithmeticFunction.vonMangoldt d * (n / d : ℕ)) / (n : ℝ) +
              Chebyshev.psi n / n := by
            rw [Finset.sum_add_distrib, ← Finset.sum_div, ← Finset.sum_div]
            congr 2
            simp [Chebyshev.psi]

      have log_sub_one_le_floorAverage {n : ℕ} (hn : 0 < n) :
          Real.log n - 1 ≤ ((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d * (n / d : ℕ)) / (n : ℝ)) := by
        have hsum := sum_Ioc_log_eq_mangoldt_floor n
        have hfactorial := sum_Ioc_log_eq_log_factorial n
        have hstirling := Stirling.le_log_factorial_stirling hn.ne'
        have hlogn : 0 ≤ Real.log n := Real.log_natCast_nonneg n
        have hlog2pi : 0 ≤ Real.log (2 * Real.pi) := by
          apply Real.log_nonneg
          nlinarith [Real.pi_gt_three]
        have hbasic : (n : ℝ) * Real.log n - n ≤ Real.log n ! := by
          linarith
        rw [← hsum, hfactorial]
        apply (le_div_iff₀ (by exact_mod_cast hn)).2
        nlinarith

      have floorAverage_le_log {n : ℕ} (hn : 0 < n) :
          ((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d * (n / d : ℕ)) / (n : ℝ)) ≤ Real.log n := by
        have hsum := sum_Ioc_log_eq_mangoldt_floor n
        have hfactorial := sum_Ioc_log_eq_log_factorial n
        have hfacReal : (n ! : ℝ) ≤ (n : ℝ) ^ n := by
          exact_mod_cast Nat.factorial_le_pow n
        have hlogFac : Real.log (n ! : ℝ) ≤ Real.log ((n : ℝ) ^ n) := by
          exact Real.strictMonoOn_log.monotoneOn
            (by simp only [Set.mem_Ioi]; positivity)
            (by simp only [Set.mem_Ioi]; positivity) hfacReal
        rw [Real.log_pow] at hlogFac
        rw [← hsum, hfactorial]
        apply (div_le_iff₀ (by exact_mod_cast hn)).2
        nlinarith

      have abs_mangoldtHarmonicSum_sub_log_le (n : ℕ) :
          |(∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) - Real.log n| ≤ Real.log 4 + 4 := by
        rcases n.eq_zero_or_pos with rfl | hn
        · have hC : (0 : ℝ) ≤ Real.log 4 + 4 := by
            have hlog4 : (0 : ℝ) ≤ Real.log (4 : ℝ) :=
              Real.log_nonneg (by norm_num)
            linarith
          simpa using hC
        have hlowerFloor := log_sub_one_le_floorAverage hn
        have hupperFloor := floorAverage_le_log hn
        have hfloorLe := floorAverage_le_harmonic hn
        have hharmonicUpper := harmonic_le_floorAverage_add_psi hn
        have hpsi := Chebyshev.psi_le_const_mul_self
          (show (0 : ℝ) ≤ n by positivity)
        have hpsiDiv : Chebyshev.psi n / n ≤ Real.log 4 + 4 := by
          apply (div_le_iff₀ (by exact_mod_cast hn)).2
          simpa [mul_comm] using hpsi
        rw [abs_le]
        constructor
        · have hC : (1 : ℝ) ≤ Real.log 4 + 4 := by
            have hlog4 : (0 : ℝ) ≤ Real.log (4 : ℝ) :=
              Real.log_nonneg (by norm_num)
            linarith
          linarith
        · linarith

      have exists_uniform_abs_mangoldtHarmonicSum_sub_log :
          ∃ C : ℝ, ∀ n : ℕ,
            |(∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) - Real.log n| ≤ C :=
        ⟨Real.log 4 + 4, abs_mangoldtHarmonicSum_sub_log_le⟩

      have mangoldtHarmonicSum_eq_prime_add_nonprime (n : ℕ) :
          (∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) =
            (∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ)) + (∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)) := by
        classical
        calc
          (∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) =
              ∑ d ∈ Ioc 0 n,
                ((if d.Prime then ArithmeticFunction.vonMangoldt d else 0) / (d : ℝ) +
                  (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)) := by
            apply Finset.sum_congr rfl
            intro d hd
            by_cases hp : d.Prime <;> simp [hp]
          _ = (∑ d ∈ Ioc 0 n,
                (if d.Prime then ArithmeticFunction.vonMangoldt d else 0) / (d : ℝ)) +
              ∑ d ∈ Ioc 0 n,
                (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ) := by
            rw [Finset.sum_add_distrib]
          _ = _ := by
            congr 1
            calc
              (∑ d ∈ Ioc 0 n,
                  (if d.Prime then ArithmeticFunction.vonMangoldt d else 0) / (d : ℝ)) =
                  ∑ p ∈ (Ioc 0 n).filter Nat.Prime,
                    ArithmeticFunction.vonMangoldt p / (p : ℝ) := by
                simp only [ite_div, zero_div, Finset.sum_filter]
              _ = ∑ p ∈ Nat.primesLE n,
                    ArithmeticFunction.vonMangoldt p / (p : ℝ) := by
                apply Finset.sum_congr
                · rw [Nat.primesLE_eq_filter_Icc_one]
                  ext p
                  simp only [Finset.mem_filter, Finset.mem_Ioc, Finset.mem_Icc]
                  constructor
                  · rintro ⟨⟨hp, hpn⟩, hprime⟩
                    exact ⟨⟨Nat.succ_le_iff.mpr hp, hpn⟩, hprime⟩
                  · rintro ⟨⟨hp, hpn⟩, hprime⟩
                    exact ⟨⟨Nat.succ_le_iff.mp hp, hpn⟩, hprime⟩
                · intro p hp
                  rfl
              _ = ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) := by
                apply Finset.sum_congr rfl
                intro p hp
                rw [ArithmeticFunction.vonMangoldt_apply_prime
                  (Nat.prime_of_mem_primesLE hp)]

      have summable_nonprimeMangoldtTerm :
          Summable fun n : ℕ =>
            (if n.Prime then 0 else ArithmeticFunction.vonMangoldt n) / (n : ℝ) := by
        letI : Subsingleton (ZMod 1) := ZMod.subsingleton_iff.mpr rfl
        have hcast : ∀ n : ℕ, (n : ZMod 1) = 0 :=
          fun n => Subsingleton.elim _ _
        simpa [ArithmeticFunction.vonMangoldt.residueClass, hcast] using
          (ArithmeticFunction.vonMangoldt.summable_residueClass_non_primes_div
            (0 : ZMod 1))
      let f : ℕ → ℝ := fun d =>
        (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)
      refine ⟨Real.log 4 + 4 + ∑' d : ℕ, f d, fun n => ?_⟩
      have hfNonneg (d : ℕ) : 0 ≤ f d := by
        unfold f
        split_ifs <;> positivity
      have hfSummable : Summable f := summable_nonprimeMangoldtTerm
      have hnonprimeNonneg : 0 ≤ (∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)) := by
        change 0 ≤ ∑ d ∈ Ioc 0 n, f d
        exact Finset.sum_nonneg fun d hd => hfNonneg d
      have hnonprimeLe : (∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)) ≤ ∑' d : ℕ, f d := by
        change (∑ d ∈ Ioc 0 n, f d) ≤ ∑' d : ℕ, f d
        exact hfSummable.sum_le_tsum (Ioc 0 n) fun d hd => hfNonneg d
      have hsplit := mangoldtHarmonicSum_eq_prime_add_nonprime n
      have heq : (∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ)) - Real.log n =
          ((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) - Real.log n) -
            (∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ)) := by
        rw [hsplit]
        ring
      rw [heq]
      calc
        |((∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) - Real.log n) -
            (∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ))| ≤
            |(∑ d ∈ Ioc 0 n, ArithmeticFunction.vonMangoldt d / (d : ℝ)) - Real.log n| +
              |(∑ d ∈ Ioc 0 n, (if d.Prime then 0 else ArithmeticFunction.vonMangoldt d) / (d : ℝ))| := abs_sub _ _
        _ ≤ (Real.log 4 + 4) + (∑' d : ℕ, f d) := by
          apply add_le_add (abs_mangoldtHarmonicSum_sub_log_le n)
          rwa [abs_of_nonneg hnonprimeNonneg]
  obtain ⟨C, hC⟩ := hM
  have hC0 : 0 ≤ C := (abs_nonneg _).trans (hC 0)
  have hl2 : 0 < Real.log 2 := Real.log_pos (by norm_num)
  have hL : ∀ n : ℕ, 2 ≤ n → Real.log 2 ≤ Real.log (n : ℝ) := fun n hn =>
    Real.log_le_log (by norm_num) (by exact_mod_cast hn)
  have htel : ∀ f : ℕ → ℝ, ∀ x : ℕ, 2 ≤ x →
      ∑ n ∈ Finset.Ico 2 x, (f (n + 1) - f n) = f x - f 2 := by
    intro f x hx
    induction x, hx using Nat.le_induction with
    | base => simp
    | succ x hx ih => rw [Finset.sum_Ico_succ_top hx, ih]; ring
  have htel' : ∀ f : ℕ → ℝ, ∀ x : ℕ, 2 ≤ x →
      ∑ n ∈ Finset.Ico 2 x, (f n - f (n + 1)) = f 2 - f x := by
    intro f x hx
    induction x, hx using Nat.le_induction with
    | base => simp
    | succ x hx ih => rw [Finset.sum_Ico_succ_top hx, ih]; ring
  have habel : ∀ x : ℕ, 2 ≤ x →
      ∑ p ∈ Nat.primesLE x, (1 : ℝ) / p
        = (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ)) / Real.log (x : ℝ)
          + ∑ n ∈ Finset.Ico 2 x, (∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
              * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ)) := by
    intro x hx
    induction x, hx using Nat.le_induction with
    | base =>
      have h2 : Nat.primesLE 2 = {2} := by decide
      have : Real.log 2 ≠ 0 := hl2.ne'
      simp [h2]
      field_simp
    | succ x hx ih =>
      have ha : Real.log (x : ℝ) ≠ 0 := (lt_of_lt_of_le hl2 (hL x hx)).ne'
      have hb : Real.log ((x + 1 : ℕ) : ℝ) ≠ 0 :=
        (lt_of_lt_of_le hl2 (hL (x + 1) (by omega))).ne'
      have hnot : x + 1 ∉ Nat.primesLE x := fun h => by
        have := (Nat.mem_primesLE.mp h).1
        omega
      have hx1 : ((x + 1 : ℕ) : ℝ) ≠ 0 := by positivity
      rw [Finset.sum_Ico_succ_top hx, Nat.primesLE_succ]
      split_ifs with hp
      · rw [Finset.sum_insert hnot, Finset.sum_insert hnot, ih]
        field_simp
        ring
      · rw [ih]
        field_simp
        ring
  have hreal : ∀ a b A : ℝ, 0 < a → a ≤ b → b - a ≤ 1 → |A - a| ≤ C →
      0 ≤ 1 / a - 1 / b ∧
        |A * (1 / a - 1 / b) - (Real.log b - Real.log a)| ≤ (C + 1) * (1 / a - 1 / b) := by
    intro a b A ha0 hab hba hA
    have hb0 : 0 < b := ha0.trans_le hab
    have hd0 : 0 ≤ 1 / a - 1 / b := by
      rw [sub_nonneg]
      exact one_div_le_one_div_of_le ha0 hab
    have hv : Real.log b - Real.log a = Real.log (b / a) :=
      (Real.log_div hb0.ne' ha0.ne').symm
    have hlow := Real.one_sub_inv_le_log_of_pos (show 0 < b / a by positivity)
    have hup := Real.log_le_sub_one_of_pos (show 0 < b / a by positivity)
    have hR := abs_le.mp hA
    have hu : a * (1 / a - 1 / b) = 1 - (b / a)⁻¹ := by
      field_simp
    have hw : b / a - 1 - (1 - (b / a)⁻¹) = (b - a) * (1 / a - 1 / b) := by
      field_simp
    have hw2 : (b - a) * (1 / a - 1 / b) ≤ 1 * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hba hd0
    have h1 : -C * (1 / a - 1 / b) ≤ (A - a) * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hR.1 hd0
    have h2 : (A - a) * (1 / a - 1 / b) ≤ C * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hR.2 hd0
    have e : A * (1 / a - 1 / b) - (Real.log b - Real.log a)
        = (A - a) * (1 / a - 1 / b) + (a * (1 / a - 1 / b) - Real.log (b / a)) := by
      rw [hv]
      ring
    refine ⟨hd0, ?_⟩
    rw [e, abs_le]
    constructor <;> nlinarith
  have hpt : ∀ n : ℕ, 2 ≤ n →
      |(∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
            * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ))
          - (Real.log (Real.log ((n + 1 : ℕ) : ℝ)) - Real.log (Real.log (n : ℝ)))|
        ≤ (C + 1) * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ)) := by
    intro n hn
    have hn0 : (0 : ℝ) < n := by exact_mod_cast (by omega : 0 < n)
    have hn1 : (0 : ℝ) < ((n + 1 : ℕ) : ℝ) := by positivity
    have hab : Real.log (n : ℝ) ≤ Real.log ((n + 1 : ℕ) : ℝ) :=
      Real.log_le_log hn0 (by push_cast; linarith)
    have hba : Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ) ≤ 1 := by
      have h1 : Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ)
          = Real.log (((n + 1 : ℕ) : ℝ) / n) := (Real.log_div hn1.ne' hn0.ne').symm
      have h2 := Real.log_le_sub_one_of_pos (show 0 < ((n + 1 : ℕ) : ℝ) / n by positivity)
      have h3 : ((n + 1 : ℕ) : ℝ) / n - 1 = 1 / n := by
        push_cast
        field_simp
        ring
      have h4 : (1 : ℝ) / n ≤ 1 := by
        rw [div_le_one hn0]
        exact_mod_cast (by omega : 1 ≤ n)
      linarith
    exact (hreal _ _ _ (lt_of_lt_of_le hl2 (hL n hn)) hab hba (hC n)).2
  refine ⟨1 + C / Real.log 2 + |Real.log (Real.log 2)| + (C + 1) / Real.log 2, by positivity, ?_⟩
  intro x hx
  have hLx : Real.log 2 ≤ Real.log (x : ℝ) := hL x hx
  have hLx0 : 0 < Real.log (x : ℝ) := hl2.trans_le hLx
  have hv := htel (fun n => Real.log (Real.log (n : ℝ))) x hx
  have hd := htel' (fun n => 1 / Real.log (n : ℝ)) x hx
  simp only [Nat.cast_ofNat] at hv hd
  have hsum : |∑ n ∈ Finset.Ico 2 x, ((∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
            * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ))
          - (Real.log (Real.log ((n + 1 : ℕ) : ℝ)) - Real.log (Real.log (n : ℝ))))|
        ≤ (C + 1) / Real.log 2 := by
    refine (Finset.abs_sum_le_sum_abs _ _).trans ?_
    refine (Finset.sum_le_sum (fun n hn => hpt n (Finset.mem_Ico.mp hn).1)).trans ?_
    rw [← Finset.mul_sum, hd, div_eq_mul_one_div (C + 1)]
    have : 0 ≤ 1 / Real.log (x : ℝ) := by positivity
    nlinarith
  rw [Finset.sum_sub_distrib, hv] at hsum
  have hq : |(∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ) - Real.log (x : ℝ)) / Real.log (x : ℝ)|
      ≤ C / Real.log 2 := by
    rw [abs_div, abs_of_pos hLx0]
    calc _ ≤ C / Real.log (x : ℝ) := by gcongr; exact hC x
      _ ≤ C / Real.log 2 := by gcongr
  have e1 : (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ)) / Real.log (x : ℝ)
      = 1 + (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ) - Real.log (x : ℝ)) / Real.log (x : ℝ) := by
    rw [sub_div, div_self hLx0.ne']
    ring
  have hab := habel x hx
  have h3 := abs_le.mp hsum
  have h4 := abs_le.mp hq
  have h5 := neg_abs_le (Real.log (Real.log 2))
  have h6 := le_abs_self (Real.log (Real.log 2))
  rw [abs_le]
  constructor <;> linarith
