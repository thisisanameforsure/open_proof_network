# 402-R6-a: generator for the skeleton on the hole `hgen` (4 scoped holes).
# usage: gen3.py <header file up to and incl ':= by\n'> <out>
import sys, pathlib
HYP='''∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  '''
PAIR="(∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ))"
def GEN(n,ind):
    return (f"∃ p : ℕ, p.Prime ∧ {n} < p ∧ p < 2 * {n} ∧ 2 * (2 * {n} - p) ≤ {n} + 2 ∧\n{ind}∀ α : ℕ, α < {n} → p < α + {n} →\n"
            f"{ind}  (∃ q : ℕ, q.Prime ∧ {n} ≤ 3 * q ∧ q ∣ α * (p - α)) ∨\n{ind}  (∀ x y : ℕ, x < y → x * y ∣ α → {n} * x ≤ α * y)")
Wn=lambda n:f"∃ p : ℕ, p.Prime ∧ {n} < p ∧ p < 2 * {n} ∧ (2 * {n} - p) * (2 * {n} - p) ≤ {n}"
Ts=lambda lo,hi:f"∀ n : ℕ, {lo} ≤ n → n ≤ {hi} →\n          "+GEN('n','            ')
Tw=f"∀ n : ℕ, 681 ≤ n → n ≤ 200014 →\n          "+Wn('n')
Tlarge=HYP+"200014 < B.card →\n                    "+PAIR+" ∨\n                    "+GEN('B.card','                      ')
allT=[("hs1",Ts(10,228)),("hs2",Ts(229,200014)),("hlarge",Tlarge)]
L=[]
L.append("  -- Split of `hgen` by size n = |B| (agent 402-R6-a; statements prepared with agents 402-R5-b and 402-R6-b). Three holes,")
L.append("  -- each in its own goal so none inherits another:")
L.append("  -- `hs1` (10 ≤ n ≤ 228) and `hs2` (229 ≤ n ≤ 200014): a prime with the generalised window hypotheses exists. Finite")
L.append("  -- certificates; both have complete Lean proofs ready.")
L.append("  -- `hlarge` (n > 200014): the node's own conclusion for large sets. This is NOT a finite check and not a small lemma: it")
L.append("  -- needs, for every large n, a prime within about √n below 2n, which no unconditional theorem gives; see the annex on it.")
L.append("  -- The assembly proves the sizes below 10 and the case split.")
L.append("  have hall : ("+")\n      ∧ (".join(t for _,t in allT)+") := by")
L.append("    refine ⟨"+", ".join("?_" for _ in allT)+"⟩")
for nm,t in allT:
    L.append(f"    · have {nm} : {t} := by\n        sorry\n      exact {nm}")
L.append("  obtain ⟨"+", ".join(nm for nm,_ in allT)+"⟩ := hall")
L.append("  intro B h0 hne hg hnp hq hle hpk")
L.append("  by_cases hbig : 200014 < B.card\n  · exact hlarge B h0 hne hg hnp hq hle hpk hbig")
L.append("  by_cases c229 : 229 ≤ B.card\n  · exact Or.inr (hs2 B.card c229 (by omega))")
L.append("  by_cases c10 : 10 ≤ B.card\n  · exact Or.inr (hs1 B.card c10 (by omega))")
L.append("  by_cases h1 : B.card = 1\n  · obtain ⟨a, ha⟩ := hne\n    refine Or.inl ⟨a, ha, a, ha, ?_⟩\n    rw [h1]\n    simp")
L.append("  by_cases h9 : B.card = 9\n  · refine Or.inr ⟨17, by norm_num, by omega, by omega, by omega, fun α h1 h2 => ?_⟩\n    omega")
L.append("  have hpos : 0 < B.card := Finset.card_pos.mpr hne")
for e in (2,3,5,7):
    L.append(f"  have x{e} : B.card ≠ {e} := by\n    intro h\n    rw [h] at hnp\n    exact hnp (by norm_num)")
for e in (4,6,8):
    L.append(f"  have x{e} : B.card ≠ {e} := hq {e-1} (by norm_num)")
L.append("  omega")
pathlib.Path(sys.argv[2]).write_text(pathlib.Path(sys.argv[1]).read_text()+"\n".join(L)+"\n")
