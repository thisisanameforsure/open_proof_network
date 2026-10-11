import re
src=open('All.lean').read()
# split into theorems
chunks=re.split(r'\n(?=theorem )', re.sub(r'/--.*?-/\n', '', src, flags=re.S))
ths=[c for c in chunks if c.startswith('theorem ')]
out=[]
names=[]
for c in ths:
    m=re.match(r'theorem (\S+)(.*?):= by\n(.*)', c, flags=re.S)
    name, sig, body = m.group(1), m.group(2), m.group(3)
    # split sig into binders and type: last top-level " :\n" or ") :"
    depth=0; idx=None
    for i,ch in enumerate(sig):
        if ch in '([{': depth+=1
        elif ch in ')]}': depth-=1
        elif ch==':' and depth==0 and sig[i+1]!='=':
            idx=i; break
    binders=sig[:idx].strip(); typ=sig[idx+1:].strip()
    bn=[]
    for b in re.findall(r'\(([^():]+):', binders): bn+=b.split()
    names.append(name)
    binders=' '.join(binders.split()); typ=' '.join(typ.split())
    body='\n'.join(('  '+l if l.strip() else l) for l in body.rstrip('\n').split('\n'))
    out.append(f"  have {name.replace('.','_')} : ∀ {binders},\n      {typ} := by\n    intro {' '.join(bn)}\n{body}\n")
text=''.join(out)
for n in names: text=text.replace(n, n.replace('.','_'))
head='''import Mathlib

open Filter

theorem erdos_402__h3_v2__h1__h1 : ∀ (B : Finset ℕ),
  (0 : ℕ) ∉ B →
    B.Nonempty →
      B.gcd id = (1 : ℕ) →
        ¬Nat.Prime B.card →
          (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
            (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
              (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                  ∃ (p : ℕ), Nat.Prime p ∧ B.card ≤ (2 : ℕ) * p ∧ ∃ a ∈ B, p ∣ a := by
  -- Hole `hmid`: B has a pair with gcd(a, b) ≤ a / n, or an element with a prime factor p ≥ n / 3.
  -- The assembly proves: in a strict counterexample no prime p with 2p < n ≤ 3p divides an element
  -- (block lemma for k = 2, matching lemma for B = {2p} ∪ T, and the dual set for the other side).
  have hmid : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.gcd id = 1 → ¬ B.card.Prime →
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) →
      (∃ a ∈ B, ∃ b ∈ B, (a.gcd b : ℚ) ≤ (a : ℚ) / (B.card : ℚ)) ∨
        ∃ p : ℕ, p.Prime ∧ B.card ≤ 3 * p ∧ ∃ a ∈ B, p ∣ a := sorry
'''
tail='''  intro B h0 hne hgcd hnp hnp1 hle hpp
  rcases hmid B h0 hne hgcd hnp hnp1 hle hpp with h | ⟨p, hp, hn3, a, ha, hpa⟩
  · exact Or.inl h
  · by_cases h2 : B.card ≤ 2 * p
    · exact Or.inr ⟨p, hp, h2, a, ha, hpa⟩
    · left
      by_contra hcon
      have hn : 0 < B.card := hne.card_pos
      have hnq : (0 : ℚ) < B.card := by exact_mod_cast hn
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
      obtain ⟨hp3, h9⟩ := R2b_small B.card p hp (by omega) hn3 hnp hnp1
      exact R2b_no_mid_prime B h0 hgcd hlt p hp hp3 (by omega) hn3 h9 a ha hpa
'''
open('skeleton-h1h1.lean','w').write(head+text+tail)
