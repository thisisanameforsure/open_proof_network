import json,os,re,sys
D=json.load(open('decls.json'))
SF="/Users/mikehiggins/Desktop/repos/open_proof_network/engineering/evidence/testers-2026-10-15b/S/fixes"
st=open('Statement.lean').read()
k=st.index('theorem erdos_1094__h2__h2__h2__h3__h1__h1__h1__h1')
head,thm=st[:k],st[k:]
parts=[];src=[]
for i,d in enumerate(D):
    nm=d['name']
    if os.path.exists(f"{SF}/{nm}.lean"): t=open(f"{SF}/{nm}.lean").read(); src.append(('S',nm))
    elif os.path.exists(f"fixes/{nm}.lean"): t=open(f"fixes/{nm}.lean").read(); src.append(('T',nm))
    else: t=d['full']; src.append(('orig',nm))
    t=t.strip('\n')
    t=re.sub(r'^(private\s+)?(noncomputable\s+)?def ','private noncomputable def ',t,count=1)
    t=re.sub(r'^(private\s+)?(lemma|theorem) ',r'private \2 ',t,count=1)
    parts.append(t)
proof=thm.replace(":= by\n  sorry", ":= by\n  intro r hr s hs M hM W hW u w h1 h2 h3 h4\n  exact small_integer_linear_relation_proof r hr s hs M hM W hW u w h1 h2 h3 h4")
assert proof!=thm
out=head+'\n\n'.join(parts)+'\n\n'+proof
open('Proof.lean','w').write(out)
print(len(out), [s for s in src if s[0]!='orig'].__len__(), 'S:',sum(1 for s in src if s[0]=='S'),'T:',sum(1 for s in src if s[0]=='T'))
bad=[l for l in out.split('\n') if re.match(r'^(open|set_option|noncomputable section|namespace|end\b|variable|attribute|@\[)',l)]
print('forbidden lines:',bad[:5])
