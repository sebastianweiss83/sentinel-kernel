# Sentinel Demo Environment

Spin up the full sovereignty platform — decision kernel, OTel collector,
Prometheus, Grafana, self-hosted LangFuse, and a realistic demo application —
with one command.

## Run in three commands

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel/demo
docker compose up --build
```

Then open:

- **http://localhost:3001** — Grafana (user: `admin`, pass: `sentinel`)
  Pre-provisioned "Sentinel Sovereignty" dashboard.
- **http://localhost:3000** — LangFuse (self-hosted, EU-sovereign)
- **http://localhost:9090** — Prometheus

The `sentinel-demo` service runs `demo_app.py` automatically. Watch its logs
with `docker compose logs -f sentinel-demo`.

## What you'll see

`demo_app.py` runs three scenarios back to back:

### Scenario A — Autonomous procurement approval (EU AI Act Art. 9 + 14)

A policy evaluator blocks procurement requests over €50 000. The demo
processes a batch of four requests, then engages the kill switch mid-run
to demonstrate Art. 14 human oversight. Every blocked call is recorded
as a DENY trace with a linked `HumanOverride`.

### Scenario B — LangChain-style document analysis (mocked LLM)

A realistic wrapper around a (mocked) document classifier. The Sentinel
trace layer records every decision without touching the agent logic.
No API keys required.

### Scenario C — Sovereignty + EU AI Act report

Runs `RuntimeScanner`, `CICDScanner`, `InfrastructureScanner` and builds
a `DefenceContractor` manifesto report. Writes:

- `demo-output/sovereignty_report.html` — self-contained HTML report
- `demo-output/manifesto.json` — machine-readable manifesto state
- `demo-output/sentinel-demo.db` — the SQLite trace database

## Air-gapped mode

```bash
docker compose --profile airgap up
```

Runs without external network egress. `maybe_wire_otel()` in the demo
app will log a warning and continue — local storage and the audit
trail are always written first, regardless of OTel reachability.

## Ports

| Service         | Port | Notes                              |
|-----------------|------|------------------------------------|
| LangFuse        | 3000 | Self-hosted LangFuse UI            |
| Grafana         | 3001 | Sovereignty dashboard              |
| OTLP gRPC       | 4317 | OTel collector                     |
| OTLP HTTP       | 4318 | OTel collector                     |
| Prometheus      | 9090 | Metrics                            |
| OTel Prometheus | 8889 | Scrape target for collector        |

## Sovereignty notes

- **Grafana, Prometheus, OpenTelemetry collector** are CNCF / Grafana Labs
  open source and run entirely inside your network — no vendor phone-home.
- **LangFuse** is Berlin-based and self-hostable. The demo uses a local
  PostgreSQL volume; no LangFuse Cloud connection is made.
- **Base images** are pulled from Docker Hub (US-hosted) in this demo.
  For a fully sovereign deployment, mirror these images to an
  EU-sovereign registry such as Harbor or GitLab Container Registry.

The demo is a convenience for evaluation, not a production-ready
sovereign deployment. See `docs/bsi-profile.md` for the production
path to v1.0.
