import Mathlib

theorem witness_hcint : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        ∀ (M : ℕ → ℕ),
          (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
            ∀ (C : ℕ → ℕ),
              (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧
                  ∀ k ≤ n,
                    ∃ (z : ℤ),
                      (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                        (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
  refine ⟨_, _, _, 0, rfl, rfl, rfl, fun M hM C hC => ?_⟩
  subst hM hC
  refine ⟨?_, ?_⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨1, by norm_num⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨0, by norm_num⟩

theorem witness_hsize : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        ∀ (M : ℕ → ℕ),
          (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
            ∀ (C : ℕ → ℕ),
              (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧
                  (∀ k ≤ n,
                      ∃ (z : ℤ),
                        (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                          (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) ∧
                    (∃ (z : ℤ),
                        (↑z : ℚ) = (↑(C n) : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
                      n ≠ (5 : ℕ) ∧ n ≠ (7 : ℕ) := by
  refine ⟨_, _, _, 0, rfl, rfl, rfl, fun M hM C hC => ?_⟩
  subst hM hC
  refine ⟨?_, ?_, ⟨0, by norm_num⟩, by decide, by decide⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨1, by norm_num⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨0, by norm_num⟩

theorem witness_hsmall : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        ∀ (M : ℕ → ℕ),
          (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
            ∀ (C : ℕ → ℕ),
              (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧
                  (∀ k ≤ n,
                      ∃ (z : ℤ),
                        (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                          (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) ∧
                    (∃ (z : ℤ),
                        (↑z : ℚ) = (↑(C n) : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
                      (n ≠ (5 : ℕ) →
                        n ≠ (7 : ℕ) →
                          ((2 : ℕ) ^ (n * (n + (1 : ℕ)) / (2 : ℕ)) * M n * C n) ^ (2 : ℕ) ≤ (2 : ℕ) ^ ((3 : ℕ) * n * n)) := by
  refine ⟨_, _, _, 0, rfl, rfl, rfl, fun M hM C hC => ?_⟩
  subst hM hC
  refine ⟨?_, ?_, ⟨0, by norm_num⟩, fun _ _ => by decide⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨1, by norm_num⟩
  · intro k hk
    obtain rfl : k = 0 := by omega
    exact ⟨0, by norm_num⟩

theorem witness_hQcint : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        ∀ (M : ℕ → ℕ),
          (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
            ∀ (C : ℕ → ℕ),
              (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) → ∃ (k : ℕ), k ≤ n := by
  refine ⟨_, _, _, 0, rfl, rfl, rfl, fun M hM C hC => ?_⟩
  subst hM hC
  exact ⟨0, le_rfl⟩

theorem witness_hpint : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        ∀ (M : ℕ → ℕ),
          (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
            ∀ (C : ℕ → ℕ),
              (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                ∃ (k : ℕ), (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧ k ≤ n := by
  refine ⟨_, _, _, 0, rfl, rfl, rfl, fun M hM C hC => ?_⟩
  subst hM hC
  refine ⟨0, ?_, le_rfl⟩
  intro k hk
  obtain rfl : k = 0 := by omega
  exact ⟨1, by norm_num⟩

