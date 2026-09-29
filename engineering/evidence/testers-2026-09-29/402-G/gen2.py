import sys, math
sys.path.insert(0,'.')
from colour import colour
WORDS={8:'eight',9:'nine',10:'ten',11:'eleven',12:'twelve',13:'thirteen',14:'fourteen',15:'fifteen',16:'sixteen',18:'eighteen'}
def header(n, nodeid=None):
    L = math.lcm(*range(1,n))
    nvals = len({L*j//k for k in range(2,n) for j in range(1,k)})
    imp = "import Mathlib\n" + (f"import Nodes.«{nodeid}».Context\n" if nodeid else "")
    doc = (f"/-! Graham's gcd conjecture (Erdős problem 402) for {WORDS[n]}-element sets. With M the largest\n"
           f"element, if gcd(M, x) > M/{n} for every x then every other x is (j/k)M with j < k ≤ {n-1}, so\n"
           f"L·x/M (L = lcm(1..{n-1}) = {L}) lies in a fixed set S of {nvals} values. S splits into {n-2} classes in\n"
           f"each of which any two distinct values c, d have {n}·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of\n"
           f"the {n-1} other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/\n")
    thm = (f"theorem Opn.erdos_402_card_{WORDS[n]} :\n"
           f"    ∀ (A : Finset ℕ), 0 ∉ A → A.card = {n} → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by\n")
    return imp + "\n" + doc + "\n" + thm
def statement(n, nodeid=None):
    return header(n, nodeid) + "  sorry\n"
def proof(n, nodeid=None, dec="decide"):
    L, vals, col = colour(n, n-2)
    S = "({" + ", ".join(map(str, vals)) + "} : Finset ℕ)"
    f = "(fun a : ℕ => " + " ".join(f"if a = {v} then {col[v]} else" for v in vals) + " 0)"
    M = "A.max' hne"
    body = f"""  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : {M} ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < {M} := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, ({M}).gcd x * {n} ≤ {M}
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have forms : ∀ x ∈ A.erase ({M}), ∃ a ∈ {S}, {L} * x = a * {M} := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < {M} := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left ({M}) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right ({M}) x
    have hgpos : 0 < ({M}).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < {n} := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left (({M}).gcd x) hh
      omega
    have hjk : j < k := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left (({M}).gcd x) hh
      omega
    have hj1 : 1 ≤ j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    have hk0 : 0 < k := by omega
    have hmemall : ∀ k < {n}, ∀ j < k, 1 ≤ j → {L} * j / k ∈ {S} := by {dec}
    have hdvdall : ∀ k < {n}, 0 < k → k ∣ {L} := by {dec}
    refine ⟨{L} * j / k, hmemall k hkN j hjk hj1, ?_⟩
    obtain ⟨q, hq⟩ := hdvdall k hkN hk0
    have hdiv : {L} * j / k = q * j := by
      rw [hq, Nat.mul_assoc, Nat.mul_div_cancel_left _ hk0]
    rw [hdiv, hq]
    conv_lhs => rw [hj]
    conv_rhs => rw [hk]
    ring
  have hcard : (A.erase ({M})).card = {n-1} := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hS : ∀ a ∈ {S}, {f} a < {n-2} := by {dec}
  have hmaps : ∀ x ∈ A.erase ({M}), {f} ({L} * x / {M}) ∈ Finset.range {n-2} := by
    intro x hx
    obtain ⟨a, ha, hax⟩ := forms x hx
    rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
    exact hS a ha
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨a, ha, hax⟩ := forms x hx
  obtain ⟨b, hb, hby⟩ := forms y hy
  rw [hax, hby, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hab : a ≠ b := by
    intro h
    subst h
    apply hxy
    omega
  have hpair : ∀ a ∈ {S}, ∀ b ∈ {S}, a ≠ b → {f} a = {f} b →
      {n} * a.gcd b ≤ a ∨ {n} * a.gcd b ≤ b := by {dec}
  have hgcd : a.gcd b * {M} = {L} * x.gcd y := by
    have h1 : Nat.gcd ({L} * x) ({L} * y) = {L} * x.gcd y := Nat.gcd_mul_left {L} x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hpair a ha b hb hab hc with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right ({M}) h
    have h3 : x.gcd y * {n} * {L} ≤ x * {L} := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right ({M}) h
    have h3 : x.gcd y * {n} * {L} ≤ y * {L} := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
"""
    return header(n, nodeid) + body
def check_req(text, node=None, mode="check"):
    import json
    d={"target_id":"erdos-402","mode":mode,"content":text}
    if node: d["node_id"]=node
    return json.dumps(d)
if __name__=='__main__':
    n=int(sys.argv[1]); dec=sys.argv[2] if len(sys.argv)>2 else "decide"
    open(f'p{n}.lean','w').write(proof(n, None, dec))
    open(f'p{n}.req','w').write(check_req(proof(n,None,dec)))
