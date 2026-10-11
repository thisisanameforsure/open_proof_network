import Mathlib

open Filter

theorem erdos_402__h3_v2__h1__h1__h1__h1 : ∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                    ∃ (p : ℕ), Nat.Prime p ∧ B.card < p ∧ p < 2 * B.card ∧
                    (2 * B.card - p) * (2 * B.card - p) ≤ B.card := by
  -- Second step of the window-prime route (402-R5-a). Holes: `hres` (the seven sizes with no window prime),
  -- `hlarge` (sizes above 200014; analytic, see the node's annex), `hw1`..`hw18` (window primes for 681..200014,
  -- finite certificates). The assembly proves the window primes for 2..680 and the case split.
  have hall : (∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  (B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680) →
                    (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)))
      ∧ (∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  200014 < B.card →
                    (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                    ∃ (p : ℕ), Nat.Prime p ∧ B.card < p ∧ p < 2 * B.card ∧
                    (2 * B.card - p) * (2 * B.card - p) ≤ B.card)
      ∧ (∀ n : ℕ, 681 ≤ n → n ≤ 2228 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 2229 ≤ n → n ≤ 4844 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 4845 ≤ n → n ≤ 8527 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 8528 ≤ n → n ≤ 13392 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 13393 ≤ n → n ≤ 19388 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 19389 ≤ n → n ≤ 26540 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 26541 ≤ n → n ≤ 34904 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 34905 ≤ n → n ≤ 44504 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 44505 ≤ n → n ≤ 55208 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 55209 ≤ n → n ≤ 67128 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 67129 ≤ n → n ≤ 80268 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 80269 ≤ n → n ≤ 94617 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 94618 ≤ n → n ≤ 110089 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 110090 ≤ n → n ≤ 126814 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 126815 ≤ n → n ≤ 144754 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 144755 ≤ n → n ≤ 163941 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 163942 ≤ n → n ≤ 184361 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n)
      ∧ (∀ n : ℕ, 184362 ≤ n → n ≤ 200014 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n) := by
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · have hres : ∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  (B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680) →
                    (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) := by
        sorry
      exact hres
    · have hlarge : ∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  200014 < B.card →
                    (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                    ∃ (p : ℕ), Nat.Prime p ∧ B.card < p ∧ p < 2 * B.card ∧
                    (2 * B.card - p) * (2 * B.card - p) ≤ B.card := by
        sorry
      exact hlarge
    · have hw1 : ∀ n : ℕ, 681 ≤ n → n ≤ 2228 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw1
    · have hw2 : ∀ n : ℕ, 2229 ≤ n → n ≤ 4844 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw2
    · have hw3 : ∀ n : ℕ, 4845 ≤ n → n ≤ 8527 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw3
    · have hw4 : ∀ n : ℕ, 8528 ≤ n → n ≤ 13392 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw4
    · have hw5 : ∀ n : ℕ, 13393 ≤ n → n ≤ 19388 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw5
    · have hw6 : ∀ n : ℕ, 19389 ≤ n → n ≤ 26540 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw6
    · have hw7 : ∀ n : ℕ, 26541 ≤ n → n ≤ 34904 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw7
    · have hw8 : ∀ n : ℕ, 34905 ≤ n → n ≤ 44504 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw8
    · have hw9 : ∀ n : ℕ, 44505 ≤ n → n ≤ 55208 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw9
    · have hw10 : ∀ n : ℕ, 55209 ≤ n → n ≤ 67128 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw10
    · have hw11 : ∀ n : ℕ, 67129 ≤ n → n ≤ 80268 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw11
    · have hw12 : ∀ n : ℕ, 80269 ≤ n → n ≤ 94617 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw12
    · have hw13 : ∀ n : ℕ, 94618 ≤ n → n ≤ 110089 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw13
    · have hw14 : ∀ n : ℕ, 110090 ≤ n → n ≤ 126814 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw14
    · have hw15 : ∀ n : ℕ, 126815 ≤ n → n ≤ 144754 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw15
    · have hw16 : ∀ n : ℕ, 144755 ≤ n → n ≤ 163941 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw16
    · have hw17 : ∀ n : ℕ, 163942 ≤ n → n ≤ 184361 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw17
    · have hw18 : ∀ n : ℕ, 184362 ≤ n → n ≤ 200014 → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
        sorry
      exact hw18
  obtain ⟨hres, hlarge, hw1, hw2, hw3, hw4, hw5, hw6, hw7, hw8, hw9, hw10, hw11, hw12, hw13, hw14, hw15, hw16, hw17, hw18⟩ := hall
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  have hsmall : ∀ n : ℕ, 2 ≤ n → n ≤ 680 → n ≠ 5 → n ≠ 8 → n ≠ 14 → n ≠ 18 → n ≠ 48 → n ≠ 61 → n ≠ 62 → n ≠ 63 → n ≠ 74 → n ≠ 105 → n ≠ 111 → n ≠ 153 → n ≠ 165 → n ≠ 270 → n ≠ 677 → n ≠ 678 → n ≠ 679 → n ≠ 680 →
      ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro n h2 h680 e5 e8 e14 e18 e48 e61 e62 e63 e74 e105 e111 e153 e165 e270 e677 e678 e679 e680
    by_cases c2 : n ≤ 2
    · exact blk 3 2 2 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c2
    by_cases c3 : n ≤ 3
    · exact blk 5 3 3 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c3
    by_cases c4 : n ≤ 4
    · exact blk 7 4 4 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c4
    by_cases c6 : n ≤ 6
    · exact blk 11 6 6 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c6
    by_cases c7 : n ≤ 7
    · exact blk 13 7 7 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c7
    by_cases c10 : n ≤ 10
    · exact blk 17 9 10 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c10
    by_cases c11 : n ≤ 11
    · exact blk 19 11 11 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c11
    by_cases c13 : n ≤ 13
    · exact blk 23 12 13 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c13
    by_cases c16 : n ≤ 16
    · exact blk 29 15 16 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c16
    by_cases c17 : n ≤ 17
    · exact blk 31 17 17 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c17
    by_cases c20 : n ≤ 20
    · exact blk 37 19 20 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c20
    by_cases c22 : n ≤ 22
    · exact blk 41 21 22 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c22
    by_cases c23 : n ≤ 23
    · exact blk 43 23 23 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c23
    by_cases c25 : n ≤ 25
    · exact blk 47 24 25 3 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c25
    by_cases c26 : n ≤ 26
    · exact blk 47 26 26 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c26
    by_cases c29 : n ≤ 29
    · exact blk 53 27 29 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c29
    by_cases c32 : n ≤ 32
    · exact blk 59 30 32 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c32
    by_cases c33 : n ≤ 33
    · exact blk 61 33 33 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c33
    by_cases c36 : n ≤ 36
    · exact blk 67 34 36 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c36
    by_cases c39 : n ≤ 39
    · exact blk 73 37 39 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c39
    by_cases c42 : n ≤ 42
    · exact blk 79 40 42 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c42
    by_cases c44 : n ≤ 44
    · exact blk 83 43 44 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c44
    by_cases c47 : n ≤ 47
    · exact blk 89 45 47 5 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c47
    by_cases c52 : n ≤ 52
    · exact blk 97 49 52 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c52
    by_cases c55 : n ≤ 55
    · exact blk 103 53 55 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c55
    by_cases c58 : n ≤ 58
    · exact blk 109 56 58 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c58
    by_cases c60 : n ≤ 60
    · exact blk 113 59 60 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c60
    by_cases c67 : n ≤ 67
    · exact blk 127 64 67 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c67
    by_cases c69 : n ≤ 69
    · exact blk 131 68 69 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c69
    by_cases c73 : n ≤ 73
    · exact blk 139 70 73 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c73
    by_cases c78 : n ≤ 78
    · exact blk 149 75 78 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c78
    by_cases c82 : n ≤ 82
    · exact blk 157 79 82 7 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c82
    by_cases c86 : n ≤ 86
    · exact blk 163 83 86 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c86
    by_cases c91 : n ≤ 91
    · exact blk 173 87 91 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c91
    by_cases c95 : n ≤ 95
    · exact blk 181 92 95 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c95
    by_cases c100 : n ≤ 100
    · exact blk 191 96 100 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c100
    by_cases c104 : n ≤ 104
    · exact blk 199 101 104 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c104
    by_cases c110 : n ≤ 110
    · exact blk 211 106 110 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c110
    by_cases c116 : n ≤ 116
    · exact blk 223 112 116 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c116
    by_cases c121 : n ≤ 121
    · exact blk 233 117 121 9 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c121
    by_cases c126 : n ≤ 126
    · exact blk 241 122 126 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c126
    by_cases c131 : n ≤ 131
    · exact blk 251 127 131 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c131
    by_cases c137 : n ≤ 137
    · exact blk 263 132 137 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c137
    by_cases c141 : n ≤ 141
    · exact blk 271 138 141 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c141
    by_cases c147 : n ≤ 147
    · exact blk 283 142 147 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c147
    by_cases c152 : n ≤ 152
    · exact blk 293 148 152 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c152
    by_cases c159 : n ≤ 159
    · exact blk 307 154 159 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c159
    by_cases c164 : n ≤ 164
    · exact blk 317 160 164 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c164
    by_cases c171 : n ≤ 171
    · exact blk 331 166 171 11 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c171
    by_cases c175 : n ≤ 175
    · exact blk 337 172 175 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c175
    by_cases c181 : n ≤ 181
    · exact blk 349 176 181 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c181
    by_cases c186 : n ≤ 186
    · exact blk 359 182 186 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c186
    by_cases c193 : n ≤ 193
    · exact blk 373 187 193 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c193
    by_cases c198 : n ≤ 198
    · exact blk 383 194 198 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c198
    by_cases c205 : n ≤ 205
    · exact blk 397 199 205 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c205
    by_cases c211 : n ≤ 211
    · exact blk 409 206 211 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c211
    by_cases c217 : n ≤ 217
    · exact blk 421 212 217 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c217
    by_cases c223 : n ≤ 223
    · exact blk 433 218 223 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c223
    by_cases c228 : n ≤ 228
    · exact blk 443 224 228 13 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c228
    by_cases c236 : n ≤ 236
    · exact blk 457 229 236 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c236
    by_cases c241 : n ≤ 241
    · exact blk 467 237 241 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c241
    by_cases c247 : n ≤ 247
    · exact blk 479 242 247 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c247
    by_cases c253 : n ≤ 253
    · exact blk 491 248 253 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c253
    by_cases c259 : n ≤ 259
    · exact blk 503 254 259 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c259
    by_cases c262 : n ≤ 262
    · exact blk 509 260 262 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c262
    by_cases c269 : n ≤ 269
    · exact blk 523 263 269 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c269
    by_cases c278 : n ≤ 278
    · exact blk 541 271 278 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c278
    by_cases c286 : n ≤ 286
    · exact blk 557 279 286 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c286
    by_cases c293 : n ≤ 293
    · exact blk 571 287 293 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c293
    by_cases c302 : n ≤ 302
    · exact blk 587 294 302 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c302
    by_cases c309 : n ≤ 309
    · exact blk 601 303 309 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c309
    by_cases c318 : n ≤ 318
    · exact blk 619 310 318 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c318
    by_cases c324 : n ≤ 324
    · exact blk 631 319 324 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c324
    by_cases c332 : n ≤ 332
    · exact blk 647 325 332 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c332
    by_cases c339 : n ≤ 339
    · exact blk 661 333 339 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c339
    by_cases c347 : n ≤ 347
    · exact blk 677 340 347 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c347
    by_cases c354 : n ≤ 354
    · exact blk 691 348 354 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c354
    by_cases c363 : n ≤ 363
    · exact blk 709 355 363 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c363
    by_cases c373 : n ≤ 373
    · exact blk 727 364 373 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c373
    by_cases c381 : n ≤ 381
    · exact blk 743 374 381 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c381
    by_cases c390 : n ≤ 390
    · exact blk 761 382 390 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c390
    by_cases c396 : n ≤ 396
    · exact blk 773 391 396 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c396
    by_cases c403 : n ≤ 403
    · exact blk 787 397 403 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c403
    by_cases c408 : n ≤ 408
    · exact blk 797 404 408 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c408
    by_cases c415 : n ≤ 415
    · exact blk 811 409 415 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c415
    by_cases c424 : n ≤ 424
    · exact blk 829 416 424 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c424
    by_cases c429 : n ≤ 429
    · exact blk 839 425 429 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c429
    by_cases c439 : n ≤ 439
    · exact blk 859 430 439 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c439
    by_cases c448 : n ≤ 448
    · exact blk 877 440 448 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c448
    by_cases c454 : n ≤ 454
    · exact blk 887 449 454 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c454
    by_cases c464 : n ≤ 464
    · exact blk 907 455 464 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c464
    by_cases c475 : n ≤ 475
    · exact blk 929 465 475 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c475
    by_cases c484 : n ≤ 484
    · exact blk 947 476 484 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c484
    by_cases c494 : n ≤ 494
    · exact blk 967 485 494 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c494
    by_cases c502 : n ≤ 502
    · exact blk 983 495 502 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c502
    by_cases c509 : n ≤ 509
    · exact blk 997 503 509 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c509
    by_cases c520 : n ≤ 520
    · exact blk 1019 510 520 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c520
    by_cases c530 : n ≤ 530
    · exact blk 1039 521 530 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c530
    by_cases c542 : n ≤ 542
    · exact blk 1061 531 542 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c542
    by_cases c546 : n ≤ 546
    · exact blk 1069 543 546 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c546
    by_cases c558 : n ≤ 558
    · exact blk 1093 547 558 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c558
    by_cases c570 : n ≤ 570
    · exact blk 1117 559 570 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c570
    by_cases c576 : n ≤ 576
    · exact blk 1129 571 576 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c576
    by_cases c588 : n ≤ 588
    · exact blk 1153 577 588 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c588
    by_cases c597 : n ≤ 597
    · exact blk 1171 589 597 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c597
    by_cases c608 : n ≤ 608
    · exact blk 1193 598 608 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c608
    by_cases c620 : n ≤ 620
    · exact blk 1217 609 620 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c620
    by_cases c630 : n ≤ 630
    · exact blk 1237 621 630 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c630
    by_cases c642 : n ≤ 642
    · exact blk 1259 631 642 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c642
    by_cases c654 : n ≤ 654
    · exact blk 1283 643 654 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c654
    by_cases c666 : n ≤ 666
    · exact blk 1307 655 666 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c666
    by_cases c676 : n ≤ 676
    · exact blk 1327 667 676 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c676
    omega
  intro B h0 hne hg hnp hq hle hpk
  have hpos : 0 < B.card := Finset.card_pos.mpr hne
  by_cases hbig : 200014 < B.card
  · exact hlarge B h0 hne hg hnp hq hle hpk hbig
  by_cases c184362 : 184362 ≤ B.card
  · exact Or.inr (hw18 B.card c184362 (by omega))
  by_cases c163942 : 163942 ≤ B.card
  · exact Or.inr (hw17 B.card c163942 (by omega))
  by_cases c144755 : 144755 ≤ B.card
  · exact Or.inr (hw16 B.card c144755 (by omega))
  by_cases c126815 : 126815 ≤ B.card
  · exact Or.inr (hw15 B.card c126815 (by omega))
  by_cases c110090 : 110090 ≤ B.card
  · exact Or.inr (hw14 B.card c110090 (by omega))
  by_cases c94618 : 94618 ≤ B.card
  · exact Or.inr (hw13 B.card c94618 (by omega))
  by_cases c80269 : 80269 ≤ B.card
  · exact Or.inr (hw12 B.card c80269 (by omega))
  by_cases c67129 : 67129 ≤ B.card
  · exact Or.inr (hw11 B.card c67129 (by omega))
  by_cases c55209 : 55209 ≤ B.card
  · exact Or.inr (hw10 B.card c55209 (by omega))
  by_cases c44505 : 44505 ≤ B.card
  · exact Or.inr (hw9 B.card c44505 (by omega))
  by_cases c34905 : 34905 ≤ B.card
  · exact Or.inr (hw8 B.card c34905 (by omega))
  by_cases c26541 : 26541 ≤ B.card
  · exact Or.inr (hw7 B.card c26541 (by omega))
  by_cases c19389 : 19389 ≤ B.card
  · exact Or.inr (hw6 B.card c19389 (by omega))
  by_cases c13393 : 13393 ≤ B.card
  · exact Or.inr (hw5 B.card c13393 (by omega))
  by_cases c8528 : 8528 ≤ B.card
  · exact Or.inr (hw4 B.card c8528 (by omega))
  by_cases c4845 : 4845 ≤ B.card
  · exact Or.inr (hw3 B.card c4845 (by omega))
  by_cases c2229 : 2229 ≤ B.card
  · exact Or.inr (hw2 B.card c2229 (by omega))
  by_cases c681 : 681 ≤ B.card
  · exact Or.inr (hw1 B.card c681 (by omega))
  by_cases h7 : B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680
  · exact Or.inl (hres B h0 hne hg hnp hq hle hpk h7)
  by_cases h1 : B.card = 1
  · obtain ⟨a, ha⟩ := hne
    refine Or.inl ⟨a, ha, a, ha, ?_⟩
    rw [h1]
    simp
  have x5 : B.card ≠ 5 := by
    intro h
    rw [h] at hnp
    exact hnp (by norm_num)
  have x8 : B.card ≠ 8 := hq 7 (by norm_num)
  have x14 : B.card ≠ 14 := hq 13 (by norm_num)
  have x18 : B.card ≠ 18 := hq 17 (by norm_num)
  have x48 : B.card ≠ 48 := hq 47 (by norm_num)
  have x61 : B.card ≠ 61 := by
    intro h
    rw [h] at hnp
    exact hnp (by norm_num)
  have x62 : B.card ≠ 62 := hq 61 (by norm_num)
  have x74 : B.card ≠ 74 := hq 73 (by norm_num)
  have x270 : B.card ≠ 270 := hq 269 (by norm_num)
  have x677 : B.card ≠ 677 := by
    intro h
    rw [h] at hnp
    exact hnp (by norm_num)
  have x678 : B.card ≠ 678 := hq 677 (by norm_num)
  exact Or.inr (hsmall B.card (by omega) (by omega) x5 x8 x14 x18 x48 x61 x62 (by omega) x74 (by omega) (by omega) (by omega) (by omega) x270 x677 x678 (by omega) (by omega))
