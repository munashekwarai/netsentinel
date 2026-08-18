import json,typer
from . import core
app=typer.Typer()
@app.command()
def dns(host:str): print(json.dumps(core.dns(host).json()))
@app.command()
def port(host:str,port:int): print(json.dumps(core.tcp(host,port).json()))
@app.command()
def https(url:str): print(json.dumps(core.http(url).json()))
@app.command()
def check(host:str):
 r=[core.dns(host),core.tcp(host,443),core.tls(host)];print(json.dumps({"state":core.state(r),"checks":[x.json() for x in r]}))
if __name__=="__main__": app()
