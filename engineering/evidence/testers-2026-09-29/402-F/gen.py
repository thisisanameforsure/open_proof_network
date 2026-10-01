import math,sys
from cert import cert
names={9:'nine',10:'ten',16:'sixteen',18:'eighteen',11:'eleven',12:'twelve',8:'eight'}
def verify(n,L,S,col):
    assert all(L*j%k==0 and L*j//k in S for k in range(2,n) for j in range(1,k))
    assert all(col[a]+2<n for a in S)
    for a in S:
        for b in S:
            if a!=b and col[a]==col[b]: assert n*math.gcd(a,b)<=a or n*math.gcd(a,b)<=b
def cfun(S,col):
    # nested ifs, default 0
    s=' else '.join(f'if a = {a} then {col[a]}' for a in S)
    return f'(fun a : ℕ => {s} else 0)'
def app(n, tac='decide'):
    L,S,col=cert(n); verify(n,L,S,col)
    Ss='{'+', '.join(map(str,S))+'}'
    return L,S,col,f'''  exact Opn.erdos_402_card_of_colouring {n} {L} {Ss}
    {cfun(S,col)}
    (by norm_num) (by norm_num) (by {tac}) (by {tac}) (by {tac}) A hA hn'''
if __name__=='__main__':
    n=int(sys.argv[1]); tac=sys.argv[2] if len(sys.argv)>2 else 'decide'
    L,S,col,body=app(n,tac)
    s2=open('S2.lean').read()
    print(s2+f'''
theorem Opn.erdos_402_card_{names.get(n,str(n))}_test :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = {n} → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
{body}
''')
