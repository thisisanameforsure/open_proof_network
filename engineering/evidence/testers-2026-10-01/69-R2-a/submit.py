# Precheck Proof.lean for spec-7d098d5c under the token, then submit it. Run only after PR #339 has merged
# and the node's products have rendered (else 409 node-pending / products-pending).
import json,sys,time,urllib.request
TOK=open(sys.argv[1]).read().strip()
NODE='spec-7d098d5c'
bundle={f'targets/erdos-69/nodes/{NODE}/Proof.lean':open('Proof.lean').read()}
def call(method,path,body=None):
    req=urllib.request.Request('https://api.openproofnetwork.org'+path,method=method,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+TOK})
    try: return json.load(urllib.request.urlopen(req,timeout=180))
    except urllib.error.HTTPError as e: return {'http':e.code,'body':e.read().decode()[:3000]}
j=call('POST','/precheck',{'node_id':NODE,'bundle':bundle})
if 'id' not in j: print(j); sys.exit(1)
print('precheck job',j['id'])
while True:
    time.sleep(15)
    r=call('GET','/precheck/'+j['id'])
    if r.get('state') in ('done','error'): break
res=r.get('result') or {}
print('state',r.get('state'),'verdict',res.get('verdict'),'first failing',res.get('first_failing_step'))
for s in res.get('steps',[]): print(' ',s.get('step'),s.get('name'),s.get('result'))
if res.get('verdict')!='pass': print(json.dumps(res)[:3000]); sys.exit(1)
s=call('POST','/submissions',{'node_id':NODE,'artifact_type':'proof','bundle':bundle,'precheck_job_id':j['id'],
  'tooling':{'model':'Claude Fable 5.1 (claude-fable-5-1)','version':None,'harness':'Claude Code; POST /check'}})
print(json.dumps({k:v for k,v in s.items() if 'token' not in k and 'nonce' not in k})[:1500])
