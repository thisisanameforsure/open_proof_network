from math import gcd, lcm
from functools import reduce
import sys, time
n=int(sys.argv[1])
L=reduce(lcm,range(1,n)); S=sorted({L//k*j for k in range(2,n) for j in range(1,k)})
conf={c:{d for d in S if d!=c and not (n*gcd(c,d)<=c or n*gcd(c,d)<=d)} for c in S}
best=[]
def ext(R,P):
    global best
    if len(R)>len(best): best=R[:]; print(len(best), time.strftime('%H:%M:%S')); sys.stdout.flush()
    for v in sorted(P, key=lambda v:-len(conf[v]&P)):
        if len(R)+len(P)<=len(best): return
        ext(R+[v], P & conf[v]); P = P-{v}
ext([], set(S)); print("n",n,"clique",len(best),"K",n-2)
