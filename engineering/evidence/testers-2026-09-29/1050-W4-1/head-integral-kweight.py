exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
# S1 = sum_k A_k H_k with H_k = sum_{i<=k} 1/(1-c 2^i).  Identity: H_k = k - y * d/dy log prod_{i<=k}(1 - y 2^i) at y = c.
# Split S1 = T + R with T = sum_k k A_k (a "log-weighted" Lagrange sum) and R = S1 - T = -c * sum_k A_k * sum_{i<=k} (-2^i)/(1-c 2^i).
for n in range(1,26):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    L=1
    for d in range(1,n): L*=Phi(d)
    W=9**n*P*L
    H=F(0); S1=F(0)
    for k in range(1,n+1):
        H+=1/(1-c*2**k); S1+=As[k]*H
    T=sum(k*As[k] for k in range(1,n+1)); R=S1-T
    b0=sum(As.values())
    print(n,'W*S1',(W*S1).denominator==1,'| W*T den',fac((W*T).denominator),'| W*R den',fac((W*R).denominator),'| 9^nP*T den',fac((9**n*P*T).denominator),flush=True)
