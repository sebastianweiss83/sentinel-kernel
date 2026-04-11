# Integration guide

Sentinel wraps any function that makes an AI decision. The pattern is the same regardless of framework or model.

## The universal pattern

```python
@sentinel.trace
async def your_decision_function(input_context):
    # your existing logic — completely unchanged
    return await your_model_or_agent.run(input_context)
```

For synchronous functions:

```python
@sentinel.trace
def your_sync_decision(input_context):
    return your_model.predict(input_context)
```

## Context manager (for finer control)

```python
async with sentinel.span("procurement_decision") as span:
    result = await agent.run(context)
    span.set_output(result)
```

## Sovereignty checklist for every integration

Before any integration PR is merged, the author must document:

1. **Does this framework send data to a third-party service at runtime?**
   If yes: which service? What jurisdiction is the parent company?

2. **Does this framework work in a network-isolated environment?**
   If no: mark as `NOT CLEARED FOR AIR-GAPPED DEPLOYMENT` in the integration docs.

3. **Does this framework introduce a US CLOUD Act dependency in the critical path?**
   If yes: the integration must not be in the default import path. It must be explicitly opted into.

## Five mandatory tests per integration

Every integration PR must include:

1. Happy path — trace emitted, fields correct
2. Offline — local storage, zero network calls
3. Policy DENY — execution blocked, DENY recorded with rule name
4. Override — second linked trace entry, original untouched
5. EU AI Act fields — all mandatory fields present and non-null

## Planned integrations

| Framework | Status | Notes |
|---|---|---|
| LangChain callback handler | v0.3 | Wraps any LangChain agent or chain |
| LangGraph | v0.3 | State machine agents |
| OpenTelemetry export | v0.3 | Complements LangFuse and Grafana |
| AutoGen | v0.4 | Multi-agent coordination |
