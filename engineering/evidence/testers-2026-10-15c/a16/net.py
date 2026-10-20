import json,urllib.request,time
def req(url,data=None,headers=None,tries=4):
    for i in range(tries):
        try:
            r=urllib.request.Request(url,data=data,headers=headers or {})
            return json.loads(urllib.request.urlopen(r,timeout=90).read())
        except urllib.error.HTTPError as e:
            return {"http_error":e.code,"body":e.read().decode()}
        except Exception as e:
            print("retry",i,e); time.sleep(3)
