import json,urllib.request,time,sys
A="https://api.openproofnetwork.org"
def req(m,p,b=None):
    for i in range(3):
        try:
            r=urllib.request.Request(A+p,data=json.dumps(b).encode() if b else None,method=m,headers={"Content-Type":"application/json"})
            return json.loads(urllib.request.urlopen(r,timeout=120).read())
        except urllib.error.HTTPError as e: print(e.code,e.read()[:500]); raise
        except Exception as e: print("retry",e)
C=sys.argv[1]
pf="targets/tutorial/nodes/tutorial-and-swap/Proof.lean"
j=req("POST","/precheck",{"node_id":"tutorial-and-swap","bundle":{pf:open(C+"/"+pf).read()}})
job,nonce=j["id"],j["nonce"]; print("job",job)
while True:
    s=req("GET","/precheck/"+job)
    if s["state"] in("done","error"): break
    time.sleep(10)
print(s["state"],s.get("result",{}).get("verdict"))
v=req("GET","/dco.json")["version"]
t=req("POST","/tokens",{"proof":{"kind":"tutorial","job_id":job,"nonce":nonce},"pseudonym":"t1015c-a13","dco":{"version":v,"accepted":True}})
open("token","w").write(t["token"]); print("identity",t["identity"]["pseudonym"])
