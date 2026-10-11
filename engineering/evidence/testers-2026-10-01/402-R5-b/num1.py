# 402-R5-b num1: for each residual n and each prime p in (n,2n): k=2n-p, shapes {a,b} a+b=p in [n-k+1,n-1],
# smooth filter (no prime factor >= n/3), rectangle failure set F(a,b), max clique M, sum vs need (k+1)/2
from math import gcd, isqrt
from itertools import combinations
import sys
def isp(m): return m>1 and all(m%i for i in range(2,isqrt(m)+1))
def lpf(m):
    r=1;i=2
    while i*i<=m:
        while m%i==0: r=i;m//=i
        i+=1
    return max(r,m) if m>1 else r
def divs(m): return [d for d in range(1,m+1) if m%d==0]
def fails(n,al,be):
    F=set()
    Da=divs(al);Db=divs(be)
    for e1 in Da:
      for e2 in Da:
        if gcd(e1,e2)!=1: continue
        for f1 in Db:
          for f2 in Db:
            if gcd(f1,f2)!=1: continue
            # d1=e1 f1 m1, al*e1*m1 < n*e2 and be*f1*m1 < n*f2
            m1max=min((n*e2-1)//(al*e1),(n*f2-1)//(be*f1))
            m2max=min((n*e1-1)//(al*e2),(n*f1-1)//(be*f2))
            for m1 in range(1,m1max+1):
              d1=e1*f1*m1
              for m2 in range(1,m2max+1):
                d2=e2*f2*m2
                if d1==d2 or gcd(d1,d2)!=1: continue
                g1=gcd(al*d1,be*d2);g2=gcd(be*d1,al*d2)
                if al*d1<n*g1 and be*d2<n*g1 and be*d1<n*g2 and al*d2<n*g2 and d1<n and d2<n:
                    F.add((min(d1,d2),max(d1,d2)))
    return F
def analyse(n,p,verbose=False):
    k=2*n-p; P=(n+2)//3  # primes q with 3q>=n excluded
    shapes=[(a,p-a) for a in range(n-k+1,n) if a<p-a]
    tot=0;info=[]
    for (a,b) in shapes:
        if lpf(a)*3>=n or lpf(b)*3>=n: continue
        F={(x,y) for (x,y) in fails(n,a,b) if lpf(x)*3<n and lpf(y)*3<n}
        # crude clique bound: 1 if F empty, else 2 if no triangle-able..., report F
        M=1 if not F else 2+len(F)-1  # upper bound placeholder
        info.append((a,b,sorted(F)))
        tot+=1
    return k,len(shapes),info
if __name__=="__main__":
  for n in [int(x) for x in sys.argv[1:]] or [63,105,111,153,165,679,680]:
      print("n=",n)
      for p in range(2*n-1,n,-1):
          if not isp(p): continue
          k,ns,info=analyse(n,p)
          nf=sum(1 for i in info if i[2])
          print("  p=%d k=%d need>=%d shapes=%d smooth=%d withF=%d"%(p,k,(k+1)//2,ns,len(info),nf), [ (a,b,F) for a,b,F in info if F][:4] if nf<=4 else "")
          if k>6*isqrt(n): break
  