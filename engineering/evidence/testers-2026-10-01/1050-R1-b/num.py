from fractions import Fraction as F
from math import factorial
def run(n):
    c=F(8,3)
    def D(k):
        p=F(1)
        for l in range(1,n+1):
            if l!=k: p*=1-F(2)**(l-k)
        return p
    def A(k,x):
        p=F(1)
        for t in range(1,n): p*=1-x*2**(t+k)
        return -p/D(k)
    S1=sum(A(k,c)*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    # alpha: coeffs of prod_{t=1}^{n-1}(1-2^t y)
    al=[F(1)]
    for t in range(1,n):
        new=[F(0)]*(len(al)+1)
        for j,a in enumerate(al): new[j]+=a; new[j+1]-=a*2**t
        al=new
    # h_e(2,4,..,2^n)
    h=[F(0)]*(n+1); h[0]=F(1)
    for k in range(1,n+1):
        for e in range(1,n+1): h[e]+=2**k*h[e-1]
    E=sum(F(1,2**j-1)*sum(al[jp]*(h[jp]-h[jp-j])*c**(jp-j) for jp in range(j,n)) for j in range(1,n))
    b=[sum(A(k,F(1,2**i)) for k in range(1,n+1)) for i in range(1,n+1)]
    b2=[-sum(al[jp]*h[jp]*F(1,2**(i*jp)) for jp in range(n)) for i in range(1,n+1)]
    assert b==b2
    R=sum(b[i-1]/(1-c*2**i) for i in range(1,n+1))
    ok=(S1==E+R)
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    M=F(1)
    for k in range((n+1)//2,n+1): M*=1-2**k
    return ok, all(x.denominator==1 for x in b), (3**(max(n-2,0))*M*E).denominator, (3**n*P*R).denominator
for n in range(1,14): print(n, run(n))
