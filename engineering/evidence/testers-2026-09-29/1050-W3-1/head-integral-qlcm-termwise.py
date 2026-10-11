exec(open('head-integral-qlcm.py').read().split('for n in range(1,23)')[0])
for n in range(2,19):
    As=[A(n,k) for k in range(1,n+1)]
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    ql1=1
    for d in range(1,n): ql1*=Phi(d)
    w=9**n*P*ql1
    tk=[ (w*As[k-1]*sum(1/(1-c*2**i) for i in range(1,k+1))).denominator for k in range(1,n+1)]
    ti=[ (w*sum(As[k-1] for k in range(i,n+1))/(1-c*2**i)).denominator for i in range(1,n+1)]
    ak=[ (w*As[k-1]).denominator for k in range(1,n+1)]
    print(n,'A_k*H_k bad',sum(d!=1 for d in tk),'h_i*T_i bad',sum(d!=1 for d in ti),'A_k bad',sum(d!=1 for d in ak))
