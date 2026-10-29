# X = e - 2 + 1/3 (an irrational number with X - e rational). Every core on the record, evaluated at X with S's own c_N.
from fractions import Fraction as F
from math import factorial as f
M=60
e=sum(F(1,f(m)) for m in range(0,M)); X=e-2+F(1,3)
def fr(v): return v-(v.numerator//v.denominator)
bad=[]
for N in range(4,40):
    c=sum(F(f(N),f(m)-1) for m in range(N+1,M))
    d=fr(F(f(N))*X); x=fr(F(f(N))*X-c)
    h3 = x<1-F(2,N); Cp = x<=1-F(1,N); hd = F(2,N+1)<=d<1-F(1,N+1); notint = d!=0
    bad.append((N,h3,Cp,hd,notint))
print("any h3:",any(b[1] for b in bad),"any C':",any(b[2] for b in bad),"any hd:",any(b[3] for b in bad),"N!X never integer:",all(b[4] for b in bad))
