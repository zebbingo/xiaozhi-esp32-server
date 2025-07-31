# Security Overview

This project now supports HTTPS and WSS with optional SSL certificates. Token-based authentication is enforced for WebSocket connections and all HTTP endpoints. A simple rate limiting middleware has been added to mitigate abuse.

## Enabling TLS
Configure the `server.ssl` section in `config.yaml` and provide valid `certfile` and `keyfile` paths. When enabled, the server will start on HTTPS/WSS.

## Authentication
Set `server.auth.enabled` to `true` and configure allowed tokens. All endpoints require a `Bearer` token in the `Authorization` header.

## Rate Limiting
Rate limiting parameters are defined under `server.rate_limit`. Suspicious activities such as rate limit violations and failed authentications are logged to `tmp/server.log`.
