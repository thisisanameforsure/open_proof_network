# 402-R5-b num2: divisor-gap condition G(n,k): no alpha in (n-k,n), e1<e2, e1*e2 | alpha, alpha*e2 < n*e1 ; and 2k<=n+2
from math import isqrt
import sys
def isp(m): return m>1 and all(m%i for i in range(2,isqrt(m)+1))
def bad(n,k):
    out=[]
    for al in range(max(1,n-k+1),n):
        for e1 in range(1,isqrt(al)+1):
            if al%e1: continue
            for e2 in range(e1+1,al//e1+1):
                if al%(e1*e2)==0 and al*e2<n*e1: out.append((al,e1,e2))
    return out
def best(n):
    for p in range(2*n-1,n,-1):
        if isp(p):
            k=2*n-p
            if 2*k>n+2: return None
            b=bad(n,k)
            if not b: return p
    return None
if __name__=="__main__":
    for n in [63,105,111,153,165,679,680]:
        print(n)
        for p in range(2*n-1,n,-1):
            if isp(p):
                k=2*n-p; b=bad(n,k)
                print("   p=%d k=%d k^2/n=%.2f bad=%s"%(p,k,k*k/n,b[:6]))
                if len(b)>3 or k*k>12*n: break
    ex=[n for n in range(2,int(sys.argv[1]) if len(sys.argv)>1 else 3000) if best(n) is None]
    print("exceptions of generalised criterion:",ex)
