# 402-R6-a, independent: for which n does a prime p meet the hypotheses of r5b_gen_criterion?
# hyp: n<p<2n, 2(2n-p)<=n+2, for all a with p-n<a<n: (exists prime q, n<=3q, q | a*(p-a)) or (for all x<y, x*y|a -> n*x<=a*y)
import sys
N=int(sys.argv[1]) if len(sys.argv)>1 else 700
L=2*N+5
spf=list(range(L))
for i in range(2,int(L**.5)+1):
    if spf[i]==i:
        for j in range(i*i,L,i):
            if spf[j]==j: spf[j]=i
def isp(m): return m>=2 and spf[m]==m
def maxpf(m):
    r=1
    while m>1:
        r=max(r,spf[m]); m//=spf[m]
    return r
def divs(m):
    return [d for d in range(1,m+1) if m%d==0]
def gap(n,a):
    D=divs(a)
    for x in D:
        for y in D:
            if x<y and a%(x*y)==0 and n*x>a*y: return False
    return True
def simple(n,p): return (2*n-p)**2<=n
def gen(n,p,excl=True):
    if not(isp(p) and n<p<2*n and 2*(2*n-p)<=n+2): return False
    for a in range(p-n+1,n):
        ok = gap(n,a) or (excl and (3*maxpf(a)>=n or 3*maxpf(p-a)>=n))
        if not ok: return False
    return True
nos=[];noe=[];nog=[]
for n in range(2,N+1):
    ps=[p for p in range(n+1,2*n) if isp(p)]
    if not any(simple(n,p) for p in ps): nos.append(n)
    if not any(gen(n,p,False) for p in ps): noe.append(n)
    if not any(gen(n,p) for p in ps): nog.append(n)
print("range 2..",N)
print("no simple-window prime:",nos)
print("no generalised prime without the q-exclusion:",noe)
print("no generalised prime (full hypotheses):",nog)
