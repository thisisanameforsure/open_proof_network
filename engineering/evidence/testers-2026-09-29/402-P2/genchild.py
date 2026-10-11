# usage: genchild.py OUT --cut=C [--enc=tbl] [--only=n1,n2,...] [--header=FILE]
# --enc=tbl uses general2.txt (colour table indexed by (k, j); about 5x cheaper to check than findIdx).
# Writes a partial proof of the hole #289 creates: sizes < C closed (certificates for the sizes that are
# neither prime nor prime+1), one hole for C <= |B|. --only keeps only those certificate cases (others
# sorry) so a piece fits /check's 20 s. --header: the child's Statement.lean up to and including ':= by'.
import sys, json
import os
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from certs import res, verify
from math import lcm
from functools import reduce
D='/home/user/open_proof_network/engineering/evidence/testers-2026-09-29/402-D/le24/Proof.final.lean'
src=open(D).read()
g0=src.index("  have general :"); g1=src.index("  intro A hA hne hle")
general=src[g0:g1]
ENC='findidx'
for a in sys.argv[2:]:
    if a=='--enc=tbl': ENC='tbl'; general=open(os.path.join(HERE,'general2.txt')).read()
out=sys.argv[1]
only=None
HDR=None
for a in sys.argv[2:]:
    if a.startswith("--only="): only=set(int(x) for x in a[7:].split(",") if x)
    if a.startswith("--header="): HDR=open(a[9:]).read()
import glob
for fj in glob.glob(os.path.join(HERE,'certs','found_*.json')):
    for k,v in json.load(open(fj)).items(): res[int(k)]=v
CUT=None
for a in sys.argv[2:]:
    if a.startswith("--cut="): CUT=int(a[6:])
def isprime(n): return n>1 and all(n%d for d in range(2,int(n**.5)+1))
if HDR is None:
    HDR='''import Mathlib

open Filter

theorem hole_child : ∀ (B : Finset ℕ),
  (0 : ℕ) ∉ B →
    B.Nonempty →
      B.gcd id = (1 : ℕ) →
        ¬Nat.Prime B.card →
          (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
            (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
              (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                ∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ) := by
'''
body=HDR.rstrip("\n")+"\n"
body+='''  -- Sizes up to %d are closed here. A prime size or one more than a prime is excluded by the
  -- hypotheses, size 1 is a = b, and every other size n has a finite certificate (the "largest
  -- element" colouring argument of spec-fa8046e4 and variant-77918742, inlined as `general`
  -- because a proof may not add an import): with L = lcm(1..n-1), the values L·j/k
  -- (1 ≤ j < k < n) split into n - 2 classes in which two distinct members c, d have
  -- n·gcd(c, d) ≤ c or ≤ d. What is left open:
  -- Graham's bound for the same primitive sets when |B| ≥ %d.
  have hbig : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.gcd id = 1 → ¬ B.card.Prime →
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) →
      %d ≤ B.card →
      ∃ a ∈ B, ∃ b ∈ B, a.gcd b ≤ (a / B.card : ℚ) := sorry
''' % (CUT-1, CUT, CUT)
body+=general
body+='''  intro B hB hne _hg hnp hnq _hle _hpp
  by_cases hc : %d ≤ B.card
  · exact hbig B hB hne _hg hnp hnq _hle _hpp hc
  obtain ⟨n, hn⟩ : ∃ n, B.card = n := ⟨_, rfl⟩
  have h1 : 1 ≤ n := by rw [← hn]; exact Finset.card_pos.mpr hne
  have hN : n ≤ %d := by omega
  rw [hn] at hnp hnq
  interval_cases n
''' % (CUT, CUT-1)
cases=[]
for n in range(1,CUT):
    if n==1:
        body+='''  · obtain ⟨a, rfl⟩ := Finset.card_eq_one.mp hn
    exact ⟨a, by simp, a, by simp, by simp⟩
'''
    elif isprime(n):
        body+="  · exact (hnp (by norm_num)).elim\n"
    elif isprime(n-1):
        body+="  · exact (hnq %d (by norm_num) rfl).elim\n" % (n-1)
    else:
        cases.append(n)
        if only is not None and n not in only:
            body+="  · sorry\n"; continue
        L,_,_=verify(n,res[n]); cls=res[n][:n-2]
        if ENC=='tbl':
            where={v:i for i,c in enumerate(cls) for v in c}
            tbl=[[ (where[L//k*j] if (k>0 and j>0) else 0) for j in range(k)] for k in range(n)]
            body+="  · exact general %d %d %s %s (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel)\n      (by decide +kernel) B hB hn\n" % (n,L,json.dumps(cls).replace("],[","], ["),json.dumps(tbl).replace("],[","], ["))
        else:
            body+="  · exact general %d %d %s (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel)\n      (by decide +kernel) B hB hn\n" % (n,L,json.dumps(cls).replace("],[","], ["))
open(out,"w").write(body)
print("certificate cases:",cases, "bytes", len(body))
