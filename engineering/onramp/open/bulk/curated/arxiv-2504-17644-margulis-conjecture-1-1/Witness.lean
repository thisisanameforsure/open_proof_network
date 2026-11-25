/-! Non-vacuity witness (D-4 step 7): n = 3 and the lattice of the order ℤ[θ], θ³ = 3θ - 1 (a totally
real cubic field), embedded by its three real places and scaled to covolume one. Its diagonal orbit
is compact: the units θ² and (1 - θ)² act on it by integer matrices of determinant one, and every
diagonal matrix is a product of their powers and of a diagonal matrix with entries at most e⁵. -/

theorem witness : ∃ (n : ℕ) (g : Matrix.SpecialLinearGroup (Fin n) ℝ ⧸
      Subgroup.map (Matrix.SpecialLinearGroup.map (Int.castRingHom ℝ)) ⊤),
    3 ≤ n ∧ IsCompact (closure (MulAction.orbit
      (Matrix.SpecialLinearGroup.diagonalSubgroup (Fin n) ℝ) g)) := by
  classical
  -- the three real roots of x ^ 3 - 3 x + 1
  have hcont : Continuous (fun x : ℝ => x ^ 3 - 3 * x + 1) := by fun_prop
  obtain ⟨t0, ⟨h0l, h0u⟩, hf0⟩ := intermediate_value_Icc (a := (-1.9 : ℝ)) (b := -1.8)
    (by norm_num) hcont.continuousOn (show (0 : ℝ) ∈ Set.Icc _ _ by constructor <;> norm_num)
  obtain ⟨t1, ⟨h1l, h1u⟩, hf1⟩ := intermediate_value_Icc' (a := (0.34 : ℝ)) (b := 0.35)
    (by norm_num) hcont.continuousOn (show (0 : ℝ) ∈ Set.Icc _ _ by constructor <;> norm_num)
  obtain ⟨t2, ⟨h2l, h2u⟩, hf2⟩ := intermediate_value_Icc (a := (1.5 : ℝ)) (b := 1.6)
    (by norm_num) hcont.continuousOn (show (0 : ℝ) ∈ Set.Icc _ _ by constructor <;> norm_num)
  simp only at hf0 hf1 hf2
  set θ : Fin 3 → ℝ := ![t0, t1, t2] with hθ
  have hfθ : ∀ i, θ i ^ 3 - 3 * θ i + 1 = 0 := by
    intro i; fin_cases i <;> simpa [θ]
  -- the lattice: rows are the three embeddings of the basis 1, θ, θ²
  set V : Matrix (Fin 3) (Fin 3) ℝ := Matrix.of fun i j => θ i ^ (j : ℕ) with hV
  have hdetV : V.det = (t1 - t0) * (t2 - t0) * (t2 - t1) := by
    simp [V, θ, Matrix.det_fin_three]; ring
  have hDpos : 0 < V.det := by
    rw [hdetV]; apply mul_pos; apply mul_pos <;> linarith
    linarith
  set c : ℝ := V.det ^ (-(1 : ℝ) / 3) with hc
  have hc3 : c ^ 3 * V.det = 1 := by
    rw [hc, ← Real.rpow_mul_natCast hDpos.le]
    norm_num [Real.rpow_neg_one]
    exact inv_mul_cancel₀ hDpos.ne'
  have hdetg : (c • V).det = 1 := by
    rw [Matrix.det_smul]; simpa using hc3
  obtain ⟨g0, hg0⟩ : ∃ g0 : Matrix.SpecialLinearGroup (Fin 3) ℝ,
      (g0 : Matrix (Fin 3) (Fin 3) ℝ) = c • V := ⟨⟨c • V, hdetg⟩, rfl⟩
  set H : Subgroup (Matrix.SpecialLinearGroup (Fin 3) ℝ) :=
    Subgroup.map (Matrix.SpecialLinearGroup.map (Int.castRingHom ℝ)) ⊤ with hH
  -- multiplication by θ² and by (1 - θ)² in the basis 1, θ, θ²
  set MuR : Matrix (Fin 3) (Fin 3) ℝ := !![0, -1, 0; 0, 3, -1; 1, 0, 3] with hMuR
  set MvR : Matrix (Fin 3) (Fin 3) ℝ := !![1, -1, 2; -2, 4, -7; 1, -2, 4] with hMvR
  have key : ∀ t : ℝ, t ^ 3 - 3 * t + 1 = 0 →
      (∀ j : Fin 3, t ^ 2 * t ^ (j : ℕ) = ∑ k : Fin 3, t ^ (k : ℕ) * MuR k j) ∧
      (∀ j : Fin 3, (1 - t) ^ 2 * t ^ (j : ℕ) = ∑ k : Fin 3, t ^ (k : ℕ) * MvR k j) := by
    intro t ht
    refine ⟨fun j => ?_, fun j => ?_⟩ <;> fin_cases j <;>
      simp [MuR, MvR, Fin.sum_univ_three] <;>
      first
        | ring1
        | linear_combination ht
        | linear_combination (-1 : ℝ) * ht
        | linear_combination t * ht
        | linear_combination (-t) * ht
        | linear_combination (t - 2) * ht
        | linear_combination (2 - t) * ht
  -- a diagonal matrix acting on the lattice by an integer matrix of determinant one
  have conjH : ∀ (a : Fin 3 → ℝ) (M : Matrix (Fin 3) (Fin 3) ℝ) (MZ : Matrix (Fin 3) (Fin 3) ℤ),
      MZ.det = 1 → MZ.map (Int.cast : ℤ → ℝ) = M →
      (∀ i j : Fin 3, a i * θ i ^ (j : ℕ) = ∑ k : Fin 3, θ i ^ (k : ℕ) * M k j) →
      ∃ U : Matrix.SpecialLinearGroup (Fin 3) ℝ,
        (U : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal a ∧ g0⁻¹ * U * g0 ∈ H := by
    intro a M MZ hMZ hMap hrel
    have hrelM : Matrix.diagonal a * V = V * M := by
      ext i j
      rw [Matrix.diagonal_mul, Matrix.mul_apply]
      simpa [V] using hrel i j
    have hdetM : M.det = 1 := by
      have := RingHom.map_det (Int.castRingHom ℝ) MZ
      rw [hMZ] at this
      simp only [map_one, RingHom.mapMatrix_apply, Int.coe_castRingHom] at this
      rw [← hMap]; exact this.symm
    have hdeta : (Matrix.diagonal a).det = 1 := by
      have := congrArg Matrix.det hrelM
      rw [Matrix.det_mul, Matrix.det_mul, hdetM, mul_one] at this
      exact (mul_eq_right₀ hDpos.ne').1 this
    obtain ⟨U0, hU0⟩ : ∃ U0 : Matrix.SpecialLinearGroup (Fin 3) ℝ,
        (U0 : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal a := ⟨⟨_, hdeta⟩, rfl⟩
    refine ⟨U0, hU0, ?_⟩
    have hMZsl : MZ.det = 1 := hMZ
    let MZs : Matrix.SpecialLinearGroup (Fin 3) ℤ := ⟨MZ, hMZsl⟩
    have hmem : Matrix.SpecialLinearGroup.map (Int.castRingHom ℝ) MZs ∈ H :=
      Subgroup.mem_map_of_mem _ (Subgroup.mem_top _)
    have hUg : U0 * g0 =
        g0 * Matrix.SpecialLinearGroup.map (Int.castRingHom ℝ) MZs := by
      ext1
      simp only [Matrix.SpecialLinearGroup.coe_mul, hg0, Matrix.SpecialLinearGroup.map_apply_coe,
        RingHom.mapMatrix_apply, hU0]
      rw [Matrix.mul_smul, Matrix.smul_mul, hrelM]
      congr 2
      rw [← hMap]; rfl
    rw [mul_assoc, hUg, ← mul_assoc, inv_mul_cancel, one_mul]
    exact hmem
  have ⟨U, hU, hUH⟩ := conjH (fun i => θ i ^ 2) MuR !![0, -1, 0; 0, 3, -1; 1, 0, 3]
    (by simp [Matrix.det_fin_three]) (by ext i j; fin_cases i <;> fin_cases j <;> simp [MuR])
    (fun i j => (key (θ i) (hfθ i)).1 j)
  have ⟨W, hW, hWH⟩ := conjH (fun i => (1 - θ i) ^ 2) MvR !![1, -1, 2; -2, 4, -7; 1, -2, 4]
    (by simp [Matrix.det_fin_three]) (by ext i j; fin_cases i <;> fin_cases j <;> simp [MvR])
    (fun i j => (key (θ i) (hfθ i)).2 j)
  -- integer powers of such an element
  have hpow : ∀ (a : Fin 3 → ℝ) (U : Matrix.SpecialLinearGroup (Fin 3) ℝ), (∀ i, a i ≠ 0) →
      (U : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal a → g0⁻¹ * U * g0 ∈ H → ∀ t : ℤ,
      ∃ P : Matrix.SpecialLinearGroup (Fin 3) ℝ,
        (P : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal (fun i => a i ^ t) ∧
        g0⁻¹ * P * g0 ∈ H := by
    intro a U ha hU hUH t
    refine ⟨U ^ t, ?_, ?_⟩
    · have hnat : ∀ n : ℕ, ((U ^ n : Matrix.SpecialLinearGroup (Fin 3) ℝ) :
          Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal (fun i => a i ^ n) := by
        intro n
        rw [Matrix.SpecialLinearGroup.coe_pow, hU, Matrix.diagonal_pow]
        rfl
      rcases t with n | n
      · simpa using hnat n
      · rw [zpow_negSucc]
        set X := (U ^ (n + 1))⁻¹ with hX
        have hm := congrArg (fun M : Matrix.SpecialLinearGroup (Fin 3) ℝ =>
          (M : Matrix (Fin 3) (Fin 3) ℝ)) (inv_mul_cancel (U ^ (n + 1)))
        simp only [Matrix.SpecialLinearGroup.coe_mul, Matrix.SpecialLinearGroup.coe_one,
          hnat] at hm
        have hdi : Matrix.diagonal (fun i => a i ^ (n + 1)) *
            Matrix.diagonal (fun i => a i ^ (Int.negSucc n)) = 1 := by
          rw [Matrix.diagonal_mul_diagonal, ← Matrix.diagonal_one]
          congr 1; funext i
          rw [zpow_negSucc]
          exact mul_inv_cancel₀ (pow_ne_zero _ (ha i))
        calc ((X : Matrix.SpecialLinearGroup (Fin 3) ℝ) : Matrix (Fin 3) (Fin 3) ℝ)
            = (X : Matrix (Fin 3) (Fin 3) ℝ) * (Matrix.diagonal (fun i => a i ^ (n + 1)) *
                Matrix.diagonal (fun i => a i ^ (Int.negSucc n))) := by rw [hdi, Matrix.mul_one]
          _ = Matrix.diagonal (fun i => a i ^ (Int.negSucc n)) := by
                rw [← Matrix.mul_assoc, hm, Matrix.one_mul]
    · have := map_zpow (MulAut.conj g0⁻¹) U t
      simp only [MulAut.conj_apply, inv_inv] at this
      rw [this]
      exact Subgroup.zpow_mem _ hUH t
  -- the logarithms of the two units at the first two places
  have he1 : (2.7182818283 : ℝ) < Real.exp 1 := Real.exp_one_gt_d9
  have he2 : Real.exp 1 < 2.7182818286 := Real.exp_one_lt_d9
  have hexp2 : Real.exp 2 = Real.exp 1 * Real.exp 1 := by rw [← Real.exp_add]; norm_num
  have hexp3 : Real.exp 3 = Real.exp 1 * Real.exp 1 * Real.exp 1 := by
    rw [← Real.exp_add, ← Real.exp_add]; norm_num
  have hm1 : Real.exp (-1) * Real.exp 1 = 1 := by rw [← Real.exp_add]; norm_num
  have hm2 : Real.exp (-2) * Real.exp 2 = 1 := by rw [← Real.exp_add]; norm_num
  have hm3 : Real.exp (-3) * Real.exp 3 = 1 := by rw [← Real.exp_add]; norm_num
  have hp1 := Real.exp_pos (-1)
  have hp2 := Real.exp_pos (-2)
  have hp3 := Real.exp_pos (-3)
  have hE2u : Real.exp 2 < 7.39 := by rw [hexp2]; nlinarith only [he1, he2, Real.exp_pos 1]
  have hE2l' : 7.38 < Real.exp 1 * Real.exp 1 := by nlinarith only [he1, he2, Real.exp_pos 1]
  have hE2l : 7.38 < Real.exp 2 := by rw [hexp2]; exact hE2l'
  have hE3l : 20 < Real.exp 3 := by rw [hexp3]; nlinarith only [hE2l', he1, Real.exp_pos 1]
  have hEm1 : Real.exp (-1) < 0.37 := by nlinarith only [hm1, he1, hp1]
  have hEm2 : 0.13 < Real.exp (-2) := by nlinarith only [hm2, hE2u, hp2, Real.exp_pos 2]
  have hEm3 : Real.exp (-3) < 0.05 := by nlinarith only [hm3, hE3l, hp3]
  have ht0sq : 0 < t0 ^ 2 := by nlinarith only [h0u]
  have ht1sq : 0 < t1 ^ 2 := by nlinarith only [h1l]
  have hs0sq : 0 < (1 - t0) ^ 2 := by nlinarith only [h0u]
  have hs1sq : 0 < (1 - t1) ^ 2 := by nlinarith only [h1u]
  set A0 := Real.log (t0 ^ 2) with hA0
  set A1 := Real.log (t1 ^ 2) with hA1
  set B0 := Real.log ((1 - t0) ^ 2) with hB0
  set B1 := Real.log ((1 - t1) ^ 2) with hB1
  have hA0l : 0 < A0 := Real.log_pos (by nlinarith only [h0u])
  have hA0u : A0 < 2 := (Real.log_lt_iff_lt_exp ht0sq).2 (by nlinarith only [h0l, h0u, hE2l])
  have hA1u : A1 < -2 := (Real.log_lt_iff_lt_exp ht1sq).2 (by nlinarith only [h1l, h1u, hEm2])
  have hA1l : -3 < A1 := (Real.lt_log_iff_exp_lt ht1sq).2 (by nlinarith only [h1l, h1u, hEm3])
  have hB0l : 2 < B0 := (Real.lt_log_iff_exp_lt hs0sq).2 (by nlinarith only [h0l, h0u, hE2u])
  have hB0u : B0 < 3 := (Real.log_lt_iff_lt_exp hs0sq).2 (by nlinarith only [h0l, h0u, hE3l])
  have hB1u : B1 < 0 := Real.log_neg hs1sq (by nlinarith only [h1l, h1u])
  have hB1l : -1 < B1 := (Real.lt_log_iff_exp_lt hs1sq).2 (by nlinarith only [h1l, h1u, hEm1])
  set Δ := A0 * B1 - A1 * B0 with hΔ
  have hΔpos : 0 < Δ := by nlinarith only [hA0l, hA0u, hA1u, hB0l, hB1l, hB1u]
  -- the compact pieces
  set Bset : Set (Fin 3 → ℝ) := {y | (∀ i, |y i| ≤ Real.exp 5) ∧ y 0 * y 1 * y 2 = 1} with hBset
  have hBc : IsCompact Bset := by
    apply (isCompact_univ_pi (fun _ : Fin 3 => isCompact_Icc
      (a := -Real.exp 5) (b := Real.exp 5))).of_isClosed_subset
    · have : Bset = (⋂ i, {y : Fin 3 → ℝ | |y i| ≤ Real.exp 5}) ∩
          {y | y 0 * y 1 * y 2 = 1} := by
        ext; simp [Bset]
      rw [this]
      exact IsClosed.inter
        (isClosed_iInter fun i => isClosed_le ((continuous_apply i).abs) continuous_const)
        (isClosed_eq (by fun_prop) continuous_const)
    · intro y hy i _
      exact abs_le.1 (hy.1 i)
  set K : Set (Matrix.SpecialLinearGroup (Fin 3) ℝ) :=
    {M | ∃ y ∈ Bset, (M : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal y * (c • V)} with hK
  have hKc : IsCompact K := by
    have hψdet : ∀ y : Bset, (Matrix.diagonal y.1 * (c • V)).det = 1 := fun y => by
      rw [Matrix.det_mul, hdetg, Matrix.det_diagonal, Fin.prod_univ_three, y.2.2, mul_one]
    let ψ : Bset → Matrix.SpecialLinearGroup (Fin 3) ℝ := fun y => ⟨_, hψdet y⟩
    have hψ : Continuous ψ := Continuous.subtype_mk
      ((Continuous.matrix_diagonal continuous_subtype_val).matrix_mul continuous_const) _
    have : K = Set.range ψ := by
      ext M
      constructor
      · rintro ⟨y, hy, hM⟩
        exact ⟨⟨y, hy⟩, Subtype.ext hM.symm⟩
      · rintro ⟨⟨y, hy⟩, rfl⟩
        exact ⟨y, hy, rfl⟩
    rw [this]
    haveI := isCompact_iff_compactSpace.1 hBc
    exact isCompact_range hψ
  set C : Set (Matrix.SpecialLinearGroup (Fin 3) ℝ) :=
    {u | ∀ i j, |(u : Matrix (Fin 3) (Fin 3) ℝ) i j - (1 : Matrix (Fin 3) (Fin 3) ℝ) i j| ≤ 1}
    with hC
  have hCc : IsCompact C := by
    set Cm : Set (Matrix (Fin 3) (Fin 3) ℝ) := {N | N.det = 1 ∧
        ∀ i j, |N i j - (1 : Matrix (Fin 3) (Fin 3) ℝ) i j| ≤ 1} with hCm
    have hCmc : IsCompact Cm := by
      have hbox : IsCompact (Set.pi Set.univ (fun _ : Fin 3 => Set.pi Set.univ
          (fun _ : Fin 3 => Set.Icc (-2 : ℝ) 2)) : Set (Matrix (Fin 3) (Fin 3) ℝ)) :=
        isCompact_univ_pi (fun _ => isCompact_univ_pi (fun _ => isCompact_Icc))
      apply hbox.of_isClosed_subset
      · have : Cm = {N : Matrix (Fin 3) (Fin 3) ℝ | N.det = 1} ∩
            ⋂ i, ⋂ j, {N | |N i j - (1 : Matrix (Fin 3) (Fin 3) ℝ) i j| ≤ 1} := by
          ext; simp [Cm]
        rw [this]
        exact IsClosed.inter (isClosed_eq (continuous_id.matrix_det) continuous_const)
          (isClosed_iInter fun i => isClosed_iInter fun j =>
            isClosed_le ((continuous_id.matrix_elem i j).sub continuous_const).abs
              continuous_const)
      · rintro N ⟨-, h2⟩ i _ j _
        have := abs_le.1 (h2 i j)
        constructor
        · by_cases hij : i = j <;> simp [Matrix.one_apply, hij] at this ⊢ <;> linarith
        · by_cases hij : i = j <;> simp [Matrix.one_apply, hij] at this ⊢ <;> linarith
    let χ : Cm → Matrix.SpecialLinearGroup (Fin 3) ℝ := fun N => ⟨N.1, N.2.1⟩
    have hχ : Continuous χ := continuous_subtype_val.subtype_mk _
    have : C = Set.range χ := by
      ext M
      constructor
      · intro hM
        exact ⟨⟨M.1, M.2, hM⟩, rfl⟩
      · rintro ⟨⟨N, hN⟩, rfl⟩
        exact hN.2
    rw [this]
    haveI := isCompact_iff_compactSpace.1 hCmc
    exact isCompact_range hχ
  refine ⟨3, QuotientGroup.mk g0, le_rfl, ?_⟩
  -- every point of the orbit is the image of a point of K
  have horb : MulAction.orbit (Matrix.SpecialLinearGroup.diagonalSubgroup (Fin 3) ℝ)
      (QuotientGroup.mk g0 : Matrix.SpecialLinearGroup (Fin 3) ℝ ⧸ H) ⊆
      (QuotientGroup.mk : Matrix.SpecialLinearGroup (Fin 3) ℝ → _ ⧸ H) '' K := by
    rintro p ⟨d, rfl⟩
    have hd : Matrix.SpecialLinearGroup.toGL (d : Matrix.SpecialLinearGroup (Fin 3) ℝ) ∈
        Subgroup.map (Matrix.GeneralLinearGroup.diagonalHom (Fin 3) ℝ) ⊤ := d.2
    obtain ⟨w, -, hw⟩ := Subgroup.mem_map.1 hd
    have hx : ((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) : Matrix (Fin 3) (Fin 3) ℝ) =
        Matrix.diagonal (fun i => (w i : ℝ)) := (congrArg Units.val hw).symm
    set x : Fin 3 → ℝ := fun i => (w i : ℝ) with hxdef
    have hxne : ∀ i, x i ≠ 0 := fun i => (w i).ne_zero
    set α := (Real.log |x 0| * B1 - Real.log |x 1| * B0) / Δ with hα
    set β := (A0 * Real.log |x 1| - A1 * Real.log |x 0|) / Δ with hβ
    have hα0 : α * A0 + β * B0 = Real.log |x 0| := by
      rw [hα, hβ]; field_simp; ring
    have hα1 : α * A1 + β * B1 = Real.log |x 1| := by
      rw [hα, hβ]; field_simp; ring
    have hθne : ∀ i, θ i ≠ 0 := by
      intro i; fin_cases i <;> simp [θ] <;> intro h <;> subst h <;> norm_num at *
    have h1θne : ∀ i, 1 - θ i ≠ 0 := by
      intro i; fin_cases i <;> simp [θ] <;> intro h <;> linarith
    obtain ⟨Pu, hPu, hPuH⟩ := hpow (fun i => θ i ^ 2) U (fun i => pow_ne_zero _ (hθne i)) hU hUH
      (-⌊α⌋)
    obtain ⟨Pw, hPw, hPwH⟩ := hpow (fun i => (1 - θ i) ^ 2) W
      (fun i => pow_ne_zero _ (h1θne i)) hW hWH (-⌊β⌋)
    set y : Fin 3 → ℝ := fun i => x i * (θ i ^ 2) ^ (-⌊α⌋) * ((1 - θ i) ^ 2) ^ (-⌊β⌋) with hy
    have hdy : (((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * Pu * Pw :
        Matrix.SpecialLinearGroup (Fin 3) ℝ) : Matrix (Fin 3) (Fin 3) ℝ) = Matrix.diagonal y := by
      rw [Matrix.SpecialLinearGroup.coe_mul, Matrix.SpecialLinearGroup.coe_mul, hx, hPu, hPw,
        Matrix.diagonal_mul_diagonal, Matrix.diagonal_mul_diagonal]
    have hyprod : y 0 * y 1 * y 2 = 1 := by
      have := ((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * Pu * Pw).2
      rw [hdy, Matrix.det_diagonal, Fin.prod_univ_three] at this
      exact this
    have hyne : ∀ i, y i ≠ 0 := by
      intro i h
      fin_cases i <;> simp only [Fin.zero_eta, Fin.mk_one, Fin.reduceFinMk] at h <;>
        simp [h] at hyprod
    have hlogy : ∀ i, Real.log |y i| = Real.log |x i| - ⌊α⌋ * Real.log (θ i ^ 2)
        - ⌊β⌋ * Real.log ((1 - θ i) ^ 2) := by
      intro i
      have ha : 0 < θ i ^ 2 := lt_of_le_of_ne (sq_nonneg _) (Ne.symm (pow_ne_zero 2 (hθne i)))
      have hb : 0 < (1 - θ i) ^ 2 :=
        lt_of_le_of_ne (sq_nonneg _) (Ne.symm (pow_ne_zero 2 (h1θne i)))
      have hxa := abs_pos.2 (hxne i)
      show Real.log |x i * (θ i ^ 2) ^ (-⌊α⌋) * ((1 - θ i) ^ 2) ^ (-⌊β⌋)| = _
      rw [abs_mul, abs_mul, abs_of_pos (zpow_pos ha _), abs_of_pos (zpow_pos hb _),
        Real.log_mul (mul_pos hxa (zpow_pos ha _)).ne' (zpow_pos hb _).ne',
        Real.log_mul hxa.ne' (zpow_pos ha _).ne', Real.log_zpow, Real.log_zpow]
      push_cast; ring
    have hfa := Int.floor_le α
    have hfa' := Int.lt_floor_add_one α
    have hfb := Int.floor_le β
    have hfb' := Int.lt_floor_add_one β
    have hl0 : Real.log |y 0| = (α - ⌊α⌋) * A0 + (β - ⌊β⌋) * B0 := by
      rw [hlogy 0]; simp only [θ, Matrix.cons_val_zero]; rw [← hα0]; ring
    have hl1 : Real.log |y 1| = (α - ⌊α⌋) * A1 + (β - ⌊β⌋) * B1 := by
      rw [hlogy 1]; simp only [θ, Matrix.cons_val_one, Matrix.cons_val_zero]; rw [← hα1]; ring
    have hl2 : Real.log |y 0| + Real.log |y 1| + Real.log |y 2| = 0 := by
      rw [← Real.log_mul (by simp [hyne 0]) (by simp [hyne 1]),
        ← Real.log_mul (by simp [hyne 0, hyne 1]) (by simp [hyne 2]), ← abs_mul, ← abs_mul,
        hyprod]
      simp
    have hb0l : 0 ≤ Real.log |y 0| := by
      rw [hl0]; nlinarith only [hA0l, hB0l, hfa, hfb, mul_nonneg (sub_nonneg.2 hfa) hA0l.le,
        mul_nonneg (sub_nonneg.2 hfb) (by linarith : (0 : ℝ) ≤ B0)]
    have hb0u : Real.log |y 0| ≤ 5 := by
      rw [hl0]; nlinarith only [hA0l, hA0u, hB0l, hB0u, hfa, hfa', hfb, hfb', mul_nonneg (by linarith : (0 : ℝ) ≤ 1 - (α - ⌊α⌋)) hA0l.le,
        mul_nonneg (by linarith : (0 : ℝ) ≤ 1 - (β - ⌊β⌋)) (by linarith : (0 : ℝ) ≤ B0)]
    have hb1u : Real.log |y 1| ≤ 0 := by
      rw [hl1]; nlinarith only [hA1u, hA1l, hB1u, hB1l, hfa, hfa', hfb, hfb', mul_nonneg (sub_nonneg.2 hfa) (by linarith : (0 : ℝ) ≤ -A1),
        mul_nonneg (sub_nonneg.2 hfb) (by linarith : (0 : ℝ) ≤ -B1)]
    have hb1l : -4 ≤ Real.log |y 1| := by
      rw [hl1]; nlinarith only [hA1u, hA1l, hB1u, hB1l, hfa, hfa', hfb, hfb', mul_nonneg (by linarith : (0 : ℝ) ≤ 1 - (α - ⌊α⌋))
          (by linarith : (0 : ℝ) ≤ -A1),
        mul_nonneg (by linarith : (0 : ℝ) ≤ 1 - (β - ⌊β⌋)) (by linarith : (0 : ℝ) ≤ -B1)]
    have hyb : ∀ i, |y i| ≤ Real.exp 5 := by
      intro i
      rw [← Real.log_le_iff_le_exp (abs_pos.2 (hyne i))]
      fin_cases i
      · exact hb0u
      · show Real.log |y 1| ≤ 5
        linarith
      · show Real.log |y 2| ≤ 5
        linarith
    refine ⟨(d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * Pu * Pw * g0,
      ⟨y, ⟨hyb, hyprod⟩, ?_⟩, ?_⟩
    · rw [Matrix.SpecialLinearGroup.coe_mul, hdy, hg0]
    · show (QuotientGroup.mk _ : Matrix.SpecialLinearGroup (Fin 3) ℝ ⧸ H) =
        QuotientGroup.mk ((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * g0)
      rw [QuotientGroup.eq]
      have : ((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * Pu * Pw * g0)⁻¹ *
          ((d : Matrix.SpecialLinearGroup (Fin 3) ℝ) * g0) =
          (g0⁻¹ * Pu * g0 * (g0⁻¹ * Pw * g0))⁻¹ := by group
      rw [this]
      exact H.inv_mem (H.mul_mem hPuH hPwH)
  -- the closure of the image of K lies in the image of the compact set C * K
  have hcl : closure ((QuotientGroup.mk : Matrix.SpecialLinearGroup (Fin 3) ℝ → _ ⧸ H) '' K) ⊆
      (QuotientGroup.mk : Matrix.SpecialLinearGroup (Fin 3) ℝ → _ ⧸ H) ''
        ((fun q => q.1 * q.2) '' (C ×ˢ K)) := by
    intro p hp
    obtain ⟨z, rfl⟩ := QuotientGroup.mk_surjective p
    set O : Set (Matrix.SpecialLinearGroup (Fin 3) ℝ) := {u | ∀ i j,
      |((u⁻¹ : Matrix.SpecialLinearGroup (Fin 3) ℝ) : Matrix (Fin 3) (Fin 3) ℝ) i j -
        (1 : Matrix (Fin 3) (Fin 3) ℝ) i j| < 1} with hO
    have hcv : Continuous (fun u : Matrix.SpecialLinearGroup (Fin 3) ℝ =>
        ((u⁻¹ : Matrix.SpecialLinearGroup (Fin 3) ℝ) : Matrix (Fin 3) (Fin 3) ℝ)) :=
      continuous_subtype_val.comp continuous_inv
    have hOo : IsOpen O := by
      simp only [hO, Set.setOf_forall]
      exact isOpen_iInter_of_finite fun i => isOpen_iInter_of_finite fun j =>
        isOpen_lt (((hcv.matrix_elem i j).sub
          continuous_const).abs) continuous_const
    have h1O : (1 : Matrix.SpecialLinearGroup (Fin 3) ℝ) ∈ O := by
      intro i j; simp
    have hN := QuotientGroup.isOpenMap_coe (N := H) _ (isOpenMap_mul_right z _ hOo)
    obtain ⟨q, ⟨_, ⟨u, hu, rfl⟩, rfl⟩, ⟨k, hk, hkq⟩⟩ :=
      mem_closure_iff.1 hp _ hN ⟨1 * z, ⟨1, h1O, rfl⟩, by rw [one_mul]⟩
    refine ⟨u⁻¹ * k, ⟨(u⁻¹, k), ⟨show u⁻¹ ∈ C from fun i j => (hu i j).le, hk⟩, rfl⟩, ?_⟩
    rw [QuotientGroup.eq] at hkq ⊢
    have : (u⁻¹ * k)⁻¹ * z = k⁻¹ * (u * z) := by group
    rw [this]
    exact hkq
  exact (((hCc.prod hKc).image continuous_mul).image QuotientGroup.continuous_mk).of_isClosed_subset isClosed_closure
    ((closure_mono horb).trans hcl)
