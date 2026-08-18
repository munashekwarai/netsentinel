# NetSentinel Security Design

## Trust boundaries

The CLI and REST API accept destinations that cause outbound DNS, socket, HTTP, TLS, or operating-system ICMP activity. A caller who may define checks can therefore make NetSentinel contact addresses reachable from its network. Check creation is an administrative capability, not a public endpoint.

## Controls implemented

- Target, name, timeout, status, threshold, and port values have explicit bounds.
- TCP, HTTP, TLS, and ICMP operations use finite timeouts.
- HTTP checks accept only absolute `http` or `https` URLs.
- TLS uses the platform trust store, SNI, and hostname verification.
- Database statements are parameterized and result details are JSON encoded.
- Probe errors are converted to bounded evidence; raw tracebacks are not API responses.
- Compose exposes the API on loopback, runs as a non-root user, uses a read-only filesystem, and enables `no-new-privileges`.
- Structured logs exclude configuration secrets and response bodies.

## Deployment requirements

The reference API has no built-in identity layer. Keep it on a trusted management network or place it behind an authenticating reverse proxy with authorization and request limits. Restrict container egress when checks should reach only approved subnets. Protect the SQLite volume as operational data because targets, failure times, and topology can be sensitive. Do not put credentials in monitored URLs.

## Operational safeguards

Review new destinations, set retention and backup policy, monitor the monitor itself, and test alert thresholds against planned failures. Use separate NetSentinel instances or egress policies when customers or security zones must not share a monitoring vantage point.
