import sys
from cert import cert
from gen import verify, names
def app2(n,tac='decide +kernel'):
    L,S,col=cert(n); verify(n,L,S,col)
    Sl='['+', '.join(map(str,S))+']'
    Cl='['+', '.join(f'({a}, {col[a]})' for a in S)+']'
    return f'''  exact Opn.erdos_402_card_of_colouring {n} {L} ({Sl} : List ℕ).toFinset
    (fun a : ℕ => ((({Cl} : List (ℕ × ℕ)).lookup a).getD 0))
    (by norm_num) (by norm_num) (by {tac}) (by {tac}) (by {tac}) A hA hn'''
if __name__=='__main__':
    n=int(sys.argv[1])
    print(open('S2.lean').read()+f'''
theorem Opn.erdos_402_card_{names.get(n,str(n))}_test :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = {n} → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
{app2(n)}
''')
