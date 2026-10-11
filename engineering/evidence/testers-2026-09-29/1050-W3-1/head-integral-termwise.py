from fractions import Fraction as F
from math import factorial
c=F(8,3)
def W(n):
    p=F(factorial(max(n-2,0)))
    for k in range(1,n+1): p*=1-c*2**k
    for k in range((n+1)//2,n+1): p*=1-F(2)**k
    return p
def A(n,k):
    num=F(1)
    for t in range(1,n): num*=1-c*F(2)**(t+k)
    den=F(1)
    for l in range(1,n+1):
        if l!=k: den*=1-F(2)**(l-k)
    return -num/den
fails={}
for n in range(1,19):
    w=9**n*W(n)
    As=[A(n,k) for k in range(1,n+1)]
    S1=sum(As[k-1]*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    tot=w*S1
    bad=[]
    for i in range(1,n+1):
        Ti=sum(As[k-1] for k in range(i,n+1))
        term=w*Ti/(1-c*2**i)
        if term.denominator!=1: bad.append((i,term.denominator))
    print(n, 'S1 int' if tot.denominator==1 else ('S1 NOT int',tot.denominator), 'termwise bad:',bad[:4])
