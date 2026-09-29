from fractions import Fraction as F
from qadic import Qc, pk
bad=0; cnt=0
for q in (2,3,5):
  for n in range(1,14):
    for k in range(0,n+1):
        c=lambda j: Qc(n,j,q)
        s = sum((F(1,1-q**(n+1+i-k)) for i in range(n)),F(0))
        s -= sum((F(q**(k-j), q**(k-j)-1) for j in range(k)),F(0))
        s -= sum((F(1,1-q**(j-k)) for j in range(k+1,n+1)),F(0))
        rhs = c(k)*s + sum((c(j)*F(q**(j-k), q**(j-k)-1) for j in range(k+1,n+1)),F(0))
        cnt+=1
        if rhs != pk(n,k,q): bad+=1; print("MISMATCH",q,n,k)
print("checked",cnt,"cases, mismatches",bad)
