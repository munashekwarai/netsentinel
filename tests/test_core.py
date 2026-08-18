from app import core
def test_dns_localhost():
 r=core.dns("localhost");assert r.healthy and r.detail["addresses"]
def test_bad_port():
 try: core.tcp("localhost",0)
 except ValueError: pass
 else: raise AssertionError("invalid port accepted")
def test_state(): assert core.state([core.Result("x","x",True,1,{})])=="HEALTHY"
def test_history_and_repeated_failure_alert():
 h=core.History();r=core.Result("tcp","host:1",False,2,{})
 for _ in range(2):h.record(r)
 assert h.uptime("host:1")==0
 a=core.AlertTracker(2);assert a.observe(r)=="WARNING" and a.observe(r)=="ALERT"
