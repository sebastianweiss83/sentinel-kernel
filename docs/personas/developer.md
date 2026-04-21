# For developers

You're here because you need a working audit trail for an AI decision
function — and you don't want to stand up a SaaS, an API key, or a
cloud account to get one. Fine. Five commands, no accounts, and you're
running.

## 90 seconds to your first trace

```bash
pipx install 'sentinel-kernel[pdf]'
sentinel quickstart
python hello_sentinel.py
sentinel audit-gap
```

That's a real trace store (SQLite at `./.sentinel/traces.db`), a real
hash-only decision record per call, and a real readiness score you can
re-run every time you change something.

## Wrap your own agent

```python
from sentinel import Sentinel

sentinel = Sentinel()        # privacy-by-default, SQLite, zero config

@sentinel.trace
def approve(request: dict) -> dict:
    # your existing logic — unchanged
    return {"decision": "approved", "amount": request["amount"]}

approve({"amount": 5_000, "requester": "alice"})
```

One line on top of whatever function makes the decision. Sync or async.
LLM, ML classifier, rule engine, robotic control — Sentinel doesn't
care what decides. It records that the decision happened, what policy
ran, and what hashed inputs produced what hashed output.

## When you want raw payloads

Default is hash-only (GDPR Art. 25 by design). When you have legal
basis and controlled access, opt in explicitly:

```python
sentinel = Sentinel(store_inputs=True, store_outputs=True)
```

See the honest reasoning: [docs/provability.md](../provability.md) and
[docs/explainability-art-22.md](../explainability-art-22.md).

## Framework integrations

| Framework     | Import                                                                           | Extra          |
|---------------|----------------------------------------------------------------------------------|----------------|
| LangChain     | `from sentinel.integrations.langchain import SentinelCallbackHandler`            | `[langchain]`  |
| CrewAI        | `from sentinel.integrations.crewai import SentinelCrewCallback`                  | `[crewai]`     |
| AutoGen       | `from sentinel.integrations.autogen import SentinelAutoGenHook`                  | `[autogen]`    |
| Haystack      | `from sentinel.integrations.haystack import SentinelHaystackCallback`            | `[haystack]`   |
| OpenTelemetry | `from sentinel.integrations.otel import OTelExporter`                            | `[otel]`       |
| LangFuse      | `from sentinel.integrations.langfuse import LangFuseEnricher`                    | `[langfuse]`   |
| Prometheus    | `from sentinel.integrations.prometheus import PrometheusExporter`                | `[prometheus]` |
| FastAPI       | `from sentinel.integrations.fastapi import SentinelMiddleware`                   | `[fastapi]`    |
| Django        | `from sentinel.integrations.django import SentinelMiddleware`                    | `[django]`     |
| Jupyter       | `from sentinel.integrations.jupyter import SentinelWidget`                       | `[jupyter]`    |

Detail: [docs/integration-guide.md](../integration-guide.md). Every
class name above is a real, imported symbol in v3.4 — each table row
is copy-paste safe.

## Debug / day-to-day commands

```bash
sentinel status                    # decision activity + readiness, one screen
sentinel demo --no-kill-switch     # narrative defence-logistics walk
sentinel scan                      # dependency + CI/CD sovereignty
sentinel export --output out.ndjson
sentinel verify --all              # recompute hashes for every stored trace
```

## Breaking change — v3.2.0 privacy default

v3.1.0 defaulted to `store_inputs=True`. v3.2.0 defaults to `False`.
If you upgrade without changing config, your *new* traces will hold
hashes only — your *existing* traces are unaffected. Full migration
note: [docs/migration-v3.2.md](../migration-v3.2.md).

## Next

- Your `sentinel audit-gap` score < 80 %? Run `sentinel fix kill-switch`
  and `sentinel fix retention --days 2555`. Score moves. That's the
  point.
- Ready for an auditor? `sentinel evidence-pack --output audit.pdf`.
- Need deployment help? Open a
  [pilot enquiry on GitHub](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md).
