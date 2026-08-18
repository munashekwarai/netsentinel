# NetSentinel Deployment

## Local service

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
NETSENTINEL_DB=./data/netsentinel.db uvicorn app.api:app --host 127.0.0.1 --port 8000
```

## Container

```bash
docker compose build
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

Compose binds only to loopback, stores SQLite in a named volume, uses a read-only root filesystem, and runs the image as UID 10001. Put an authenticated TLS reverse proxy in front of the service before allowing remote access.

## Continuous worker

The CLI can act as the scheduler independently of the API:

```bash
netsentinel watch /etc/netsentinel/checks.json \
  --database /var/lib/netsentinel/netsentinel.db \
  --interval 60
```

Run it under systemd or another supervisor with restart limits, a dedicated user, write access only to its database directory, and network access only to monitored destinations.

## Backup and recovery

Stop writers or use SQLite's online backup facility, encrypt the copy, and test restoration. Check definitions can be recreated from reviewed JSON configuration, while result history is operational evidence with a retention policy. Restore into the same application release, start the API, call `/health`, then execute a non-critical check.

## Rollback

Deploy the preceding immutable image. This release creates tables and indexes idempotently and performs no destructive migration. Back up the database before every upgrade and avoid rolling two versions against the same SQLite file.
