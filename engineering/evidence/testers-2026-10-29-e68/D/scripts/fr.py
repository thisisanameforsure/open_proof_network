from fractions import Fraction as F
from math import factorial as f
for N in range(2,41):
    s=sum(F(f(N),f(n)-1) for n in range(2,N+1))
    fr=s-(s.numerator//s.denominator)
    # residue form
    r=sum(F((f(N)//f(n))%(f(n)-1), f(n)-1) for n in range(2,N+1))
    print(N, float(fr), float(1-F(2,N)), fr<1-F(2,N), float(r))
