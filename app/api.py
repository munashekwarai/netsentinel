from fastapi import FastAPI
from .core import dns,tcp,http,tls
app=FastAPI(title="NetSentinel")
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/checks/dns/{host}")
def check_dns(host:str): return dns(host).json()
@app.get("/checks/tcp/{host}/{port}")
def check_tcp(host:str,port:int): return tcp(host,port).json()
