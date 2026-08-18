# Deployment

Create an isolated runtime, install pinned dependencies from the project metadata, configure environment values outside version control, run tests, then start the documented service behind a TLS reverse proxy. Restrict the listener and database to required principals, collect structured logs, monitor health, and test encrypted backup restoration before relying on the service. Roll back by deploying the preceding immutable revision and restoring only schema-compatible data.
