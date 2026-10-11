from fractions import Fraction as F
import math
exec(open('num.py').read().split('P = 9000')[0])
P=4000; S=2**P
Tsc = sum(S // (2**(m+3)-3) for m in range(P))
def E(n,t):
    num = F(2)**(n*n)
    for i in range(n): num *= (F(2)**(n+t-i)-1)
    den = F(1)
    for j in range(n+1): den *= (F(2)**(2*n+1+t-j)-1)
    return num/den
for n in range(2,9):
    qc=[Qc(n,k) for k in range(n+1)]; qx=Qx(n,qc); aq=Aq(n,qc,qx)
    x=F(3,2**n)
    s=sum(E(n,t)*x**(2*n+1+t) for t in range(400))
    R = F(qx.numerator*3*Tsc, qx.denominator*S) - aq
    ok = all(E(n,t) <= F(1,2**(2*n+t)) for t in range(60))
    print(n, float((s-R)/R), 'Ele ok', ok, 'maxratio', max(float(E(n,t)*2**(2*n+t)) for t in range(60)))
