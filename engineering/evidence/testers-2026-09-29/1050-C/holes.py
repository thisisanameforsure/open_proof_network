from defs import *
bad=[]
for n in range(31):
    for k in range(n+1):
        q=Qc(n,k)/2**((k*nsub(k,1))//2)
        if q.denominator!=1: bad.append(('hQc',n,k))
        w=M(n)*pk(n,k)/2**((k*nsub(k,1))//2)
        if w.denominator!=1: bad.append(('hp',n,k))
    for k in range(n+1,n+4):
        q=Qc(n,k)/2**((k*nsub(k,1))//2)
        if q.denominator!=1: bad.append(('hQc>n',n,k))
    if (C(n)*c(n)).denominator!=1: bad.append(('hc',n))
    if n not in (5,7) and D(n)**2>2**(3*n*n): bad.append(('hsize',n))
    # 2-power part of Qx alone
    if (2**(n*(n+1)//2)*Qx(n)).denominator!=1: bad.append(('E*Qx',n))
print('failures:',bad)
d5=lcm(Qx(5).denominator,Aq(5).denominator); d7=lcm(Qx(7).denominator,Aq(7).denominator)
print('d5',d5,'d7',d7, d5**2<=2**75, d7**2<=2**147, 'margins bits', 75-2*log2(d5), 147-2*log2(d7))
print('Qx5',Qx(5),'Aq5',Aq(5))
print('d5*Qx5',d5*Qx(5),'d5*Aq5',d5*Aq(5))
print('d7*Qx7',d7*Qx(7),'d7*Aq7',d7*Aq(7))
# tightness of hp: is the 2-adic exponent k(k-1)/2 sharp?
for n in (6,10,20):
    print(n,[v2((M(n)*pk(n,k)).numerator)-v2((M(n)*pk(n,k)).denominator) - (k*nsub(k,1))//2 if pk(n,k)!=0 else None for k in range(n+1)])
