from fractions import Fraction as F
from defs import nsub, div
def v(m,p):
    m=abs(m); r=0
    while m%p==0: m//=p; r+=1
    return r
def vq(fr,p): return v(fr.numerator,p)-v(fr.denominator,p)
def Qc(n,k,q):
    p1=F(1)
    for i in range(k): p1*=div(q**nsub(n,i)-1, q**(i+1)-1)
    p2=F(1)
    for i in range(n): p2*=div(q**nsub(nsub(2*n,k),i)-1, q**(i+1)-1)
    return F((-1)**k * q**((k*nsub(k,1))//2))*p1*p2
def pk(n,k,q): return sum((div(1,q**nsub(k,j)-1)*Qc(n,j,q) for j in range(k+1)),F(0))
for q in (2,3,4,5,7):
    worst=None
    for n in range(1,16):
        for k in range(1,n+1):
            x=pk(n,k,q)
            if x==0: continue
            s=vq(x,q) if q in (2,3,5,7) else None
            if q==4: s=vq(x,2)//2 if vq(x,2)>=0 else vq(x,2)/2
            d=s-(k*(k-1))//2
            if worst is None or d<worst[0]: worst=(d,n,k)
    print("q",q,"min over n<16,k<=n of v_q(p_k)-k(k-1)/2 =",worst)
