/-! Non-vacuity witness (D-4 step 7): the identity f(z) = z is 1-valent on the unit disk (analytic, every value attained at most once, the value 0 attained exactly once) and normalised (f 0 = 0), with p = 1 < n = 2. -/

theorem witness : ∃ (f : ℂ → ℂ) (p : ℕ) (n : ℕ), GoodmanConjecture.IsPValent f p ∧ GoodmanConjecture.IsNormalized f ∧ p < n :=
  ⟨fun z => z, 1, 2,
    { one_le_p := le_rfl
      analyticOn := analyticOn_id
      atMost := fun w => by
        calc {z ∈ Metric.ball (0 : ℂ) 1 | z = w}.encard
            ≤ ({w} : Set ℂ).encard := Set.encard_le_encard (fun z hz => hz.2)
          _ = ((1 : ℕ) : ℕ∞) := by simp
      exactly := ⟨0, by
        have h : {z ∈ Metric.ball (0 : ℂ) 1 | z = 0} = {0} := by
          ext z
          simp only [Set.mem_setOf_eq, Set.mem_singleton_iff]
          constructor
          · exact fun h => h.2
          · rintro rfl
            exact ⟨Metric.mem_ball_self one_pos, rfl⟩
        rw [h, Set.encard_singleton]
        simp⟩ },
    ⟨rfl⟩, by norm_num⟩
