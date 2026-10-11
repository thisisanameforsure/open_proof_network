# turn All.lean's three theorems into `have`s of one declaration (the predicted next hole) -> skeleton-kernel.lean
import re
src=re.sub(r'/--.*?-/\n', '', open('All.lean').read(), flags=re.S)
chunks=[c for c in re.split(r'\n(?=theorem )', src) if c.startswith('theorem ')]
intros={'R3c.block_kernel':'B N p M h0 hp hM0 hM hs hU hV',
        'R3c.no_prime_of_kernel':'B h0 hgcd hlt p k M hp hM0 hM hk hK',
        'R3c.no_quarter_prime':'B h0 hgcd hlt p hp h3p hn4 hK3'}
out=[]
for c in chunks:
    m=re.match(r'theorem (\S+)(.*?):= by\n(.*)', c, flags=re.S)
    name, sig, body = m.group(1), m.group(2), m.group(3)
    depth=0; idx=None
    for i,ch in enumerate(sig):
        if ch in '([{': depth+=1
        elif ch in ')]}': depth-=1
        elif ch==':' and depth==0 and sig[i+1]!='=': idx=i; break
    binders=' '.join(sig[:idx].split()); typ=' '.join(sig[idx+1:].split())
    body='\n'.join(('  '+l if l.strip() else l) for l in body.rstrip('\n').split('\n'))
    out.append(f"  have {name.replace('.','_')} : ∀ {binders},\n      {typ} := by\n    intro {intros[name]}\n{body}\n")
text=''.join(out)
for n in intros: text=text.replace(n, n.replace('.','_'))
K3='''(∀ (n p : ℕ) (X S : Finset ℕ), p.Prime → 3 * p < n → n ≤ 4 * p → X.Nonempty → S.Nonempty →
        (∀ x ∈ X, 0 < x) → (∀ s ∈ S, 0 < s) → (∀ s ∈ S, ¬ p ∣ s) →
        (∀ x ∈ X, ∀ x' ∈ X, x < n * Nat.gcd x x') →
        (∀ s ∈ S, ∀ t ∈ S, s < n * Nat.gcd s t) →
        (∀ x ∈ X, ∀ s ∈ S, ∃ m y : ℕ, 0 < m ∧ m ≤ 3 ∧ y < n ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧
          x * s * m = 6 * y) →
        X.card + S.card < n)'''
head='''import Mathlib

open Filter

theorem erdos_402__h3_v2__h1__h1__h1 : ∀ (B : Finset ℕ),
  (0 : ℕ) ∉ B →
    B.Nonempty →
      B.gcd id = (1 : ℕ) →
        ¬Nat.Prime B.card →
          (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
            (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
              (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                  ∃ (p : ℕ), Nat.Prime p ∧ B.card ≤ (3 : ℕ) * p ∧ ∃ a ∈ B, p ∣ a := by
  -- Hole `hquarter`, two parts (one hole, a conjunction; n = |B|):
  -- (1) B has a pair with gcd(a, b) ≤ a / n, or an element with a prime factor p ≥ n / 4;
  -- (2) the kernel K3, a statement about two finite sets of positive integers, free of B:
  --     p prime, 3p < n ≤ 4p, X and S nonempty, each with all quotients x / gcd(x, x') < n, no member of S
  --     divisible by p, and every x in X, s in S with x·s·m = 6·y for some 1 ≤ m ≤ 3, y < n, p ∤ y, gcd(m, y) = 1.
  --     Then |X| + |S| ≤ n − 1.  (Equality holds for X = {2, 3, 6}, S = {s < n : p ∤ s}: the hypotheses are satisfiable.)
  -- The assembly (block_kernel) turns a set B with all quotients < n and a prime p, 3p < n ≤ 4p, dividing an element
  -- into such X (from the multiples of p) and S (from the others) with |X| + |S| = n.
  have hquarter : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.gcd id = 1 → ¬ B.card.Prime →
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) →
      ((∃ a ∈ B, ∃ b ∈ B, (a.gcd b : ℚ) ≤ (a : ℚ) / (B.card : ℚ)) ∨
        ∃ p : ℕ, p.Prime ∧ B.card ≤ 4 * p ∧ ∃ a ∈ B, p ∣ a) ∧
      '''+K3+''' := sorry
'''
tail='''  intro B h0 hne hgcd hnp hnp1 hle hpp
  obtain ⟨h1, hK3⟩ := hquarter B h0 hne hgcd hnp hnp1 hle hpp
  rcases h1 with h | ⟨p, hp, hn4, a, ha, hpa⟩
  · exact Or.inl h
  by_cases h3 : B.card ≤ 3 * p
  · exact Or.inr ⟨p, hp, h3, a, ha, hpa⟩
  left
  by_contra hcon
  have hnq : (0 : ℚ) < B.card := by exact_mod_cast hne.card_pos
  have hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b := by
    intro a ha b hb
    rcases (hle a ha b hb).lt_or_eq with h | h
    · exact h
    · exfalso
      apply hcon
      refine ⟨a, ha, b, hb, ?_⟩
      rw [le_div_iff₀ hnq]
      have h2 : a.gcd b * B.card ≤ a := by rw [Nat.mul_comm]; exact h.ge
      exact_mod_cast h2
  exact R3c_no_quarter_prime B h0 hgcd hlt p hp (by omega) hn4 hK3 a ha hpa
'''
open('skeleton-kernel.lean','w').write(head+text+tail)
