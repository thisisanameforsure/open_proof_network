**Numerical checks of every statement of erdos-1094, 2026-10-12.** These are searches of finite ranges, not proofs. The code is at the end.

**Method.** A prime $p$ divides $\binom{n}{k}$ exactly when some base-$p$ digit of $k$ exceeds the matching digit of $n$ (Kummer, Lucas). For $p>k$ that is just $n\bmod p<k$. All arithmetic is exact. Three searches were run:

- `good`: every $(n,k)$ with $2k\le n<k^3$ and no prime $p\le k$ dividing $\binom{n}{k}$, for all $k\le 1000$.
- `resid`: every $(n,k)$ with $2k\le n<k^2$ and no prime $p\le k$ with $n\bmod p<k\bmod p$, for all $k\le 1000$.
- `hi`: every $(n,k)$ with $n\ge k^2$ and no prime $p\le\lfloor n/k\rfloor$ dividing $\binom{n}{k}$, in three ranges:
  - all $n$, for $k\le 26$. This range is complete with no cap on $n$, by the bound proved on `erdos-1094--h1`: such an exception has $\lfloor n/k\rfloor$ dividing $(k-1)!$, which leaves finitely many candidates, each resolved by finding a prime divisor.
  - $11\le k\le 60$ with $n<10^8$.
  - $k\le 1000$ with $n<2\cdot10^6$.

`good` was cross-checked against a gcd with the primorial ($k\le 45$). `resid` was cross-checked against a direct Python loop ($k\le 120$). The root's set was cross-checked against the literal Lean predicate, using `math.comb` and the `Nat.minFac` conventions ($k\le 30$, $n\le 3000$).

**Results.** For each statement: the range searched, then the pairs found and the smallest $K$ that works there.

- **Root** (all $k\le 1000$ with $n<k^3$, plus all $n$ for $k\le 26$): exactly the 14 pairs of Erdős–Lacampagne–Selfridge (1988), $(7,3)$, $(13,4)$, $(14,4)$, $(23,5)$, $(62,6)$, $(44,8)$, $(46,10)$, $(47,10)$, $(74,10)$, $(94,10)$, $(95,10)$, $(47,11)$, $(241,16)$, $(284,28)$, and nothing else. Only $(62,6)$ has $n\ge k^2$.
- **`--h2`** and **`--h2--h1`**, $k^2\le n$: only $(62,6)$, so the smallest $K$ is $6$.
- **`--h2--h2`**, $n\ge k^3$: no pair at all in any `hi` range, so any $K$ works there.
- **`--h2--h1--h1`**, good with $2k\le n<k^3$: 137 pairs. The largest are $(6459,33)$ and $(37619,35)$, and none has $36\le k\le 1000$, so the smallest $K$ is $35$.
- **`--h3`**, good with $2k\le n<k^2$: 13 pairs, the root's 14 without $(62,6)$. The smallest $K$ is $28$.
- **`--h3--h1`**, the residue form: 301 failures, the last $(773,58)$ and $(1579,58)$, so the smallest $K$ is $58$. All 13 good pairs of `--h3` are among them.
- **`--h3--h1--h1`**, $k$ even: 208 failures. The smallest $K_1$ is $58$.
- **`--h3--h1--h2`**, $k$ and $n$ odd: 93 failures, the last $(1469,39)$. The smallest $K_2$ is $39$.
- With $k$ odd and $n$ even there is no failure at all, as $p=2$ predicts.

**Edge cases of the Lean root, checked.**

- Without $0<k$, every $(n,0)$ would satisfy it, since `Nat.minFac 1 = 1 > max (n/0) 0 = 0`.
- Without $2k\le n$, there would be infinitely many: for example $(p,p-1)$ for every prime $p$. The ones with $k<30$ are $(3,2)$, $(5,4)$, $(7,4)$, $(7,6)$, $(11,10)$, …
- The symmetric partner $(n,n-k)$ of each exception is excluded unless $n=2k$.

**The set is not empty.** The following was checked with `POST /check` on 2026-10-12: `okay`, Lean 4.33.1. It is a fast, non-authoritative check, `log_id 01M4RRHZJ0BJKQ28ZJYQQ9W5HM`.

```lean
example : (7, 3) ∈ {(n, k) : ℕ × ℕ | 0 < k ∧ 2 * k ≤ n ∧ (n.choose k).minFac > max (n / k) k} := by
  show 0 < 3 ∧ 2 * 3 ≤ 7 ∧ (Nat.choose 7 3).minFac > max (7 / 3) 3
  rw [show Nat.choose 7 3 = 35 from rfl, show Nat.minFac 35 = 5 by norm_num]
  decide
```

The root's `Witness.lean` is `True`, because the statement has no hypotheses (D-4 step 7). This example is what shows the statement is not satisfied by an empty set.

**Code** (`cc -O2 e1094.c`; the run is `./e1094 good 1 1000 3`, `./e1094 resid 1 1000`, `./e1094 hi 11 60 100000000`, `./e1094 hi 1 1000 2000000`):

```c
/* Numerics for Erdos 1094 nodes. Exact integer arithmetic; divisibility of C(n,k) by a prime p
 * decided by Lucas/Kummer: p does NOT divide C(n,k) iff every base-p digit of k is <= the
 * corresponding digit of n. For p > k this reduces to: p | C(n,k) iff n mod p < k.
 *
 * Modes:
 *   good  KMIN KMAX E   : all (n,k) with 2k <= n < k^E (E = 2 or 3) and no prime p <= k dividing
 *                         C(n,k)  (i.e. minFac C(n,k) > k).  Prints "G n k".  Per-k summary "S k count".
 *   hi    KMIN KMAX NMAX: all (n,k) with k^2 <= n < min(NMAX, k!+k) and no prime p <= n/k dividing
 *                         C(n,k) (i.e. minFac C(n,k) > n/k).  Prints "H n k".
 *   resid KMIN KMAX     : all (n,k) with 2k <= n < k^2 and no prime p <= k with n%p < k%p.
 *                         Prints "R n k".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef unsigned long long u64;

static int *primes; static int np;
static void sieve(int lim){
  char *c = calloc(lim+1,1); primes = malloc(sizeof(int)*(lim/2+10)); np=0;
  for(int i=2;i<=lim;i++){ if(!c[i]){ primes[np++]=i; for(long long j=(long long)i*i;j<=lim;j+=i) c[j]=1; } }
  free(c);
}
/* 1 if p does not divide C(n,k) (k digits dominated by n digits) */
static inline int dom(u64 n,u64 k,u64 p){ while(k){ if(k%p > n%p) return 0; k/=p; n/=p; } return 1; }

int main(int argc,char**argv){
  if(argc<4){fprintf(stderr,"usage\n");return 1;}
  const char*mode=argv[1]; u64 kmin=strtoull(argv[2],0,10), kmax=strtoull(argv[3],0,10);
  if(!strcmp(mode,"good")){
    int E=atoi(argv[4]); sieve((int)kmax+1);
    for(u64 k=kmin;k<=kmax;k++){
      u64 lim = (E==2)? k*k : k*k*k; u64 cnt=0;
      u64 x=k; while(x<2*k) x=(x+1)|k;          /* supersets of k's bits: base-2 domination */
      for(; x<lim; x=(x+1)|k){
        int ok=1;
        for(int i=1;i<np && (u64)primes[i]<=k;i++){ if(!dom(x,k,primes[i])){ok=0;break;} }
        if(ok){ printf("G %llu %llu\n",x,k); cnt++; }
      }
      if(k<2*k && 2*k<lim && 0) {}
      fprintf(stderr,"S %llu %llu\n",k,cnt);
    }
  } else if(!strcmp(mode,"hi")){
    u64 nmax=strtoull(argv[4],0,10); sieve((int)(nmax/ (kmin?kmin:1))+2);
    for(u64 k=kmin;k<=kmax;k++){
      u64 f=1; int big=0; for(u64 i=2;i<=k;i++){ if(f> (u64)4e18/i){big=1;break;} f*=i; }
      u64 lim = nmax; if(!big && f+k < lim) lim=f+k;
      for(u64 n=k*k; n<lim; n++){
        u64 B=n/k; int ex=1;
        for(int i=0;i<np && (u64)primes[i]<=B;i++){
          u64 p=primes[i];
          if(p<=k){ if(!dom(n,k,p)){ex=0;break;} }
          else { if(n%p < k){ex=0;break;} }
        }
        if(ex) printf("H %llu %llu\n",n,k);
      }
      fprintf(stderr,"S %llu lim %llu\n",k,lim);
    }
  } else if(!strcmp(mode,"resid")){
    sieve((int)kmax+1);
    for(u64 k=kmin;k<=kmax;k++){
      for(u64 n=2*k;n<k*k;n++){
        int found=0;
        for(int i=0;i<np && (u64)primes[i]<=k;i++){ u64 p=primes[i]; if(n%p < k%p){found=1;break;} }
        if(!found) printf("R %llu %llu\n",n,k);
      }
    }
  }
  return 0;
}
```

The complete search for $n\ge k^2$, $k\le 26$ (`python3 hi_complete.py 26`):

```python
"""Complete enumeration (no n cap) of exceptions with n >= k^2 for small k.

Uses the fact proved in Lean on erdos-1094--h1 (Proof.lean): if n >= k^2 and minFac C(n,k) > n/k,
then m = k*(n//k) divides k!, i.e. B = n//k divides (k-1)!.  So every such exception has
n in [k*B, k*B + k - 1] for some divisor B of (k-1)! with B >= k.  For each candidate we test
primes p <= B in increasing order (Lucas digit test for p <= k; n % p < k for p > k) and stop at
the first divisor of C(n,k).  A candidate surviving all sieved primes with B beyond the sieve is
reported as UNRESOLVED (none expected).
"""
import sys, math

KMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 20
PLIM = 2_000_000

def sieve(n):
    b = bytearray([1]) * (n + 1); b[0] = b[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if b[i]:
            b[i * i::i] = bytearray(len(b[i * i::i]))
    return [i for i in range(n + 1) if b[i]]

P = sieve(PLIM)

def dom(n, k, p):
    while k:
        if k % p > n % p:
            return False
        k //= p; n //= p
    return True

def factor_fact(m):
    """prime exponents of m! (Legendre)."""
    out = {}
    for p in P:
        if p > m:
            break
        e, q = 0, p
        while q <= m:
            e += m // q; q *= p
        out[p] = e
    return out

def divisors_from(fac):
    ds = [1]
    for p, e in fac.items():
        ds = [d * p ** i for d in ds for i in range(e + 1)]
    return ds

found, unresolved = [], []
for k in range(1, KMAX + 1):
    ds = divisors_from(factor_fact(k - 1))
    cand = 0
    for B in ds:
        if B < k:
            continue
        for n in range(k * B, k * B + k):
            if n < k * k:
                continue
            cand += 1
            if n == 1 and k == 1:
                continue  # n = k = 1: minFac 1 = 1, not > 1
            divides = False
            for p in P:
                if p > B:
                    break
                if (p <= k and not dom(n, k, p)) or (p > k and n % p < k):
                    divides = True
                    break
            else:
                if B > PLIM:
                    unresolved.append((n, k))
                    continue
            if not divides:
                found.append((n, k))
    print(f"k={k}: divisors of (k-1)! = {len(ds)}, candidates n = {cand}", flush=True)
print("exceptions with n >= k^2 (complete, no n cap):", found)
print("unresolved:", unresolved)
```
