# NetSentinel

**Networking · Cybersecurity · Observability**

## Problem
Small organizations discover service failures through user complaints.

## Who This Helps
Schools, SMEs, startups, and small IT teams.

## Why It Matters
Delayed diagnosis increases downtime and makes separate DNS, TCP, HTTP, ICMP and TLS failures hard to distinguish.

## Constraints
The system must be inexpensive, inspectable, testable without paid services, conservative about claims, and safe with untrusted input. SQLite/local execution is the default; production deployments need deliberate persistence, identity, networking, and backup choices.

## Solution
A composable probe engine records timed results, derives health and alert state, and exposes CLI and REST interfaces.

## Architecture
```mermaid
flowchart LR
  Config[Check configuration] --> Scheduler[Probe scheduler]
  Scheduler --> DNS[DNS resolver]
  Scheduler --> TCP[TCP / ICMP probes]
  Scheduler --> Web[HTTP / HTTPS probe]
  Web --> TLS[TLS inspector]
  DNS & TCP & TLS --> Health[Health evaluator]
  Health --> History[(SQLite history)]
  Health --> Alerts[Failure threshold alerts]
  CLI[Typer CLI] --> Scheduler
  API[FastAPI] --> Scheduler
```
See [architecture](docs/architecture.md).

## Features
The repository implements its domain engine, validation, durable/local state where applicable, executable interfaces, meaningful tests, structured errors, and automation.

## Technology Stack
Python 3.11 provides a portable typed core; FastAPI provides OpenAPI-backed HTTP endpoints; Typer provides operator-friendly commands; SQLite provides a zero-service evidence store. CloudForge instead uses Terraform, Docker, NGINX, and shell-based verification.

## Setup
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```
Copy `.env.example` to `.env` only for local overrides; `.env` is ignored.

## Usage
```bash
python -m app.cli --help
uvicorn app.api:app --host 127.0.0.1 --port 8000
```
CloudForge users should follow `docs/deployment.md`.

## Testing
```bash
pytest -q
```
Tests exercise domain behavior and failure paths without paid infrastructure.

## Security
Inputs are bounded and validated, secrets are accepted through the environment rather than source, errors avoid sensitive internals, and CI runs tests. See [security](docs/security.md) and [threat model](docs/threat-model.md).

## Limitations
Checks observe endpoints from one vantage point; they do not replace distributed enterprise monitoring.

## Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md), add tests for behavior changes, and avoid real personal or secret data in fixtures.
