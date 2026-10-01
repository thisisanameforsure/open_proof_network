import itertools, math, random, sys, time
from functools import reduce
def H(a,b):  # a / gcd(a,b)
    return a//math.gcd(a,b)
def hyp(A):  # h3-v2 hypotheses: gcd 1, all reduced ratios u/v with u,v <= n
    n=len(A)
    return reduce(math.gcd,A)==1 and all(H(a,b)<=n for a in A for b in A)
def concl(A):
    n=len(A); return any(n*math.gcd(a,b)<=a for a in A for b in A)
t=time.time()
print("Exhaustive: all n-subsets of [1..N] satisfying h3-v2's hypotheses")
for n,N in [(2,60),(3,60),(4,48),(5,40),(6,36),(7,30),(8,26)]:
    tot=sat=fail=tight=0
    for A in itertools.combinations(range(1,N+1),n):
        tot+=1
        if hyp(A):
            sat+=1
            if not concl(A): fail+=1; print("COUNTEREXAMPLE",A)
            if max(H(a,b) for a in A for b in A)==n: tight+=1
    print(f" n={n} N={N}: subsets={tot} satisfy-hyp={sat} conclusion-fails={fail} (all hyp sets have max height exactly n: {tight==sat})")
print("Divisors-of-lcm search: gcd-1 n-sets of divisors of L=lcm(1..n) with the hypothesis")
for n in range(2,10):
    L=reduce(lambda x,y:x*y//math.gcd(x,y),range(1,n+1))
    D=[d for d in range(1,L+1) if L%d==0]
    cnt=0; fail=0; examples=[]
    for A in itertools.combinations(D,n):
        if hyp(A):
            cnt+=1
            if not concl(A): fail+=1
            if len(examples)<4: examples.append(A)
    print(f" n={n} L={L} |divisors|={len(D)} hyp-sets={cnt} failures={fail} e.g. {examples[:3]}")
print("Random: n in 5..14, sets drawn from divisors of lcm(1..n) (where every hypothesis set lives)")
random.seed(402)
for n in range(5,15):
    L=reduce(lambda x,y:x*y//math.gcd(x,y),range(1,n+1))
    D=[d for d in range(1,L+1) if L%d==0]
    trials=hits=0
    for _ in range(20000):
        A=tuple(sorted(random.sample(D,n)))
        trials+=1
        if hyp(A):
            hits+=1
            assert concl(A),A
    print(f" n={n}: {trials} random sets, {hits} satisfied hyp, all satisfied conclusion")
print("prime case sanity (pigeonhole on p-free part mod p): for prime n, sets with all heights<=n-1 are impossible:")
for p in [2,3,5,7]:
    L=reduce(lambda x,y:x*y//math.gcd(x,y),range(1,p))
    D=[d for d in range(1,L+1) if L%d==0]
    bad=[A for A in itertools.combinations(D,p) if all(H(a,b)<=p-1 for a in A for b in A)]
    print(f" p={p}: n-sets of divisors of lcm(1..p-1)={len(D)} with all heights<=p-1: {len(bad)}")
print(f"elapsed {time.time()-t:.1f}s")
