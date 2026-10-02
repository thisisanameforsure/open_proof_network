# 402-R6-b: independent check of the chains in the Lean files (trial division, no sieve shared with gen.py)
import re,sys,math
def isprime(p):
    if p<2: return False
    i=2
    while i*i<=p:
        if p%i==0: return False
        i+=1
    return True
def gen_ok(n,p):
    # hypotheses of r5b_gen_criterion at size n with prime p, brute force
    if not(isprime(p) and n<p<2*n and 2*(2*n-p)<=n+2): return False
    for al in range(p-n+1,n):
        if any(isprime(q) and n<=3*q and (al*(p-al))%q==0 for q in range(2,max(al,p-al)+1) if (al*(p-al))%q==0): continue
        for x in range(1,al+1):
            if al%x: continue
            for y in range(x+1,al//x+1):
                if al%(x*y)==0 and n*x>al*y: return False
    return True
for fn in sys.argv[1:]:
    s=open(fn).read(); covered=set(); npr=0
    for m in re.finditer(r"hP (\d+) \[([^\]]*)\] (\d+) \(by decide|key _ hP \[([^\]]*)\] (\d+) \(by decide",s):
        if m.group(1): b,lst,a=int(m.group(1)),m.group(2),int(m.group(3))
        else: lst,a=m.group(4),int(m.group(5)); b=None
        lo=a
        for p,hi in re.findall(r"\((\d+), (\d+)\)",lst):
            p=int(p);hi=int(hi); npr+=1
            assert isprime(p),p
            for n in range(lo,hi+1):
                assert n<p<2*n and (2*n-p)**2<=n,(n,p)
                covered.add(n)
            lo=hi+1
        assert b is None or lo>b
    certs={}
    for m in re.finditer(r"have r5b_cert_(\d+) .*?refine ⟨(\d+),",s,re.S):
        n,p=int(m.group(1)),int(m.group(2)); assert gen_ok(n,p),(n,p); certs[n]=p; covered.add(n)
    lo,hi=min(covered),max(covered)
    assert covered==set(range(lo,hi+1))
    print(fn,"covers",lo,"..",hi,"with",npr,"chain primes (all prime by trial division, window verified per n) and",len(certs),"brute-forced gen certificates",sorted(certs))
