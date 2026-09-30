exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
# Is R = S1 - sum_k k A_k already cleared by 9^n P(n) alone (no q-lcm)?  Is T = sum_k k A_k cleared by 9^n P L_{n-1}?
allR=True; allT=True
for n in range(1,31):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    L=1
    for d in range(1,n): L*=Phi(d)
    H=F(0); S1=F(0)
    for k in range(1,n+1):
        H+=1/(1-c*2**k); S1+=As[k]*H
    T=sum(k*As[k] for k in range(1,n+1)); R=S1-T
    r=(9**n*P*R); t=(9**n*P*L*T)
    allR&= r.denominator==1; allT&= t.denominator==1
    print(n,'9^n P R den',fac(r.denominator),'| 9^n P L T den',fac(t.denominator),flush=True)
print('9^n P R integral for all n<=30:',allR,'| 9^n P L_{n-1} T integral for all n<=30:',allT)
