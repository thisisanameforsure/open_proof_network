exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
import time
for n in range(1,41):
    t=time.time()
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    L=1
    for d in range(1,n): L*=Phi(d)
    H=F(0); S1=F(0)
    for k in range(1,n+1):
        H+=1/(1-c*2**k); S1+=As[k]*H
    x=9**n*P*L*S1
    # least power of 3
    y=P*L*S1; e=0
    while (y*3**e).denominator!=1 and e<3*n: e+=1
    print(n,'9^n P L_{n-1} S1 integral:',x.denominator==1,'least 3-power e=',e if (y*3**e).denominator==1 else 'none<=3n', 'den w/o 3s:', fac((y*3**(3*n)).denominator), round(time.time()-t,2),flush=True)
