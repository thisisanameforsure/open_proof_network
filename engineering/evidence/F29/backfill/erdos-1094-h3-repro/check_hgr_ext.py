"""h_gr shape beyond k=700: does every n in [k^2/(16 log2 k), k^2) have a carry prime in (k/2,11k/20)?
Sampled k (every k in 650..1000, then step 7 to 4000). Also the worst n's {n/p}-coverage."""
import math, numpy as np
from sympy import primerange
def fails(k, C=16):
    lo = max(2*k, math.ceil(k*k/(C*int(math.log2(k)))))
    n = np.arange(lo, k*k, dtype=np.int64); bad = np.ones(n.shape, bool)
    ps = [p for p in primerange(k//2+1, k) if 20*p < 11*k]
    for p in ps: bad &= ~((n % p) < (k % p))
    return int(bad.sum()), len(ps), n[bad][:3].tolist()
last=None
for k in list(range(650,1001))+list(range(1001,4001,7)):
    f,np_,ex = fails(k)
    if f: last=k; print("k",k,"primes in interval",np_,"failures",f,"e.g.",ex)
print("last failing k sampled:", last)
