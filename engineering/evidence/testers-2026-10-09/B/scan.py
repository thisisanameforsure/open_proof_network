# exceptions: n>=k^2, k>=1, minFac(C(n,k)) > n//k. Kummer: p | C(n,k) iff carry adding k and n-k base p.
import sys
def primes(N):
    s=bytearray([1])*(N+1); s[0:2]=b'\0\0'
    for i in range(2,int(N**.5)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return [i for i in range(N+1) if s[i]]
def carry(a,b,p):
    c=0
    while a or b:
        if a%p+b%p+c>=p: return True
        a//=p;b//=p
    return False
K=int(sys.argv[1]); NMAX=int(sys.argv[2])
P=primes(NMAX)
lo=[];hi=[]
for k in range(1,K+1):
    for n in range(k*k, NMAX+1):
        B=n//k; exc=True
        for p in P:
            if p>B: break
            if carry(k,n-k,p): exc=False;break
        if exc: (lo if n<k**3 else hi).append((n,k))
print("lo (k^2<=n<k^3):",lo[:20]); print("hi (n>=k^3):",hi[:20])
