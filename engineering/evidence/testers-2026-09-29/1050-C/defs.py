from fractions import Fraction as F
from math import lcm, log2, gcd
def nsub(a,b): return a-b if a>b else 0
def div(a,b): return F(0) if b==0 else F(a)/F(b)
def Qc(n,k):
    p1=F(1)
    for i in range(k): p1*=div(2**nsub(n,i)-1, 2**(i+1)-1)
    p2=F(1)
    for i in range(n): p2*=div(2**nsub(nsub(2*n,k),i)-1, 2**(i+1)-1)
    return F((-1)**k * 2**((k*nsub(k,1))//2))*p1*p2
def x(n): return F(3,2**n)
def Qx(n): return sum((Qc(n,k)*x(n)**k for k in range(n+1)),F(0))
def pk(n,k): return sum((div(1,2**nsub(k,j)-1)*Qc(n,j) for j in range(k+1)),F(0))
def c(n): return sum((div(3,2**(j+1)-3) for j in range(n)),F(0))
def Aq(n): return sum((pk(n,k)*x(n)**k for k in range(n+1)),F(0)) + Qx(n)*c(n)
def v2(m):
    m=abs(m); v=0
    while m%2==0: m//=2; v+=1
    return v
def M(n):
    r=1
    for m in range(n//2+1,n+1): r*=2**m-1
    return r
def C(n):
    r=1
    for j in range(2,n): r*=2**(j+1)-3
    return r
def D(n): return 2**(n*(n+1)//2)*M(n)*C(n)
