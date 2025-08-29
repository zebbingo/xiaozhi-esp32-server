# Brownfield PRD – Protocol Upgrade to MQTT + UDP + WebRTC (Zebbingo)

**Owner:** @pm\
**Stakeholders:** Firmware (ESP32), Cloud/Backend, Mobile App, QA, Security/Compliance\
**Decision Date:** 2025-08-25\
**Status:** Draft

---

## 1) Background & Problem Statement

- Current transport: WebSocket between devices and server.
- Issues observed: production reliability (intermittent disconnects behind NATs, poor backpressure handling), higher battery and CPU usage, and suboptimal latency for streaming audio/control.
- Proposed change: move to **MQTT (signaling/control) + UDP (low-latency media/telemetry paths)**, and optionally support **WebRTC** for richer features and interoperability.
- Target devices: Zebbingo speakers (ESP32-based) and future figurine/NFC accessories.
- Compatibility: must operate with existing account/registration/OTA flows.

### Success Criteria (high level)

- P95 command round-trip (cloud → device → ack) ≤ **250 ms** on Wi‑Fi.
- P99 device reconnect time after network flap ≤ **2 s**.
- Streaming voice packets one-way device→server median latency ≤ **80 ms**; loss ≤ **1%** without perceptible impact (with FEC/retransmit strategy).
- 30‑day device online availability ≥ **99.5%**.

---

## 2) Goals & Non‑Goals

**Goals**

1. Robust pub/sub control plane with exactly‑once/at‑least‑once delivery semantics where required.
2. Low-latency, low-overhead data plane for audio frames and sensor telemetry.
3. Optional WebRTC support for direct app/browser/device integration.
4. Clear migration path and rollback.
5. Strong authN/authZ per device (topic ACLs), TLS/DTLS/SRTP, and audit logging.
6. Maintain OTA and remote configuration capabilities.

**Non‑Goals**

- Replacing existing TTS/ASR providers.
- Changing mobile app SDK network stack (beyond necessary topic subscriptions for parent dashboard).
- Introducing cellular/LPWAN transport in this phase.

---

## 3) Functional Requirements (FRs)

1. **FR1:** Devices must connect securely to the broker via MQTT with mTLS.
2. **FR2:** Devices must publish/subscribe to scoped topics (status, cmd, ack, cfg, ota, telemetry).
3. **FR3:** Device must support DTLS-PSK handshake and audio streaming over UDP.
4. **FR4:** WebRTC bridge must transcode Opus 16kHz→48kHz and forward audio to apps.
5. **FR5:** OTA updates must be announced via retained `/ota` topics and executed with checksum validation.
6. **FR6:** Device must send error reports on `/telemetry` with structured codes.
7. **FR7:** Parental dashboard must be updated with telemetry via backend integration.

---

## 4) Non‑Functional Requirements (NFRs)

1. **NFR1:** Latency — command RTT ≤250ms; audio one‑way ≤80ms.
2. **NFR2:** Reliability — 99.5% availability; reconnect ≤2s.
3. **NFR3:** Security — 100% of traffic encrypted with TLS/DTLS/SRTP.
4. **NFR4:** Scalability — support 10k concurrent devices; 1k talkers.
5. **NFR5:** Privacy — logs ≤90d; audio ≤14d opt‑in; PII scrubbing at ingest.
6. **NFR6:** Observability — metrics, logs, and traces exposed for all services.

---

## 5) Epics & User Stories

### Epic 1: Control Plane (MQTT)
- **Story 1.1:** As a device, I can establish a secure MQTT connection with mTLS so that I am uniquely identified.
- **Story 1.2:** As a backend service, I can send commands on `/cmd` with QoS1 so that devices reliably execute instructions.
- **Story 1.3:** As a device, I receive OTA manifest on `/ota` and update firmware with checksum verification.

### Epic 2: Data Plane (UDP)
- **Story 2.1:** As a device, I can initiate a DTLS-PSK session and stream Opus 16kHz audio frames.
- **Story 2.2:** As the UDP ingress, I can reorder, jitter‑buffer, and decode packets so that ASR receives clean audio.
- **Story 2.3:** As a device, I can handle network loss and reconnect within 2s.

### Epic 3: WebRTC Bridge
- **Story 3.1:** As a backend, I can transcode 16kHz Opus to 48kHz and forward via WebRTC for browser playback.
- **Story 3.2:** As an app user, I can connect over WebRTC with ICE/STUN/TURN and monitor device audio.

### Epic 4: Security & Compliance
- **Story 4.1:** As a device, I authenticate with a per-device cert so that only valid devices connect.
- **Story 4.2:** As a compliance officer, I can enforce data retention limits (logs 90d, audio 14d) so regulations are met.
- **Story 4.3:** As a parent, I can delete/export child data from dashboard to comply with GDPR/COPPA.

### Epic 5: Observability & Ops
- **Story 5.1:** As an SRE, I can see MQTT sessions, UDP packet loss, and WebRTC stats on Grafana dashboards.
- **Story 5.2:** As an SRE, I receive alerts when UDP loss >5% or ICE failures exceed 5%.
- **Story 5.3:** As a developer, I can trace a request from device→ASR→LLM→TTS with OTel.

---

## 6) Architecture Overview

### 3.1 Broker Choice

- **Managed Broker (Recommended):** **AWS IoT Core** for production.
  - **Why:** 99.9%+ SLA, elastic scaling, device identity/IAM, fine‑grained policies, device shadow, rules engine, multi‑AZ out of the box.
  - **Trade‑offs:** Per‑message billing; vendor lock‑in (mitigated by keeping topic schema portable and using an adapter service).
- **Staging/CI:** **EMQX** (self‑hosted, small 2–3 node cluster) with Prometheus/Grafana + Alertmanager.
- **Local Dev:** **Mosquitto** (single node), no auth locally; use the same topic schema.

**Decision:** **AWS IoT Core for production**, **EMQX** cluster for staging, **Mosquitto** for local dev.

**Topic & Policy Model (portable across brokers)**

```
<env>/<tenant>/<deviceId>/status
<env>/<tenant>/<deviceId>/cmd
<env>/<tenant>/<deviceId>/ack/<cmdId>
<env>/<tenant>/<deviceId>/cfg
<env>/<tenant>/<deviceId>/ota
<env>/<tenant>/<deviceId>/telemetry
```

### 3.2 Control Plane (MQTT/TCP+TLS)

- **Broker options:** AWS IoT Core (prod), EMQX (staging), Mosquitto (local).
- **Client library (device):** ESP‑IDF `esp-mqtt` with TLS 1.2+, mTLS.
- **QoS:** QoS1 for commands/config/OTA; QoS0 for ephemeral presence pings.
- **Retained messages:** last-will status and bootstrap configs (device shadow), with expirations.

### 3.3 Data Plane (UDP)

- **Use cases:** half‑duplex voice frames, wakeword/VAD events, real‑time metrics.
- **Transport:** UDP sockets from device to ingress gateway; DTLS-PSK for encryption.
- **Reliability:** sequence numbers + jitter buffer + optional FEC.
- **Backpressure:** gateway drops late packets; device adapts bitrate/frame size.

### 3.4 Data Plane (WebRTC – Optional)

- **Use cases:** richer interop with browsers/mobile apps, built-in NAT traversal.
- **Transport:** WebRTC peer connection (DTLS-SRTP).
- **Features:** adaptive jitter buffering, NACK/FEC, congestion control, ICE/STUN/TURN.
- **Gateway:** optional WebRTC bridge that converts ESP32 UDP packets to WebRTC RTP for app consumption (e.g., Pion or aiortc).

### 3.5 UDP Packet Format (v1)

```
| VER | TYPE | FLAGS | SEQ | TS | LEN | PAYLOAD |
VER=1; TYPE: 0=audio,1=vad,2=metric; TS=ms; LEN=bytes
```

- Codec: Opus 16 kHz mono, 20 ms frame.
- Encrypted with DTLS (PSK or cert).

**Sequencing & Jitter Buffer Rules**

- Drop late frames where `now - TS > 200 ms`.
- Reorder up to 50 ms window using `SEQ`.
- Conceal up to 2 consecutive losses; enable XOR‑FEC every 5 frames (optional).

**NAT Keepalive**

- Send 1‑byte keepalive (TYPE=2, LEN=0) every 25s when idle.

---

## 4) Security Mode Decision (ESP32)

### Chosen Approach (v1)

- **MQTT:** x.509 **mTLS** using per‑device certificates issued from our CA.
- **UDP:** **DTLS‑PSK** using ephemeral keys, rotated periodically.
- **WebRTC:** **DTLS-SRTP** with ICE/STUN/TURN.

**Why:** Strong identity and authorization on the control plane; lightweight UDP path for constrained devices; optional WebRTC path for rich clients and direct interoperability.

### PSK Lifecycle (UDP)

- Provision via MQTT `/cfg`, rotate every 7 days, revoke via new epoch.
- Store securely in NVS; drop expired PSKs.

### Certificate Profile (MQTT)

- RSA‑2048 or EC‑P256 device key; validity ≤ 3 years.
- CN/SubjectAltName = `thing-<deviceId>`; attach broker policy scoped to `<deviceId>`.

---

## 5) Detailed Requirements

- **Device bootstrap:** obtain broker endpoint, client cert, and UDP/WebRTC params.
- **Presence & health:** LWT retained message; heartbeat.
- **Command handling:** JSON commands via MQTT `/cmd` with acks.
- **Config management:** retained `/cfg` includes `udp_psk`, `webrtc_enabled`, `turn_servers`.
- **OTA:** announced via `/ota` with signed manifest URL.
- **Audio streaming:** UDP packets or WebRTC RTP.
- **Error reporting:** telemetry topic with structured errors.

---

## 6) Migration Plan

1. Implement firmware with MQTT/UDP (DTLS‑PSK) as the baseline.
2. Optionally add WebRTC bridge support for app interoperability.
3. Rollout in cohorts 1%→10%→25%→50%→100% with SLO gates.
4. Rollback via `/cfg` flag if severe issues.

---

## 7) Risks & Mitigations

- **NAT traversal/UDP blocking:** fallback to WebRTC (with TURN) or TCP over MQTT.
- **Packet loss under Wi‑Fi interference:** Opus FEC, adaptive jitter buffer.
- **ESP32 resource limits:** WebRTC only supported via gateway; not on device.
- **Security key leakage:** rotate device creds; remote wipe.

---

## 8) Test Plan

- **Unit:** topic ACLs, JSON schema validation, DTLS handshake, jitter buffer.
- **Integration:** device ↔ broker ↔ gateway (MQTT+UDP and WebRTC bridge).
- **Load:** 10k MQTT clients, 1k talkers.
- **Chaos:** Wi‑Fi loss, packet loss, broker failover.
- **Security:** mTLS negative tests, DTLS invalid PSK, WebRTC ICE edge cases.

---

## 9) Acceptance Criteria

- Success criteria in §1 met.
- OTA and remote commands work over MQTT.
- Audio streaming verified via UDP and WebRTC bridge.
- Audit logs complete.

---

## 10) Milestones & Ownership

- **M1 – Broker & UDP ingress ready (1.5 weeks)** Cloud/Backend
- **M2 – ESP32 client (MQTT + UDP + DTLS) (2 weeks)** Firmware
- **M3 – WebRTC bridge service (1 week)** Cloud/Backend
- **M4 – End‑to‑end staging tests (1 week)** QA
- **M5 – Canary rollout (2 weeks)** PM/DevOps

---

## 11) Monitoring & Observability

- **MQTT broker metrics**.
- **UDP ingress metrics** (packet rate, jitter).
- **WebRTC stats** (RTT, jitter, bitrate, loss).
- **Device telemetry dashboards**.

---

## 12) Resolved Decisions

- **Opus sampling:** Keep device encode at 16 kHz for CPU/battery efficiency; transcode to 48 kHz at WebRTC bridge for browser/app compatibility.
- **TURN deployment:** Start with single‑region coturn (APAC‑Singapore). Expand to multi‑region (US‑West, EU‑Central) once relay ratio >25% or ICE RTT >800 ms median.
- **Privacy defaults:** Recording off by default. Audio artifacts retained ≤14 days (opt‑in); logs/metrics ≤90 days; PII scrubbing at ingest; parental dashboard supports export/delete.
- **Broker choice:** AWS IoT Core for production; EMQX for staging; Mosquitto for local dev.

---

## 13) Appendix

- **Color/Brand:** Zebbingo Blue = Pantone 2905C.
- **Future:** BLE gateway mode; multicast LAN discovery; potential move to ESP32‑S3 or Linux SoC for native WebRTC.
