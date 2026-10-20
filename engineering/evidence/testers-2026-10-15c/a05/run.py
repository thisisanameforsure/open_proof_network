import json, subprocess, time, sys, os
D=os.path.dirname(os.path.abspath(__file__)); S="/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/85614363-b225-4c5e-8f33-6eebe144b2d6/scratchpad/a05"
LOG=open(D+"/run.log","a")
def log(m): LOG.write(time.strftime("%H:%M:%SZ ",time.gmtime())+m+"\n"); LOG.flush()
def call(tool,args):
    for i in range(6):
        try:
            p=subprocess.run(["python3",D+"/mcp.py",tool,json.dumps(args)],capture_output=True,text=True,timeout=120)
            return json.loads(p.stdout)
        except Exception as e: log(f"{tool} retry {i}: {type(e).__name__}")
    raise SystemExit("gave up "+tool)
def poll(job):
    while True:
        r=call("get_precheck",{"job_id":job}); b=r.get("body",r)
        if b.get("state") in ("done","error"): return b
        time.sleep(15)
NODE="erdos-1094--h2--h1--h1--h1"
if not os.path.exists(S+"/token"):
    tj=json.load(open(S+"/tutjob2.json"))["body"]
    b=poll(tj["id"]); log("tutorial "+str(b.get("state"))+" "+str((b.get("result") or {}).get("verdict")))
    dco=json.load(open(S+"/dco.json"))["version"] if "version" in json.load(open(S+"/dco.json")) else json.load(open(S+"/dco.json"))["body"]["version"]
    r=call("get_token",{"proof":{"kind":"tutorial","job_id":tj["id"],"nonce":tj["nonce"]},"pseudonym":"t1015c-a05","dco":{"accepted":True,"version":dco}})
    rb=r.get("body",r); tok=rb.get("token")
    if not tok: log("token failed "+json.dumps(r)[:500]); sys.exit(1)
    open(S+"/token","w").write(tok); log("token ok "+json.dumps(rb.get("identity")))
r=call("claim_node",{"node_id":NODE}); log("claim "+json.dumps(r)[:400])
ts=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())
path=f"targets/erdos-1094/nodes/{NODE}/attempts/{ts}-t1015c-a05-partial.lean"
bundle={path:open(D+"/partial.lean").read()}
json.dump(bundle,open(D+"/bundle.json","w"))
r=call("precheck_submission",{"node_id":NODE,"bundle":bundle}); b=r.get("body",r); job=b.get("id"); log("precheck job "+str(job)+" "+json.dumps(r)[:300])
b=poll(job); res=b.get("result") or {}; log("precheck "+str(b.get("state"))+" verdict "+str(res.get("verdict"))+" first_fail "+str(res.get("first_failing_step")))
json.dump(b,open(D+"/precheck.json","w"))
if res.get("verdict")!="pass": sys.exit(1)
r=call("submit_proof",{"node_id":NODE,"artifact_type":"partial","bundle":bundle,"precheck_job_id":job,"automation":{"method":"agent","models":["claude-opus-5-5"],"framework":"Claude Code"}})
log("submit "+json.dumps(r)[:800])
