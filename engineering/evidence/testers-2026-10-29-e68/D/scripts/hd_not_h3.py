# X with factorial digit m-2 at m in P and m-1 at m+1 (others 0); S's own c_N. Want: hd i.o. and not-h3 at every N>=N0.
from fractions import Fraction as F
from math import factorial as f
M=80
P=set(range(8,M-2,5))
X=sum(F(m-2,f(m)) for m in P)+sum(F(m,f(m+1)) for m in P)
def fr(v): return v-(v.numerator//v.denominator)
h3=[];hd=[]
for N in range(5,60):
    c=sum(F(f(N),f(m)-1) for m in range(N+1,M+3))
    d=fr(F(f(N))*X); x=fr(F(f(N))*X-c)
    if x<1-F(2,N): h3.append(N)
    if F(2,N+1)<=d<1-F(1,N+1): hd.append(N)
print("h3 holds at", h3); print("hd holds at", hd)
