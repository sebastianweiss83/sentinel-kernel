# Migrating to v3.2.0

*Applies to users upgrading from v3.1.x.*

## The one change that matters

`Sentinel()` now defaults to **hash-only storage**. Raw input and output
payloads are no longer persisted unless you opt in explicitly.

| | v3.1.x default | v3.2.0+ default |
|---|---|---|
| `store_inputs` | `True` | **`False`** |
| `store_outputs` | `True` | **`False`** |
| `inputs_hash` | always populated | always populated |
| `output_hash` | always populated | always populated |

Your *existing* trace records are untouched. The change applies only
to traces written **after** the upgrade.

## If you relied on raw-payload storage

Add the two flags explicitly:

```python
from sentinel import Sentinel

sentinel = Sentinel(
    store_inputs=True,
    store_outputs=True,
)
```

Preserve the v3.1 behaviour exactly. Only enable this when you have
a legal basis (GDPR Art. 6/9) and controlled access to the trace
store. The rationale is in
[docs/provability.md#privacy-by-default-v320](provability.md#privacy-by-default-v320).

## If you're fine with hash-only

Nothing to change. Your upgraded kernel will:

- still compute `inputs_hash` and `output_hash` from the real payloads
  (the redaction happens at the storage boundary, not before hashing);
- still emit every policy result, kill-switch event, and sovereignty
  field as before;
- satisfy EU AI Act Art. 12 proof-of-logging unchanged.

Your auditors see hashes; your regulator sees proof; your database
stops being a GDPR Art. 25 liability.

## If you're building GDPR Art. 22 explanations

Hash-only storage means Sentinel cannot reconstruct "why was this
customer declined?" from its own trace store. Three options:

1. **Use `store_outputs=True`** for the decision path that needs
   explainability. Hash-only stays the default everywhere else.
2. **Keep a separate, access-controlled explanation store** and
   reference it from the trace's `tags` field by key.
3. **Regenerate the explanation on demand** by re-running the model
   on the stored inputs — requires `store_inputs=True`.

Pattern: [docs/explainability-art-22.md](explainability-art-22.md).

## Concrete upgrade checklist

1. `pip install --upgrade sentinel-kernel` (or `pipx upgrade sentinel-kernel`).
2. Run your existing test suite. Any test that asserts on
   `trace.inputs == {...}` or `trace.output == {...}` will fail
   unless the fixture passes `store_inputs=True` / `store_outputs=True`.
3. Decide, per use case, whether hash-only is right. Most production
   deployments: yes. Debugging-heavy development instances: add the
   flags back.
4. Re-run `sentinel audit-gap`. Score is unchanged by this upgrade;
   the gap categories remain the same.

## What this does NOT change

- The trace schema version (`schema_version` remains `1.0.0`).
- The storage backends, NDJSON export format, or attestation model.
- The kill-switch semantics, policy-evaluator contract, or integration
  APIs.
- Any previously-written traces on disk.

Backward-compatibility in the narrow sense — the function signature
(`store_inputs: bool = False`) is source-compatible; only the default
value changed. Any caller that passed either flag explicitly in v3.1.x
keeps its exact behaviour in v3.2.0.

## Why this is a minor-version bump

This is a breaking *default-behaviour* change. Strictly semver-purist
readings would require a 4.0.0 bump. We chose 3.2.0 for two reasons:

1. The stored trace format is unchanged. Traces written under v3.1.x
   remain readable by v3.2.0 verbatim.
2. The API surface is unchanged. No signature was removed or renamed.

We accept the critique that this is a grey zone. A one-time
`UserWarning` fires on first import under v3.2.0 if it detects a
pre-v3.2 trace DB in the default location without explicit flags,
precisely so the change is visible at upgrade time.

If this is unacceptable for your setup, pin v3.1.x:
`pip install 'sentinel-kernel>=3.1,<3.2'`.
