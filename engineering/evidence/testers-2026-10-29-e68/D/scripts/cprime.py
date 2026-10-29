# Hypothetical X = sum over m in P of (m-1)/m!  (factorial digit "-1" at sparse m), with S's own c_N.
# x_N(X) = fract(N! X - c_N). Check: not-h3 (x_N >= 1-2/N for all N>=N0) and C' (x_N <= 1-1/N i.o.).
from fractions import Fraction as F
from math import factorial as f
M=70
P=set(range(6,M,4))
X=sum(F(m-1,f(m)) for m in P)
for N in range(4,50):
    c=sum(F(f(N),f(m)-1) for m in range(N+1,M))
    v=F(f(N))*X-c; x=v-(v.numerator//v.denominator)
    print(N, N+1 in P, float(1-x)*N, "h3" if x<1-F(2,N) else "", "C'" if x<=1-F(1,N) else "")
