import sys
def primes(N):
    s = bytearray([1])*(N+1); s[0]=s[1]=0
    for i in range(2,int(N**.5)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return [i for i in range(N+1) if s[i]]
K = int(sys.argv[1]); P = primes(K+1)
for k in range(4, K+1):
    ps = [p for p in P if k < 2*p <= 2*k]
    fails = [n for n in range(2*k, k*k) if not any(n % p < k - p for p in ps)]
    allp = [p for p in P if p <= k]
    hard = [n for n in fails if not any(n % p < k % p for p in allp)]
    if k % 25 == 0 or k <= 12:
        lo = min(fails)/k if fails else None; hi = max(fails)/(k*k) if fails else None
        print(k, len(ps), 'fails(big)=', len(fails), 'min n/k', lo and round(lo,2), 'max n/k^2', hi and round(hi,3), 'fails(all)=', len(hard))
