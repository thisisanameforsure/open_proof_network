import Mathlib

/-- 402-R5-b. For every size 10 ≤ n ≤ 228 there is a prime p satisfying the hypotheses of the generalised
criterion r5b_gen_criterion (window certificates + bridge for the non-exceptional n, one divisor-gap
certificate for each exceptional n: 14, 18, 48, 61, 62, 63, 74, 105, 111, 153, 165). -/
theorem r5b_small_10_228 : ∀ n : ℕ, 10 ≤ n → n ≤ 228 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2 ∧
      ∀ α : ℕ, α < n → p < α + n →
        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
  have r5b_bridge : ∀ n p : ℕ, n < p → p < 2 * n → (2 * n - p) * (2 * n - p) ≤ n →
      2 * (2 * n - p) ≤ n + 2 ∧
      ∀ α : ℕ, α < n → p < α + n →
        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
    intro n p h1 h2 h3
    generalize hk : 2 * n - p = k at *
    constructor
    · rcases Nat.lt_or_ge k 3 with h | h
      · omega
      · have : 3 * k ≤ k * k := Nat.mul_le_mul_right _ h
        omega
    · intro α hα1 hα2
      right
      intro x y hxy hd
      by_contra hc
      have h : α * y < n * x := by omega
      have α0 : 0 < α := by omega
      have hx : x * y ≤ α := Nat.le_of_dvd α0 hd
      obtain ⟨s, rfl⟩ : ∃ s, n = α + s := ⟨n - α, by omega⟩
      have hs : s < k := by omega
      have a1 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
      have a2 : α < s * x := by nlinarith
      have a3 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
      have a4 : x + 1 < s := by
        by_contra hc
        have : s * x ≤ (x + 1) * x := Nat.mul_le_mul_right _ (by omega)
        nlinarith
      have a5 : (s + 1) * (s + 1) ≤ k * k := Nat.mul_le_mul hs hs
      have a6 : s * x ≤ s * s := Nat.mul_le_mul_left _ (by omega)
      nlinarith

  have r5b_window_10_228 : ∀ n : ℕ, 10 ≤ n → n ≤ 228 → n ≠ 14 → n ≠ 18 → n ≠ 48 → n ≠ 61 → n ≠ 62 → n ≠ 63 → n ≠ 74 → n ≠ 105 → n ≠ 111 → n ≠ 153 → n ≠ 165 →
      ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
        ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
      intro p lo hi k hp h1 h2 h3 h4 n hl hh
      refine ⟨p, hp, by omega, by omega, ?_⟩
      have : 2 * n - p ≤ k := by omega
      exact le_trans (Nat.mul_le_mul this this) (by omega)
    intro n hl hh e14 e18 e48 e61 e62 e63 e74 e105 e111 e153 e165
    by_cases h11 : n ≤ 11
    · exact blk 19 10 11 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11
    by_cases h13 : n ≤ 13
    · exact blk 23 12 13 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13
    by_cases h16 : n ≤ 16
    · exact blk 29 15 16 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16
    by_cases h17 : n ≤ 17
    · exact blk 31 17 17 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17
    by_cases h20 : n ≤ 20
    · exact blk 37 19 20 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20
    by_cases h22 : n ≤ 22
    · exact blk 41 21 22 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22
    by_cases h23 : n ≤ 23
    · exact blk 43 23 23 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23
    by_cases h25 : n ≤ 25
    · exact blk 47 24 25 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25
    by_cases h26 : n ≤ 26
    · exact blk 47 26 26 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26
    by_cases h29 : n ≤ 29
    · exact blk 53 27 29 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29
    by_cases h32 : n ≤ 32
    · exact blk 59 30 32 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32
    by_cases h33 : n ≤ 33
    · exact blk 61 33 33 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33
    by_cases h36 : n ≤ 36
    · exact blk 67 34 36 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36
    by_cases h39 : n ≤ 39
    · exact blk 73 37 39 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39
    by_cases h42 : n ≤ 42
    · exact blk 79 40 42 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42
    by_cases h44 : n ≤ 44
    · exact blk 83 43 44 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44
    by_cases h47 : n ≤ 47
    · exact blk 89 45 47 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47
    by_cases h52 : n ≤ 52
    · exact blk 97 49 52 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52
    by_cases h55 : n ≤ 55
    · exact blk 103 53 55 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55
    by_cases h58 : n ≤ 58
    · exact blk 109 56 58 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58
    by_cases h60 : n ≤ 60
    · exact blk 113 59 60 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60
    by_cases h67 : n ≤ 67
    · exact blk 127 64 67 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67
    by_cases h69 : n ≤ 69
    · exact blk 131 68 69 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69
    by_cases h73 : n ≤ 73
    · exact blk 139 70 73 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73
    by_cases h78 : n ≤ 78
    · exact blk 149 75 78 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78
    by_cases h82 : n ≤ 82
    · exact blk 157 79 82 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82
    by_cases h86 : n ≤ 86
    · exact blk 163 83 86 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86
    by_cases h91 : n ≤ 91
    · exact blk 173 87 91 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91
    by_cases h95 : n ≤ 95
    · exact blk 181 92 95 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95
    by_cases h100 : n ≤ 100
    · exact blk 191 96 100 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100
    by_cases h104 : n ≤ 104
    · exact blk 199 101 104 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104
    by_cases h110 : n ≤ 110
    · exact blk 211 106 110 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110
    by_cases h116 : n ≤ 116
    · exact blk 223 112 116 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116
    by_cases h121 : n ≤ 121
    · exact blk 233 117 121 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121
    by_cases h126 : n ≤ 126
    · exact blk 241 122 126 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126
    by_cases h131 : n ≤ 131
    · exact blk 251 127 131 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131
    by_cases h137 : n ≤ 137
    · exact blk 263 132 137 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137
    by_cases h141 : n ≤ 141
    · exact blk 271 138 141 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141
    by_cases h147 : n ≤ 147
    · exact blk 283 142 147 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147
    by_cases h152 : n ≤ 152
    · exact blk 293 148 152 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152
    by_cases h159 : n ≤ 159
    · exact blk 307 154 159 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159
    by_cases h164 : n ≤ 164
    · exact blk 317 160 164 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164
    by_cases h171 : n ≤ 171
    · exact blk 331 166 171 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171
    by_cases h175 : n ≤ 175
    · exact blk 337 172 175 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175
    by_cases h181 : n ≤ 181
    · exact blk 349 176 181 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181
    by_cases h186 : n ≤ 186
    · exact blk 359 182 186 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186
    by_cases h193 : n ≤ 193
    · exact blk 373 187 193 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193
    by_cases h198 : n ≤ 198
    · exact blk 383 194 198 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198
    by_cases h205 : n ≤ 205
    · exact blk 397 199 205 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h205
    by_cases h211 : n ≤ 211
    · exact blk 409 206 211 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h211
    by_cases h217 : n ≤ 217
    · exact blk 421 212 217 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h217
    by_cases h223 : n ≤ 223
    · exact blk 433 218 223 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h223
    by_cases h228 : n ≤ 228
    · exact blk 443 224 228 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h228
    omega

  have r5b_cert_14 : ∃ p : ℕ, p.Prime ∧ 14 < p ∧ p < 2 * 14 ∧ 2 * (2 * 14 - p) ≤ 14 + 2 ∧
      ∀ α : ℕ, α < 14 → p < α + 14 →
        (∃ q : ℕ, q.Prime ∧ 14 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 14 * x ≤ α * y) := by
    refine ⟨23, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 14 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 10 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 10 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 3 ≤ x := by omega
    have x2 : x ≤ 3 := by
      by_contra h
      have : 4 * 4 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 4 := by omega
      interval_cases y <;> omega

  have r5b_cert_18 : ∃ p : ℕ, p.Prime ∧ 18 < p ∧ p < 2 * 18 ∧ 2 * (2 * 18 - p) ≤ 18 + 2 ∧
      ∀ α : ℕ, α < 18 → p < α + 18 →
        (∃ q : ℕ, q.Prime ∧ 18 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 18 * x ≤ α * y) := by
    refine ⟨31, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 18 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 14 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 14 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 4 ≤ x := by omega
    have x2 : x ≤ 3 := by
      by_contra h
      have : 4 * 4 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_48 : ∃ p : ℕ, p.Prime ∧ 48 < p ∧ p < 2 * 48 ∧ 2 * (2 * 48 - p) ≤ 48 + 2 ∧
      ∀ α : ℕ, α < 48 → p < α + 48 →
        (∃ q : ℕ, q.Prime ∧ 48 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 48 * x ≤ α * y) := by
    refine ⟨89, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 48 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 42 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 42 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 8 ≤ x := by omega
    have x2 : x ≤ 6 := by
      by_contra h
      have : 7 * 7 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_61 : ∃ p : ℕ, p.Prime ∧ 61 < p ∧ p < 2 * 61 ∧ 2 * (2 * 61 - p) ≤ 61 + 2 ∧
      ∀ α : ℕ, α < 61 → p < α + 61 →
        (∃ q : ℕ, q.Prime ∧ 61 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 61 * x ≤ α * y) := by
    refine ⟨113, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 61 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 53 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 53 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 7 ≤ x := by omega
    have x2 : x ≤ 7 := by
      by_contra h
      have : 8 * 8 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 8 := by omega
      interval_cases y <;> omega

  have r5b_cert_62 : ∃ p : ℕ, p.Prime ∧ 62 < p ∧ p < 2 * 62 ∧ 2 * (2 * 62 - p) ≤ 62 + 2 ∧
      ∀ α : ℕ, α < 62 → p < α + 62 →
        (∃ q : ℕ, q.Prime ∧ 62 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 62 * x ≤ α * y) := by
    refine ⟨113, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 62 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 52 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 52 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 6 ≤ x := by omega
    have x2 : x ≤ 7 := by
      by_contra h
      have : 8 * 8 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 7 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 8 := by omega
      interval_cases y <;> omega

  have r5b_cert_63 : ∃ p : ℕ, p.Prime ∧ 63 < p ∧ p < 2 * 63 ∧ 2 * (2 * 63 - p) ≤ 63 + 2 ∧
      ∀ α : ℕ, α < 63 → p < α + 63 →
        (∃ q : ℕ, q.Prime ∧ 63 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 63 * x ≤ α * y) := by
    refine ⟨113, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 63 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 51 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 51 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 5 ≤ x := by omega
    have x2 : x ≤ 7 := by
      by_contra h
      have : 8 * 8 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 6 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 7 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 8 := by omega
      interval_cases y <;> omega

  have r5b_cert_74 : ∃ p : ℕ, p.Prime ∧ 74 < p ∧ p < 2 * 74 ∧ 2 * (2 * 74 - p) ≤ 74 + 2 ∧
      ∀ α : ℕ, α < 74 → p < α + 74 →
        (∃ q : ℕ, q.Prime ∧ 74 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 74 * x ≤ α * y) := by
    refine ⟨139, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 74 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 66 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 66 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 9 ≤ x := by omega
    have x2 : x ≤ 8 := by
      by_contra h
      have : 9 * 9 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_105 : ∃ p : ℕ, p.Prime ∧ 105 < p ∧ p < 2 * 105 ∧ 2 * (2 * 105 - p) ≤ 105 + 2 ∧
      ∀ α : ℕ, α < 105 → p < α + 105 →
        (∃ q : ℕ, q.Prime ∧ 105 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 105 * x ≤ α * y) := by
    refine ⟨199, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 105 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 95 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 95 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 10 ≤ x := by omega
    have x2 : x ≤ 9 := by
      by_contra h
      have : 10 * 10 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_111 : ∃ p : ℕ, p.Prime ∧ 111 < p ∧ p < 2 * 111 ∧ 2 * (2 * 111 - p) ≤ 111 + 2 ∧
      ∀ α : ℕ, α < 111 → p < α + 111 →
        (∃ q : ℕ, q.Prime ∧ 111 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 111 * x ≤ α * y) := by
    refine ⟨211, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 111 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 101 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 101 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 11 ≤ x := by omega
    have x2 : x ≤ 10 := by
      by_contra h
      have : 11 * 11 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_153 : ∃ p : ℕ, p.Prime ∧ 153 < p ∧ p < 2 * 153 ∧ 2 * (2 * 153 - p) ≤ 153 + 2 ∧
      ∀ α : ℕ, α < 153 → p < α + 153 →
        (∃ q : ℕ, q.Prime ∧ 153 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 153 * x ≤ α * y) := by
    refine ⟨293, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 153 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 141 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 141 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 12 ≤ x := by omega
    have x2 : x ≤ 11 := by
      by_contra h
      have : 12 * 12 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  have r5b_cert_165 : ∃ p : ℕ, p.Prime ∧ 165 < p ∧ p < 2 * 165 ∧ 2 * (2 * 165 - p) ≤ 165 + 2 ∧
      ∀ α : ℕ, α < 165 → p < α + 165 →
        (∃ q : ℕ, q.Prime ∧ 165 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 165 * x ≤ α * y) := by
    refine ⟨317, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 165 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 153 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 153 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 13 ≤ x := by omega
    have x2 : x ≤ 12 := by
      by_contra h
      have : 13 * 13 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega

  intro n hl hh
  by_cases e14 : n = 14
  · subst e14
    exact r5b_cert_14
  by_cases e18 : n = 18
  · subst e18
    exact r5b_cert_18
  by_cases e48 : n = 48
  · subst e48
    exact r5b_cert_48
  by_cases e61 : n = 61
  · subst e61
    exact r5b_cert_61
  by_cases e62 : n = 62
  · subst e62
    exact r5b_cert_62
  by_cases e63 : n = 63
  · subst e63
    exact r5b_cert_63
  by_cases e74 : n = 74
  · subst e74
    exact r5b_cert_74
  by_cases e105 : n = 105
  · subst e105
    exact r5b_cert_105
  by_cases e111 : n = 111
  · subst e111
    exact r5b_cert_111
  by_cases e153 : n = 153
  · subst e153
    exact r5b_cert_153
  by_cases e165 : n = 165
  · subst e165
    exact r5b_cert_165
  obtain ⟨p, hp, a, b, c⟩ := r5b_window_10_228 n hl (by omega) e14 e18 e48 e61 e62 e63 e74 e105 e111 e153 e165
  have br := r5b_bridge n p a b c
  exact ⟨p, hp, a, b, br.1, br.2⟩
