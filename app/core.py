from __future__ import annotations
import socket, ssl, subprocess, time, urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
@dataclass
class Result:
 check:str; target:str; healthy:bool; latency_ms:float; detail:dict
 def json(self): return asdict(self)
def _timed(kind,target,fn):
 start=time.perf_counter()
 try: detail=fn(); ok=True
 except Exception as e: detail={"error":type(e).__name__,"message":str(e)[:200]};ok=False
 return Result(kind,target,ok,round((time.perf_counter()-start)*1000,2),detail)
def dns(host): return _timed("dns",host,lambda:{"addresses":sorted({x[4][0] for x in socket.getaddrinfo(host,None)})})
def tcp(host,port,timeout=3):
 if not 1<=port<=65535: raise ValueError("port must be 1..65535")
 return _timed("tcp",f"{host}:{port}",lambda:(socket.create_connection((host,port),timeout).close() or {"port":port}))
def http(url,timeout=5):
 if urlparse(url).scheme not in {"http","https"}: raise ValueError("http(s) URL required")
 def go():
  with urllib.request.urlopen(url,timeout=timeout) as r: return {"status":r.status,"content_type":r.headers.get("content-type")}
 return _timed("http",url,go)
def tls(host,port=443,timeout=3):
 def go():
  ctx=ssl.create_default_context()
  with socket.create_connection((host,port),timeout) as raw:
   with ctx.wrap_socket(raw,server_hostname=host) as s:
    c=s.getpeercert();return {"issuer":dict(x[0] for x in c.get("issuer",())),"not_after":c.get("notAfter"),"sans":[v for k,v in c.get("subjectAltName",()) if k=="DNS"]}
 return _timed("tls",f"{host}:{port}",go)
def icmp(host,timeout=3):
 return _timed("icmp",host,lambda:{"reachable":subprocess.run(["ping","-c","1","-W",str(timeout),host],capture_output=True,timeout=timeout+1).returncode==0})
def state(results):
 failures=sum(not r.healthy for r in results)
 return "HEALTHY" if failures==0 else ("DEGRADED" if failures<len(results) else "DOWN")

class History:
 def __init__(self,path=":memory:"):
  import sqlite3
  self.db=sqlite3.connect(path);self.db.execute("create table if not exists results(id integer primary key, target text, check_type text, healthy integer, latency_ms real, detail text, checked_at text)")
 def record(self,result):
  import json
  self.db.execute("insert into results(target,check_type,healthy,latency_ms,detail,checked_at) values(?,?,?,?,?,?)",(result.target,result.check,int(result.healthy),result.latency_ms,json.dumps(result.detail),datetime.now(timezone.utc).isoformat()));self.db.commit()
 def uptime(self,target,limit=100):
  rows=self.db.execute("select healthy from results where target=? order by id desc limit ?",(target,limit)).fetchall()
  return round(sum(x[0] for x in rows)/len(rows)*100,2) if rows else None
class AlertTracker:
 def __init__(self,failure_threshold=3):self.threshold=failure_threshold;self.failures={}
 def observe(self,result):
  count=0 if result.healthy else self.failures.get(result.target,0)+1;self.failures[result.target]=count
  return "ALERT" if count>=self.threshold else ("WARNING" if count else "OK")
