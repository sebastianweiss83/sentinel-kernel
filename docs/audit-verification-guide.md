# Audit verification guide

*For auditors who have received a Sentinel evidence pack and need to
verify it independently.*

## What you have

Typically three things, delivered by the deployment operator:

1. **An evidence-pack PDF** — self-contained, human-readable.
2. **An NDJSON trace export** (optional but common) — one JSON
   object per line, each representing an immutable decision record.
3. **A public verification key** (optional) — present only if the
   deployment used a persistent signer.

## Installing the verification tool

```bash
pipx install sentinel-kernel
sentinel --version        # confirm ≥ 3.2.0
```

Installation is offline-safe after the initial download; the
verification commands below make zero network calls.

## Verifying hash integrity

Load the NDJSON export into a scratch database, then recompute every
hash:

```bash
sentinel import --input evidence/traces.ndjson --db /tmp/verify.db
sentinel verify --all --db /tmp/verify.db
```

Expected output:

```
Verifying 1247 traces...
  inputs_hash     1247 matched, 0 failed
  output_hash     1247 matched, 0 failed
  schema_version  1247 ok
Result: 1247 verified, 0 failed.
```

Any non-zero failure count means the trace store was modified after
emission. Investigate.

## Verifying signatures (if present)

```bash
sentinel verify --all --db /tmp/verify.db --public-key signing.pub
```

Adds:

```
  signature      1247 matched, 0 failed
```

If the operator used the **ephemeral-per-process** signer (the default
when no `signer=` is passed to `Sentinel()`), this verification is
**not possible across process restarts**. That is by design — ephemeral
signing is useful inside a single process, not for long-term audit.
If the deployment needs verifiable long-term signatures, the operator
should have generated a persistent `ML-DSA-65` keypair.

## Verifying the pack manifest

The evidence pack's hash manifest (last page) carries a pack-level
digest computed over every included trace. Recompute:

```bash
sentinel export --db /tmp/verify.db --output /tmp/export.ndjson
sha256sum /tmp/export.ndjson
```

Compare the output with the "Pack digest" on the manifest page. If
the pack was built with a `--since`/`--until` window, use the same
window on export.

## Independent re-verification against source-of-truth

If the deployment kept raw inputs out-of-band (the v3.2.0+ default is
**not** to store them), you can prove that a given original payload
produced a given trace:

```python
from sentinel.core.trace import DecisionTrace
target_hash = DecisionTrace._hash({"application": original_payload})
# target_hash should equal the trace's inputs_hash
```

This is how Art. 22 explanations and Art. 15 accuracy-record reviews
hand over: the auditor gets the raw payload from the source-of-truth
store, hashes it with Sentinel's canonical function, and confirms the
hash matches the stored trace.

## Failure modes and what they mean

| Output | Meaning |
|---|---|
| `inputs_hash 42 failed` | The stored inputs were modified after the trace was written. Trace integrity compromised — investigate the write path and access controls on the trace store. |
| `signature 42 failed` | Either the signatures were produced by a different key than the `signing.pub` you were given, or the trace payload was modified. Ask the operator which key was active at the window under audit. |
| `schema_version 42 ok, 5 other` | Mixed schema versions. Sentinel is forward-compatible; verify the current release notes for the older schema version. |
| `PermissionError on /tmp/verify.db` | Your scratch directory is restricted; pass `--db ~/verify.db`. |

## What the pack does NOT prove

- It does not prove policy correctness. Sentinel records what the
  evaluator returned; the auditor may need to review the policy
  source and its version separately.
- It does not prove that organisational obligations (Art. 9 risk
  management, Art. 11 Annex IV, Art. 15 accuracy) are met. Those
  live in your client's governance documents.
- Unsigned packs do not prove producer authenticity. Ask for the
  signer configuration and the public key if authenticity matters.

## Questions to ask the operator

1. "Which version of Sentinel emitted these traces?" (check the
   `schema_version` field — 1.0.0 corresponds to v3.0.x+).
2. "Was a persistent signer configured during this window? If so,
   give us the public key."
3. "Were `store_inputs` and `store_outputs` enabled?" (affects
   whether raw-payload re-verification is possible).
4. "Did the kill switch engage at any point in this window?" (DENY
   traces with `kill_switch=engaged` tag show when).
5. "What is the retention policy?" (should match
   `.sentinel/config.json` retention entry).
