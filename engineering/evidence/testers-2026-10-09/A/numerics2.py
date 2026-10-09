# Check h_sieve split: failures of "exists prime p<=k with n%p<k%p" for 2k<=n<k^2, k<=K,
# classified by parity class; confirms p=2 always handles (k odd, n even).
import sys
def primes(N):
    s = bytearray([1])*(N+1); s[0]=s[1]=0
    for i in range(2,int(N**.5)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return [i for i in range(N+1) if s[i]]
K = int(sys.argv[1]); P = primes(K)
last = {"keven": None, "odd": None, "kodd_neven": None}; cnt = {k: 0 for k in last}
for k in range(2, K+1):
    ps = [p for p in P if p <= k]
    for n in range(2*k, k*k):
        if any(n % p < k % p for p in ps): continue
        cls = "keven" if k % 2 == 0 else ("odd" if n % 2 == 1 else "kodd_neven")
        cnt[cls] += 1; last[cls] = (n, k)
print("k <=", K, "failure counts", cnt, "last failure per class", last)
