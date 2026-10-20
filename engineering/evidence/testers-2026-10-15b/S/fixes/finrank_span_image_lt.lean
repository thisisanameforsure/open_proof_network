lemma finrank_span_image_lt (s r : ℕ) (k : Fin r)
    (f : Fin r → (Fin s → ℝ)) :
    Module.finrank ℝ (Submodule.span ℝ (f '' {j | j.val < k.val})) ≤ k.val := by
  refine' le_trans ( finrank_span_le_card _ ) _ ; norm_num;
  refine' le_trans ( Finset.card_le_card _ ) _;
  exact Finset.image f ( Finset.Iio k );
  · grind;
  · exact Finset.card_image_le.trans ( by simp )