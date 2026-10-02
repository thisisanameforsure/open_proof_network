# builds CriterionSingle.lean: the whole criterion as ONE declaration (lemmas as `have`s), target's ℚ form
import re
parts=[open(f).read() for f in ['Arith.lean','RectCore.body','Pair.body','Main.body']]
s="\n".join(parts).replace("import Mathlib\n","")
# drop the def; the class function becomes a local obtained with its defining equation
s=re.sub(r"/-- 402-R4-c\. Fold class.*?\ndef r4cCls.*?\n\n","",s,flags=re.S)
s=re.sub(r"/--(.*?)-/",lambda m:"\n".join("-- "+l.strip() for l in m.group(1).strip().splitlines()),s,flags=re.S)
s=s.replace("unfold r4cCls at hc","rw [hcls, hcls] at hc").replace("    unfold r4cCls\n","    rw [hcls]\n")
s=s.replace("theorem ","have ").replace("r4cCls","cls")
body="\n".join(("  "+l if l.strip() else l) for l in s.splitlines())
head='''import Mathlib

/-- 402-R4-c. The prime criterion for Graham's gcd problem as ONE declaration, in the target's form:
a prime p with n < p < 2n and (2n − p)² ≤ n forces a pair with gcd(a, b) ≤ a / n. -/
theorem r4c_criterion_single : ∀ (A : Finset ℕ), 0 ∉ A → ∀ p : ℕ, p.Prime → A.card < p →
    p < 2 * A.card → (2 * A.card - p) * (2 * A.card - p) ≤ A.card →
    ∃ a ∈ A, ∃ b ∈ A, (a.gcd b : ℚ) ≤ (a : ℚ) / (A.card : ℚ) := by
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → ℕ → ℕ, ∀ p a, cls p a =
      min (ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p))
        (p - ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p)) := ⟨_, fun _ _ => rfl⟩
'''
tail='''
  intro A h0 p hp h1 h2 h3
  obtain ⟨a, ha, b, hb, h⟩ := r4c_criterion A h0 p hp h1 h2 h3
  refine ⟨a, ha, b, hb, ?_⟩
  have n0 : (0 : ℚ) < (A.card : ℚ) := by
    have : 0 < A.card := Finset.card_pos.mpr ⟨a, ha⟩
    exact_mod_cast this
  rw [le_div_iff₀ n0]
  have : a.gcd b * A.card ≤ a := by rw [Nat.mul_comm]; exact h
  exact_mod_cast this
'''
open('CriterionSingle.lean','w').write(head+body+tail)
