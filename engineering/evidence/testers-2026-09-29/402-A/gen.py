import sys, re, ast
from math import gcd, lcm
from functools import reduce
N=int(sys.argv[1]); name=sys.argv[2]; header=open(sys.argv[3]).read(); out=sys.argv[4]
data=open('/home/user/open_proof_network/engineering/evidence/testers-2026-09-29/402-A/colourings-n9-to-n18.txt').read().splitlines()
for i,l in enumerate(data):
    if l.startswith(f'{N} L='): cls=ast.literal_eval(data[i+1].strip()); break
L=reduce(lcm,range(1,N)); K=N-2
vals=sorted(v for c in cls for v in c)
assert vals==sorted({L*j//k for k in range(2,N) for j in range(1,k)})
for c in cls:
    for a in c:
        for b in c:
            assert a==b or N*gcd(a,b)<=max(a,b)
def wrap(xs, ind):
    s=', '.join(map(str,xs)); lines=[]; cur=''
    for tok in s.split(' '):
        if len(cur)+len(tok)+1>88: lines.append(cur); cur=tok
        else: cur=(cur+' '+tok) if cur else tok
    lines.append(cur); return ('\n'+ind).join(lines)
V='['+wrap(vals,'      ')+']'
C='['+wrap(['['+', '.join(map(str,c))+']' for c in cls],'      ').replace("'","")+']'
C='['+(',\n      ').join('['+', '.join(map(str,c))+']' for c in cls)+']'
body=f'''  intro A h0 hcard
  have toQ : ∀ a b : ℕ, {N} * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b hab
    have hN : ((A.card : ℕ) : ℚ) = {N} := by rw [hcard]; norm_num
    rw [hN, le_div_iff₀ (by norm_num : (0 : ℚ) < {N})]
    exact_mod_cast (by omega : a.gcd b * {N} ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  have hMA : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero fun h => h0 (h ▸ hMA)
  by_cases hdirect : ∃ x ∈ A, {N} * (A.max' hne).gcd x ≤ A.max' hne
  · obtain ⟨x, hxA, hx⟩ := hdirect
    exact ⟨A.max' hne, hMA, x, hxA, toQ _ x hx⟩
  simp only [not_exists, not_and, not_le] at hdirect
  -- every other element x has {L} x = c M with c = {L} j / k, 1 ≤ j < k ≤ {N-1}
  have hval : ∀ x ∈ A.erase (A.max' hne), ∃ c ∈ ({V} : List ℕ),
      {L} * x = c * A.max' hne := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero fun h => h0 (h ▸ hxA)
    have hxlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
    have hbig : A.max' hne < {N} * (A.max' hne).gcd x := hdirect x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < {N} := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hjk : j < k := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj
        omega
      · exact h
    refine ⟨{L} * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  -- a split of the {len(vals)} values into {K} classes, each pairwise good (found by computer search)
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → List ℕ, cls = fun i => {C}.getD i [] :=
    ⟨_, rfl⟩
  obtain ⟨col, hcol⟩ : ∃ col : ℕ → ℕ, col = fun c => {C}.findIdx
      (fun D => D.contains c) := ⟨_, rfl⟩
  have hcover : ∀ c ∈ ({V} : List ℕ),
      col c < {K} ∧ c ∈ cls (col c) := by
    subst hcol hcls
    decide
  have hgood : ∀ i < {K}, ∀ c ∈ cls i, ∀ d ∈ cls i, c = d ∨ {N} * c.gcd d ≤ c ∨ {N} * c.gcd d ≤ d := by
    subst hcls
    decide
  -- pigeonhole: {N-1} other elements, {K} classes
  have hmaps : ∀ x ∈ A.erase (A.max' hne), col ({L} * x / A.max' hne) ∈ Finset.range {K} := by
    intro x hx
    obtain ⟨c, hc, hxc⟩ := hval x hx
    rw [Finset.mem_range, hxc, Nat.mul_div_cancel _ hMpos]
    exact (hcover c hc).1
  have hlt : (Finset.range {K}).card < (A.erase (A.max' hne)).card := by
    rw [Finset.card_erase_of_mem hMA, hcard, Finset.card_range]
    norm_num
  obtain ⟨x, hx, y, hy, hxy, hxycol⟩ := Finset.exists_ne_map_eq_of_card_lt_of_maps_to hlt hmaps
  obtain ⟨c, hc, hxc⟩ := hval x hx
  obtain ⟨d, hd, hyd⟩ := hval y hy
  rw [hxc, hyd, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hxycol
  have hcd : c ≠ d := by
    rintro rfl
    exact hxy (by omega)
  have hcmem := (hcover c hc).2
  have hdmem := (hcover d hd).2
  rw [← hxycol] at hdmem
  -- carry the good pair of values back to x and y
  have hg : c.gcd d * A.max' hne = {L} * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxc, ← hyd, Nat.gcd_mul_left]
  have hxA : x ∈ A := (Finset.mem_erase.mp hx).2
  have hyA : y ∈ A := (Finset.mem_erase.mp hy).2
  rcases hgood (col c) (hcover c hc).1 c hcmem d hdmem with h | h | h
  · exact absurd h hcd
  · refine ⟨x, hxA, y, hyA, toQ x y ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hxc] at h2
    omega
  · refine ⟨y, hyA, x, hxA, toQ y x ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hyd] at h2
    rw [Nat.gcd_comm]
    omega
'''
i=header.index(':= by\n')
open(out,'w').write(header[:i]+':= by\n'+body)
