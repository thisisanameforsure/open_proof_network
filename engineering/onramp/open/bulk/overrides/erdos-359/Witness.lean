/-! Non-vacuity witness (D-4 step 7): the greedy sequence itself — A 0 = 1 and A (j+1) the least natural above A j that is not a sum of consecutive earlier terms (Nat.find; such a number exists because the sum of all earlier terms plus A j plus one exceeds every consecutive sum). -/

theorem witness : ∃ (A : ℕ → ℕ), IsGoodFor A 1 := by
  classical
  let P : (ℕ → ℕ) → ℕ → ℕ → Prop := fun B j m =>
    B j < m ∧ ∀ a b, Finset.Icc a b ⊆ Finset.Iic j → m ≠ ∑ i ∈ Finset.Icc a b, B i
  have hex : ∀ (B : ℕ → ℕ) (j : ℕ), ∃ m, P B j m := by
    intro B j
    refine ⟨(∑ i ∈ Finset.Iic j, B i) + B j + 1, ?_, ?_⟩
    · omega
    · intro a b hab
      have := Finset.sum_le_sum_of_subset (f := B) hab
      omega
  let v : ℕ → (ℕ → ℕ) := fun n =>
    Nat.rec (fun _ => 1) (fun k vk => Function.update vk (k + 1) (Nat.find (hex vk k))) n
  have hv0 : v 0 = fun _ => 1 := rfl
  have hvs : ∀ k, v (k + 1) = Function.update (v k) (k + 1) (Nat.find (hex (v k) k)) :=
    fun k => rfl
  have hagree : ∀ j i, i ≤ j → v j i = v i i := by
    intro j
    induction j with
    | zero => intro i hi; have : i = 0 := by omega
              subst this; rfl
    | succ j ih =>
      intro i hi
      rcases Nat.lt_or_ge i (j + 1) with h | h
      · rw [hvs, Function.update_of_ne (by omega)]
        exact ih i (by omega)
      · have : i = j + 1 := by omega
        subst this; rfl
  refine ⟨fun n => v n n, rfl, ?_, ?_⟩
  · refine strictMono_nat_of_lt_succ fun j => ?_
    show v j j < v (j + 1) (j + 1)
    rw [hvs, Function.update_self]
    exact (Nat.find_spec (hex (v j) j)).1
  · intro j
    have hset : ∀ m, P (v j) j m ↔
        (v j j < m ∧ ∀ a b, Finset.Icc a b ⊆ Finset.Iic j → m ≠ ∑ i ∈ Finset.Icc a b, v i i) := by
      intro m
      have hsum : ∀ a b, Finset.Icc a b ⊆ Finset.Iic j →
          ∑ i ∈ Finset.Icc a b, v j i = ∑ i ∈ Finset.Icc a b, v i i := by
        intro a b hab
        refine Finset.sum_congr rfl fun i hi => hagree j i ?_
        exact Finset.mem_Iic.mp (hab hi)
      constructor
      · rintro ⟨h1, h2⟩
        exact ⟨h1, fun a b hab => by rw [← hsum a b hab]; exact h2 a b hab⟩
      · rintro ⟨h1, h2⟩
        exact ⟨h1, fun a b hab => by rw [hsum a b hab]; exact h2 a b hab⟩
    show IsLeast {m : ℕ | v j j < m ∧ ∀ a b, Finset.Icc a b ⊆ Finset.Iic j →
        m ≠ ∑ i ∈ Finset.Icc a b, v i i} (v (j + 1) (j + 1))
    rw [hvs, Function.update_self]
    refine ⟨(hset _).mp (Nat.find_spec (hex (v j) j)), fun m hm => ?_⟩
    exact Nat.find_min' (hex (v j) j) ((hset m).mpr hm)
