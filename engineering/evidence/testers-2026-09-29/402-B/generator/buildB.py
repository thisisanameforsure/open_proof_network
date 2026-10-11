import sys
from math import gcd,lcm
from functools import reduce
exec(open('chrom.py').read().split('for N in range')[0])
N=int(sys.argv[1]); node=sys.argv[2]
n,K,r,col=run(N,120)
assert r
L=reduce(lcm,range(1,N))
V=sorted({L*j//k for k in range(2,N) for j in range(1,k)})
for a in V:
  for b in V:
    if a!=b and col[a]==col[b]: assert N*gcd(a,b)<=max(a,b)
Vs="({"+", ".join(map(str,V))+"} : Finset ℕ)"
F="(fun a : ℕ => "+" ".join(f"if a = {v} then {col[v]} else" for v in V)+" 0)"
stmt=open(f'graph/targets/erdos-402/nodes/{node}/Statement.lean',encoding='utf-8').read()
body=f'''  intro A h0 hcard
  -- the rational inequality is {N} * gcd a b ≤ a
  have red : ∀ a b : ℕ, {N} * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [hcard, le_div_iff₀ (by norm_num)]
    exact_mod_cast (by omega : a.gcd b * {N} ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  obtain ⟨M, hMA, hMmax⟩ : ∃ M ∈ A, ∀ x ∈ A, x ≤ M :=
    ⟨A.max' hne, A.max'_mem hne, fun x hx => A.le_max' x hx⟩
  have hMpos : 0 < M := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hMA)
  by_cases hsmall : ∃ x ∈ A, {N} * M.gcd x ≤ M
  · obtain ⟨x, hx, h⟩ := hsmall
    exact ⟨M, hMA, x, hx, red M x h⟩
  push Not at hsmall
  -- the values L * j / k (0 < j < k < {N}) all lie in the list, and every k < {N} divides L
  have hmemV : ∀ k < {N}, ∀ j < k, 0 < j → {L} * j / k ∈ {Vs} := by decide +kernel
  have hdvd : ∀ k < {N}, 0 < k → k ∣ {L} := by decide +kernel
  -- every other element x has {L} * x = v * M for one of the {len(V)} values v = {L} * j / k
  have hval : ∀ x ∈ A.erase M, ∃ v ∈ {Vs}, {L} * x = v * M := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hxA)
    have hlt : x < M := lt_of_le_of_ne (hMmax x hxA) hxM
    have hbig : M < {N} * M.gcd x := hsmall x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left M x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right M x
    have hkN : k < {N} := by
      by_contra hh
      have : M.gcd x * {N} ≤ M.gcd x * k := Nat.mul_le_mul_left _ (by omega)
      omega
    have hjk : j < k := by
      have : M.gcd x * j < M.gcd x * k := by omega
      exact Nat.lt_of_mul_lt_mul_left this
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj; omega
      · exact h
    obtain ⟨c, hc⟩ := hdvd k hkN (by omega)
    have e : {L} * j / k = c * j := by
      rw [hc, Nat.mul_assoc, Nat.mul_div_cancel_left _ (by omega)]
    refine ⟨{L} * j / k, hmemV k hkN j hjk hj0, ?_⟩
    rw [e]
    rw [hc]
    generalize M.gcd x = g at hk hj
    subst hk
    rw [hj]
    ring
  -- colour the {len(V)} values with {K} colours, each colour class pairwise good
  have hcol : ∀ v ∈ {Vs}, {F} v < {K} := by decide +kernel
  have hgood : ∀ v ∈ {Vs}, ∀ w ∈ {Vs}, v ≠ w → {F} v = {F} w →
      {N} * v.gcd w ≤ v ∨ {N} * v.gcd w ≤ w := by decide +kernel
  have hmaps : ∀ x ∈ A.erase M, {F} ({L} * x / M) ∈ Finset.range {K} := by
    intro x hx
    obtain ⟨v, hv, hxv⟩ := hval x hx
    rw [Finset.mem_range, hxv, Nat.mul_div_cancel _ hMpos]
    exact hcol v hv
  have hcardE : (A.erase M).card = {N-1} := by rw [Finset.card_erase_of_mem hMA, hcard]
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcardE, Finset.card_range]; omega) hmaps
  obtain ⟨v, hv, hxv⟩ := hval x hx
  obtain ⟨w, hw, hyw⟩ := hval y hy
  rw [hxv, hyw, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hvw : v ≠ w := by
    rintro rfl
    exact hxy (by omega)
  have hg : v.gcd w * M = {L} * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxv, ← hyw, Nat.gcd_mul_left]
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hgood v hv w hw hvw hc with h | h
  · have h2 : {N} * (v.gcd w * M) ≤ v * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨x, hxA, y, hyA, red x y (by omega)⟩
  · have h2 : {N} * (v.gcd w * M) ≤ w * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨y, hyA, x, hxA, red y x (by rw [Nat.gcd_comm]; omega)⟩
'''
proof=stmt.replace("  sorry\n",body)
assert proof!=stmt
open(f'ProofB-{N}.lean','w',encoding='utf-8').write(proof)
