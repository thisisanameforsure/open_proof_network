# hd (B's level-2 draft): 2/(N+1) <= fract(N! S) < 1 - 1/(N+1); also test on the separating X of bin/cprime.py
from fractions import Fraction as F
from math import factorial as f
M=80
Sv=sum(F(1,f(m)-1) for m in range(2,M))
P=set(range(6,M,4)); X=sum(F(m-1,f(m)) for m in P)
def fr(v): return v-(v.numerator//v.denominator)
cnt=0
for N in range(2,45):
    d=fr(F(f(N))*Sv); dx=fr(F(f(N))*X)
    hS = F(2,N+1)<=d<1-F(1,N+1); hX = F(2,N+1)<=dx<1-F(1,N+1)
    cnt+=hS
    print(N, round(float(d)*(N+1),3), hS, "| X:", round(float(dx)*(N+1),3), hX)
print("hd holds for S at", cnt, "of 43 N")
