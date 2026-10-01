import json, os, time, urllib.request, urllib.error, subprocess, datetime, sys
API="https://api.openproofnetwork.org"
DIR=os.path.dirname(os.path.abspath(__file__))
TOKEN=json.load(open('/tmp/claude-0/-home-user-open-proof-network/fe0dce4d-88fe-5afa-a01c-9c03f386c48f/scratchpad/tokens/t0929-5.json'))['token']
NODE="variant-9724698e"; PATH_=f"targets/erdos-402/nodes/{NODE}/Proof.lean"
proof=open(os.path.join(DIR,'Proof13.lean')).read()
DEADLINE=datetime.datetime(2026,9,29,21,24,tzinfo=datetime.timezone.utc)
def now(): return datetime.datetime.now(datetime.timezone.utc)
def log(msg):
    subprocess.run([os.path.join(DIR,'logl.sh'), "pipeline13: "+msg])
    print(now().isoformat(), msg, flush=True)
def call(method, path, body=None, auth=True):
    req=urllib.request.Request(API+path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header('Content-Type','application/json')
    if auth: req.add_header('Authorization','Bearer '+TOKEN)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read() or b'null')
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read() or b'null')
            except Exception: return e.code, None
        except Exception as e:
            print('transport', e, flush=True); time.sleep(10)
    return 0, None
# 1. wait for the node to be verifiable (supervisor 19:36Z: /submissions/<id> at most every 5 min)
while now()<datetime.datetime(2026,9,29,20,0,tzinfo=datetime.timezone.utc): time.sleep(30)
last=None
while now()<DEADLINE:
    st,sd=call('GET','/submissions/246',auth=False)
    pr=(sd or {}).get('pull_request') or {}
    w=pr.get('waiting_on'); w='queue(merge|branch-update)' if w in ('merge','branch-update') else w
    k2=(pr.get('state'),pr.get('merged'),w)
    if k2!=last: log(f"PR #246 state={k2[0]} merged={k2[1]} waiting_on={k2[2]} gate_verdict={(sd or {}).get('gate_verdict')}"); last=k2
    if pr.get('state')=='closed' and not pr.get('merged'): log("PR #246 closed unmerged; stopping"); sys.exit(0)
    if (sd or {}).get('pull_request_error') and not globals().get('_pe'): log(f"GET /submissions/246 pull_request_error: {str(sd.get('pull_request_error'))[:300]}"); globals()['_pe']=1
    if pr.get('merged') and pr.get('waiting_on') in (None,'products'): break
    time.sleep(300)
last=None
while now()<DEADLINE:
    st,d=call('POST','/check',{"target_id":"erdos-402","node_id":NODE,"mode":"verify","content":proof})
    key=(st, (d or {}).get('error'), ((d or {}).get('details') or {}).get('waiting_on'))
    if key!=last: log(f"POST /check verify -> {st} {key[1]} {key[2]}"); last=key
    if st==200: break
    time.sleep(300)
else:
    log("deadline reached before node became verifiable"); sys.exit(0)
json.dump(d,open(os.path.join(DIR,'verify13.json'),'w'))
log(f"verify: okay={d.get('okay')} lint={[w.get('code') for w in d.get('lint',[])]} user_error={d.get('user_error')} log_id={d.get('log_id')}")
if d.get('okay') is not True: sys.exit(0)
# 2. check no duplicate
st,subs=call('GET','/submissions.json',auth=False)
dups=[s for s in (subs or {}).get('open',[]) if s.get('node_id')==NODE and s.get('kind') in ('proof','partial')]
if dups: log(f"open proof submissions already on node: {[s['pr_number'] for s in dups]}; not submitting"); sys.exit(0)
# 3. precheck
body={"node_id":NODE,"artifact_type":"proof","bundle":{PATH_:proof}}
while True:
    st,j=call('POST','/precheck',body)
    if st==202: break
    log(f"POST /precheck -> {st} {json.dumps(j)[:300]}")
    if st in (409,429,502) and now()<DEADLINE: time.sleep(600); continue
    sys.exit(0)
job=j['id']; log(f"POST /precheck -> 202 job {job}")
while True:
    time.sleep(60)
    st,r=call('GET',f'/precheck/{job}',auth=False)
    if r and r.get('state') in ('done','error'): break
json.dump(r,open(os.path.join(DIR,'precheck13.json'),'w'))
res=r.get('result') or {}
log(f"precheck {job}: state={r.get('state')} verdict={res.get('verdict')} first_failing_step={res.get('first_failing_step')} steps={[(s['step'],s['result']) for s in res.get('steps',[])]}")
if res.get('verdict')!='pass': sys.exit(0)
# 4. submit
sub={"node_id":NODE,"artifact_type":"proof","bundle":{PATH_:proof},"precheck_job_id":job,
     "tooling":{"model":"claude-opus-5-5","version":None,"harness":"Claude Code agent 402-C (HTTP path, Python colouring search + /check)"}}
st,s=call('POST','/submissions',sub)
json.dump(s,open(os.path.join(DIR,'submit13.json'),'w'))
log(f"POST /submissions -> {st} {json.dumps({k:(s or {}).get(k) for k in ('submission_id','pr_number','pr_url','rivals','node_proved','becomes','error','message')})[:600]}")
