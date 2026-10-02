import itertools
from fractions import Fraction as F
from collections import defaultdict
def g(r,k): return ([5,1,0,6,4,2] if r%2==0 else [4,2,0,6,5,1])[k]
def s(r,k): return ([3*r+10,15*r+14,18*r+18,6,6*r+8,12*r+16] if r%2==0 else [6*r+12,12*r+12,18*r+18,6,3*r+6,15*r+18])[k]
H=10**9
for M in [1,2,3,4]:
    w=defaultdict(F); dils=set()
    for d in itertools.product(range(6),repeat=M):
        gi=sum(7**r*g(r,d[r]) for r in range(M)); si=sum(7**r*s(r,d[r]) for r in range(M))
        c=(-1)**sum(d); a=1+H*(1+gi); dils.add(a)
        for u in range(1,3*M+6): w[(H*si+a*u)]+=c*F(1,2**u)
    mass=sum(abs(v) for v in w.values()); 
    big=max(abs(v) for v in w.values())
    print(M,len(dils)==6**M, float(mass), big, F(1,2**(3*M+1)), sum(1 for v in w.values() if v!=0))
