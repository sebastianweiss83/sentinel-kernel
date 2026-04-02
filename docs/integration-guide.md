# Integration Guide

This guide covers how to integrate Sentinel with any AI agent framework
or model provider. Every integration must preserve Sentinel's sovereignty
guarantees and work in all deployment contexts, including air-gapped.

---

## The pattern

Sentinel wraps any function that makes an AI decision using the
`@sentinel.trace` decorator:

```python
from sentinel import Sentinel

sentinel = Sentinel()

@sentinel.trace(policy="policies/your_policy.rego")
async def your_decision_function(input_context: dict) -> dict:
    # Your existing agent logic — completely unchanged
    result = await your_agent.run(input_context)
    return result
```

This is the universal pattern. It works with any framework, any model,
any stack. The decorator intercepts the call, evaluates the policy in-process,
records the trace, and passes through the result.

---

## Framework integrations

For frameworks that support middleware, observers, or lifecycle hooks,
Sentinel provides integration helpers that slot in without changes to
your agent logic.

### Writing an integration

An integration module lives in `sentinel/integrations/<name>/` and must:

1. **Implement the standard wrapper interface** — map the framework's
   middleware/observer/hook pattern to Sentinel's trace emission.
2. **Work offline** — no mandatory network calls, no external service
   dependencies in the critical path.
3. **Emit complete traces** — all mandatory schema fields must be populated.
4. **Document its sovereignty posture** — see checklist below.

### Integration module structure

```
sentinel/integrations/<name>/
    __init__.py        # Public API
    middleware.py      # Framework-specific middleware/observer/hook
    README.md          # Sovereignty posture documentation
```

### Test requirements

Every integration must include tests that verify:

1. **Trace emission** — a traced call produces a valid decision trace
   with all mandatory fields.
2. **Policy DENY** — when policy returns DENY, the trace records
   `policy_result: DENY` and the triggering rule.
3. **Override** — a human override produces a second linked trace entry;
   the original trace is not modified.
4. **Offline operation** — all tests pass with no network connectivity
   (mock or disable any network-dependent framework features).

Tests live in `tests/integrations/test_<name>.py`.

---

## Sovereignty checklist

**Every integration PR must answer these questions in the PR description:**

### 1. Does this framework send data to a third-party service at runtime?

If yes: document which service, its corporate jurisdiction, and whether
the call is mandatory or optional.

### 2. Does it work fully offline?

If no: document which features require network access. These features
must be clearly labelled as **not cleared for air-gapped deployment**.

### 3. Does it introduce a US-owned dependency in the critical path?

If yes: **stop**. A US-owned service or library in the trace emission
critical path creates CLOUD Act exposure. This cannot be in the critical
path. It may be offered as an optional, clearly-labelled integration.

### 4. Can the data residency assertion be independently verified?

The integration must not undermine Sentinel's `data_residency` and
`sovereign_scope` assertions. If the framework sends data to an external
service, the trace's sovereignty claims may be inaccurate.

---

## Air-gapped deployment labels

Integrations that require network access for any functionality must
include clear labelling:

```python
# In the integration's __init__.py or README:
SOVEREIGNTY_POSTURE = {
    "air_gapped_compatible": False,
    "network_dependencies": ["api.example.com — model inference"],
    "jurisdiction": "EU (example provider)",
    "note": "Model inference requires network. Traces are local."
}
```

---

## Example: minimal integration

```python
# sentinel/integrations/example/__init__.py
from sentinel import Sentinel

def create_example_middleware(sentinel: Sentinel, policy: str):
    """
    Wraps an example framework's agent calls with Sentinel tracing.
    Works offline. No external dependencies.
    """
    async def middleware(context, next_handler):
        @sentinel.trace(policy=policy)
        async def traced_call(ctx):
            return await next_handler(ctx)
        return await traced_call(context)
    return middleware
```

---

## Quickstart example requirements

Every integration should include a quickstart example in
`examples/<name>_quickstart.py` that:

- Is under 30 lines of code
- Uses local storage only (no cloud accounts, no API keys)
- Produces a visible trace output
- Can be run with `python examples/<name>_quickstart.py`

---

## Non-negotiables

- **No mandatory network call** in the trace emission path.
- **No breaking change** to the storage interface.
- **Sovereignty must be documentable** — if the integration cannot clearly
  state its data residency and jurisdiction posture, it is not ready.
