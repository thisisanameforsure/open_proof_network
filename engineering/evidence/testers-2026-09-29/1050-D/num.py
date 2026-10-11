from fractions import Fraction as F
from math import lcm, gcd
import sys
def sub(a,b): return a-b if a>=b else 0
def Qc(n,k):
    r = F((-1)**k) * F(2)**(k*sub(k,1)//2)
    for i in range(k):
        den = F(2)**(i+1)-1
        r *= (F(2)**sub(n,i)-1)/den if den!=0 else 0
    for i in range(n):
        den = F(2)**(i+1)-1
        r *= (F(2)**sub(sub(2*n,k),i)-1)/den if den!=0 else 0
    return r
def div(a,b): return a/b if b!=0 else F(0)
def Qx(n, qc):
    x = F(3, 2**n)
    return sum(qc[k]*x**k for k in range(n+1))
def Aq(n, qc, qx):
    x = F(3, 2**n)
    s = F(0)
    for k in range(n+1):
        inner = sum(div(qc[j], F(2)**sub(k,j)-1) for j in range(k+1))
        s += inner * x**k
    c = sum(div(F(3), F(2)**(j+1)-3) for j in range(n))
    return s + qx*c
P = 9000
S = 2**P
Tsc = sum(S // (2**(m+3)-3) for m in range(P))  # T*2^P, error < P+1 units
N = int(sys.argv[1]) if len(sys.argv)>1 else 30
for n in range(N+1):
    qc = [Qc(n,k) for k in range(n+1)]
    qx = Qx(n,qc); aq = Aq(n,qc,qx)
    d = lcm(qx.denominator, aq.denominator)
    import math
    dbits = math.log2(d)
    ok_den = d*d <= 2**(3*n*n)
    # R = qx*3T - aq
    Rsc = qx.numerator*3*Tsc*aq.denominator - aq.numerator*qx.denominator*S  # R * S * qx.den*aq.den
    D = qx.denominator*aq.denominator
    err = abs(qx.numerator)*3*(P+2)*aq.denominator
    # R = Rsc/(S*D); check sign reliably
    pos = Rsc - err > 0
    # R^2 2^(4n^2) <= 2^(2n+4)  <=> Rsc^2 * 2^(4n^2) <= 2^(2n+4) * S^2 D^2
    Rhi = abs(Rsc)+err
    ok_rem = Rhi*Rhi*2**(4*n*n) <= 2**(2*n+4)*S*S*D*D
    # log2 of R*2^(2n^2) relative
    import math
    if Rsc!=0:
        lr = math.log2(abs(Rsc)) - P - math.log2(D)
    else: lr=float('-inf')
    margin = (2*n+4) - (2*lr + 4*n*n)   # bits of slack in the squared inequality
    print(f"n={n:2d} den_bits={dbits:9.2f} bound_bits={1.5*n*n:8.1f} hden_ok={ok_den} | R>0:{pos} log2|R|={lr:10.2f} rem_ok={ok_rem} slack_bits={margin:8.2f} sign(Rsc)={'+' if Rsc>0 else '-'}", flush=True)
