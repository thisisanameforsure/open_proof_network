import Mathlib

/-- 402-R5-b (generator after 402-R4-c's cover.py). Window primes for 10 ≤ n ≤ 228 except n ∈ {14, 18, 48, 61, 62, 63, 74, 105, 111, 153, 165}:
53 primality certificates by `norm_num`, no `native_decide`. -/
theorem r5b_window_10_228 : ∀ n : ℕ, 10 ≤ n → n ≤ 228 → n ≠ 14 → n ≠ 18 → n ≠ 48 → n ≠ 61 → n ≠ 62 → n ≠ 63 → n ≠ 74 → n ≠ 105 → n ≠ 111 → n ≠ 153 → n ≠ 165 →
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
