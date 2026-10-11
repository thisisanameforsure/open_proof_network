from fractions import Fraction as F
from qadic import Qc
from defs import M
q=2
fails={}
for n in range(1,26):
    Mn=M(n)
    for k in range(0,n+1):
        c=lambda j: Qc(n,j,q)
        T=(k*(k-1))//2 if k>0 else 0
        terms=[]
        terms.append(('A',sum((c(k)*F(1,1-q**(n+1+i-k)) for i in range(n)),F(0))))
        for i in range(n): terms.append(('Ai',c(k)*F(1,1-q**(n+1+i-k))))
        terms.append(('B',c(k)*sum((F(q**b, q**b-1) for b in range(1,k+1)),F(0))))
        terms.append(('C',c(k)*sum((F(1,1-q**b) for b in range(1,n-k+1)),F(0))))
        terms.append(('D',sum((c(k+b)*F(q**b,q**b-1) for b in range(1,n-k+1)),F(0))))
        for name,t in terms:
            if (Mn*t/2**T).denominator!=1: fails[name]=fails.get(name,0)+1
print("n<=25 termwise failures of M_n*term/2^(k(k-1)/2) in Z, by term group:",fails)
