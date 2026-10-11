import sys,re
from gen import app
# usage: inl.py n statement_file [tac]
n=int(sys.argv[1]); st=open(sys.argv[2]).read(); tac=sys.argv[3] if len(sys.argv)>3 else 'decide'
s2=open('S2.lean').read(); p2=open('P2.lean').read()
# statement type of the reduction
typ=s2.split('theorem Opn.erdos_402_card_of_colouring :\n',1)[1].split(':= by\n  sorry')[0]
body=p2.split(':= by\n',1)[1]
typ_lines=typ.rstrip().split('\n')
have='  have red :\n'+'\n'.join('  '+l for l in typ_lines)+' := by\n'+'\n'.join(('  '+l) if l else l for l in body.rstrip('\n').split('\n'))
L,S,col,appl=app(n,tac)
appl=appl.replace('exact Opn.erdos_402_card_of_colouring','exact red')
proof=st.replace(':= by\n  sorry', ':= by\n  intro A hA hn\n'+have+'\n'+appl)
assert proof!=st
print(proof,end='' if proof.endswith('\n') else '\n')
