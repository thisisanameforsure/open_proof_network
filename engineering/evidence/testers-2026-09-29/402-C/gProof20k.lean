import Mathlib

theorem Opn.erdos_402_card_twenty :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 20 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  obtain ⟨M, hMdef⟩ : ∃ M, M = A.max' hne := ⟨_, rfl⟩
  have hM : M ∈ A := by rw [hMdef]; exact Finset.max'_mem A hne
  have hle : ∀ x ∈ A, x ≤ M := by
    intro x hx
    rw [hMdef]
    exact Finset.le_max' A x hx
  have hMpos : 0 < M := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, M.gcd x * 20 ≤ M
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨M, hM, x, hx, key M x (by rw [hn]; exact h)⟩
  push Not at hw
  obtain ⟨S, hS⟩ : ∃ S : List ℕ, S = [12252240, 12932920, 13693680, 14549535, 15519504, 16628040, 17907120, 19399380, 21162960, 23279256, 24504480, 25865840, 27387360, 29099070, 31039008, 33256080, 35814240, 36756720, 38798760, 41081040, 42325920, 43648605, 46558512, 49008960, 49884120, 51731680, 53721360, 54774720, 58198140, 61261200, 62078016, 63488880, 64664600, 66512160, 68468400, 69837768, 71628480, 72747675, 73513440, 77597520, 82162080, 83140200, 84651840, 85765680, 87297210, 89535600, 90530440, 93117024, 95855760, 96996900, 98017920, 99768240, 101846745, 103463360, 105814800, 107442720, 108636528, 109549440, 110270160, 116396280, 122522400, 123243120, 124156032, 125349840, 126977760, 129329200, 130945815, 133024320, 134774640, 135795660, 136936800, 139675536, 142262120, 143256960, 145495350, 147026880, 148140720, 149652360, 150630480, 155195040, 159279120, 160044885, 161164080, 162954792, 164324160, 166280400, 168127960, 169303680, 170714544, 171531360, 174594420, 178017840, 179071200, 181060880, 182908440, 183783600, 186234048, 189143955, 190466640, 191711520, 193993800, 196035840, 196978320, 199536480, 201753552, 203693490, 205405200, 206926720, 208288080, 209513304, 211629600, 213393180, 214885440, 216164520, 217273056, 218243025, 219098880, 219859640, 220540320] := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C : List (List ℕ), C = [[116396280, 159279120, 164324160, 170714544, 179071200], [77597520, 109549440, 134774640, 149652360, 162954792, 211629600, 214885440, 218243025], [14549535, 61261200, 69837768, 123243120, 148140720, 155195040, 182908440], [58198140, 85765680, 124156032, 129329200, 161164080, 178017840, 199536480], [38798760, 110270160, 126977760, 150630480, 166280400, 186234048, 203693490], [33256080, 62078016, 68468400, 90530440, 122522400, 143256960, 174594420], [46558512, 73513440, 95855760, 103463360, 145495350, 190466640, 196978320, 216164520], [19399380, 36756720, 83140200, 93117024, 101846745, 136936800, 206926720], [29099070, 54774720, 125349840, 139675536, 169303680, 171531360, 193993800], [17907120, 64664600, 66512160, 87297210, 98017920, 108636528, 191711520, 213393180], [23279256, 51731680, 89535600, 99768240, 130945815, 135795660, 147026880, 201753552, 205405200], [16628040, 31039008, 41081040, 84651840, 96996900, 107442720, 160044885, 181060880, 183783600, 209513304], [25865840, 49008960, 49884120, 82162080, 105814800, 189143955, 217273056], [21162960, 27387360, 43648605, 71628480, 142262120, 196035840], [12252240, 42325920, 53721360, 72747675, 133024320, 168127960, 219098880], [13693680, 24504480, 63488880, 219859640], [12932920, 35814240, 208288080], [15519504, 220540320]] := ⟨_, rfl⟩
  have P1 : ∀ k, k < 20 → ∀ j, j < k → 0 < j → k ∣ 232792560 ∧ 232792560 / k * j ∈ S := by
    subst hS
    decide +kernel
  have P3 : ∀ a ∈ S, C.findIdx (fun l => l.contains a) < 18 ∧
      a ∈ C.getD (C.findIdx (fun l => l.contains a)) [] := by
    subst hS hC
    decide +kernel
  have P2 : ∀ i, i < 18 → ∀ a ∈ C.getD i [], ∀ b ∈ C.getD i [], a ≠ b →
      20 * a.gcd b ≤ a ∨ 20 * a.gcd b ≤ b := by
    subst hC
    decide +kernel
  have forms : ∀ x ∈ A.erase M, ∃ a ∈ S, 232792560 * x = a * M := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < M := lt_of_le_of_ne (hle x hx.2) hx.1
    have hg := hw x hx.2
    have hd1 := Nat.gcd_dvd_left M x
    have hd2 := Nat.gcd_dvd_right M x
    have hgpos : 0 < M.gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    generalize M.gcd x = g at hg hd1 hd2 hgpos
    obtain ⟨k, hk⟩ := hd1
    obtain ⟨j, hj⟩ := hd2
    have hk20 : k < 20 := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hjk : j < k := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hj1 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    obtain ⟨hdvd, hmem⟩ := P1 k hk20 j hjk hj1
    refine ⟨232792560 / k * j, hmem, ?_⟩
    obtain ⟨q, hq⟩ := hdvd
    have hkpos : 0 < k := by omega
    rw [hq, Nat.mul_div_cancel_left q hkpos, hk, hj]
    ring
  have hcard : (A.erase M).card = 19 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase M, C.findIdx (fun l => l.contains (232792560 * x / M)) ∈ Finset.range 18 := by
    intro x hx
    obtain ⟨a, ha, hax⟩ := forms x hx
    rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
    exact (P3 a ha).1
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨a, ha, hax⟩ := forms x hx
  obtain ⟨b, hb, hby⟩ := forms y hy
  simp only [hax, hby, Nat.mul_div_cancel _ hMpos] at hc
  have hab : a ≠ b := by
    intro h
    subst h
    apply hxy
    omega
  obtain ⟨hi, hai⟩ := P3 a ha
  obtain ⟨_, hbi⟩ := P3 b hb
  rw [← hc] at hbi
  have hgcd : a.gcd b * M = 232792560 * x.gcd y := by
    have h1 : Nat.gcd (232792560 * x) (232792560 * y) = 232792560 * x.gcd y := Nat.gcd_mul_left 232792560 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases P2 _ hi a hai b hbi hab with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 20 * 232792560 ≤ x * 232792560 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 20 * 232792560 ≤ y * 232792560 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
