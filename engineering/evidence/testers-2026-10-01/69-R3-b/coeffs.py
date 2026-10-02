# Part A: the signed weights c_x of 69-R2-b's pattern (exact), their mass, energy and the
# model decay exponent kappa(M,q) = sum_x (1 - cos(2 pi q c_x))  (per unit of sum 1/p over generic primes).
import itertools, math
from fractions import Fraction as F
from collections import defaultdict
def g(r,k): return ([5,1,0,6,4,2] if r%2==0 else [4,2,0,6,5,1])[k]
def s(r,k): return ([3*r+10,15*r+14,18*r+18,6,6*r+8,12*r+16] if r%2==0 else [6*r+12,12*r+12,18*r+18,6,3*r+6,15*r+18])[k]
H=10**9   # stands for P#: any H larger than every index gives the same incidence pattern
def table(M,U):
    w=defaultdict(F)
    for d in itertools.product(range(6),repeat=M):
        gi=sum(7**r*g(r,d[r]) for r in range(M)); si=sum(7**r*s(r,d[r]) for r in range(M))
        c=(-1)**sum(d); a=1+H*(1+gi)
        for u in range(1,U+1): w[(H*si+a*u,u)]+=c*F(1,2**u)
    return w
if __name__=="__main__":
    print("M depthcap lines  nonzero_pts  first_nonzero_depth  mass  (3/4)^M  energy  recoincidences(|c|>2^-u)")
    for M in [1,2,3,4,5]:
        U=3*M+30
        w=table(M,U)
        nz={k:v for k,v in w.items() if v!=0}
        mass=sum(abs(v) for v in nz.values()); en=sum(v*v for v in nz.values())
        first=min(u for (_,u) in nz)
        rec=sum(1 for (x,u),v in nz.items() if abs(v)>F(1,2**u))
        maxdepth_rec=max([u for (x,u),v in w.items() if abs(v)!=F(1,2**u)] or [0])
        print(M,U,6**M,len(nz),first,float(mass),0.75**M,float(en),rec,"deepest depth with a coincidence:",maxdepth_rec)
        print("   kappa(M,q), q=1..12:",[round(sum(1-math.cos(2*math.pi*q*float(v)) for v in nz.values()),5) for q in range(1,13)])
