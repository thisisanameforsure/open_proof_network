exec(open('head-integral-qlcm.py').read().split('for n in range(1,23)')[0])
res=[]
for n in range(1,23):
    As=[A(n,k) for k in range(1,n+1)]
    S1=sum(As[k-1]*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    ql1=1
    for d in range(1,n): ql1*=Phi(d)
    M=1
    for k in range((n+1)//2,n+1): M*=2**k-1
    e=0
    while (F(3)**e*P*ql1*S1).denominator!=1: e+=1
    res.append((n,e,M%ql1==0))
print(res)
