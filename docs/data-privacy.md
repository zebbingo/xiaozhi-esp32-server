# Data Privacy and GDPR Support

This project now includes optional GDPR features. When enabled, users can
request their stored data or request deletion through new HTTP endpoints.

## Endpoints

- `GET /privacy/data` – Retrieve current conversation logs and memory files.
- `PUT /privacy/data` – Replace stored memory with the provided request body.
- `DELETE /privacy/data` – Remove conversation logs and memory files.

These endpoints return `403` if GDPR features are disabled in `config.yaml`.

## Retention Policy

The `gdpr.retention_days` setting defines how long data is stored. When the
server starts, any log or memory files older than this limit are purged
automatically.

## Enabling

Edit `data/.config.yaml` or `config.yaml` and set:

```yaml
gdpr:
  enabled: true
  retention_days: 30
```

This enables GDPR endpoints and sets the retention period to 30 days.
