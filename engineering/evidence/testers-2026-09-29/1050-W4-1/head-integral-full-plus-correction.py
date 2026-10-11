exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
for n in range(1,17):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    L=1
    for d in range(1,n): L*=Phi(d)
    W=9**n*P*L
    S1=sum(As[k]*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    R=[sum(As[k]/(1-c*F(2)**(k-j)) for k in range(1,n+1)) for j in range(0,n)]
    V=sum(R); C=S1-V
    Rbad=[j for j,r in enumerate(R) if (W*r).denominator!=1]
    print(n,'V',fac((W*V).denominator),'C',fac((W*C).denominator),'R_j bad',Rbad[:6], 'Wbeta0', (W*sum(As.values())).denominator)
