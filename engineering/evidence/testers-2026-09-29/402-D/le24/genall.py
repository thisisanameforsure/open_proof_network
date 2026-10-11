import json, sys
from math import lcm
from functools import reduce
N=int(sys.argv[1]); stmt_path=sys.argv[2]; out=sys.argv[3]
res=json.load(open('../sweep.json')); 
res.update(json.load(open('../sweep_small.json')))
try: res.update(json.load(open('../sweep2.json')))
except Exception: pass
stmt=open(stmt_path).read()
body = r'''  have general : ∀ (n L : ℕ) (cls : List (List ℕ)), 2 ≤ n → 0 < L →
      (∀ k < n, 0 < k → L / k * k = L) →
      (∀ k < n, ∀ j < k, 0 < j →
        cls.findIdx (fun l => decide (L / k * j ∈ l)) < n - 2 ∧
        L / k * j ∈ cls.getD (cls.findIdx (fun l => decide (L / k * j ∈ l))) []) →
      (∀ i < n - 2, ∀ v ∈ cls.getD i [], ∀ w ∈ cls.getD i [], v ≠ w →
        n * v.gcd w ≤ v ∨ n * v.gcd w ≤ w) →
      ∀ A : Finset ℕ, 0 ∉ A → A.card = n → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
    intro n L cls hn2 hLpos hL H1 H2 A hA hn
    have hpos : 0 < A.card := by omega
    have hne : A.Nonempty := Finset.card_pos.mp hpos
    have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
      intro a b h
      rw [le_div_iff₀ (by exact_mod_cast hpos)]
      exact_mod_cast h
    have hM : A.max' hne ∈ A := Finset.max'_mem A hne
    have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
    by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * n ≤ A.max' hne
    · obtain ⟨x, hx, h⟩ := hw
      exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
    push_neg at hw
    have forms : ∀ x ∈ A.erase (A.max' hne), ∃ k j, k < n ∧ j < k ∧ 0 < j ∧
        L * x = L / k * j * A.max' hne := by
      intro x hx
      rw [Finset.mem_erase] at hx
      have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
      have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
      have hg := hw x hx.2
      obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
      obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
      obtain ⟨g, hgd⟩ : ∃ g, (A.max' hne).gcd x = g := ⟨_, rfl⟩
      rw [hgd] at hk hj hg
      have hkN : k < n := by
        by_contra hh
        push_neg at hh
        have := Nat.mul_le_mul_left g hh
        omega
      have hjk : j < k := by
        by_contra hh
        push_neg at hh
        have := Nat.mul_le_mul_left g hh
        omega
      have hj1 : 0 < j := by
        rcases Nat.eq_zero_or_pos j with h | h
        · subst h
          omega
        · exact h
      refine ⟨k, j, hkN, hjk, hj1, ?_⟩
      have hLk := hL k hkN (by omega)
      rw [hj, hk]
      calc L * (g * j) = (L / k * k) * (g * j) := by rw [hLk]
        _ = L / k * j * (g * k) := by ring
    have hcard : (A.erase (A.max' hne)).card = n - 1 := by
      rw [Finset.card_erase_of_mem hM, hn]
    have hmaps : ∀ x ∈ A.erase (A.max' hne),
        cls.findIdx (fun l => decide (L * x / A.max' hne ∈ l)) ∈ Finset.range (n - 2) := by
      intro x hx
      obtain ⟨k, j, hk, hj, hj0, he⟩ := forms x hx
      rw [Finset.mem_range, he, Nat.mul_div_cancel _ hMpos]
      exact (H1 k hk j hj hj0).1
    obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
      Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; omega) hmaps
    obtain ⟨k, j, hk, hj, hj0, hex⟩ := forms x hx
    obtain ⟨k', j', hk', hj', hj0', hey⟩ := forms y hy
    have ex' : L * x / A.max' hne = L / k * j := by
      rw [hex, Nat.mul_div_cancel _ hMpos]
    have ey' : L * y / A.max' hne = L / k' * j' := by
      rw [hey, Nat.mul_div_cancel _ hMpos]
    simp only [ex', ey'] at hc
    have h1 := (H1 k hk j hj hj0).2
    have h2 := (H1 k' hk' j' hj' hj0').2
    rw [hc] at h1
    have hvw : L / k * j ≠ L / k' * j' := by
      intro h
      apply hxy
      apply Nat.eq_of_mul_eq_mul_left hLpos
      rw [hex, hey, h]
    have hgcd : (L / k * j).gcd (L / k' * j') * A.max' hne = L * x.gcd y := by
      have h := Nat.gcd_mul_left L x y
      rw [hex, hey, Nat.gcd_mul_right] at h
      exact h
    have hxA := (Finset.mem_erase.mp hx).2
    have hyA := (Finset.mem_erase.mp hy).2
    rcases H2 _ (H1 k' hk' j' hj' hj0').1 _ h1 _ h2 hvw with h | h
    · refine ⟨x, hxA, y, hyA, key x y ?_⟩
      rw [hn]
      have h3 := Nat.mul_le_mul_right (A.max' hne) h
      have h5 : L * (x.gcd y * n) ≤ L * x := by
        calc L * (x.gcd y * n) = n * (L * x.gcd y) := by ring
          _ = n * ((L / k * j).gcd (L / k' * j') * A.max' hne) := by rw [hgcd]
          _ = n * (L / k * j).gcd (L / k' * j') * A.max' hne := by ring
          _ ≤ L / k * j * A.max' hne := h3
          _ = L * x := hex.symm
      exact Nat.le_of_mul_le_mul_left h5 hLpos
    · refine ⟨y, hyA, x, hxA, key y x ?_⟩
      rw [hn, Nat.gcd_comm]
      have h3 := Nat.mul_le_mul_right (A.max' hne) h
      have h5 : L * (x.gcd y * n) ≤ L * y := by
        calc L * (x.gcd y * n) = n * (L * x.gcd y) := by ring
          _ = n * ((L / k * j).gcd (L / k' * j') * A.max' hne) := by rw [hgcd]
          _ = n * (L / k * j).gcd (L / k' * j') * A.max' hne := by ring
          _ ≤ L / k' * j' * A.max' hne := h3
          _ = L * y := hey.symm
      exact Nat.le_of_mul_le_mul_left h5 hLpos
  intro A hA hne hle
  obtain ⟨n, hn⟩ : ∃ n, A.card = n := ⟨_, rfl⟩
  have h1 : 1 ≤ n := by rw [← hn]; exact Finset.card_pos.mpr hne
  have hN : n ≤ NMAX := by omega
  interval_cases n
  · obtain ⟨a, rfl⟩ := Finset.card_eq_one.mp hn
    exact ⟨a, by simp, a, by simp, by simp⟩
'''.replace("NMAX", str(N))
for n in range(2, N+1):
    if n==2:
        cls=[]; 
    else:
        cls=res[str(n)]
    L=reduce(lcm, range(1,n)) if n>2 else 1
    C="[" + ", ".join("[" + ", ".join(map(str,c)) + "]" for c in cls) + "]"
    body += f"  · exact general {n} {L} {C} (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel)\n      (by decide +kernel) A hA hn\n"
proof = stmt.replace("  sorry\n", body); assert proof!=stmt
open(out,'w').write(proof); print(len(proof))
