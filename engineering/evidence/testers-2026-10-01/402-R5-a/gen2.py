# 402-R5-a: generator for the second skeleton (on the hole `hwin` of skeleton-window-final.lean).
import math, re, glob, pathlib, sys
def isprime(m): return m>1 and all(m%d for d in range(2,math.isqrt(m)+1))
def W(n): return any(isprime(p) for p in range(max(n+1,2*n-math.isqrt(n)),2*n))
EXC=[n for n in range(2,681) if not W(n)]
assert EXC==[5,8,14,18,48,61,62,63,74,105,111,153,165,270,677,678,679,680]
SEVEN=[63,105,111,153,165,679,680]
# own cover of 2..680 minus EXC
blocks=[]; n=2
while n<=680:
    if n in EXC: n+=1; continue
    k=math.isqrt(n); p=max(q for q in range(max(n+1,2*n-k),2*n) if isprime(q))
    hi=min((p+k)//2,p-1,680)
    assert all(n2<p<2*n2 and (2*n2-p)**2<=n2 for n2 in range(n,hi+1))
    blocks.append((p,n,hi,2*hi-p)); n=hi+1
# window ranges from 402-R4-c/Window (file names only)
rng=sorted(tuple(map(int,re.search(r'window_(\d+)_(\d+)',f).groups())) for f in glob.glob('../402-R4-c/Window/*.lean'))
assert rng[0][0]==681 and rng[-1][1]==200014 and all(rng[i][1]+1==rng[i+1][0] for i in range(len(rng)-1)), rng
Wn=lambda n:f"∃ p : ℕ, p.Prime ∧ {n} < p ∧ p < 2 * {n} ∧ (2 * {n} - p) * (2 * {n} - p) ≤ {n}"
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
WB="∃ (p : ℕ), Nat.Prime p ∧ B.card < p ∧ p < 2 * B.card ∧\n                    (2 * B.card - p) * (2 * B.card - p) ≤ B.card"
GOAL=HYP+PAIR+" ∨\n                    "+WB
Tres=HYP+"(B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680) →\n                    "+PAIR
Tlarge=HYP+"200014 < B.card →\n                    "+PAIR+" ∨\n                    "+WB
Tw=lambda lo,hi:f"∀ n : ℕ, {lo} ≤ n → n ≤ {hi} → {Wn('n')}"
names=[f"hw{i+1}" for i in range(len(rng))]
allT=[("hres",Tres),("hlarge",Tlarge)]+[(nm,Tw(lo,hi)) for nm,(lo,hi) in zip(names,rng)]
scoped = (sys.argv[1]=="scoped")
L=[]
L.append("  -- Second step of the window-prime route (402-R5-a). Holes: `hres` (the seven sizes with no window prime),")
L.append("  -- `hlarge` (sizes above 200014; analytic: see the annex of 2026-10-01 on the parent node), `hw1`..`hw18` (window primes for 681..200014,")
L.append("  -- finite certificates). The assembly proves the window primes for 2..680 and the case split.")
if scoped:
    L.append("  have hall : ("+")\n      ∧ (".join(t for _,t in allT)+") := by")
    L.append("    refine ⟨"+", ".join("?_" for _ in allT)+"⟩")
    for nm,t in allT:
        L.append(f"    · have {nm} : {t} := by\n        sorry\n      exact {nm}")
    L.append("  obtain ⟨"+", ".join(nm for nm,_ in allT)+"⟩ := hall")
else:
    for nm,t in allT:
        L.append(f"  have {nm} : {t} := by\n    sorry")
L.append(f"  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →\n      ∀ n : ℕ, lo ≤ n → n ≤ hi → {Wn('n')} := by")
L.append("    intro p lo hi k hp h1 h2 h3 h4 n hl hh\n    refine ⟨p, hp, by omega, by omega, ?_⟩\n    have : 2 * n - p ≤ k := by omega\n    exact le_trans (Nat.mul_le_mul this this) (by omega)")
L.append("  have hsmall : ∀ n : ℕ, 2 ≤ n → n ≤ 680 → "+" → ".join(f"n ≠ {e}" for e in EXC)+f" →\n      {Wn('n')} := by")
L.append("    intro n h2 h680 "+" ".join(f"e{e}" for e in EXC))
for (p,lo,hi,k) in blocks:
    L.append(f"    by_cases c{hi} : n ≤ {hi}")
    L.append(f"    · exact blk {p} {lo} {hi} {k} (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) c{hi}")
L.append("    omega")
L.append("  intro B h0 hne hg hnp hq hle hpk")
L.append("  have hpos : 0 < B.card := Finset.card_pos.mpr hne")
L.append("  by_cases hbig : 200014 < B.card\n  · exact hlarge B h0 hne hg hnp hq hle hpk hbig")
for nm,(lo,hi) in reversed(list(zip(names,rng))):
    L.append(f"  by_cases c{lo} : {lo} ≤ B.card\n  · exact Or.inr ({nm} B.card c{lo} (by omega))")
L.append("  by_cases h7 : B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680\n  · exact Or.inl (hres B h0 hne hg hnp hq hle hpk h7)")
L.append("  by_cases h1 : B.card = 1\n  · obtain ⟨a, ha⟩ := hne\n    refine Or.inl ⟨a, ha, a, ha, ?_⟩\n    rw [h1]\n    simp")
for e in EXC:
    if e in SEVEN: continue
    if isprime(e):
        L.append(f"  have x{e} : B.card ≠ {e} := by\n    intro h\n    rw [h] at hnp\n    exact hnp (by norm_num)")
    else:
        assert isprime(e-1)
        L.append(f"  have x{e} : B.card ≠ {e} := hq {e-1} (by norm_num)")
L.append("  exact Or.inr (hsmall B.card (by omega) (by omega) "+" ".join("(by omega)" if e in SEVEN else f"x{e}" for e in EXC)+")")
body="\n".join(L)+"\n"
hdr=sys.argv[2]   # file with header up to and incl ':= by\n'
pathlib.Path(sys.argv[3]).write_text(pathlib.Path(hdr).read_text()+body)
print(len(blocks),"small blocks;",len(rng),"window holes;",len(body.splitlines()),"body lines")
