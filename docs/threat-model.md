# NetSentinel Threat Model

## Assets

- Monitoring definitions and internal service topology.
- Historical availability, latency, and diagnostic evidence.
- Integrity of health and alert decisions.
- Availability of the monitoring process and its network vantage point.

## Adversaries

An unauthenticated network client, a user allowed to view but not administer monitoring, a compromised monitored endpoint, and a malicious or mistaken operator are considered. Host-root compromise and physical attacks are outside the application boundary.

## Threats and mitigations

| Threat | Impact | Mitigation |
|---|---|---|
| SSRF through a configured target | Internal network scanning or metadata access | Treat check creation as administrative, loopback binding, deploy authorization and egress allowlists |
| Slow or unreachable destination | Worker exhaustion | Per-check timeout bounded to 30 seconds; bounded ICMP subprocess timeout |
| DNS rebinding or redirect | Destination changes after validation | Trusted operators only; restrict egress at the network boundary; record final HTTP URL |
| Crafted HTTP response | Memory or log pressure | Do not read or store response bodies; retain bounded headers and status only |
| SQL injection | Evidence corruption | Parameterized statements and structured JSON serialization |
| Alert suppression | Hidden outage | Persistent consecutive-failure state, history, and separation of check evidence from notification policy |
| Database theft | Topology and outage disclosure | Filesystem least privilege, encrypted host/backup storage, retention policy |
| ICMP command injection | Host command execution | Argument-array subprocess invocation with no shell and validated timeout |
| Forged TLS endpoint | False healthy state | Default CA validation, SNI, hostname verification, and certificate-expiry evidence |

## Residual risk

A trusted administrator can deliberately configure sensitive destinations. A single probe location cannot distinguish a globally unavailable service from a local path failure. SQLite and one scheduler are a single availability domain. Authentication, distributed consensus, notification delivery, and enterprise retention are intentionally deployment responsibilities.
