from fractions import Fraction as F
from qadic import Qc
from math import prod
bad=0; cnt=0
for q in (2,3,5):
  for n in range(0,14):
    for j in range(n+1):
        lhs=Qc(n,j,q)*q**j*prod((F(q**j-q**l) for l in range(n+1) if l!=j),start=F(1))
        rhs=prod((F(q**j-q**(n+1+i)) for i in range(n)),start=F(1))
        cnt+=1
        if lhs!=rhs: bad+=1; print("MISMATCH",q,n,j,lhs,rhs) if bad<5 else None
print("Lagrange-coefficient identity: checked",cnt,"cases, mismatches",bad)
