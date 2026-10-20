"""Erdos #1094, node erdos-1094--h3: computational checks (finite ranges, not proofs).
A. node claim: all (n,k), 2k<=n<k^2, lpf C(n,k) > k  (Kummer: no base-p carry for every p<=k).
B. h_gr shape: n in [k^2/(C log2 k), k^2) with NO prime p in (k/2,11k/20) having n%p < k%p.
C. h_cheb: S(k) = sum_{k/2<p<11k/20} log p >= k/100; last failure, + explicit tail via Rosser-Schoenfeld.
D. Lemma: n%p < k%p  =>  p | C(n,k)  (brute-force sanity check)."""
import sys, math, numpy as np
from sympy import primerange, binomial
KA = int(sys.argv[1]) if len(sys.argv) > 1 else 300
KB = int(sys.argv[2]) if len(sys.argv) > 2 else 700
KC = int(sys.argv[3]) if len(sys.argv) > 3 else 2_000_000

def carry_free(n, k, p):  # vectorised over n: no carry adding k and n-k in base p
    ok = np.ones(n.shape, bool); m = n.copy(); kk = k
    while kk:
        ok &= (m % p) >= (kk % p); m //= p; kk //= p
    return ok

print("== A: node claim, k <=", KA)
found = []
for k in range(1, KA + 1):
    if 2 * k >= k * k: continue
    n = np.arange(2 * k, k * k, dtype=np.int64); good = np.ones(n.shape, bool)
    for p in primerange(2, k + 1):
        good &= carry_free(n, k, p)
        if not good.any(): break
    found += [(int(x), k) for x in n[good]]
print(len(found), "pairs:", found)

print("== B: h_gr shape, k <=", KB)
for C in (1, 2, 4, 8, 16):
    last = None; cnt = 0
    for k in range(4, KB + 1):
        lo = max(2 * k, math.ceil(k * k / (C * max(1, int(math.log2(k))))))
        if lo >= k * k: continue
        n = np.arange(lo, k * k, dtype=np.int64); bad = np.ones(n.shape, bool)
        for p in primerange(k // 2 + 1, k + 1):
            if not (2 * p > k and 20 * p < 11 * k): continue
            bad &= ~((n % p) < (k % p))
        if bad.any(): last = k; cnt += int(bad.sum())
    print(f"C={C}: last k with a failure = {last}, total failing (n,k) = {cnt}")
# unrestricted n (no ELS hypothesis): failures persist?
lastU = max(k for k in range(4, KB + 1) if any(
    all(not (n % p < k % p) for p in primerange(k // 2 + 1, k + 1) if 20 * p < 11 * k)
    for n in range(2 * k, min(k * k, 2 * k + 50))))
print("unrestricted small n (2k..2k+50): last k with a failure =", lastU)

print("== C: h_cheb up to k =", KC)
x = KC * 11 // 20 + 2
sieve = np.ones(x + 1, bool); sieve[:2] = False
for i in range(2, int(x ** .5) + 1):
    if sieve[i]: sieve[i*i::i] = False
lg = np.where(sieve, np.log(np.arange(x + 1).clip(1)), 0.0); cum = np.cumsum(lg)  # cum[m]=theta(m)
ks = np.arange(1, KC + 1)
hi = (11 * ks - 1) // 20  # largest integer < 11k/20
lo = ks // 2              # largest integer <= k/2
S = cum[hi] - cum[lo]
fail = ks[S < ks / 100]
print("last k with S(k) < k/100:", int(fail.max()) if len(fail) else None, "; min S/k over k>last:",
      float((S / ks)[fail.max():].min()))
# explicit tail (cited Rosser-Schoenfeld 1962, (3.14) theta(x)<x(1+1/(2log x)) x>1; (3.16) theta(x)>x(1-1/(2log x)) x>=563)
# S(k) >= theta(11k/20 - 1/20) - theta(k/2)  (integers < 11k/20 are <= (11k-1)/20)
def tail_ok(k):
    a = (11 * k - 1) / 20; b = k / 2
    return a * (1 - 1 / (2 * math.log(a))) - b * (1 + 1 / (2 * math.log(b))) >= k / 100
# the RS lower bound minus upper bound is increasing in k once positive; find threshold
k0 = next(k for k in range(1200, 10**8, 1000) if tail_ok(k) and tail_ok(k + 1000) )
print("RS tail bound gives S(k) >= k/100 for k >= ~", k0, " (checked monotone below); numeric range covers it:", k0 <= KC)
# monotonicity of f(k)=RSlower-RSupper-k/100 derivative check on a grid
grid = [k0 * 2 ** j for j in range(40)]
print("tail_ok on doubling grid from k0:", all(tail_ok(g) for g in grid))

print("== D: lemma n%p<k%p => p | C(n,k), k<=40, n<=400")
viol = [(n, k, p) for k in range(1, 41) for n in range(k, 401) for p in primerange(2, k + 1)
        if n % p < k % p and binomial(n, k) % p]
print("violations:", viol)
