from defs import *
print("n  log2(dmin)  1.5n^2  margin(bits of d^2 vs 2^{3n^2})  | D_n ok? log2 D  margin")
for n in range(31):
    a,b=Qx(n),Aq(n)
    dmin=lcm(a.denominator,b.denominator)
    Dn=D(n)
    ok=(Dn*a).denominator==1 and (Dn*b).denominator==1
    print(n, round(log2(dmin),2), 1.5*n*n, round(3*n*n-2*log2(dmin),2), '|', ok, round(log2(Dn),2), round(3*n*n-2*log2(Dn),2), 'fits' if Dn*Dn<=2**(3*n*n) else 'NO', 'dmin fits' if dmin*dmin<=2**(3*n*n) else 'DMIN NO', 'v2den Qx',v2(a.denominator),'Aq',v2(b.denominator))
