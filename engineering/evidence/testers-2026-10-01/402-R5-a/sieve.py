# 402-R5-a, independent of 402-R4-c's and 402-R3-b's scripts.
# W(n): exists prime p, n < p < 2n, (2n-p)^2 <= n.   W2(n): additionally a prime q with p-n <= q <= n.
import math, bisect
N=200000
M=2*N+10
sv=bytearray([1])*(M+1); sv[0]=sv[1]=0
for i in range(2,int(M**.5)+1):
    if sv[i]: sv[i*i::i]=bytearray(len(sv[i*i::i]))
primes=[i for i in range(M+1) if sv[i]]
def has_prime(lo,hi):  # prime in [lo,hi]
    i=bisect.bisect_left(primes,lo); return i<len(primes) and primes[i]<=hi
def W(n):
    k=math.isqrt(n)            # 2n-p <= k, and p<2n, p>n
    lo=max(n+1,2*n-k)
    i=bisect.bisect_left(primes,lo)
    return i<len(primes) and primes[i]<2*n
def W2(n):
    k=math.isqrt(n); lo=max(n+1,2*n-k)
    i=bisect.bisect_left(primes,lo)
    while i<len(primes) and primes[i]<2*n:
        p=primes[i]
        if has_prime(p-n,n): return True
        i+=1
    return False
def opn(n): return not sv[n] and not sv[n-1]
for lo in (2,10):
    exc=[n for n in range(lo,N+1) if not W(n)]
    print("range",lo,N,"W fails at",len(exc),":",exc)
    print("  open (not prime, not prime+1):",[n for n in exc if opn(n)])
    e2=[n for n in range(lo,N+1) if opn(n) and not W2(n)]
    print("  two-prime version fails at open n:",len(e2),e2)
print("count open n in 10..N:",sum(1 for n in range(10,N+1) if opn(n)))
# also up to 200014 (range claimed for the Window files)
print("W fails in 681..200014:",[n for n in range(681,200015) if not W(n)])
