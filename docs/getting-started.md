# Getting started with Sentinel

Two minutes from install to your first auditor-grade decision record.

---

## 1. Install

```bash
# macOS (recommended — avoids PEP 668 "externally-managed-environment")
brew install pipx
pipx install sentinel-kernel
sentinel demo

# Linux / Docker / CI
pip install sentinel-kernel
sentinel demo

# Alternative (always works)
python3 -m pip install sentinel-kernel
python3 -m sentinel demo
```

`python3 -m sentinel` is equivalent to the `sentinel` entry point. Use it
whenever the bin directory is not on PATH.

Zero required dependencies. Works with Python 3.11 and 3.12.

---

## 2. Your first decision record

Create `first_trace.py`:

```python
from sentinel import Sentinel

sentinel = Sentinel()  # SQLite, no config, no network

@sentinel.trace
def approve(request: dict) -> dict:
    # your existing logic — completely unchanged
    return {"decision": "approved", "amount": request["amount"]}

result = approve({"amount": 5_000, "requester": "alice"})
print(result)

# Inspect the trace that was just written
traces = sentinel.query(limit=1)
print(traces[0].to_json())
```

Run it:

```bash
python first_trace.py
```

You just produced a tamper-resistant decision record with:

- a unique trace id (ULID-style)
- SHA-256 hash of the inputs (raw payload **not** stored by default —
  see [provability.md#privacy-by-default](provability.md#privacy-by-default-v320))
- ISO-8601 UTC timestamp
- wall-clock latency in milliseconds
- policy result (`NOT_EVALUATED` — you haven't attached a policy yet)
- jurisdictional metadata (`data_residency`, `sovereign_scope`,
  `schema_version`)

Stored locally. No network call. No cloud account. No API key.
GDPR Art. 25 by design: Sentinel records the proof, not the payload.

---

## 3. Add a policy

A decision record is more useful if the decision was evaluated
against a rule first. Start with a Python-callable policy:

```python
from sentinel import Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator

def approval_policy(inputs: dict) -> tuple[bool, str | None]:
    request = inputs.get("request", {})
    if request.get("amount", 0) > 10_000:
        return False, "amount_exceeds_cap"
    return True, None

sentinel = Sentinel(
    policy_evaluator=SimpleRuleEvaluator({
        "policies/approval.py": approval_policy,
    }),
)

@sentinel.trace(policy="policies/approval.py")
def approve(request: dict) -> dict:
    return {"decision": "approved"}

# Works under the cap
approve({"amount": 5_000})

# Blocked over the cap
from sentinel import PolicyDeniedError
try:
    approve({"amount": 50_000})
except PolicyDeniedError as exc:
    print(f"Blocked by policy: {exc}")
```

Every call produces a trace. The DENY trace records the rule name
(`amount_exceeds_cap`) so an auditor can reconstruct why the
decision was blocked.

For OPA / Rego policies, use `LocalRegoEvaluator`. See
[examples/04_policy_rego.py](../examples/04_policy_rego.py).

---

## 4. Add a kill switch (EU AI Act Art. 14)

EU AI Act Article 14 requires that humans can halt a high-risk AI
system. Sentinel ships a runtime kill switch — no restart required.

```python
from sentinel import KillSwitchEngaged, Sentinel

sentinel = Sentinel()

@sentinel.trace
def process(item: dict) -> dict:
    return {"processed": item["id"]}

# Normal operation
process({"id": 1})

# Human operator halts the system
sentinel.engage_kill_switch("Suspicious pattern detected — halt pending review")

try:
    process({"id": 2})
except KillSwitchEngaged as exc:
    # Wrapped function was NOT called.
    # A DENY trace with a HumanOverride entry was written.
    print(f"Halted: {exc}")

# Review complete, resume operation
sentinel.disengage_kill_switch("Review complete, cleared to resume")
process({"id": 3})  # works again
```

No restart. Thread-safe. Every blocked call is recorded with the
reason and timestamp for audit.

---

## 5. Check your EU AI Act posture

```bash
sentinel compliance check
```

Runs the automated EU AI Act checker and prints a per-article
status table. Honest about what's machine-checkable (Art. 9, 12,
13, 14, 17) and what needs organisational action (Art. 10, 11, 15).

For a shareable HTML version:

```bash
sentinel compliance check --html --output compliance.html
```

Open `compliance.html` in any browser. Self-contained, no CDN
references, safe to email.

---

## 6. Scan your dependency posture

```bash
sentinel scan
```

Inventories every installed Python package, every CI/CD configuration
file, and every Terraform / Kubernetes resource in the current
directory, then classifies each by parent-company jurisdiction.

Output (text):

```
RUNTIME  59 packages  score=100%  us_owned=0  unknown=5
CI/CD    2 files, 2 findings, us_controlled=2
INFRA    0 files, 0 findings, us_controlled=0
```

For a full provability report as HTML:

```bash
sentinel report --output provability.html
```

---

## 7. Declare your requirements in code

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    Required,
    AcknowledgedGap,
    Targeting,
)

class MyPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    airgap = Required()             # name "airgap" is checked by convention
    bsi_certification = Targeting(by="2026-Q4")

    # Honest acknowledged gap with a migration plan
    cicd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Forgejo (self-hosted)",
        by="2027-Q2",
        reason="No production-ready EU-operated CI alternative",
    )

report = MyPolicy().check()
print(report.as_text())
```

Acknowledged gaps are not violations — they are honest documented
positions with deadlines. They show up in every report separately
from unacknowledged gaps.

---

## Where to go next

- [docs/real-world-examples.md](real-world-examples.md) — industry scenarios
- [examples/](../examples/) — 13 runnable examples, progressive complexity
- [docs/schema.md](schema.md) — full trace schema reference
- [docs/eu-ai-act.md](eu-ai-act.md) — Art. 9 / 12 / 13 / 14 / 17 mapping
- [demo/](../demo/) — full Docker Compose stack with Grafana dashboard
