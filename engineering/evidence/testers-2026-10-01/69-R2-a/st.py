import json,sys,urllib.request
r=json.load(urllib.request.urlopen('https://api.openproofnetwork.org/submissions/'+sys.argv[1]))
pr=r.get('pull_request') or {}
print(pr.get('state'),'merged',pr.get('merged'),'waiting_on',pr.get('waiting_on'),[(x['name'],x['status'],x['conclusion']) for x in pr.get('runs',[])])
if r.get('gate_verdict'): print(json.dumps(r['gate_verdict'],indent=1)[:2500])
