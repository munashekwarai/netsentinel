# Security Design

Trust boundaries exist at every CLI, HTTP, file, network, and synchronization input. Controls include bounded strings and payloads, allowlisted states, parameterized SQLite statements, timeouts for outbound operations, non-root containers where supplied, environment-based configuration, and minimal error disclosure. Operators must add TLS, authentication, authorization, retention, encrypted backups, and network policy appropriate to their environment.
