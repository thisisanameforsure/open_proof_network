exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
# Conjecture C(n): 3^(n-1) * L_{n-1} * T(n) is an integer, T(n) = sum_{k=1..n} k*A(n,k), L_{n-1} = prod_{d<n} Phi_d(2).  Also compare with beta0.
ok=True
for n in range(1,41):
    As={k:A(n,k) for k in range(1,n+1)}
    L=1
    for d in range(1,n): L*=Phi(d)
    T=sum(k*As[k] for k in range(1,n+1)); b0=sum(As.values())
    x=3**(n-1)*L*T
    e=0
    while ((L*T)*3**e).denominator!=1: e+=1
    e0=0
    while (b0*3**e0).denominator!=1: e0+=1
    ok&=x.denominator==1
    print(n,'3^(n-1) L T integral:',x.denominator==1,' least e for L*T:',e,' least e for beta0:',e0,flush=True)
print('C(n) holds for n=1..40:',ok)
